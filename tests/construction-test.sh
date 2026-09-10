#!/usr/bin/env bash
# construction-test.sh — validate the native construction worker role files + the invariant checker.
# The six roles spawn ONLY through Codex's native subagent mechanism (Codex loads each role's full
# contract — instructions, model, and effort — from .codex/agents/<role>.toml). There is no shell
# launcher to mirror, so this gate validates the real role source files, not a reproduction of a parser.
# TIER: T1 — reads repo files and a disposable temp copy only. No network, no tracked-file writes.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

EXPECTED_ROLES=(archivist companion default_executor investigator senior_executor tester)
LEGACY_ROLES=(scout mechanic builder)

pass=0; fail=0
ok()   { printf '  ✓ %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  ✗ %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }

# Check the contracts which are carried by the role files and the current construction surfaces.
# This is deliberately a source-contract check: native Codex owns dispatch, so there is no local
# launcher or workflow runtime to exercise. The temporary fixtures below prove that each assertion
# rejects a meaningful drift instead of merely matching text in the test itself.
construction_contract_check() {
  python3 - "$1" <<'PY'
import pathlib
import re
import sys
import tomllib

root = pathlib.Path(sys.argv[1])
errors = []

expected_roles = (
    "archivist",
    "companion",
    "default_executor",
    "investigator",
    "senior_executor",
    "tester",
)
legacy_roles = ("scout", "mechanic", "builder")

capsule_parts = {
    "companion": (
        "Project Context Scope",
        "Context Task + Goal",
        "Main-Agent Context Guidance",
    ),
    "investigator": (
        "Investigation Context",
        "Evidence Question + Goal",
        "Main-Agent Investigation Guidance",
    ),
    "default_executor": (
        "Implementation Context + Ownership",
        "Implementation Task + Goal",
        "Main-Agent Implementation Guidance",
    ),
    "senior_executor": (
        "Implementation Context + Ownership",
        "Implementation Task + Goal",
        "Main-Agent Implementation Guidance",
    ),
    "tester": (
        "Verification Context",
        "Verification Goal",
        "Main-Agent Verification Guidance",
    ),
    "archivist": (
        "Documentation Context + Audience",
        "Documentation Task + Goal",
        "Main-Agent Documentation Guidance",
    ),
}

capsule_intro = {
    "companion": "Expect an initial package with `Task ID`, then `Project Context Scope`, `Context Task + Goal`, and `Main-Agent Context Guidance`",
    "investigator": "Expect an initial package with `Task ID`, then `Investigation Context`, `Evidence Question + Goal`, and `Main-Agent Investigation Guidance`",
    "default_executor": "Expect `Task ID`, then `Implementation Context + Ownership`, `Implementation Task + Goal`, and `Main-Agent Implementation Guidance`",
    "senior_executor": "Expect `Task ID`, then `Implementation Context + Ownership`, `Implementation Task + Goal`, and `Main-Agent Implementation Guidance`",
    "tester": "Expect an initial package with `Task ID`, then `Verification Context`, `Verification Goal`, and `Main-Agent Verification Guidance`",
    "archivist": "Expect `Task ID`, then `Documentation Context + Audience`, `Documentation Task + Goal`, and `Main-Agent Documentation Guidance`",
}

follow_up_language = {
    "archivist": "follow-ups repeat the task id and carry only the delta",
    "companion": "a follow-up repeats the task id and carries only the delta",
    "default_executor": "a follow-up repeats the task id and carries only the delta",
    "investigator": "a follow-up repeats the task id and carries only the delta",
    "senior_executor": "a follow-up repeats the task id and carries only the delta",
    "tester": "a follow-up repeats the task id and carries only the delta",
}

# Each role uses a role-specific negative context, not just an action-word substring. This matters
# because an imperative such as "Workers orchestrate ..." can contain the same words while reversing
# the boundary. The companion/investigator wording is intentionally different because their contracts
# are read-only context/evidence lanes, but all six still prohibit acting as a worker coordinator.
non_orchestration_marker = {
    "archivist": "Do not orchestrate other workers or decide acceptance.",
    "companion": "You are not a message bus — workers report to Main, not to you.",
    "default_executor": "Do not orchestrate other workers; workers never spawn workers.",
    "investigator": "Do not modify files, implement a solution, coordinate another worker, or make the architecture,",
    "senior_executor": "Do not orchestrate other workers. Never weaken validation",
    "tester": "but do not repair production code, modify durable documentation or Git state, hand-edit generated outputs (`inventory/`, `docs/generated/`), or orchestrate other workers.",
}

all_capsule_headings = tuple(
    dict.fromkeys(heading for parts in capsule_parts.values() for heading in parts)
)


def normalized(text: str) -> str:
    return " ".join(text.split())


def read_text(relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{relative}: cannot read: {exc}")
        return ""


def require(needle: str, haystack: str, label: str) -> None:
    if needle not in haystack:
        errors.append(f"{label}: missing required contract: {needle}")


role_dir = root / ".codex" / "agents"
actual_roles = tuple(sorted(path.stem for path in role_dir.glob("*.toml")))
if actual_roles != tuple(sorted(expected_roles)):
    errors.append(
        "role TOMLs drifted: expected "
        + repr(tuple(sorted(expected_roles)))
        + ", got "
        + repr(actual_roles)
    )
for legacy in legacy_roles:
    if (role_dir / f"{legacy}.toml").exists():
        errors.append(f"retired role TOML remains: {legacy}.toml")

for role in expected_roles:
    path = role_dir / f"{role}.toml"
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"{role}: TOML cannot be loaded: {exc}")
        continue

    instructions = str(document.get("developer_instructions", ""))
    if "sandbox_mode" in document:
        errors.append(f"{role}: sandbox_mode must inherit the spawning aliammar session")
    flat = normalized(instructions)
    lowered = flat.lower()
    require(normalized(capsule_intro[role]), flat, f"{role} capsule introduction")
    require(
        follow_up_language[role],
        lowered,
        f"{role} follow-up capsule contract",
    )
    require(
        "include the task id in every report",
        lowered,
        f"{role} report identity contract",
    )

    wanted_headings = set(capsule_parts[role])
    for heading in all_capsule_headings:
        count = flat.count(f"`{heading}`")
        expected_count = 1 if heading in wanted_headings else 0
        if count != expected_count:
            errors.append(
                f"{role}: capsule heading `{heading}` occurs {count} times; "
                f"expected {expected_count}"
            )

    require(
        non_orchestration_marker[role],
        flat,
        f"{role} worker-does-not-orchestrate boundary",
    )
    if re.search(
        r"\bworkers?\s+(?:(?:may|can|should|will|must)\s+)?(?:orchestrate|coordinate)\b",
        lowered,
    ):
        errors.append(f"{role}: worker contract grants orchestration authority")
    if re.search(r"\bspawn_agent\b|\bagent_type\s*=", instructions, re.IGNORECASE):
        errors.append(f"{role}: worker contract contains a child-dispatch mechanism")

    if role in {"default_executor", "senior_executor"}:
        require("ordinary repair", lowered, f"{role} executor repair ownership")
    if role == "tester":
        require(
            "do not repair production code",
            lowered,
            "tester repair boundary",
        )
        require(
            "ordinary defects route back to the owning executor, then back to you",
            lowered,
            "tester defect-routing contract",
        )

construction = normalized(read_text("docs/conventions/construction.md"))
runbook = normalized(read_text("runbooks/construction-delegation.md"))

# These are the current, machine-provable lifecycle and ownership contracts. They intentionally do
# not assert route chronology or prose history; only the durable boundaries that dispatch/roles need.
for phrase, label in (
    (
        "Workers are native Codex subagents; they never orchestrate children.",
        "construction worker orchestration boundary",
    ),
    (
        "**Default Executor** — owns local discovery, implementation, self-check, deployment operations, and ordinary repair inside one bounded package.",
        "construction Executor repair ownership",
    ),
    (
        "**Tester** — independent verifier owning the assigned verification, test assets, and execution; it does not perform production repair.",
        "construction Tester repair boundary",
    ),
    (
        "Executor implements + self-checks → Tester independently verifies → ordinary defect?",
        "construction verification sequence",
    ),
    (
        "yes → same owning Executor repairs → same Tester rechecks → PASS",
        "construction same-Tester recheck",
    ),
    (
        "Companion | `gpt-5.6-luna` | xhigh | `aliammar` account; read-only ownership | exactly 1 persistent per deployment",
        "exactly-one Companion quantity",
    ),
    (
        "Senior Executor | `gpt-5.6-sol` | medium | `aliammar` account | at most 1",
        "at-most-one Senior quantity",
    ),
    (
        "exactly one persistent Companion per deployment",
        "exactly-one Companion semantic limit",
    ),
    (
        "at most one Senior Executor",
        "at-most-one Senior semantic limit",
    ),
):
    require(normalized(phrase).lower(), construction.lower(), label)

for phrase, label in (
    (
        "Spawn a worker only through the native Codex subagent mechanism",
        "runbook native worker dispatch",
    ),
    (
        "Default/Senior Executors own bounded implementation and ordinary repair",
        "runbook Executor repair ownership",
    ),
    (
        "An ordinary defect returns to the owning Executor and the same Tester rechecks it.",
        "runbook same-Tester recheck",
    ),
):
    require(normalized(phrase).lower(), runbook.lower(), label)

# The doctrine names retired architecture only in one explicit prohibition. Remove that exact,
# current negative rule before scanning active vocabulary, so the check rejects a reintroduced
# manager/scheduler/transport while retaining the rule itself as a required contract.
retired_prohibition = normalized(
    "Do not add an LLM wave manager, scheduler, queue, DAG engine, workflow database, "
    "lease/heartbeat service, or custom agent transport unless native Codex genuinely cannot "
    "express a required behaviour and Ali separately authorises that complexity. `[manual]`"
).lower()
require(
    retired_prohibition,
    construction.lower(),
    "retired-architecture prohibition",
)

runtime_files = [
    "runbooks/construction-delegation.md",
    "invariants.json",
    "scripts/check-invariants.sh",
    ".codex/config.toml",
    *[f".codex/agents/{role}.toml" for role in expected_roles],
]
runtime_text = {
    relative: normalized(read_text(relative)).lower() for relative in runtime_files
}
runtime_text["docs/conventions/construction.md"] = construction.lower().replace(
    retired_prohibition,
    "",
)
retired_vocabulary = re.compile(
    r"\b(?:scheduler|queue|dag|transport|scout|mechanic|builder)\b|llm wave manager"
    r"|workflow database|lease/heartbeat|heartbeat service",
    re.IGNORECASE,
)
for relative, text in {
    "docs/conventions/construction.md": runtime_text["docs/conventions/construction.md"],
    **runtime_text,
}.items():
    matches = sorted({match.group(0).lower() for match in retired_vocabulary.finditer(text)})
    if matches:
        errors.append(
            f"{relative}: retired current-runtime vocabulary remains: {', '.join(matches)}"
        )

testing_guidance = (
    "canonical repository test commands and maintained fixtures",
    "language-native temporary-directory lifecycle handling",
)
for role in ("default_executor", "senior_executor", "tester"):
    role_text = normalized(read_text(f".codex/agents/{role}.toml")).lower()
    for phrase in testing_guidance:
        require(
            phrase.lower(),
            role_text,
            f"{role} testing guidance",
        )

for relative in ("docs/conventions/construction.md", "runbooks/construction-delegation.md"):
    surface_text = runtime_text[relative]
    for phrase in testing_guidance:
        require(
            phrase.lower(),
            surface_text,
            f"{relative} testing guidance",
        )

config_text = read_text(".codex/config.toml")
try:
    config_document = tomllib.loads(config_text)
except tomllib.TOMLDecodeError as exc:
    errors.append(f".codex/config.toml: cannot be parsed while checking approval policy: {exc}")
else:
    def contains_key(value: object, key: str) -> bool:
        if isinstance(value, dict):
            return key in value or any(contains_key(child, key) for child in value.values())
        if isinstance(value, list):
            return any(contains_key(child, key) for child in value)
        return False

    for inherited_key in ("approval_policy", "sandbox_mode", "sandbox_workspace_write"):
        if contains_key(config_document, inherited_key):
            errors.append(
                f".codex/config.toml: project {inherited_key} must remain inherited"
            )

if errors:
    sys.stderr.write("\n".join(errors) + "\n")
    raise SystemExit(1)
print(f"construction contracts valid: {len(expected_roles)} native roles and current lifecycle boundaries")
PY
}

echo "== construction doctrine: the invariant gate runs and passes on a clean tree =="
gate_out="$(./scripts/check-invariants.sh 2>&1)"; gate_status=$?
eq "check-invariants.sh exits cleanly" "${gate_status}" "0"
printf '%s\n' "${gate_out}" | grep -q 'construction permission posture' \
  && ok "check-invariants.sh runs the construction block" \
  || bad "check-invariants.sh did not run the construction block"

echo "== role files: exactly the six native roles, no legacy vocabulary =="
present="$(cd .codex/agents && ls *.toml 2>/dev/null | sed 's/\.toml$//' | sort | tr '\n' ' ')"
expected="$(printf '%s ' "${EXPECTED_ROLES[@]}")"
eq "exactly the six role TOMLs are present" "${present}" "${expected}"
for legacy in "${LEGACY_ROLES[@]}"; do
  [ -e ".codex/agents/${legacy}.toml" ] && bad "legacy role TOML ${legacy}.toml still present" \
    || ok "no legacy role TOML ${legacy}.toml"
done

echo "== role files: each parses and carries its full native contract =="
# Parse every role file with a real TOML parser and emit one validated TSV row per file. A parse error,
# a name that does not match the filename, a missing/empty required field, or a sandbox override fails
# here (non-zero exit) and is reported below. This validates the source Codex actually loads, not a shim.
contract_tsv="$(python3 - "${EXPECTED_ROLES[@]}" <<'PY'
import sys, tomllib, pathlib
expected = set(sys.argv[1:])
rows, errors, seen = [], [], set()
for stem in sorted(expected):
    p = pathlib.Path(".codex/agents", f"{stem}.toml")
    try:
        d = tomllib.load(open(p, "rb"))
    except Exception as e:                       # parse failure is a hard fail
        errors.append(f"{stem}: does not parse as TOML: {e}")
        continue
    name = d.get("name", "")
    if name != stem:
        errors.append(f"{stem}: name is {name!r}, expected {stem!r} (name must match filename)")
    if name in seen:
        errors.append(f"{stem}: duplicate role name {name!r}")
    seen.add(name)
    for field in ("model", "model_reasoning_effort", "description",
                  "developer_instructions"):
        if not str(d.get(field, "")).strip():
            errors.append(f"{stem}: missing or empty {field}")
    if "sandbox_mode" in d:
        errors.append(f"{stem}: sandbox_mode must inherit the spawning aliammar session")
    rows.append("\t".join([stem, name, str(d.get("model","")), str(d.get("model_reasoning_effort","")),
                            str(len(str(d.get("description","")))),
                            str(len(str(d.get("developer_instructions",""))))]))
if errors:
    sys.stderr.write("\n".join(errors) + "\n")
    sys.exit(1)
print("\n".join(rows))
PY
)"
parse_rc=$?
if [ "${parse_rc}" -ne 0 ]; then
  bad "role contract validation failed:"$'\n'"${contract_tsv}"
