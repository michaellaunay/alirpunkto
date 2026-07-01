# Updated AlirPunkto translation scripts

This archive updates:

- `tools/translate.py`
- `tools/translate.sh`

## Main behavior

The new workflow uses:

- `alirpunkto/locale/alirpunkto.pot` as the canonical list of gettext messages;
- `alirpunkto/locale/en/LC_MESSAGES/alirpunkto.po` as English context;
- `alirpunkto/locale/fr/LC_MESSAGES/alirpunkto.po` as French context;
- the existing target `alirpunkto.po` as the preferred style and terminology source.

For `.po` files, removed messages are removed from the target catalog because the new file is rebuilt from the `.pot` file.

For `.pt` templates, the English locale is the structural source of truth. Missing target templates are created. Stale target templates are removed by default when the corresponding English template no longer exists.

Existing translations are preserved by default when they are present and not fuzzy. Use `--revise-existing` to ask the model to improve existing translations using the English/French context.

## Requirements

```bash
pip install --upgrade openai python-dotenv polib
export OPENAI_API_KEY="..."
```

`msgfmt` is optional but recommended to compile `.po` files into `.mo` files:

```bash
sudo apt install gettext
```

## Install

From the repository root:

```bash
cp /mnt/data/translate.i18n.py tools/translate.py
cp /mnt/data/translate.i18n.sh tools/translate.sh
chmod +x tools/translate.py tools/translate.sh
```

## Preview

```bash
tools/translate.sh --dry-run
```

Preview selected languages:

```bash
tools/translate.sh --dry-run --languages fr,de,es
```

## Update missing and fuzzy entries only

```bash
tools/translate.sh --languages fr,de,es,it,nl
```

## Revise existing translations

```bash
tools/translate.sh --revise-existing --languages de
```

## Force regeneration

```bash
tools/translate.sh --force --languages fr
```

## Keep stale templates

By default, stale `.pt` files that no longer exist in the English locale are removed from target locales.

To disable this cleanup:

```bash
tools/translate.sh --keep-stale
```
