#!/bin/bash
# Author: Michaël Launay
# Date: 2024-08-09
# Description: This script translates files from the 'en' locale to other
#     locales using the translate.py script, which leverages ChatGPT for
#     translation.

# Declare an associative array to map language codes to language names
declare -A languages
export SOURCES=~/workspace/alirpunkto
languages=(
  ["bg"]="Bulgarian"
  ["cs"]="Czech"
  ["da"]="Danish"
  ["eo"]="Esperanto"
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


# List all .pot and .po files in the English locale directory
export FILES=$(cd $SOURCES/alirpunkto/locale/en/LC_MESSAGES/ && ls -1 *.pt *.po)

# Iterate over each language code and file
for code in "${!languages[@]}"; do
    for FILE in $FILES; do
        # Check if the translation file does not exist in the target locale
        if [ ! -f $SOURCES/alirpunkto/locale/$code/LC_MESSAGES/$FILE ]; then
            # Run the translation script
            python3 tools/translate.py --source_lang english --target_lang "${languages[$code]}" \
            $SOURCES/alirpunkto/locale/en/LC_MESSAGES/$FILE $SOURCES/alirpunkto/locale/$code/LC_MESSAGES/$FILE
        fi
    done
done
