"""Behavioral tests for both local Skynet command entry points."""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
Run = Callable[..., subprocess.CompletedProcess[str]]


def entrypoint_runners() -> list[Callable[[Path], Run]]:
    """Select an entry point when package build stages cannot expose both yet."""
    requested = os.environ.get("SKYNET_ENTRYPOINT")
    runners = {"module": module_runner, "console": console_runner}
    if requested is None:
        return list(runners.values())
    return [runners[requested]]


def module_runner(tmp_path: Path) -> Run:
    """Run the source module from outside the checkout."""
    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "skynet", *arguments],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    return run


def console_runner(tmp_path: Path) -> Run:
    """Run the Nix-packaged console entry point from outside the checkout."""
    executable = shutil.which("skynet")
    assert executable is not None, "run CLI tests through `nix develop -c pytest -q`"

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [executable, *arguments],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    return run


@pytest.fixture(params=entrypoint_runners())
def run(request: pytest.FixtureRequest, tmp_path: Path) -> Run:
    return request.param(tmp_path)  # type: ignore[no-any-return]


def test_help_and_version(run: Run) -> None:
    help_result = run("--help")
    version_result = run("--version")

    assert help_result.returncode == 0
    assert "doctor" in help_result.stdout
    assert version_result.returncode == 0
    assert version_result.stdout.startswith("skynet ")


def test_doctor_human_and_json_agree(run: Run) -> None:
    human = run("doctor")
    machine = run("doctor", "--json")

    assert human.returncode == 0
    assert machine.returncode == 0
    report = json.loads(machine.stdout)
    human_fields = dict(
        line.split(": ", maxsplit=1) for line in human.stdout.splitlines()[1:] if ": " in line
    )
    assert report == {
        "outcome": "success",
        "scope": "runtime",
        "version": human_fields["version"],
        "python_version": human_fields["python_version"],
    }
    assert human_fields["outcome"] == "success"
    assert human_fields["scope"] == "runtime"


@pytest.mark.parametrize("arguments", [(), ("collect",), ("--unknown",)])
def test_invalid_commands_and_options_fail_with_a_diagnostic(run: Run, arguments: tuple[str, ...]) -> None:
    result = run(*arguments)

    assert result.returncode == 2
    assert result.stderr.strip()
