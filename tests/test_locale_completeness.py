"""Locale completeness locks (i18n audit 2026-08-08).

The audit's worst finding: 21 recent msgids were absent from 31 of
the 33 catalogs, so raw symbolic keys could reach users' screens.
Train 0098 synchronised every catalog with explicit non-fuzzy
English fallbacks and recompiled every .mo. These locks make the
repaired state a verified property of the repository: full POT
coverage in every PO, the audit keys present in every compiled MO,
directory-only locale discovery, and ratchets that forbid the fuzzy
and empty-entry debts from growing while real translation happens.
"""

import glob
import os
import re
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE_DIR = os.path.join(ROOT, "alirpunkto", "locale")

#: The audit's synchronised keys — spot-checked in every compiled MO.
AUDIT_KEYS = (
    "your_profile_title", "your_profile_introduction", "cancel_button",
    "your_groups_label", "group_label_community", "group_label_board",
    "group_label_cooperators", "departure_date_label",
)

#: Ratchet baselines, measured after the 0098 synchronisation. They
#: may only go DOWN as real translations replace the debt.
FUZZY_BASELINE = 747
EMPTY_BASELINE = 140


def _po_msgids(path):
    ids = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        match = re.match(r'^msgid "(.+)"\s*$', line)
        if match:
            ids.add(match.group(1))
    return ids


def _mo_msgids(path):
    data = open(path, "rb").read()
    magic = struct.unpack("<I", data[:4])[0]
    order = "<" if magic == 0x950412DE else ">"
    count, orig_offset = struct.unpack(order + "II", data[8:16])
    ids = set()
    for index in range(count):
        length, offset = struct.unpack(
            order + "II", data[orig_offset + 8 * index:
                               orig_offset + 8 * index + 8])
        ids.add(data[offset:offset + length].decode(
            "utf-8", errors="replace"))
    return ids


def _catalogs():
    return sorted(glob.glob(os.path.join(
        LOCALE_DIR, "*", "LC_MESSAGES", "alirpunkto.po")))


def test_every_catalog_covers_the_full_pot():
    pot_ids = _po_msgids(os.path.join(LOCALE_DIR, "alirpunkto.pot"))
    assert len(pot_ids) > 300
    offenders = {}
    for po in _catalogs():
        missing = pot_ids - _po_msgids(po)
        if missing:
            offenders[po.split(os.sep)[-3]] = sorted(missing)[:5]
    assert not offenders, (
        "POT keys missing from catalogs (raw msgids would reach "
        f"users): {offenders}")


def test_the_audit_keys_reach_every_compiled_mo():
    """A stale .mo silently undoes a .po repair: the runtime reads
    the binary. The audit keys must be inside every compiled MO."""
    for po in _catalogs():
        mo = po[:-3] + ".mo"
        assert os.path.exists(mo), f"missing compiled catalog: {mo}"
        ids = _mo_msgids(mo)
        lang = po.split(os.sep)[-3]
        for key in AUDIT_KEYS:
            assert key in ids, f"{lang}: {key} absent from the .mo"


def test_locale_discovery_lists_directories_only():
    from alirpunkto.constants_and_globals import get_locales
    locales = get_locales()
    assert len(locales) == len(set(locales)), "duplicate locales"
    assert "en" in locales
    for locale in locales:
        assert os.path.isdir(os.path.join(LOCALE_DIR, locale)), locale


def test_the_translation_debt_only_shrinks():
    fuzzy = empty = 0
    for po in _catalogs():
        text = open(po, encoding="utf-8", errors="replace").read()
        fuzzy += text.count("#, fuzzy")
        empty += len(re.findall(r'msgstr ""\n\n', text))
    assert fuzzy <= FUZZY_BASELINE, (
        f"fuzzy entries grew: {fuzzy} > {FUZZY_BASELINE} — translate "
        "or use explicit English fallbacks, never fuzzy")
    assert empty <= EMPTY_BASELINE, (
        f"empty msgstr grew: {empty} > {EMPTY_BASELINE}")
