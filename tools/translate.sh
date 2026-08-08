#!/usr/bin/env bash
# =============================================================================
# tools/translate.sh
#
# Repair and synchronize AlirPunkto locale files.
#
# The canonical gettext source is alirpunkto/locale/alirpunkto.pot. English is
# the semantic source and French is secondary context. Locale directories on
# disk are the processing inventory: the script never invents a new language.
#
# By default, the script:
#   - rebuilds every target .po against the POT;
#   - preserves existing non-fuzzy translations written in the target language;
#   - translates missing, empty, fuzzy and explicit English-fallback entries;
#   - synchronizes every .pt template from the English structure;
#   - removes stale .pt templates absent from English;
#   - validates and compiles each .po with msgfmt --check --check-format;
#   - runs a structural audit after each locale.
#
# Requirements:
#   pip install --upgrade openai python-dotenv polib
#   sudo apt install gettext
#   export OPENAI_API_KEY="..."
# =============================================================================

set -euo pipefail

SOURCE_DIR="${SOURCES:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MODEL="${OPENAI_TRANSLATION_MODEL:-gpt-5.6-luna}"
FORCE=0
DRY_RUN=0
AUDIT_ONLY=0
REVISE_EXISTING=0
KEEP_ENGLISH_FALLBACKS=0
MISSING_TEMPLATES_ONLY=0
DELETE_STALE=1
COMPILE_MO=1
LANG_FILTER=""

POT_FILE="alirpunkto/locale/alirpunkto.pot"
LOCALE_ROOT="alirpunkto/locale"
EN_DIR="$LOCALE_ROOT/en/LC_MESSAGES"
FR_DIR="$LOCALE_ROOT/fr/LC_MESSAGES"
EN_PO="$EN_DIR/alirpunkto.po"
FR_PO="$FR_DIR/alirpunkto.po"

language_name() {
  case "$1" in
    be) printf '%s' "Belarusian" ;;
    bg) printf '%s' "Bulgarian" ;;
    bs) printf '%s' "Bosnian" ;;
    cs) printf '%s' "Czech" ;;
    da) printf '%s' "Danish" ;;
    de) printf '%s' "German" ;;
    el) printf '%s' "Greek" ;;
    en) printf '%s' "English" ;;
    eo) printf '%s' "Esperanto" ;;
    es) printf '%s' "Spanish" ;;
    et) printf '%s' "Estonian" ;;
    fi) printf '%s' "Finnish" ;;
    fr) printf '%s' "French" ;;
    ga) printf '%s' "Irish" ;;
    hr) printf '%s' "Croatian" ;;
    hu) printf '%s' "Hungarian" ;;
    is) printf '%s' "Icelandic" ;;
    it) printf '%s' "Italian" ;;
    lt) printf '%s' "Lithuanian" ;;
    lv) printf '%s' "Latvian" ;;
    mt) printf '%s' "Maltese" ;;
    nl) printf '%s' "Dutch" ;;
    no) printf '%s' "Norwegian" ;;
    pl) printf '%s' "Polish" ;;
    pt) printf '%s' "Portuguese" ;;
    ro) printf '%s' "Romanian" ;;
    sk) printf '%s' "Slovak" ;;
    sl) printf '%s' "Slovenian" ;;
    sq) printf '%s' "Albanian" ;;
    sr) printf '%s' "Serbian" ;;
    sv) printf '%s' "Swedish" ;;
    tr) printf '%s' "Turkish" ;;
    uk) printf '%s' "Ukrainian" ;;
    *)  printf '%s' "$1" ;;
  esac
}

