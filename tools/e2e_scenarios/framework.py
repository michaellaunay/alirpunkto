"""Scenario framework: browser journeys that produce the user manual.

Each scenario is a numbered sequence of steps against the local test
stack; every step captures the screen and records a bilingual
caption. The output — screenshots plus ``manifest.json`` — is the
single source ``tools/generate_user_manual.py`` builds the fr/en
manual from. Deterministic journeys, reproducible screenshots: the
documentation regenerates itself on every green CI run.
"""

import json
import os
import re
import subprocess  # nosec B404 — fixed argv, no shell (see fetch_email)
import tempfile
import time

SHOT_DIR = os.environ.get(
    "E2E_SHOT_DIR", os.path.join(tempfile.gettempdir(), "e2e-shots"))

#: words the challenge generator emits, per language (the e-mail
#: template's own language may differ from the operand language —
#: the bench showed an Esperanto template carrying English words)
_NUMBER_WORDS = {
    "en": ["zero", "one", "two", "three", "four", "five", "six",
           "seven", "eight", "nine"],
    "fr": ["zéro", "un", "deux", "trois", "quatre", "cinq", "six",
           "sept", "huit", "neuf"],
    "eo": ["nulo", "unu", "du", "tri", "kvar", "kvin", "ses",
           "sep", "ok", "naŭ"],
}
_WORD_TO_NUMBER = {
    word: value
    for words in _NUMBER_WORDS.values()
    for value, word in enumerate(words)
}


def solve_math_challenge(text: str, lang: str = None) -> int:
    """Solve one challenge line: num1 * num2 + num3.

    The structure is fixed by generate_math_challenges; only the
    words vary with the candidate's language, and the surrounding
    operator words vary with the catalog ("times" is rendered
    "multiplied by" in the real English template). So the parser
    does not match operators at all: it extracts the first three
    number words of the line, whatever the language."""
    numbers = [
        _WORD_TO_NUMBER[token]
        for token in re.findall(r"[\w\u00c0-\u017f]+", text.lower())
        if token in _WORD_TO_NUMBER
    ]
    if len(numbers) < 3:
        raise ValueError(f"fewer than three number words in: {text!r}")
    a, b, c = numbers[:3]
    return a * b + c


def solve_all_challenges(body: str, lang: str = None) -> dict:
    """Extract and solve the four labelled challenges of the e-mail.

    A challenge line is any line naming the label (A-D) as a lone
    word and carrying at least three number words — this survives
    template languages ("A: ..." as much as "Operacio A estas ...").
    Returns {'A': int, 'B': int, 'C': int, 'D': int}."""
    solutions = {}
    for line in body.splitlines():
        for label in ("A", "B", "C", "D"):
            if label in solutions:
                continue
            if re.search(r"\b" + label + r"\b", line):
                try:
                    solutions[label] = solve_math_challenge(line)
                except ValueError:
                    continue
    missing = [l for l in ("A", "B", "C", "D") if l not in solutions]
    if missing:
        raise ValueError(f"challenges not found in the e-mail: {missing}")
    return solutions


def fetch_email(recipient: str, timeout: int = 60) -> str:
    """Return the decoded body of the newest e-mail for ``recipient``.

    The transport is pluggable through E2E_MAIL_CMD (a shell command
    printing the raw mailbox); the default reads the test stack's
    postfix container mailboxes. Retries until ``timeout``."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    command = os.environ.get(
        "E2E_MAIL_CMD",
        f"docker compose --env-file {root}/docker/.env.test "
        f"-f {root}/docker/test-docker-compose.yaml exec -T postfix "
        "sh -c 'cat /var/mail/catchall 2>/dev/null'",
    )
    deadline = time.time() + timeout
    last = ""
    attempts = 0
    while time.time() < deadline:
        result = subprocess.run(  # nosec B602 — operator-provided command
            command, shell=True, capture_output=True, text=True
        )
        if result.returncode != 0 and attempts == 0:
            print(f"[fetch_email] command failed (rc={result.returncode}): "
                  f"{result.stderr.strip()[:200]}")
        attempts += 1
        raw = result.stdout
        if recipient.split("@")[0] in raw:
            import email as email_lib
            import email.policy
            # last message in an mbox: split on the From_ separators
            chunks = re.split(r"(?m)^From ", raw)
            for chunk in reversed(chunks):
                if recipient.split("@")[0] not in chunk:
                    continue
                msg = email_lib.message_from_string(
                    "From " + chunk, policy=email.policy.default)
                body = msg.get_body(preferencelist=("plain", "html"))
                if body is not None:
                    return body.get_content()
            last = raw
        time.sleep(3)
    raise TimeoutError(
        f"no e-mail for {recipient} within {timeout}s (last mailbox "
        f"size: {len(last)})")


class Scenario:
    """Collects captures and bilingual captions for one journey."""

    def __init__(self, slug: str, title_fr: str, title_en: str):
        self.slug = slug
        self.title_fr = title_fr
        self.title_en = title_en
        self.steps = []
        os.makedirs(SHOT_DIR, exist_ok=True)

    def step(self, page, slug: str, fr: str, en: str) -> None:
        index = len(self.steps) + 1
        filename = f"{self.slug}_{index:02d}_{slug}.png"
        page.screenshot(path=os.path.join(SHOT_DIR, filename),
                        full_page=True)
        self.steps.append(
            {"index": index, "file": filename, "fr": fr, "en": en})
        print(f"[scenario:{self.slug}] {index:02d} {slug}")

    def close(self) -> None:
        manifest_path = os.path.join(SHOT_DIR, "manifest.json")
        manifest = {"scenarios": []}
        if os.path.exists(manifest_path):
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
        manifest["scenarios"] = [
            s for s in manifest["scenarios"] if s["slug"] != self.slug
        ] + [{
            "slug": self.slug, "title_fr": self.title_fr,
            "title_en": self.title_en, "steps": self.steps,
        }]
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=1)
