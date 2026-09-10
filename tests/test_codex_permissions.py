"""Contracts for Codex's prompt-free aliammar construction posture."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_CONFIG = ROOT / "nix/home/aliammar.nix"
PROJECT_CONFIG = ROOT / ".codex/config.toml"


def codex_section() -> str:
    text = HOME_CONFIG.read_text(encoding="utf-8")
    return text.split("programs.codex = {", 1)[1].split("programs.opencode = {", 1)[0]


def rendered_rules() -> str:
    match = re.search(r"rules\.skynet = ''\n(.*?)\n\s*'';", codex_section(), re.DOTALL)
    if match is None:
        raise AssertionError("programs.codex.rules.skynet was not found")
    return textwrap.dedent(match.group(1))


class CodexPermissionContractTests(unittest.TestCase):
    def test_home_manager_owns_no_prompt_full_account_posture(self) -> None:
        section = codex_section()
        self.assertIn('approval_policy = "never";', section)
        self.assertIn('sandbox_mode = "danger-full-access";', section)
        self.assertNotIn('approval_policy = "on-request";', section)
        self.assertEqual(section.count("prefix_rule("), 3)
        self.assertNotIn('decision = "prompt"', section)

    def test_project_and_roles_do_not_override_the_session(self) -> None:
        project = PROJECT_CONFIG.read_text(encoding="utf-8")
        self.assertNotRegex(project, r"(?m)^\s*approval_policy\s*=")
        self.assertNotRegex(project, r"(?m)^\s*sandbox_mode\s*=")
        self.assertNotIn("[sandbox_workspace_write]", project)
        for role in (ROOT / ".codex/agents").glob("*.toml"):
            self.assertNotRegex(
                role.read_text(encoding="utf-8"),
                r"(?m)^\s*sandbox_mode\s*=",
                role.name,
            )

    def test_installed_execpolicy_hard_blocks_only_special_cases(self) -> None:
        if shutil.which("codex") is None:
            self.skipTest("installed Codex is verified on the target host, not supplied by CI")
        rules = rendered_rules()
        with tempfile.TemporaryDirectory(prefix="codex-rules-") as temporary:
            path = Path(temporary) / "skynet.rules"
            path.write_text(rules, encoding="utf-8")

            blocked = (
                ["gh", "pr", "merge", "250"],
                ["bin/grant-root", "docker-dmz", "1h"],
                ["./bin/grant-root", "docker-dmz", "1h"],
            )
            normal = (
                ["git", "switch", "feature/example"],
                ["git", "push", "origin", "feature/example"],
                ["gh", "pr", "create", "--draft"],
                ["nix", "develop", "-c", "pytest", "-q"],
                ["mkdir", "-p", "/tmp/codex-example"],
            )
            for command in blocked:
                result = self.check_policy(path, command)
                self.assertEqual(result.get("decision"), "forbidden", command)
            for command in normal:
                result = self.check_policy(path, command)
                self.assertNotIn(result.get("decision"), {"prompt", "forbidden"}, command)

    def check_policy(self, path: Path, command: list[str]) -> dict[str, object]:
        completed = subprocess.run(
            ["codex", "execpolicy", "check", "--rules", str(path), *command],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
        return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()