else
  while IFS=$'\t' read -r stem name model effort dlen ilen; do
    [ -n "${stem}" ] || continue
    ok "${stem}: parses; name=${name}; model=${model}; effort=${effort}; inherited-session; desc ${dlen}B; instructions ${ilen}B"
  done <<< "${contract_tsv}"
fi

echo "== invariants.json and the role files agree on the six inherited-session roles =="
declared_roles="$(jq -r '.construction.agents[].role' invariants.json | sort | tr '\n' ' ')"
eq "invariants declares exactly the six roles" "${declared_roles}" "${expected}"
for role in "${EXPECTED_ROLES[@]}"; do
  grep -qE '^[[:space:]]*sandbox_mode[[:space:]]*=' ".codex/agents/${role}.toml" \
    && bad "${role} overrides the inherited session posture" \
    || ok "${role} inherits the spawning aliammar session posture"
done

echo "== the project config does not override Home Manager permissions =="
project_config="$(jq -r '.construction.project_config' invariants.json)"
grep -qE '^[[:space:]]*(approval_policy|sandbox_mode)[[:space:]]*=|^[[:space:]]*\[sandbox_workspace_write\]' "${project_config}" \
  && bad "${project_config} overrides inherited approval/sandbox settings" \
  || ok "${project_config} inherits Home Manager approval/sandbox settings"

