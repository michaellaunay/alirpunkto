#!/bin/bash
# Author: Michaël Launay (modified)
# Date: 2025-07-07
# Description: This script translates LaTeX files using the translate_latex.py 
#     script, which leverages ChatGPT for translation with LaTeX-aware chunking.

# Declare an associative array to map language codes to language names
declare -A languages
export SOURCES=~/workspace/alirpunkto

languages=(
  ["bg"]="Bulgarian"
  ["cs"]="Czech"
  ["da"]="Danish"
  ["eo"]="Esperanto"
  ["en"]="English"
  ["et"]="Estonian"
  ["fi"]="Finnish"
  ["ga"]="Irish"
  ["hr"]="Croatian"
  ["hu"]="Hungarian"
  ["lt"]="Lithuanian"
  ["lv"]="Latvian"
  ["mt"]="Maltese"
  ["sk"]="Slovak"
  ["sl"]="Slovenian"
  ["sv"]="Swedish"
  ["fr"]="French"
  ["de"]="German"
  ["es"]="Spanish"
  ["it"]="Italian"
  ["pt"]="Portuguese"
  ["nl"]="Dutch"
  ["el"]="Greek"
  ["pl"]="Polish"
  ["ro"]="Romanian"
  ["tr"]="Turkish"
  ["no"]="Norwegian"
  ["is"]="Icelandic"
  ["sq"]="Albanian"
  ["bs"]="Bosnian"
  ["mk"]="Macedonian"
  ["sr"]="Serbian"
  ["uk"]="Ukrainian"
  ["be"]="Belarusian"
)

# Function to display usage information
usage() {
    echo "Usage: $0 [OPTIONS] INPUT_FILE"
    echo ""
    echo "Options:"
    echo "  -l, --lang LANG_CODE    Translate to specific language (e.g., fr, de, es)"
    echo "  -a, --all              Translate to all supported languages"
    echo "  -o, --output DIR       Output directory (default: same as input with _translated suffix)"
    echo "  -s, --source LANG      Source language (default: English)"
    echo "  -h, --help             Display this help message"
    echo ""
    echo "Supported language codes:"
    for code in "${!languages[@]}"; do
        echo "  $code - ${languages[$code]}"
    done | sort
    echo ""
    echo "Examples:"
    echo "  $0 -l fr document.tex                    # Translate to French only"
    echo "  $0 -a document.tex                       # Translate to all languages"
    echo "  $0 -l de -o ./translations document.tex  # Translate to German with custom output dir"
}

# Function to translate a single file to a specific language
translate_file() {
    local input_file="$1"
    local target_lang_code="$2"
    local target_lang_name="$3"
    local output_dir="$4"
    local source_lang="$5"
    
    local filename=$(basename "$input_file")
    local filename_no_ext="${filename%.*}"
    local extension="${filename##*.}"
    
    local output_file="$output_dir/${filename_no_ext}_${target_lang_code}.${extension}"
    
    # Create output directory if it doesn't exist
    mkdir -p "$output_dir"
    
    # Check if the translation file already exists
    if [ -f "$output_file" ]; then
        echo "Translation already exists: $output_file"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping $target_lang_name translation."
            return
        fi
    fi
    
    echo "Translating $filename to $target_lang_name..."
    
    # Run the translation script
    if python3 tools/translate_latex.py \
        --source_lang "$source_lang" \
        --target_lang "$target_lang_name" \
        "$input_file" \
        "$output_file"; then
        echo "✓ Translation completed: $output_file"
        
        # Run post-processing to fix any structural issues
        echo "Running post-processing..."
        if [ -f "tools/latex_postprocess.py" ]; then
            temp_fixed_file="${output_file%.*}_temp_fixed.${extension}"
            if python3 tools/latex_postprocess.py "$output_file" -o "$temp_fixed_file"; then
                # Replace original with fixed version if post-processing succeeded
                if [ -f "$temp_fixed_file" ]; then
                    mv "$temp_fixed_file" "$output_file"
                    echo "✓ Post-processing completed: $output_file"
                else
                    echo "⚠ Post-processing completed but no fixed file generated"
                fi
            else
                echo "⚠ Post-processing had issues, but translation file is available: $output_file"
                # Clean up temp file if it exists
                [ -f "$temp_fixed_file" ] && rm "$temp_fixed_file"
            fi
        else
            echo "⚠ Post-processing script not found, skipping"
        fi
        
        echo "✓ Successfully translated to $target_lang_name: $output_file"
    else
        echo "✗ Failed to translate to $target_lang_name"
        return 1
    fi
}

