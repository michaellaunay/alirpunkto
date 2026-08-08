"""Locks for the manual-producing scenario framework.

The user manual regenerates from the validation scenarios: every
green test-stack run yields the fr/en pages with their screenshots
as the user-manual artifact. These locks pin the chain — solver,
scenarios, generator, workflow wiring — without needing a browser.
"""

import json
import os
import py_compile
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "e2e_scenarios"))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_the_challenge_solver_reads_both_languages():
    from framework import solve_all_challenges, solve_math_challenge
    assert solve_math_challenge("three times seven plus two") == 23
    assert solve_math_challenge("sept fois neuf, plus un", "fr") == 64
    body = ("A: two times two plus one\nB: nine times one plus zero\n"
            "C: five times three plus four\nD: one times one plus one\n")
    assert solve_all_challenges(body) == {"A": 5, "B": 9, "C": 19, "D": 2}


def test_the_scenarios_and_tools_compile():
    for name in ("e2e_scenarios/framework.py",
                 "e2e_scenarios/scenario_registration.py",
                 "e2e_scenarios/run_all.py",
                 "generate_user_manual.py"):
        py_compile.compile(os.path.join(ROOT, "tools", name), doraise=True)


def test_the_scenarios_use_the_registration_form_field_names():
    """The journeys must speak the template's exact field names —
    result_{label} is built dynamically for the four challenges."""
    scenario = _read("tools", "e2e_scenarios", "scenario_registration.py")
    template = _read("alirpunkto", "templates", "register.pt")
    for field in ("email", "choice", "pseudonym", "password_confirm",
                  "result_"):
        assert field in scenario, f"scenario no longer fills {field}"
    for field in ("email", "choice", "result_A", "result_B",
                  "result_C", "result_D"):
        assert f'name="{field}"' in template, (
            f"register.pt renamed {field}: update the scenarios")


def test_the_generator_builds_bilingual_pages():
    from generate_user_manual import build
    shots = tempfile.mkdtemp()
    out = tempfile.mkdtemp()
    with open(os.path.join(shots, "s_01_a.png"), "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(shots, "manifest.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"scenarios": [{
            "slug": "s", "title_fr": "T", "title_en": "T",
            "steps": [{"index": 1, "file": "s_01_a.png",
                       "fr": "Légende.", "en": "Caption."}]}]}, handle)
    build(shots, out)
    assert "Légende." in _readfile(out, "fr", "s.md")
    assert "Caption." in _readfile(out, "en", "s.md")
    assert os.path.exists(os.path.join(out, "en", "images", "s_01_a.png"))


def _readfile(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as handle:
        return handle.read()


def test_the_workflow_runs_scenarios_and_publishes_the_manual():
    workflow = _read(".github", "workflows", "test-stack.yml")
    assert "run_all.py" in workflow
    assert "generate_user_manual.py" in workflow
    assert "name: user-manual" in workflow
    assert workflow.index("run_all.py") < workflow.index("user-manual")


def test_every_scenario_step_carries_both_captions():
    """The manual is bilingual by contract: every step() call ships
    fr AND en texts — the framework signature enforces it, this lock
    keeps anyone from defaulting one side."""
    scenario = _read("tools", "e2e_scenarios", "scenario_registration.py")
    assert scenario.count("scenario.step(") >= 10
    from framework import Scenario
    import inspect
    params = list(inspect.signature(Scenario.step).parameters)
    assert params[-2:] == ["fr", "en"]
