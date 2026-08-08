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

#: words the challenge generator emits, per language
_NUMBER_WORDS = {
    "en": ["zero", "one", "two", "three", "four", "five", "six",
           "seven", "eight", "nine"],
    "fr": ["zéro", "un", "deux", "trois", "quatre", "cinq", "six",
           "sept", "huit", "neuf"],
}
_OPERATORS = {"en": ("times", "plus"), "fr": ("fois", "plus")}


def solve_math_challenge(text: str, lang: str = "en") -> int:
    """Solve one 'X times Y plus Z' challenge written in words.

    The anti-spam design writes operands as translated words — a
    scripted candidate must do what a human does: read, translate,
    compute. num1 * num2 + num3, per generate_math_challenges."""
    words = {w: i for i, w in enumerate(_NUMBER_WORDS[lang])}
    times, plus = _OPERATORS[lang]
    pattern = (r"(\w+)\s+" + times + r"\s+(\w+)\s*[,;]?\s*" + plus +
               r"\s+(\w+)")
    match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
    if not match:
        raise ValueError(f"no challenge found in: {text!r}")
    a, b, c = (words[w.lower()] for w in match.groups())
    return a * b + c


def solve_all_challenges(body: str, lang: str = "en") -> dict:
    """Extract and solve the four labelled challenges of the e-mail.

    Returns {'A': int, 'B': int, 'C': int, 'D': int}."""
    solutions = {}
    for label in ("A", "B", "C", "D"):
        section = re.search(
            label + r"\s*[:=]\s*(.+)", body)
        if not section:
            raise ValueError(f"challenge {label} not found in the e-mail")
        solutions[label] = solve_math_challenge(section.group(1), lang)
    return solutions


def fetch_email(recipient: str, timeout: int = 60) -> str:
    """Return the decoded body of the newest e-mail for ``recipient``.

    The transport is pluggable through E2E_MAIL_CMD (a shell command
    printing the raw mailbox); the default reads the test stack's
    postfix container mailboxes. Retries until ``timeout``."""
    command = os.environ.get(
        "E2E_MAIL_CMD",
        "docker compose --env-file docker/.env.test "
        "-f docker/test-docker-compose.yaml exec -T postfix "
        "sh -c 'cat /var/mail/* /var/spool/mail/* 2>/dev/null'",
    )
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        raw = subprocess.run(  # nosec B602 — operator-provided command
            command, shell=True, capture_output=True, text=True
        ).stdout
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
