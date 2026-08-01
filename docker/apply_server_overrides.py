"""Derive a container-local Pyramid config with the Docker server values.

Fourth audit pass (2026-08-01, P0): the values in production.ini's
[server:main] are correct for the bare-host deployment (doc chapter 13)
but wrong inside the compose stack — Waitress must bind 0.0.0.0 there
(Apache lives in another container and cannot reach this loopback) and
trust the Apache container's fixed address instead of 127.0.0.1, or the
login throttle folds every visitor onto one window.

The config file is bind-mounted read-only and shared with the bare
host, so it is never edited in place. When PYRAMID_LISTEN and/or
PYRAMID_TRUSTED_PROXY are set, the start scripts call this helper to
write a derived copy next to the original (same directory, so
%(here)s keeps pointing at the application root) and serve that copy.
Only the two lines inside [server:main] are rewritten — the section
targeting mirrors the proven normalizer in docker/init_test.sh.

Usage: apply_server_overrides.py SRC DST
"""
import os
import re
import sys

SERVER_SECTION = re.compile(r"(?ms)^(\[server:main\]\n)(.*?)(?=^\[|\Z)")


def set_option(body: str, name: str, value: str) -> str:
    """Replace ``name = …`` inside a section body, or prepend it."""
    line = f"{name} = {value}"
    pattern = re.compile(rf"(?m)^\s*{name}\s*=.*$")
    if pattern.search(body):
        return pattern.sub(line, body, count=1)
    return line + "\n" + body


def apply_overrides(text: str, listen: str, trusted_proxy: str) -> str:
    match = SERVER_SECTION.search(text)
    if not match:
        raise SystemExit("[apply_server_overrides] no [server:main] section")
    body = match.group(2)
    if listen:
        body = set_option(body, "listen", listen)
    if trusted_proxy:
        body = set_option(body, "trusted_proxy", trusted_proxy)
    return text[: match.start(2)] + body + text[match.end(2) :]


def main(argv: list) -> None:
    if len(argv) != 3:
        raise SystemExit("Usage: apply_server_overrides.py SRC DST")
    src, dst = argv[1], argv[2]
    listen = os.environ.get("PYRAMID_LISTEN", "")
    trusted_proxy = os.environ.get("PYRAMID_TRUSTED_PROXY", "")
    with open(src, encoding="utf-8") as handle:
        text = handle.read()
    text = apply_overrides(text, listen, trusted_proxy)
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(
        f"[apply_server_overrides] wrote {dst} "
        f"(listen={listen or 'unchanged'}, "
        f"trusted_proxy={trusted_proxy or 'unchanged'})"
    )


if __name__ == "__main__":  # pragma: no cover — exercised via subprocess
    main(sys.argv)
