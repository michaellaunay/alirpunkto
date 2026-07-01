#!/usr/bin/env bash
# =============================================================================
# tools/translate.sh
#
# Synchronize AlirPunkto locale files.
#
# The canonical gettext source is alirpunkto/locale/alirpunkto.pot. The English
# and French .po catalogs are used as semantic context to translate the other
# languages and reduce ambiguity. Existing target translations are reused as the
# preferred wording, and can optionally be revised in place.
#
# By default, the script:
#   - synchronizes every target alirpunkto.po against the POT file;
#   - keeps existing non-fuzzy msgstr values;
#   - translates only missing or fuzzy entries;
#   - creates missing .pt templates from the English source templates;
#   - removes stale .pt templates that no longer exist in English;
#   - compiles alirpunkto.mo with msgfmt when available.
#
# Requirements:
#   pip install --upgrade openai python-dotenv polib
#   export OPENAI_API_KEY="..."
# =============================================================================

set -euo pipefail

SOURCE_DIR="${SOURCES:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MODEL="${OPENAI_TRANSLATION_MODEL:-gpt-4o-mini}"
SOURCE_LANG="English"
FORCE=0
DRY_RUN=0
REVISE_EXISTING=0
DELETE_STALE=1
COMPILE_MO=1
LANG_FILTER=""

POT_FILE="alirpunkto/locale/alirpunkto.pot"
EN_DIR="alirpunkto/locale/en/LC_MESSAGES"
FR_DIR="alirpunkto/locale/fr/LC_MESSAGES"
EN_PO="$EN_DIR/alirpunkto.po"
FR_PO="$FR_DIR/alirpunkto.po"

# Keep this list aligned with the locale directories supported by the project.
declare -A LANGUAGES=(
  [be]="Belarusian"
  [bg]="Bulgarian"
  [bs]="Bosnian"
  [cs]="Czech"
  [da]="Danish"
  [de]="German"
  [el]="Greek"
  [eo]="Esperanto"
  [es]="Spanish"
  [et]="Estonian"
  [fi]="Finnish"
  [fr]="French"
  [ga]="Irish"
  [hr]="Croatian"
  [hu]="Hungarian"
  [is]="Icelandic"
  [it]="Italian"
  [lt]="Lithuanian"
  [lv]="Latvian"
  [mk]="Macedonian"
  [mt]="Maltese"
  [nl]="Dutch"
  [no]="Norwegian"
  [pl]="Polish"
  [pt]="Portuguese"
  [ro]="Romanian"
  [sk]="Slovak"
  [sl]="Slovenian"
  [sq]="Albanian"
  [sr]="Serbian"
  [sv]="Swedish"
  [tr]="Turkish"
  [uk]="Ukrainian"
)

usage() {
  cat <<'EOF'
Usage:
  tools/translate.sh [options]

Options:
  --source-dir PATH        Repository root. Defaults to the parent of tools/.
  --model MODEL            OpenAI model. Defaults to OPENAI_TRANSLATION_MODEL or gpt-4o-mini.
  --languages CODES        Comma-separated target language codes, e.g. fr,de,es.
  --force                  Re-translate entries/templates even when target content exists.
  --revise-existing        Ask the model to revise existing translations using en/fr context.
  --dry-run                Print actions without calling the API or writing files.
  --keep-stale             Do not remove stale .pt files absent from the English locale.
  --delete-stale           Remove stale .pt files absent from the English locale. Default.
  --no-compile             Do not compile .po files into .mo.
  --pot PATH               Canonical POT file. Default: alirpunkto/locale/alirpunkto.pot.
  --english-po PATH        English PO context file. Default: en/LC_MESSAGES/alirpunkto.po.
  --french-po PATH         French PO context file. Default: fr/LC_MESSAGES/alirpunkto.po.
  -h, --help               Show this help.

Examples:
  tools/translate.sh --dry-run
  tools/translate.sh --languages fr,de,es
  tools/translate.sh --revise-existing --languages de
  tools/translate.sh --force --languages fr
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
    --force)
      FORCE=1
      shift
      ;;
    --revise-existing)
      REVISE_EXISTING=1
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

if [[ ! -f "$TRANSLATE_PY" ]]; then
  echo "ERROR: missing $TRANSLATE_PY" >&2
  exit 1
fi

if [[ ! -f "$POT_FILE" ]]; then
  echo "ERROR: missing POT file: $POT_FILE" >&2
  exit 1
fi

if [[ ! -f "$EN_PO" ]]; then
  echo "ERROR: missing English PO context: $EN_PO" >&2
  exit 1
fi

if [[ ! -f "$FR_PO" ]]; then
  echo "ERROR: missing French PO context: $FR_PO" >&2
  exit 1
fi

if [[ ! -d "$EN_DIR" ]]; then
  echo "ERROR: missing English locale directory: $EN_DIR" >&2
  exit 1
fi

if [[ "$DRY_RUN" -eq 0 && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: OPENAI_API_KEY is not set. Use --dry-run to preview actions without the API." >&2
  exit 2
fi

IFS=',' read -r -a REQUESTED_CODES <<< "$LANG_FILTER"

should_process_code() {
  local code="$1"

  # English is the source context. Do not generate it from itself.
  if [[ "$code" == "en" ]]; then
    return 1
  fi

  if [[ -z "$LANG_FILTER" ]]; then
    return 0
  fi

  local requested
  for requested in "${REQUESTED_CODES[@]}"; do
    if [[ "$requested" == "$code" ]]; then
      return 0
    fi
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

for code in $(printf '%s\n' "${!LANGUAGES[@]}" | sort); do
  should_process_code "$code" || continue

  target_lang="${LANGUAGES[$code]}"
  target_dir="alirpunkto/locale/$code/LC_MESSAGES"
  target_po="$target_dir/alirpunkto.po"
  target_mo="$target_dir/alirpunkto.mo"

  echo "[translate] === $code / $target_lang ==="
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

  run_or_echo "${po_args[@]}"

  for template in "${SOURCE_TEMPLATES[@]}"; do
    source_template="$EN_DIR/$template"
    french_template="$FR_DIR/$template"
    target_template="$target_dir/$template"

    # Existing templates are considered valid unless explicitly revising/forcing.
    if [[ -f "$target_template" && "$FORCE" -eq 0 && "$REVISE_EXISTING" -eq 0 ]]; then
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
    if command -v msgfmt >/dev/null 2>&1; then
      run_or_echo msgfmt "$target_po" -o "$target_mo"
    else
      echo "[translate] msgfmt not found; skipping $target_mo" >&2
    fi
  fi
done