echo "== no workflow concurrency cap is pinned =="
grep -qE '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' .codex/config.toml \
  && bad ".codex/config.toml pins a concurrency cap — the no-workflow-quota model is in effect" \
  || ok ".codex/config.toml pins no workflow concurrency cap"

echo "== temporary drift is rejected =="
TMP=""
cleanup_tmp() {
  if [ -n "${TMP}" ]; then
    python3 - "${TMP}" <<'PY'
import shutil
import sys

shutil.rmtree(sys.argv[1], ignore_errors=True)
PY
  fi
}
TMP="$(python3 - <<'PY'
import tempfile

print(tempfile.mkdtemp(prefix="construction-test-"))
PY
)"
trap cleanup_tmp EXIT

copy_contract_fixture() {
  local destination="$1"
  mkdir -p "${destination}/.codex/agents" \
    "${destination}/docs/conventions" "${destination}/runbooks" "${destination}/scripts"
  cp .codex/config.toml "${destination}/.codex/config.toml"
  cp .codex/agents/*.toml "${destination}/.codex/agents/"
  cp invariants.json "${destination}/invariants.json"
  cp scripts/check-invariants.sh "${destination}/scripts/check-invariants.sh"
  cp docs/conventions/construction.md "${destination}/docs/conventions/construction.md"
  cp runbooks/construction-delegation.md "${destination}/runbooks/construction-delegation.md"
}

expect_contract_failure() {
  local label="$1"
  local fixture="$2"
  if construction_contract_check "${fixture}" >"${TMP}/${label}.out" 2>"${TMP}/${label}.err"; then
    bad "${label} drift was accepted"
  else
    ok "${label} drift is rejected"
  fi
}

echo "== construction contracts: canonical surfaces and role capsules =="
if construction_contract_check "${REPO_DIR}" >"${TMP}/canonical-contract.out" 2>"${TMP}/canonical-contract.err"; then
  ok "native role capsules and lifecycle boundaries pass the source-contract check"
else
  bad "canonical construction contracts failed"
  sed -n '1,12p' "${TMP}/canonical-contract.err" >&2
fi

echo "== construction contracts: disposable drift fixtures fail closed =="
fixture="${TMP}/capsule-heading"; copy_contract_fixture "${fixture}"
sed -i 's/`Context Task + Goal`/`Wrong Task + Goal`/' \
  "${fixture}/.codex/agents/companion.toml"
expect_contract_failure "capsule-heading" "${fixture}"

fixture="${TMP}/follow-up-language"; copy_contract_fixture "${fixture}"
sed -i 's/carries only the/carries only the summary/' \
  "${fixture}/.codex/agents/companion.toml"
expect_contract_failure "follow-up-language" "${fixture}"

fixture="${TMP}/worker-orchestration"; copy_contract_fixture "${fixture}"
sed -i 's/Do not orchestrate other/Workers may orchestrate other/' \
  "${fixture}/.codex/agents/default_executor.toml"
expect_contract_failure "worker-orchestration" "${fixture}"

fixture="${TMP}/tester-imperative-orchestration"; copy_contract_fixture "${fixture}"
sed -i 's/orchestrate other workers\./Workers orchestrate other workers./' \
  "${fixture}/.codex/agents/tester.toml"
expect_contract_failure "tester-imperative-orchestration" "${fixture}"

fixture="${TMP}/investigator-imperative-coordination"; copy_contract_fixture "${fixture}"
sed -i 's/coordinate another worker/Coordinate another worker/' \
  "${fixture}/.codex/agents/investigator.toml"
expect_contract_failure "investigator-imperative-coordination" "${fixture}"

fixture="${TMP}/executor-repair-owner"; copy_contract_fixture "${fixture}"
sed -i 's/ordinary repair/ordinary maintenance/g' \
  "${fixture}/.codex/agents/default_executor.toml"
expect_contract_failure "executor-repair-owner" "${fixture}"

fixture="${TMP}/tester-no-repair"; copy_contract_fixture "${fixture}"
sed -i 's/do not repair production code/repairs production code/' \
  "${fixture}/.codex/agents/tester.toml"
expect_contract_failure "tester-no-repair" "${fixture}"

fixture="${TMP}/tester-routes-defects"; copy_contract_fixture "${fixture}"
sed -i 's/ordinary defects route back to/ordinary defects are handled here/' \
  "${fixture}/.codex/agents/tester.toml"
expect_contract_failure "tester-routes-defects" "${fixture}"

fixture="${TMP}/same-tester-recheck"; copy_contract_fixture "${fixture}"
sed -i 's/same Tester rechecks it/different Tester rechecks it/' \
  "${fixture}/runbooks/construction-delegation.md"
expect_contract_failure "same-tester-recheck" "${fixture}"

fixture="${TMP}/companion-quantity"; copy_contract_fixture "${fixture}"
sed -i 's/exactly 1 persistent per deployment/exactly 2 persistent per deployment/' \
  "${fixture}/docs/conventions/construction.md"
expect_contract_failure "companion-quantity" "${fixture}"

fixture="${TMP}/senior-quantity"; copy_contract_fixture "${fixture}"
sed -i 's/at most one Senior/at most two Senior/' \
  "${fixture}/docs/conventions/construction.md"
expect_contract_failure "senior-quantity" "${fixture}"

fixture="${TMP}/retired-manager"; copy_contract_fixture "${fixture}"
printf '\nAn LLM wave manager coordinates workers.\n' >> \
  "${fixture}/docs/conventions/construction.md"
expect_contract_failure "retired-manager" "${fixture}"

fixture="${TMP}/retired-scheduler"; copy_contract_fixture "${fixture}"
printf '\nA scheduler launches each role.\n' >> \
  "${fixture}/runbooks/construction-delegation.md"
expect_contract_failure "retired-scheduler" "${fixture}"

fixture="${TMP}/retired-transport"; copy_contract_fixture "${fixture}"
printf '\n# A custom agent transport carries worker reports.\n' >> \
  "${fixture}/.codex/config.toml"
expect_contract_failure "retired-transport" "${fixture}"

fixture="${TMP}/legacy-role-vocabulary"; copy_contract_fixture "${fixture}"
printf '\n# Scout, Mechanic, and Builder are not current worker roles.\n' >> \
  "${fixture}/.codex/agents/default_executor.toml"
expect_contract_failure "legacy-role-vocabulary" "${fixture}"

fixture="${TMP}/project-approval-override"; copy_contract_fixture "${fixture}"
printf '\napproval_policy = "on-request"\n' >> "${fixture}/.codex/config.toml"
expect_contract_failure "project-approval-override" "${fixture}"

fixture="${TMP}/project-sandbox-override"; copy_contract_fixture "${fixture}"
printf '\nsandbox_mode = "workspace-write"\n' >> "${fixture}/.codex/config.toml"
expect_contract_failure "project-sandbox-override" "${fixture}"

fixture="${TMP}/role-sandbox-override"; copy_contract_fixture "${fixture}"
printf '\nsandbox_mode = "read-only"\n' >> "${fixture}/.codex/agents/tester.toml"
expect_contract_failure "role-sandbox-override" "${fixture}"

# A reintroduced cap is detectable by the same rule the gate uses.
cp .codex/config.toml "${TMP}/config.toml"
printf '\nmax_concurrent_threads_per_session = 2\n' >> "${TMP}/config.toml"
grep -qE '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' "${TMP}/config.toml" \
  && ok "a reintroduced max_concurrent_threads_per_session is detectable" \
  || bad "a reintroduced concurrency cap went undetected"

echo
echo "construction-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
