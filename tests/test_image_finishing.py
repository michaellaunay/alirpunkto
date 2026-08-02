"""Sixth audit pass (2026-08-01, §11) — image finishing.

Four reserves remained on the production image: an editable install
where an immutable image wants a wheel (§11.1); an implicit assumption
that every locked dependency ships a wheel — a future sdist would
silently compile against builder-only libraries and fail at runtime
(§11.2); apt resolving against the moving archive (§11.3); and COPY .
shipping the CI tree, the extra locks and dev config into the runtime
stage (§11.4). Investigating §11.2 also uncovered that the "all
wheels" belief was a pip-cache illusion: three locked packages are
sdist-only on PyPI — pure python, hence the NAMED exception list. And
reworking §11.4 exposed a latent first-start crash: .dockerignore
excludes docker/, so apply_server_overrides.py — which the entrypoint
calls whenever compose sets PYRAMID_LISTEN (it does, by default) —
never reached the image at all.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PURE_SDIST_EXCEPTIONS = (
    "pyramid-chameleon",
    "pyramid-handlers",
    "validate-email",
)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def _pyramid_stages():
    dockerfile = _read("docker", "DockerfilePyramid")
    builder, runtime = dockerfile.split("# ── Runtime stage")
    return dockerfile, builder, runtime


def test_the_application_installs_as_a_wheel_not_editable():
    """§11.1: an immutable image wants an installed wheel, not an
    editable finder pointing back at a source tree."""
    dockerfile, _, _ = _pyramid_stages()
    assert "--no-build-isolation --no-deps ." in dockerfile
    assert " -e ." not in dockerfile


def test_wheels_are_enforced_with_the_named_pure_exceptions():
    """§11.2: --only-binary=:all: makes any future sdist fail the build
    explicitly. The three named exceptions are sdist-only on PyPI and
    pure python (they build py3-none-any wheels), so nothing native is
    ever compiled — and each of them must actually be in the runtime
    lock, or the exception is stale."""
    dockerfile, _, _ = _pyramid_stages()
    assert "--only-binary=:all:" in dockerfile
    assert "--no-binary=" + ",".join(PURE_SDIST_EXCEPTIONS) in dockerfile
    lock = _read("requirements.lock")
    for name in PURE_SDIST_EXCEPTIONS:
        assert re.search(rf"(?m)^{name}==", lock), name


def test_no_stage_carries_a_compiler_or_dev_headers():
    """§11.2 consequence: with wheels enforced, the compile path is
    unreachable — the builder's compilers and dev headers were dead
    weight and a trap."""
    dockerfile, _, _ = _pyramid_stages()
    assert "build-essential" not in dockerfile
    assert not re.search(r"\S+-dev\b", dockerfile)


def test_the_runtime_stage_copies_an_explicit_allowlist():
    """§11.4: the runtime stage no longer takes the whole context."""
    _, _, runtime = _pyramid_stages()
    assert not re.search(r"(?m)^COPY (--chown=\S+ )?\. ", runtime)
    assert "COPY --chown=1001:1001 production.ini .env.example" in runtime
    assert "docker/apply_server_overrides.py" in runtime


def test_the_context_excludes_ci_and_the_extra_locks():
    """§11.4: .github/ and the test/quality locks belong to no image."""
    ignore = _read(".dockerignore")
    for line in (".github/", "requirements-test.lock",
                 "requirements-quality.lock", "development.ini"):
        assert f"\n{line}\n" in ignore, line


def test_the_override_helper_reaches_the_image():
    """The latent first-start crash: start_pyramid.sh calls
    docker/apply_server_overrides.py whenever PYRAMID_LISTEN or
    PYRAMID_TRUSTED_PROXY is set — compose sets both by default — but
    .dockerignore excludes docker/, so COPY . never shipped the helper.
    Both the re-inclusion and the explicit COPY must exist."""
    ignore = _read(".dockerignore")
    assert "!docker/apply_server_overrides.py" in ignore
    _, _, runtime = _pyramid_stages()
    assert re.search(
        r"(?m)^COPY \S* ?docker/apply_server_overrides\.py", runtime)


def test_every_dockerfile_offers_the_snapshot_switch():
    """§11.3: opt-in strict reproducibility — the deb822 Snapshot field
    (verified on noble's apt) is available on all four images and wired
    through both compose files."""
    for path in glob.glob(os.path.join(ROOT, "docker", "Dockerfile*")):
        content = open(path, encoding="utf-8").read()
        assert 'ARG UBUNTU_SNAPSHOT=""' in content, path
        assert "Snapshot: ${UBUNTU_SNAPSHOT}" in content, path
    for name in ("docker-compose.yaml", "test-docker-compose.yaml"):
        compose = _read("docker", name)
        assert "ALIRPUNKTO_UBUNTU_SNAPSHOT" in compose, name


def test_the_prod_entrypoint_never_installs_at_runtime():
    """P1 philosophy completed: the production container runs what the
    image carries, full stop."""
    script = _read("docker", "start_pyramid.sh")
    assert "pip install" not in script


def test_the_test_stack_mounts_the_lock_it_installs():
    """§11.4: the test lock left the image; the test compose bind-mounts
    it and the test entrypoint enforces the same wheel policy — with no
    editable reinstall, the image already carries the application."""
    compose = _read("docker", "test-docker-compose.yaml")
    assert "requirements-test.lock:/home/alirpunkto/app/" \
           "requirements-test.lock:ro" in compose
    script = _read("docker", "start_test_pyramid.sh")
    assert "--only-binary=:all:" in script
    assert " -e ." not in script


def test_the_wheel_carries_every_tracked_package_file(tmp_path):
    """§11.1's real trap: a wheel missing templates or catalogues would
    import fine and break on the first rendered page. Build the actual
    wheel and require file-for-file parity with the tracked package."""
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps",
         "--no-build-isolation", "-w", str(tmp_path), ROOT],
        check=True)
    wheels = list(tmp_path.glob("alirpunkto-*.whl"))
    assert len(wheels) == 1, wheels
    in_wheel = {name for name in zipfile.ZipFile(wheels[0]).namelist()
                if name.startswith("alirpunkto/")}
    tracked = set(subprocess.check_output(
        ["git", "ls-files", "alirpunkto"], text=True, cwd=ROOT
    ).splitlines())
    missing = sorted(tracked - in_wheel)
    assert not missing, missing