usage() {
  cat <<'EOF'
Usage:
  tools/translate.sh [options]

Options:
  --source-dir PATH          Repository root. Defaults to the parent of tools/.
  --model MODEL              OpenAI model. Default: OPENAI_TRANSLATION_MODEL
                             or gpt-5.6-luna.
  --languages CODES          Comma-separated locale directories, e.g. fr,de,es.
  --audit                    Audit only; no API call and no file modification.
  --force                    Re-translate all catalog entries/templates.
  --revise-existing          Ask the model to revise all existing translations.
  --keep-english-fallbacks   Preserve non-fuzzy msgstr values identical to EN.
  --missing-templates-only   Only create missing .pt templates; do not review
                             existing ones.
  --dry-run                  Print actions without API calls or writes.
  --keep-stale               Keep .pt files absent from the English locale.
  --delete-stale             Remove stale .pt files. Default.
  --no-compile               Do not validate/compile .po into .mo.
  --pot PATH                 Canonical POT file.
  --english-po PATH          English PO context file.
  --french-po PATH           French PO context file.
  -h, --help                 Show this help.

Examples:
  tools/translate.sh --audit
  tools/translate.sh --dry-run --languages de,es,eo
  tools/translate.sh --languages de,es,it,nl,pl
  tools/translate.sh --languages eo
  tools/translate.sh --revise-existing --languages fr
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-dir)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --languages)
      LANG_FILTER="$2"
      shift 2
      ;;
    --audit)
      AUDIT_ONLY=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --revise-existing)
      REVISE_EXISTING=1
      shift
      ;;
    --keep-english-fallbacks)
      KEEP_ENGLISH_FALLBACKS=1
      shift
      ;;
    --missing-templates-only)
      MISSING_TEMPLATES_ONLY=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --keep-stale)
      DELETE_STALE=0
      shift
      ;;
    --delete-stale)
      DELETE_STALE=1
      shift
      ;;
    --no-compile)
      COMPILE_MO=0
      shift
      ;;
    --pot)
      POT_FILE="$2"
      shift 2
      ;;
    --english-po)
      EN_PO="$2"
      shift 2
      ;;
    --french-po)
      FR_PO="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$SOURCE_DIR"

TRANSLATE_PY="tools/translate.py"

for required in "$TRANSLATE_PY" "$POT_FILE" "$EN_PO" "$FR_PO"; do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: missing required file: $required" >&2
    exit 1
  fi
done

if [[ ! -d "$EN_DIR" ]]; then
  echo "ERROR: missing English locale directory: $EN_DIR" >&2
  exit 1
fi

