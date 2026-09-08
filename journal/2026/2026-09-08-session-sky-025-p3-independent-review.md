---
date: 2026-09-08
time: 10:50:41
kind: session
title: SKY-025 P3 independent review
tier_touched: [T1]
grants: []
refs: [SKY-025, "PR #215", "PR #216"]
thread_status: open
---

# 2026-09-08 · session · SKY-025 P3 independent review

## What happened

Ali requested one complete P3/G2 review covering #215 and #216 together. Read the review
prompt, directive, disposition map and relevant construction/git/docs/collector contracts.
The initial cwd /home/aliammar/skynet reports a bare Git repository; git status failed there.
Created /tmp/skynet-sky-025-p3-review on plan/sky-025-p3-review from reviewed remote main.
No implementation transcript was used. The raw budget/workflow/gate-pause episodes were
consulted only to establish the recorded user-authorized scope changes.

GitHub confirmed #215 merged into main on 2026-09-07 at
05b6326c46506b1c936fbaae724a083d8a218954 and #216 on 2026-09-08 at
8e6c8502ba7c9ce8e9d39fe9bd6d5fd5a45a36df. Main was the latter SHA.
The packet starting SHA was 17db700c22cb17ad219655674eada344c215029a;
the intervening f21442c44d34baf71e01ca8938ea1305c82242f6 (#214) adds P2 review/planning
and P3 authorization, with no implementation. Compared the combined change from both the
packet starting SHA and f21442c to main, then traced current callers/consumers and tests.
Session turn metadata reports gpt-6-astra, medium; the installed model catalog supports it,
and bin/agent review dry-run resolves the same model/effort. No helper was used.

## Actions & outcomes

- `gh pr view 215/216 --repo aliammar03/skynet --json url,state,mergedAt,mergeCommit,baseRefName`
  (one invocation per PR) and `gh api repos/aliammar03/skynet/commits/main --jq .sha`
  established the merge prerequisites. `gh pr checks` for both PRs showed all four checks green,
  including their host closure builds. I did not independently build or activate a host closure.
- `nix develop --no-write-lock-file -c pytest -q` returned 87 passed in 9.46s.
  Inspected real CLI transport substitution, pool/member/resource/job/task projections,
  failure retention and redaction, and default shell chain tests.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` passed;
  `nix develop --no-write-lock-file -c mypy src/skynet` passed for six source files.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` returned 0;
  the package checks include source and installed-module tests.
  `nix flake check --no-write-lock-file --no-build` returned all checks passed, retaining
  system-rename, missing app-meta and custom deploy-output warnings.
- `bin/skynet doctor --json` returned 0, version 0.1.0/Python 3.13.15 through offline Nix.
  `bin/skynet collect-status --repo /tmp/skynet-sky-025-p3-review --json` returned 3 with a
  redacted unavailable report because this construction tree has no core marker.
- Full `.githooks/pre-commit` returned 0: hard invariants and retained shell suites passed,
  including 47 entity cases with real SQLite checks, 82 agent routing cases and both nightly
  suites. Python checks were run independently above; this planning branch does not stage
  implementation changes to trigger the hook's conditional Python block. The five paused
  documentation/style suites were not run and are not counted as passing.
- Ran the following independent probes with
  `nix develop --no-write-lock-file -c env PYTHONPATH=/tmp/skynet-sky-025-p3-review/src:/tmp/skynet-sky-025-p3-review/tests pytest -q /tmp/skynet_p3_review_probes.py`.
  Result: three diagnostic assertions passed in 1.70s. They assert observed defective/limited
  behavior, not repaired acceptance behavior. All files and child processes are synthetic.

**R1, priority P2:** after successful default collection, failing initial marker replacement
returns 1 but ordinary status returns 0. Existing tests cover the same setup only with a newer
since timestamp. bin/ops query/entities and standalone factual rendering supply no since value,
so the unsuccessful default refresh does not invalidate their gate. The nightly cutoff works.
The fix packet requires default consumers to see unavailable evidence after this setup failure.

**R2, priority P2:** the subprocess timeout test in the implementation only injects
TimeoutExpired. A real shell reader with a child sleeping 0.6s timed out at 0.15s, the collection
returned failure and released its lock, then the child created inventory/late-write. The wrapper
kills/reaps only the immediate process. Remaining shell scripts invoke pipelines and external
commands, so cleanup must encompass descendants before continuing or releasing the lock.

The direct explicit-output command also leaves a prior default marker valid when that isolated
attempt fails without changing bytes. I did not issue a separate finding for it: the packet and
nix/README explicitly distinguish isolated output from default refresh evidence. The repair
packet concerns failed default collection and its consumers.

Probe source (save as a temporary Python file; adjust only the checkout paths in the command):

```python
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from skynet import collection, proxmox
from skynet.cli import main
from test_collection import run, status

pytest_plugins = ["test_proxmox", "test_collection"]


def test_setup_failure_leaves_default_status_success(repo, credentials, transport, capsys, monkeypatch):
    assert run(repo, credentials, capsys)[0] == 0
    previous = (repo / "inventory/proxmox-core.json").read_bytes()

    def fail_replace(*args):
        raise OSError("synthetic read-only inventory")

    monkeypatch.setattr(proxmox.os, "replace", fail_replace)
    assert run(repo, credentials, capsys)[0] == 1
    assert (repo / "inventory/proxmox-core.json").read_bytes() == previous
    assert status(repo, capsys) == 0


def test_direct_core_failure_leaves_default_status_success(repo, credentials, transport, capsys):
    assert run(repo, credentials, capsys)[0] == 0
    assert main(["collect", "proxmox", "core", "--output",
                 str(repo / "inventory/proxmox-core.json"), "--credentials-file",
                 str(repo / "missing.env"), "--json"]) == 3
    capsys.readouterr()
    assert status(repo, capsys) == 0


def test_real_timeout_leaves_descendant_writing_after_collection_returns(
    repo, credentials, transport, capsys, monkeypatch,
):
    reader = repo / "scripts/slow-reader.sh"
    destination = repo / "inventory/late-write"
    child = repo / "delayed_writer.py"
    child.write_text("import time\nfrom pathlib import Path\n"
                     f"time.sleep(0.6)\nPath({str(destination)!r}).touch()\n")
    reader.write_text(f"#!{shutil.which('bash')}\n{sys.executable} {child}\nwait\n")
    reader.chmod(0o755)
    monkeypatch.setattr(collection, "REMAINING", (("slow", reader.name),))
    real_run = subprocess.run

    def short_timeout(*args, **kwargs):
        kwargs["timeout"] = 0.15
        return real_run(*args, **kwargs)

    monkeypatch.setattr(collection.subprocess, "run", short_timeout)
    code, report = run(repo, credentials, capsys)
    assert code == 1
    assert report["collectors"][-1]["outcome"] == "failure"
    assert not destination.exists()
    time.sleep(0.8)
    assert destination.exists()
```

No lab API call, production credential read, inventory refresh, profile installation, root
grant, service/timer modification, NixOS activation or recovery drill was performed.
Real endpoint parity/TLS and independent workstation/kit/state/payload recovery remain
unverified. Those map prerequisites still gate the first live transition; construction tests
do not satisfy them.

Chose FIX for complete P3/G2, retained accepted progress 2/24, and replaced the completed
implementation packets with one bounded Astra Medium fix packet. Preserved the prior packets
in reviewed git history. G2 remains open; no reason to reorder the remaining numbered roadmap
or build a process/workflow framework. Ali's documentation-gate pause and P24 restoration
requirement remain intact. Updated the map with the two qualifications.

## Graveyard — tried & abandoned

- Initial `git status` from the bare main directory failed; used an isolated registered worktree.
- Passing PYTHONPATH outside nix develop did not expose test_collection to the probe:
  pytest stopped with ModuleNotFoundError. Passed env after `nix develop -c`; probes then ran.
- A status update patch expected an older updated date; apply_patch refused it. Main already
  carries updated: 2026-09-08. Applied the status insertion without changing that date.
- Did not treat the isolated-command observation as a third defect or green CI as phase acceptance.

## Follow-ups / open threads

- After Ali merges this planning PR, start a fresh Astra Medium task:
  Read planning/prompts/execute.md and execute SKY-025 Phase 3 fixes from §5.
  Then review all P3 implementation (#215, #216 and the merged fix PR) together.
  P4 stays unreleased and accepted progress remains 2/24.
- Before any live transition, supply the map's independent workstation/state/payload recovery
  evidence. No live grant or activation is released by this repair packet.
