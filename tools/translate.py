#!/usr/bin/env python3
# =============================================================================
# tools/translate.py
#
# Translation helpers for AlirPunkto.
#
# The script supports three workflows:
#   1. translate-file: translate one plain text / Markdown / template file;
#   2. sync-template: update one translated Chameleon/TAL template from the
#      English source, optionally using the French template and the existing
#      target translation as context;
#   3. sync-po: synchronize a gettext .po catalog from the canonical .pot file,
#      using the English and French .po catalogs as translation context and the
#      existing target .po as preferred wording.
#
# Requirements:
#   pip install --upgrade openai python-dotenv polib
#
# Environment:
#   OPENAI_API_KEY=...
#   OPENAI_TRANSLATION_MODEL=gpt-5.6-luna  # optional
# =============================================================================

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional convenience dependency
    def load_dotenv(*args, **kwargs):
        return False

try:
    import polib
except ImportError:  # pragma: no cover - runtime dependency guard
    polib = None

DEFAULT_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-5.6-luna")
DEFAULT_MAX_CHARS = int(os.getenv("OPENAI_TRANSLATION_MAX_CHARS", "9000"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_TRANSLATION_MAX_OUTPUT_TOKENS", "12000"))
DEFAULT_RETRIES = int(os.getenv("OPENAI_TRANSLATION_RETRIES", "4"))


# -----------------------------------------------------------------------------
# Generic OpenAI helpers
# -----------------------------------------------------------------------------

def require_polib() -> None:
    if polib is None:
        raise RuntimeError(
            "The 'polib' package is required for .po synchronization. "
            "Install it with: pip install polib"
        )


def strip_json_fence(text: str) -> str:
    """Remove an optional Markdown code fence from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[A-Za-z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def split_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks, preferably at blank lines."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        if paragraph_len > max_chars:
            flush()
            for start in range(0, paragraph_len, max_chars):
                chunks.append(paragraph[start:start + max_chars])
            continue

        extra = paragraph_len if not current else paragraph_len + 2
        if current and current_len + extra > max_chars:
            flush()
        current.append(paragraph)
        current_len += extra

    flush()
    return chunks


def call_openai(
    *,
    model: str,
    instructions: str,
    input_text: str,
    max_output_tokens: int,
    retries: int,
    response_schema: Optional[dict] = None,
) -> str:
    """Call the OpenAI Responses API with retries and optional strict JSON."""
    try:
        from openai import (
            APIConnectionError,
            APIError,
            APITimeoutError,
            OpenAI,
            RateLimitError,
        )
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "The 'openai' package is required. Install it with: pip install openai"
        ) from exc

    client = OpenAI()
    for attempt in range(retries + 1):
        try:
            request = {
                "model": model,
                "instructions": instructions,
                "input": input_text,
                "max_output_tokens": max_output_tokens,
            }
            if model.startswith("gpt-5.6"):
                request["reasoning"] = {
                    "effort": os.getenv(
                        "OPENAI_TRANSLATION_REASONING_EFFORT", "none"
                    )
                }
            if response_schema is not None:
                request["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": "gettext_translation",
                        "strict": True,
                        "schema": response_schema,
                    }
                }

            response = client.responses.create(**request)
            output = getattr(response, "output_text", None)
            if not output:
                raise RuntimeError("OpenAI response did not contain output_text")
            return output.rstrip()
        except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
            if attempt >= retries:
                raise
            delay = min(2 ** attempt, 30)
            print(
                f"[translate] API error on attempt {attempt + 1}/{retries + 1}: "
                f"{exc.__class__.__name__}. Retrying in {delay}s...",
                file=sys.stderr,
            )
            time.sleep(delay)

    raise RuntimeError("unreachable retry state")


# -----------------------------------------------------------------------------
# Generic file translation
# -----------------------------------------------------------------------------

def build_file_instructions(source_lang: str, target_lang: str, file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    common = f"""
You are translating a project file from {source_lang} to {target_lang}.

Return only the translated file content. Do not add explanations, comments,
Markdown fences, prefaces, or postfaces.

Preserve all technical structure:
- file format and syntax;
- Markdown headings, lists, tables and links;
- code fences and code blocks;
- HTML, XML, TAL, METAL and Chameleon attributes;
- Python identifiers and dotted module paths;
- environment variable names;
- placeholders such as {{name}}, %(name)s, ${{name}}, <tal:...>;
- i18n message identifiers;
- escaped quotes and apostrophes;
- indentation and line breaks whenever possible.

Translate human-readable prose and UI text only.
"""

    if suffix in {".po", ".pot"}:
        return common + """
Special rules for gettext files:
- preserve msgid values exactly;
- translate msgstr values only;
- preserve comments, references, flags and context lines;
- preserve plural forms and placeholders;
- do not invent or remove entries.
"""
    if suffix in {".pt", ".html", ".xml"}:
        return common + """
Special rules for templates:
- preserve every tag, attribute and template expression;
- translate only visible human text and translatable attribute values;
- do not modify tal:, metal:, i18n:, href, src, id, class, name or value bindings
  unless the value is clearly human-readable text.
"""
    return common


def translate_text(
    text: str,
    *,
    source_lang: str,
    target_lang: str,
    file_name: str,
    model: str,
    max_chars: int,
    max_output_tokens: int,
    retries: int,
) -> str:
    chunks = split_text(text, max_chars)
    instructions = build_file_instructions(source_lang, target_lang, file_name)
    translated_chunks: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        print(
            f"[translate] {file_name}: chunk {index}/{len(chunks)} "
            f"({len(chunk)} chars) -> {target_lang}",
            file=sys.stderr,
        )
        translated_chunks.append(
            call_openai(
                model=model,
                instructions=instructions,
                input_text=chunk.strip(),
                max_output_tokens=max_output_tokens,
                retries=retries,
            )
        )
    return "\n\n".join(translated_chunks).rstrip() + "\n"


def translate_file(args: argparse.Namespace) -> None:
    input_path = Path(args.input_file_path)
    output_path = Path(args.output_file_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if output_path.exists() and not args.force:
        print(f"[translate] skip existing: {output_path}", file=sys.stderr)
        return

    translated = translate_text(
        input_path.read_text(encoding="utf-8"),
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        file_name=input_path.name,
        model=args.model,
        max_chars=args.max_chars,
        max_output_tokens=args.max_output_tokens,
        retries=args.retries,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(translated, encoding="utf-8")
    print(f"[translate] wrote {output_path}", file=sys.stderr)


# -----------------------------------------------------------------------------
# Template synchronization
# -----------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(
    r"\$\{[A-Za-z_][A-Za-z0-9_]*\}"
    r"|%\([A-Za-z_][A-Za-z0-9_]*\)[#0\-+]?(?:\d+|\*)?(?:\.\d+)?[diouxXeEfFgGcrsa]"
    r"|(?<!%)%(?:[#0\-+]?(?:\d+|\*)?(?:\.\d+)?)[diouxXeEfFgGcrsa]"
)
_TEMPLATE_DIRECTIVE_RE = re.compile(
    r"((?:tal|metal|i18n):[A-Za-z_-]+)\s*=\s*([\"'])(.*?)\2",
    re.S,
)


def placeholder_signature(text: str) -> Counter:
    """Return the multiset of interpolation placeholders used by *text*."""
    return Counter(_PLACEHOLDER_RE.findall(text or ""))


def template_directive_signature(text: str) -> Counter:
    """Return TAL/METAL/i18n attributes that must survive translation."""
    return Counter(
        f"{match.group(1)}={match.group(3)}"
        for match in _TEMPLATE_DIRECTIVE_RE.finditer(text or "")
    )


def assert_same_placeholders(source: str, translated: str, *, label: str) -> None:
    expected = placeholder_signature(source)
    actual = placeholder_signature(translated)
    if actual != expected:
        raise RuntimeError(
            f"Placeholder mismatch for {label}: expected {dict(expected)}, "
            f"got {dict(actual)}"
        )


def assert_template_invariants(source: str, translated: str, *, label: str) -> None:
    assert_same_placeholders(source, translated, label=label)
    expected = template_directive_signature(source)
    actual = template_directive_signature(translated)
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        raise RuntimeError(
            f"Template directives changed for {label}: "
            f"missing={dict(missing)}, extra={dict(extra)}"
        )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def sync_template(args: argparse.Namespace) -> None:
    source_path = Path(args.source_file)
    output_path = Path(args.output_file)
    french_path = Path(args.french_file) if args.french_file else None
    existing_path = Path(args.existing_file) if args.existing_file else output_path

    if not source_path.is_file():
        raise FileNotFoundError(f"Source template does not exist: {source_path}")

    if (
        output_path.exists()
        and args.skip_existing
        and not args.force
        and not args.revise_existing
    ):
        print(f"[translate] skip existing template: {output_path}", file=sys.stderr)
        return

    source_text = source_path.read_text(encoding="utf-8")
    french_text = french_path.read_text(encoding="utf-8") if french_path and french_path.is_file() else ""
    existing_text = existing_path.read_text(encoding="utf-8") if existing_path and existing_path.is_file() else ""

    instructions = f"""
You update a translated AlirPunkto Chameleon/TAL template in {args.target_lang}.

The English template is the structural source of truth. The French template is
provided only to clarify meaning. The existing {args.target_lang} template, when
present, is the preferred source for tone and terminology.

Return the complete updated {args.target_lang} template only.

Rules:
- preserve the English template structure exactly unless a translated text node
  requires a natural language difference;
- add any text or block that exists in English but is missing in the target;
- remove any target text or block that no longer exists in English;
- preserve every TAL/METAL/i18n directive and every interpolation placeholder
  exactly; never translate identifiers such as msgids, variable names or routes;
- preserve ids, classes, href/src bindings and form field names;
- translate every user-visible English sentence that belongs to the template;
- use the existing target wording for terminology and tone when it is correct;
- use the French version only as semantic context, never as structural source;
- do not return Markdown fences or explanations.
"""

    input_payload = {
        "file": source_path.name,
        "target_language": args.target_lang,
        "english_source_template": source_text,
        "french_reference_template": french_text,
        "existing_target_template": existing_text,
    }

    output = call_openai(
        model=args.model,
        instructions=instructions,
        input_text=json.dumps(input_payload, ensure_ascii=False, indent=2),
        max_output_tokens=args.max_output_tokens,
        retries=args.retries,
    )
    translated_text = strip_json_fence(output).rstrip() + "\n"
    assert_template_invariants(
        source_text,
        translated_text,
        label=f"{args.target_lang}:{source_path.name}",
    )
    atomic_write_text(output_path, translated_text)
    print(f"[translate] wrote template {output_path}", file=sys.stderr)


# -----------------------------------------------------------------------------
# PO catalog synchronization
# -----------------------------------------------------------------------------

def entry_key(entry) -> tuple[Optional[str], str]:
    return (entry.msgctxt, entry.msgid)


def find_entry(catalog, template_entry):
    if catalog is None:
        return None
    return catalog.find(template_entry.msgid, msgctxt=template_entry.msgctxt)


def entry_has_translation(entry) -> bool:
    if entry is None:
        return False
    if entry.obsolete:
        return False
    if entry.msgid_plural:
        return bool(entry.msgstr_plural) and all(
            bool(value.strip()) for value in entry.msgstr_plural.values()
        )
    return bool(entry.msgstr.strip())


def entry_is_fuzzy(entry) -> bool:
    return bool(entry and "fuzzy" in entry.flags)


def entry_texts(entry) -> list[str]:
    if entry is None:
        return []
    if entry.msgid_plural:
        return [
            str(value)
            for _, value in sorted(
                entry.msgstr_plural.items(), key=lambda item: int(item[0])
            )
        ]
    return [entry.msgstr]


def entry_matches_english(entry, english_entry) -> bool:
    """Detect explicit English fallbacks copied into a non-English catalog."""
    if entry is None or english_entry is None:
        return False
    target = [value.strip() for value in entry_texts(entry)]
    english = [value.strip() for value in entry_texts(english_entry)]
    if not target or target != english or not any(target):
        return False
    # Avoid re-translating short words/acronyms that are legitimately identical
    # in several languages. The problematic fallbacks in this repository are
    # sentences/labels with at least two alphabetic words.
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}", " ".join(target))
    return len(words) >= 2


def copy_entry_shell(template_entry):
    new_entry = polib.POEntry(
        msgid=template_entry.msgid,
        msgstr="",
        msgctxt=template_entry.msgctxt,
        msgid_plural=template_entry.msgid_plural,
        occurrences=list(template_entry.occurrences),
        comment=template_entry.comment,
        tcomment=template_entry.tcomment,
        flags=[flag for flag in template_entry.flags if flag != "fuzzy"],
        previous_msgid=template_entry.previous_msgid,
        previous_msgctxt=template_entry.previous_msgctxt,
        previous_msgid_plural=template_entry.previous_msgid_plural,
    )
    if template_entry.msgid_plural:
        new_entry.msgstr_plural = {}
    return new_entry


def plural_keys(existing_entry, template_entry, catalog=None) -> list[str]:
    if existing_entry and existing_entry.msgstr_plural:
        return [
            str(key)
            for key in sorted(
                existing_entry.msgstr_plural.keys(), key=lambda item: int(item)
            )
        ]
    if template_entry.msgid_plural:
        plural_forms = (catalog.metadata.get("Plural-Forms", "") if catalog else "")
        match = re.search(r"nplurals\s*=\s*(\d+)", plural_forms)
        count = int(match.group(1)) if match else 2
        return [str(index) for index in range(count)]
    return []


def use_existing_translation(new_entry, existing_entry) -> None:
    if new_entry.msgid_plural:
        new_entry.msgstr_plural = dict(existing_entry.msgstr_plural)
    else:
        new_entry.msgstr = existing_entry.msgstr


def reference_text_for_key(english_entry, template_entry, key=None) -> str:
    if english_entry is not None:
        if template_entry.msgid_plural:
            value = english_entry.msgstr_plural.get(int(key), "")
            if value:
                return value
        elif english_entry.msgstr:
            return english_entry.msgstr
    return template_entry.msgid_plural if key is not None else template_entry.msgid


def validate_po_translation(new_entry, english_entry, template_entry) -> None:
    if template_entry.msgid_plural:
        for key, value in new_entry.msgstr_plural.items():
            source = reference_text_for_key(
                english_entry, template_entry, key=str(key)
            )
            assert_same_placeholders(
                source,
                value,
                label=f"{template_entry.msgid}[{key}]",
            )
            if not value.strip():
                raise RuntimeError(
                    f"Empty plural translation for {template_entry.msgid}[{key}]"
                )
    else:
        source = reference_text_for_key(english_entry, template_entry)
        assert_same_placeholders(source, new_entry.msgstr, label=template_entry.msgid)
        if not new_entry.msgstr.strip():
            raise RuntimeError(f"Empty translation for {template_entry.msgid}")


def translate_po_entry(
    *,
    template_entry,
    english_entry,
    french_entry,
    existing_entry,
    target_lang: str,
    plural_keys_expected: list[str],
    model: str,
    max_output_tokens: int,
    retries: int,
):
    instructions = f"""
Translate one gettext entry for the AlirPunkto project into {target_lang}.

Return JSON only. Do not wrap it in Markdown.

If the entry has no plural form, return:
{{"msgstr": "..."}}

If the entry has plural forms, return:
{{"msgstr_plural": {{"0": "...", "1": "..."}}}}
using exactly the plural keys provided in the input.

Quality rules:
- msgid is a symbolic identifier and must never be translated;
- English is the semantic source; French is additional context;
- use the existing {target_lang} wording as terminology/style guidance when it
  is genuinely in {target_lang};
- if the existing target is English, translate it instead of preserving it;
- translate every user-visible sentence naturally, not word-for-word;
- keep AlirPunkto, CosmoPolitical, LDAP, IBAN, URLs and technical identifiers
  unchanged unless ordinary grammar requires surrounding inflection;
- preserve every placeholder exactly and with the same multiplicity;
- preserve HTML/XML tags and escaped characters;
- never invent, delete or rename variables.
"""

    payload = {
        "msgctxt": template_entry.msgctxt,
        "msgid": template_entry.msgid,
        "msgid_plural": template_entry.msgid_plural,
        "expected_plural_keys": plural_keys_expected,
        "english_msgstr": english_entry.msgstr if english_entry else "",
        "english_msgstr_plural": dict(english_entry.msgstr_plural) if english_entry and english_entry.msgstr_plural else {},
        "french_msgstr": french_entry.msgstr if french_entry else "",
        "french_msgstr_plural": dict(french_entry.msgstr_plural) if french_entry and french_entry.msgstr_plural else {},
        "existing_target_msgstr": existing_entry.msgstr if existing_entry else "",
        "existing_target_msgstr_plural": dict(existing_entry.msgstr_plural) if existing_entry and existing_entry.msgstr_plural else {},
    }

    if template_entry.msgid_plural:
        response_schema = {
            "type": "object",
            "properties": {
                "msgstr_plural": {
                    "type": "object",
                    "properties": {
                        str(key): {"type": "string"}
                        for key in plural_keys_expected
                    },
                    "required": [str(key) for key in plural_keys_expected],
                    "additionalProperties": False,
                }
            },
            "required": ["msgstr_plural"],
            "additionalProperties": False,
        }
    else:
        response_schema = {
            "type": "object",
            "properties": {"msgstr": {"type": "string"}},
            "required": ["msgstr"],
            "additionalProperties": False,
        }

    raw = call_openai(
        model=model,
        instructions=instructions,
        input_text=json.dumps(payload, ensure_ascii=False, indent=2),
        max_output_tokens=max_output_tokens,
        retries=retries,
        response_schema=response_schema,
    )
    try:
        data = json.loads(strip_json_fence(raw))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model did not return valid JSON for msgid "
            f"{template_entry.msgid!r}: {raw[:500]}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Model returned a non-object JSON value for {template_entry.msgid!r}"
        )
    return data


def sync_po(args: argparse.Namespace) -> None:
    require_polib()

    pot_path = Path(args.pot)
    english_po_path = Path(args.english_po)
    french_po_path = Path(args.french_po)
    target_po_path = Path(args.target_po)

    if not pot_path.is_file():
        raise FileNotFoundError(f"POT file does not exist: {pot_path}")

    pot = polib.pofile(str(pot_path))
    english = polib.pofile(str(english_po_path)) if english_po_path.is_file() else None
    french = polib.pofile(str(french_po_path)) if french_po_path.is_file() else None
    existing = polib.pofile(str(target_po_path)) if target_po_path.is_file() else None

    output = polib.POFile()
    output.metadata = dict(existing.metadata if existing else pot.metadata)
    output.metadata.setdefault("Content-Type", "text/plain; charset=UTF-8")
    output.metadata.setdefault("Content-Transfer-Encoding", "8bit")
    output.metadata["Language"] = args.target_code or output.metadata.get("Language", "")
    output.metadata["X-Generator"] = "AlirPunkto tools/translate.py + OpenAI API"
    output.metadata["X-Translation-Model"] = args.model

    if args.revise_existing:
        mode = "revise every entry"
    elif args.keep_english_fallbacks:
        mode = "translate missing/fuzzy; keep explicit English fallbacks"
    else:
        mode = "translate missing/fuzzy and explicit English fallbacks"
    print(f"[translate] sync-po {target_po_path} ({mode})", file=sys.stderr)

    stats = Counter()
    pot_entries = [entry for entry in pot if not entry.obsolete]
    for index, template_entry in enumerate(pot_entries, start=1):
        new_entry = copy_entry_shell(template_entry)
        old_entry = find_entry(existing, template_entry)
        english_entry = find_entry(english, template_entry)
        french_entry = find_entry(french, template_entry)
        english_fallback = (
            args.target_code != "en"
            and not args.keep_english_fallbacks
            and entry_matches_english(old_entry, english_entry)
        )

        should_keep = (
            old_entry is not None
            and entry_has_translation(old_entry)
            and not entry_is_fuzzy(old_entry)
            and not english_fallback
            and not args.revise_existing
            and not args.force
        )

        if should_keep:
            use_existing_translation(new_entry, old_entry)
            stats["kept"] += 1
        else:
            if old_entry is None:
                reason = "missing"
            elif entry_is_fuzzy(old_entry):
                reason = "fuzzy"
            elif not entry_has_translation(old_entry):
                reason = "empty"
            elif english_fallback:
                reason = "english-fallback"
            elif args.revise_existing or args.force:
                reason = "revision"
            else:
                reason = "translation"

            print(
                f"[translate] {args.target_code}:{index}/{len(pot_entries)} "
                f"{reason}: {template_entry.msgid[:70]!r}",
                file=sys.stderr,
            )
            keys = plural_keys(old_entry, template_entry, existing)
            translated = translate_po_entry(
                template_entry=template_entry,
                english_entry=english_entry,
                french_entry=french_entry,
                existing_entry=old_entry,
                target_lang=args.target_lang,
                plural_keys_expected=keys,
                model=args.model,
                max_output_tokens=args.max_output_tokens,
                retries=args.retries,
            )
            if template_entry.msgid_plural:
                values = translated.get("msgstr_plural", {})
                if not isinstance(values, dict):
                    raise RuntimeError(
                        f"Invalid msgstr_plural for {template_entry.msgid!r}"
                    )
                new_entry.msgstr_plural = {
                    int(key): str(values.get(str(key), "")) for key in keys
                }
            else:
                new_entry.msgstr = str(translated.get("msgstr", ""))

            validate_po_translation(new_entry, english_entry, template_entry)
            stats[reason] += 1

        output.append(new_entry)

    target_po_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_po_path.with_name(target_po_path.name + ".tmp")
    output.save(str(temporary))
    os.replace(temporary, target_po_path)
    print(
        f"[translate] wrote po {target_po_path}; "
        + ", ".join(f"{key}={value}" for key, value in sorted(stats.items())),
        file=sys.stderr,
    )


def audit_locale(args: argparse.Namespace) -> int:
    """Report catalog/template debt without calling the OpenAI API."""
    require_polib()

    pot_path = Path(args.pot)
    target_path = Path(args.target_po)
    english_path = Path(args.english_po)
    if not pot_path.is_file():
        raise FileNotFoundError(f"POT file does not exist: {pot_path}")

    pot = polib.pofile(str(pot_path))
    target = polib.pofile(str(target_path)) if target_path.is_file() else None
    english = polib.pofile(str(english_path)) if english_path.is_file() else None

    stats = Counter()
    pot_entries = [entry for entry in pot if not entry.obsolete]
    pot_keys = {entry_key(entry) for entry in pot_entries}

    for template_entry in pot_entries:
        target_entry = find_entry(target, template_entry)
        english_entry = find_entry(english, template_entry)
        if target_entry is None:
            stats["missing"] += 1
        elif entry_is_fuzzy(target_entry):
            stats["fuzzy"] += 1
        elif not entry_has_translation(target_entry):
            stats["empty"] += 1
        elif args.target_code != "en" and entry_matches_english(
            target_entry, english_entry
        ):
            stats["english_fallback"] += 1
        else:
            stats["translated"] += 1

    if target is not None:
        stats["obsolete"] = sum(
            1
            for entry in target
            if entry.obsolete or entry_key(entry) not in pot_keys
        )

    english_template_dir = Path(args.english_template_dir)
    target_template_dir = Path(args.target_template_dir)
    expected_templates = {
        path.name for path in english_template_dir.glob("*.pt")
    } if english_template_dir.is_dir() else set()
    actual_templates = {
        path.name for path in target_template_dir.glob("*.pt")
    } if target_template_dir.is_dir() else set()

    missing_templates = sorted(expected_templates - actual_templates)
    extra_templates = sorted(actual_templates - expected_templates)
    english_copies = []
    if args.target_code != "en" and target_template_dir.is_dir():
        for name in sorted(expected_templates & actual_templates):
            if (
                (english_template_dir / name).read_text(encoding="utf-8")
                == (target_template_dir / name).read_text(encoding="utf-8")
            ):
                english_copies.append(name)

    report = {
        "locale": args.target_code,
        "catalog": {
            "total": len(pot_entries),
            **{name: stats[name] for name in (
                "translated",
                "english_fallback",
                "fuzzy",
                "empty",
                "missing",
                "obsolete",
            )},
        },
        "templates": {
            "expected": len(expected_templates),
            "present": len(actual_templates),
            "missing": missing_templates,
            "extra": extra_templates,
            "exact_english_copies": english_copies,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    structural_issues = (
        stats["missing"]
        + stats["fuzzy"]
        + stats["empty"]
        + len(missing_templates)
    )
    return 1 if args.fail_on_structural and structural_issues else 0


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def add_common_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model.")
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help="Maximum output tokens per API call.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Retries for transient API errors.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlirPunkto translation helper.")
    sub = parser.add_subparsers(dest="command")

    file_parser = sub.add_parser("translate-file", help="Translate one file.")
    file_parser.add_argument("input_file_path")
    file_parser.add_argument("output_file_path")
    file_parser.add_argument("--source-lang", default="English")
    file_parser.add_argument("--target-lang", default="French")
    file_parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    file_parser.add_argument("--force", action="store_true")
    add_common_model_args(file_parser)

    template_parser = sub.add_parser("sync-template", help="Synchronize one translated .pt template.")
    template_parser.add_argument("--source-file", required=True)
    template_parser.add_argument("--output-file", required=True)
    template_parser.add_argument("--target-lang", required=True)
    template_parser.add_argument("--french-file")
    template_parser.add_argument("--existing-file")
    template_parser.add_argument("--force", action="store_true")
    template_parser.add_argument("--revise-existing", action="store_true")
    template_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Keep the historical behavior and only create missing templates.",
    )
    add_common_model_args(template_parser)

    po_parser = sub.add_parser("sync-po", help="Synchronize a target .po from .pot + en/fr context.")
    po_parser.add_argument("--pot", required=True)
    po_parser.add_argument("--english-po", required=True)
    po_parser.add_argument("--french-po", required=True)
    po_parser.add_argument("--target-po", required=True)
    po_parser.add_argument("--target-lang", required=True)
    po_parser.add_argument("--target-code", default="")
    po_parser.add_argument("--force", action="store_true")
    po_parser.add_argument("--revise-existing", action="store_true")
    po_parser.add_argument(
        "--keep-english-fallbacks",
        action="store_true",
        help="Do not retranslate non-fuzzy msgstr values identical to English.",
    )
    add_common_model_args(po_parser)

    audit_parser = sub.add_parser(
        "audit-locale",
        help="Report gettext/template completeness without using the OpenAI API.",
    )
    audit_parser.add_argument("--pot", required=True)
    audit_parser.add_argument("--english-po", required=True)
    audit_parser.add_argument("--target-po", required=True)
    audit_parser.add_argument("--target-code", required=True)
    audit_parser.add_argument("--english-template-dir", required=True)
    audit_parser.add_argument("--target-template-dir", required=True)
    audit_parser.add_argument("--fail-on-structural", action="store_true")

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    load_dotenv()

    # Backward-compatible mode with the previous positional API:
    #   translate.py input output --source_lang english --target_lang French
    raw_args = list(argv if argv is not None else sys.argv[1:])
    commands = {
        "translate-file",
        "sync-template",
        "sync-po",
        "audit-locale",
        "-h",
        "--help",
    }
    if raw_args and raw_args[0] not in commands:
        normalized: list[str] = ["translate-file"]
        for arg in raw_args:
            normalized.append(arg.replace("--source_lang", "--source-lang").replace("--target_lang", "--target-lang"))
        raw_args = normalized

    parser = build_parser()
    args = parser.parse_args(raw_args)

    if not args.command:
        parser.print_help(sys.stderr)
        return 2

    if args.command != "audit-locale" and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set. Export it or define it in .env.", file=sys.stderr)
        return 2

    if args.command == "translate-file":
        translate_file(args)
    elif args.command == "sync-template":
        sync_template(args)
    elif args.command == "sync-po":
        sync_po(args)
    elif args.command == "audit-locale":
        return audit_locale(args)
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