if [[ "$DRY_RUN" -eq 0 && "$AUDIT_ONLY" -eq 0 && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: OPENAI_API_KEY is not set. Use --audit or --dry-run without it." >&2
  exit 2
fi

if [[ "$COMPILE_MO" -eq 1 && "$DRY_RUN" -eq 0 && "$AUDIT_ONLY" -eq 0 ]]; then
  if ! command -v msgfmt >/dev/null 2>&1; then
    echo "ERROR: msgfmt is required for a normal translation run." >&2
    echo "Install gettext, or explicitly pass --no-compile." >&2
    exit 2
  fi
fi

mapfile -t LOCALE_CODES < <(
  find "$LOCALE_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
)

if [[ "${#LOCALE_CODES[@]}" -eq 0 ]]; then
  echo "ERROR: no locale directories found below $LOCALE_ROOT" >&2
  exit 1
fi

IFS=',' read -r -a REQUESTED_CODES <<< "$LANG_FILTER"

locale_exists() {
  local wanted="$1"
  local code
  for code in "${LOCALE_CODES[@]}"; do
    [[ "$code" == "$wanted" ]] && return 0
  done
  return 1
}

if [[ -n "$LANG_FILTER" ]]; then
  for requested in "${REQUESTED_CODES[@]}"; do
    if ! locale_exists "$requested"; then
      echo "ERROR: requested locale '$requested' has no directory in $LOCALE_ROOT" >&2
      exit 2
    fi
  done
fi

should_process_code() {
  local code="$1"

  # English is the structural/semantic source, not a translation target.
  if [[ "$code" == "en" ]]; then
    return 1
  fi

  if [[ -z "$LANG_FILTER" ]]; then
    return 0
  fi

  local requested
  for requested in "${REQUESTED_CODES[@]}"; do
    [[ "$requested" == "$code" ]] && return 0
  done
  return 1
}

run_or_echo() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

mapfile -t SOURCE_TEMPLATES < <(
  find "$EN_DIR" -maxdepth 1 -type f -name '*.pt' -printf '%f\n' | sort
)

if [[ "${#SOURCE_TEMPLATES[@]}" -eq 0 ]]; then
  echo "WARNING: no English .pt templates found in $EN_DIR" >&2
fi

for code in "${LOCALE_CODES[@]}"; do
  should_process_code "$code" || continue

  target_lang="$(language_name "$code")"
  target_dir="$LOCALE_ROOT/$code/LC_MESSAGES"
  target_po="$target_dir/alirpunkto.po"
  target_mo="$target_dir/alirpunkto.mo"

  echo "[translate] === $code / $target_lang ==="

  audit_args=(
    python3 "$TRANSLATE_PY" audit-locale
    --pot "$POT_FILE"
    --english-po "$EN_PO"
    --target-po "$target_po"
    --target-code "$code"
    --english-template-dir "$EN_DIR"
    --target-template-dir "$target_dir"
  )

  if [[ "$AUDIT_ONLY" -eq 1 ]]; then
    "${audit_args[@]}"
    continue
  fi

  run_or_echo mkdir -p "$target_dir"

  po_args=(
    python3 "$TRANSLATE_PY" sync-po
    --pot "$POT_FILE"
    --english-po "$EN_PO"
    --french-po "$FR_PO"
    --target-po "$target_po"
    --target-code "$code"
    --target-lang "$target_lang"
    --model "$MODEL"
  )

  if [[ "$FORCE" -eq 1 ]]; then
    po_args+=(--force)
  fi
  if [[ "$REVISE_EXISTING" -eq 1 ]]; then
    po_args+=(--revise-existing)
  fi
  if [[ "$KEEP_ENGLISH_FALLBACKS" -eq 1 ]]; then
    po_args+=(--keep-english-fallbacks)
  fi

  run_or_echo "${po_args[@]}"

  for template in "${SOURCE_TEMPLATES[@]}"; do
    source_template="$EN_DIR/$template"
    french_template="$FR_DIR/$template"
    target_template="$target_dir/$template"

    if [[ "$MISSING_TEMPLATES_ONLY" -eq 1 && -f "$target_template" ]]; then
      echo "[translate] skip existing template: $target_template"
      continue
    fi

    template_args=(
      python3 "$TRANSLATE_PY" sync-template
      --source-file "$source_template"
      --output-file "$target_template"
      --target-lang "$target_lang"
      --model "$MODEL"
    )

    if [[ -f "$french_template" ]]; then
      template_args+=(--french-file "$french_template")
    fi
    if [[ -f "$target_template" ]]; then
      template_args+=(--existing-file "$target_template")
    fi
    if [[ "$FORCE" -eq 1 ]]; then
      template_args+=(--force)
    fi
    if [[ "$REVISE_EXISTING" -eq 1 ]]; then
      template_args+=(--revise-existing)
    fi

    run_or_echo "${template_args[@]}"
  done

  if [[ "$DELETE_STALE" -eq 1 ]]; then
    while IFS= read -r target_template_path; do
      target_template_name="$(basename "$target_template_path")"
      if [[ ! -f "$EN_DIR/$target_template_name" ]]; then
        run_or_echo rm -f "$target_template_path"
      fi
    done < <(find "$target_dir" -maxdepth 1 -type f -name '*.pt' | sort)
  fi

  if [[ "$COMPILE_MO" -eq 1 ]]; then
    run_or_echo msgfmt --check --check-format "$target_po" -o "$target_mo"
  fi

  if [[ "$DRY_RUN" -eq 0 ]]; then
    "${audit_args[@]}" --fail-on-structural
  fi
done
