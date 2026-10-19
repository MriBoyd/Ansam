from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _load_workflow() -> dict[Any, Any]:
    assert CI_WORKFLOW_PATH.is_file(), f"Missing CI workflow at {CI_WORKFLOW_PATH}"
    loaded = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _get_triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML 1.1 parses bare `on` as boolean True unless quoted.
    triggers = workflow.get("on") or workflow.get(True)
    assert isinstance(triggers, dict)
    return triggers


def test_ci_workflow_triggers_on_main_push_and_pull_request() -> None:
    workflow = _load_workflow()
    triggers = _get_triggers(workflow)

    assert "push" in triggers
    assert triggers["push"].get("branches") == ["main"]
    assert "pull_request" in triggers
    assert triggers["pull_request"].get("branches") == ["main"]


def test_ci_workflow_matrix_covers_python_310_311_312() -> None:
    workflow = _load_workflow()
    jobs = workflow.get("jobs", {})
    assert "test" in jobs

    test_job = jobs["test"]
    assert test_job.get("runs-on") == "ubuntu-latest"

    matrix = test_job.get("strategy", {}).get("matrix", {})
    assert matrix.get("python-version") == ["3.10", "3.11", "3.12"]


def test_ci_workflow_installs_dependencies_and_runs_active_unit_tests() -> None:
    workflow = _load_workflow()
    steps = workflow["jobs"]["test"]["steps"]

    uses_steps = [step.get("uses", "") for step in steps if "uses" in step]
    assert any(u.startswith("actions/checkout@") for u in uses_steps)
    assert any(u.startswith("actions/setup-python@") for u in uses_steps)

    run_commands = {
        step.get("name"): step.get("run", "") for step in steps if "run" in step
    }
    assert "Install dependencies" in run_commands
    install_cmd = run_commands["Install dependencies"]
    assert "pip install --upgrade pip" in install_cmd
    assert "pip install -r requirements.txt" in install_cmd
    assert 'pip install -e ".[dev]"' in install_cmd

    assert "Run unit tests" in run_commands
    test_cmd = run_commands["Run unit tests"]
    assert "pytest -v" in test_cmd
    for test_module in (
        "tests/test_circuit_breaker.py",
        "tests/test_auth_manager.py",
        "tests/test_rate_limiter.py",
        "tests/test_config.py",
        "tests/test_extract_registry.py",
        "tests/test_mcp_server_production.py",
        "tests/test_ci_workflow.py",
    ):
        assert test_module in test_cmd
        assert (REPO_ROOT / test_module).is_file()
