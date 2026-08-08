#!/usr/bin/env python3
"""Build the bilingual user manual from the scenario manifest.

Input: the screenshot directory holding manifest.json and the PNG
captures the scenarios produced. Output: manual/fr/*.md and
manual/en/*.md with the images copied alongside — the documentation
regenerates identically on every green run.

Usage: generate_user_manual.py <shot_dir> <output_dir>
"""

import json
import os
import shutil
import sys


def build(shot_dir: str, out_dir: str) -> list:
    manifest_path = os.path.join(shot_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print("[manual] no manifest.json — no scenario completed, "
              "nothing to build")
        return []
    with open(manifest_path,
              encoding="utf-8") as handle:
        manifest = json.load(handle)
    written = []
    for lang, title_key, caption_key, intro in (
        ("fr", "title_fr", "fr",
         "Guide illustré généré automatiquement depuis les scénarios "
         "de validation — chaque capture provient d'un parcours réel "
         "vérifié par l'intégration continue."),
        ("en", "title_en", "en",
         "Illustrated guide generated automatically from the "
         "validation scenarios — every capture comes from a real "
         "journey checked by continuous integration."),
    ):
        lang_dir = os.path.join(out_dir, lang)
        img_dir = os.path.join(lang_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        index_lines = [f"# {'Manuel utilisateur' if lang == 'fr' else 'User manual'}",
                       "", intro, ""]
        for scenario in manifest["scenarios"]:
            lines = [f"# {scenario[title_key]}", "", intro, ""]
            for step in scenario["steps"]:
                shutil.copy(os.path.join(shot_dir, step["file"]), img_dir)
                lines += [f"## {step['index']}. {step[caption_key]}", "",
                          f"![{step[caption_key]}](images/{step['file']})",
                          ""]
            path = os.path.join(lang_dir, f"{scenario['slug']}.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
            written.append(path)
            index_lines.append(f"- [{scenario[title_key]}]({scenario['slug']}.md)")
        with open(os.path.join(lang_dir, "index.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("\n".join(index_lines) + "\n")
        written.append(os.path.join(lang_dir, "index.md"))
    return written


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    for path in build(sys.argv[1], sys.argv[2]):
        print("wrote", path)
