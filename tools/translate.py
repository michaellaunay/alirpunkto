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
#   OPENAI_TRANSLATION_MODEL=gpt-4o-mini   # optional
# =============================================================================

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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

DEFAULT_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")
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
    """Return raw JSON if the model wrapped it in a Markdown fence."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
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
) -> str:
    """Call the OpenAI Responses API with simple exponential backoff."""
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
            response = client.responses.create(
                model=model,
                instructions=instructions,
                input=input_text,
                max_output_tokens=max_output_tokens,
            )
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

def sync_template(args: argparse.Namespace) -> None:
    source_path = Path(args.source_file)
    output_path = Path(args.output_file)
    french_path = Path(args.french_file) if args.french_file else None
    existing_path = Path(args.existing_file) if args.existing_file else output_path

    if not source_path.is_file():
        raise FileNotFoundError(f"Source template does not exist: {source_path}")

    if output_path.exists() and not args.force and not args.revise_existing:
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
- preserve all TAL/METAL/i18n attributes, expressions, placeholders, ids,
  classes, href/src bindings and indentation as much as possible;
- translate visible human-readable text and human-readable attribute values;
- keep existing {args.target_lang} wording when it is correct, and edit it only
  when it is missing, obsolete, inconsistent or less accurate.
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output.rstrip() + "\n", encoding="utf-8")
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
        return any(bool(value.strip()) for value in entry.msgstr_plural.values())
    return bool(entry.msgstr.strip())


def entry_is_fuzzy(entry) -> bool:
    return bool(entry and "fuzzy" in entry.flags)


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


def plural_keys(existing_entry, template_entry) -> list[str]:
    if existing_entry and existing_entry.msgstr_plural:
        return [str(key) for key in sorted(existing_entry.msgstr_plural.keys(), key=lambda item: int(item))]
    if template_entry.msgid_plural:
        return ["0", "1"]
    return []


def use_existing_translation(new_entry, existing_entry) -> None:
    if new_entry.msgid_plural:
        new_entry.msgstr_plural = dict(existing_entry.msgstr_plural)
    else:
        new_entry.msgstr = existing_entry.msgstr


def translate_po_entry(
    *,
    template_entry,
    english_entry,
    french_entry,
    existing_entry,
    target_lang: str,
    model: str,
    max_output_tokens: int,
    retries: int,
):
    expected_plural_keys = plural_keys(existing_entry, template_entry)

    instructions = f"""
You update one gettext entry for the AlirPunkto project in {target_lang}.

Return JSON only. Do not wrap it in Markdown.

If the entry has no plural form, return:
{{"msgstr": "..."}}

If the entry has plural forms, return:
{{"msgstr_plural": {{"0": "...", "1": "..."}}}}
using exactly the plural keys provided in the input.

Rules:
- msgid is the canonical source identifier and must not be changed;
- use the English msgstr and French msgstr as semantic context;
- use the existing {target_lang} translation as the preferred wording when it is
  correct;
- edit the existing wording when it is obsolete, incomplete, inconsistent or
  less accurate;
- preserve placeholders exactly: {{name}}, %(name)s, %s, %d, ${{name}}, HTML
  tags, TAL/i18n placeholders and escaped characters;
- do not translate variables, identifiers or markup;
- produce natural UI/documentation text in {target_lang}.
"""

    payload = {
        "msgctxt": template_entry.msgctxt,
        "msgid": template_entry.msgid,
        "msgid_plural": template_entry.msgid_plural,
        "expected_plural_keys": expected_plural_keys,
        "english_msgstr": english_entry.msgstr if english_entry else "",
        "english_msgstr_plural": dict(english_entry.msgstr_plural) if english_entry and english_entry.msgstr_plural else {},
        "french_msgstr": french_entry.msgstr if french_entry else "",
        "french_msgstr_plural": dict(french_entry.msgstr_plural) if french_entry and french_entry.msgstr_plural else {},
        "existing_target_msgstr": existing_entry.msgstr if existing_entry else "",
        "existing_target_msgstr_plural": dict(existing_entry.msgstr_plural) if existing_entry and existing_entry.msgstr_plural else {},
    }

    raw = call_openai(
        model=model,
        instructions=instructions,
        input_text=json.dumps(payload, ensure_ascii=False, indent=2),
        max_output_tokens=max_output_tokens,
        retries=retries,
    )
    try:
        data = json.loads(strip_json_fence(raw))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model did not return valid JSON for msgid {template_entry.msgid!r}: {raw[:500]}"
        ) from exc

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

    if args.revise_existing:
        mode = "revise existing, translate missing/fuzzy"
    else:
        mode = "keep existing non-fuzzy translations, translate missing/fuzzy"
    print(f"[translate] sync-po {target_po_path} ({mode})", file=sys.stderr)

    pot_entries = [entry for entry in pot if not entry.obsolete]
    for index, template_entry in enumerate(pot_entries, start=1):
        new_entry = copy_entry_shell(template_entry)
        old_entry = find_entry(existing, template_entry)
        english_entry = find_entry(english, template_entry)
        french_entry = find_entry(french, template_entry)

        should_keep = (
            old_entry is not None
            and entry_has_translation(old_entry)
            and not entry_is_fuzzy(old_entry)
            and not args.revise_existing
            and not args.force
        )

        if should_keep:
            use_existing_translation(new_entry, old_entry)
        else:
            print(
                f"[translate] {target_po_path.name}: entry {index}/{len(pot_entries)} "
                f"-> {args.target_lang}: {template_entry.msgid[:60]!r}",
                file=sys.stderr,
            )
            translated = translate_po_entry(
                template_entry=template_entry,
                english_entry=english_entry,
                french_entry=french_entry,
                existing_entry=old_entry,
                target_lang=args.target_lang,
                model=args.model,
                max_output_tokens=args.max_output_tokens,
                retries=args.retries,
            )
            if template_entry.msgid_plural:
                values = translated.get("msgstr_plural", {})
                keys = plural_keys(old_entry, template_entry)
                if not keys:
                    keys = sorted(values.keys()) or ["0", "1"]
                new_entry.msgstr_plural = {int(key): str(values.get(str(key), "")) for key in keys}
            else:
                new_entry.msgstr = str(translated.get("msgstr", ""))

        output.append(new_entry)

    target_po_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(str(target_po_path))
    print(f"[translate] wrote po {target_po_path}", file=sys.stderr)


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
    add_common_model_args(po_parser)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    load_dotenv()

    # Backward-compatible mode with the previous positional API:
    #   translate.py input output --source_lang english --target_lang French
    raw_args = list(argv if argv is not None else sys.argv[1:])
    if raw_args and raw_args[0] not in {"translate-file", "sync-template", "sync-po", "-h", "--help"}:
        normalized: list[str] = ["translate-file"]
        for arg in raw_args:
            normalized.append(arg.replace("--source_lang", "--source-lang").replace("--target_lang", "--target-lang"))
        raw_args = normalized

    parser = build_parser()
    args = parser.parse_args(raw_args)

    if not args.command:
        parser.print_help(sys.stderr)
        return 2

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set. Export it or define it in .env.", file=sys.stderr)
        return 2

    if args.command == "translate-file":
        translate_file(args)
    elif args.command == "sync-template":
        sync_template(args)
    elif args.command == "sync-po":
        sync_po(args)
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