# Function to validate input file
validate_input() {
    local input_file="$1"
    
    if [ ! -f "$input_file" ]; then
        echo "Error: Input file '$input_file' does not exist."
        exit 1
    fi
    
    if [[ ! "$input_file" =~ \.(tex|latex)$ ]]; then
        echo "Warning: Input file doesn't have .tex or .latex extension."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Parse command line arguments
TARGET_LANG=""
TRANSLATE_ALL=false
OUTPUT_DIR=""
SOURCE_LANG="English"
INPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--lang)
            TARGET_LANG="$2"
            shift 2
            ;;
        -a|--all)
            TRANSLATE_ALL=true
            shift
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--source)
            SOURCE_LANG="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "$INPUT_FILE" ]; then
                INPUT_FILE="$1"
            else
                echo "Error: Multiple input files specified. Only one file is supported."
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$INPUT_FILE" ]; then
    echo "Error: No input file specified."
    usage
    exit 1
fi

if [ "$TRANSLATE_ALL" = false ] && [ -z "$TARGET_LANG" ]; then
    echo "Error: Either specify a target language (-l) or use --all flag."
    usage
    exit 1
fi

if [ "$TRANSLATE_ALL" = true ] && [ -n "$TARGET_LANG" ]; then
    echo "Error: Cannot use both --all and --lang options simultaneously."
    usage
    exit 1
fi

# Validate target language if specified
if [ -n "$TARGET_LANG" ] && [ -z "${languages[$TARGET_LANG]}" ]; then
    echo "Error: Unsupported language code '$TARGET_LANG'."
    echo "Supported codes: ${!languages[*]}"
    exit 1
fi

# Validate input file
validate_input "$INPUT_FILE"

# Set default output directory if not specified
if [ -z "$OUTPUT_DIR" ]; then
    INPUT_DIR=$(dirname "$INPUT_FILE")
    OUTPUT_DIR="$INPUT_DIR/translations"
fi

echo "Input file: $INPUT_FILE"
echo "Output directory: $OUTPUT_DIR"
echo "Source language: $SOURCE_LANG"

# Check if python scripts exist
if [ ! -f "tools/translate_latex.py" ]; then
    echo "Error: translate_latex.py not found in tools/ directory."
    echo "Please ensure the script is in the correct location."
    exit 1
fi

if [ ! -f "tools/latex_postprocess.py" ]; then
    echo "Warning: latex_postprocess.py not found in tools/ directory."
    echo "Post-processing will be skipped."
fi

# Perform translation(s)
if [ "$TRANSLATE_ALL" = true ]; then
    echo "Translating to all supported languages..."
    
    failed_translations=()
    successful_translations=()
    
    for code in "${!languages[@]}"; do
        if translate_file "$INPUT_FILE" "$code" "${languages[$code]}" "$OUTPUT_DIR" "$SOURCE_LANG"; then
            successful_translations+=("${languages[$code]}")
        else
            failed_translations+=("${languages[$code]}")
        fi
        echo "---"
    done
    
    echo "Translation Summary:"
    echo "Successful: ${#successful_translations[@]} languages"
    echo "Failed: ${#failed_translations[@]} languages"
    
    if [ ${#failed_translations[@]} -gt 0 ]; then
        echo "Failed translations: ${failed_translations[*]}"
    fi
    
else
    echo "Translating to ${languages[$TARGET_LANG]}..."
    translate_file "$INPUT_FILE" "$TARGET_LANG" "${languages[$TARGET_LANG]}" "$OUTPUT_DIR" "$SOURCE_LANG"
fi

echo "Translation process completed."