"""Synchronous deployment orchestration for immutable Compose generations.

The generation, activation, and verification modules each own one safety boundary.  This module
only composes those boundaries into the small public command surface used by the CLI.  It never
talks to Arcane directly, changes Git, or retains effective environment bytes.  Arcane observation
and the first-takeover migration proof are passed to :mod:`skynet.activation`, which performs the
pre-write guard.
"""

from __future__ import annotations

import json
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, TextIO

from skynet import activation, deployment, generation


DEFAULT_AGE_KEY = generation.DEFAULT_AGE_KEY
DEFAULT_ARCANE_CREDENTIALS = activation.DEFAULT_ARCANE_CREDENTIALS
DEFAULT_BRANCH = generation.DEFAULT_BRANCH
DEFAULT_CONTEXT = deployment.DEFAULT_CONTEXT
DEFAULT_HOST = activation.DEFAULT_HOST
DEFAULT_STATE_ROOT = activation.DEFAULT_STATE_ROOT
DEFAULT_TIMEOUT = max(generation.DEFAULT_TIMEOUT, activation.DEFAULT_TIMEOUT)

MAX_MIGRATION_EVIDENCE = 64 * 1024

_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_SAFE_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")
_MIGRATION_KEYS = frozenset(
    {
        "schema",
        "service",
        "sync_present",
        "present",
        "auto_sync_disabled",
        "autoSyncDisabled",
        "drained",
        "sync_drained",
        "old_revision",
        "running_revision",
        "old_runtime_verified",
        "runtime_verified",
        "old_services",
        "legacy_working_dir",
        "recorded_at",
    }
)


class DeployError(Exception):
    """A safe operator-facing orchestration outcome."""

    def __init__(self, reason: str, code: int = 1, *, ambiguous: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.code = code
        self.ambiguous = ambiguous


@dataclass
class Outcome:
    """Public operation evidence.  Values are limited to non-secret identities."""

    operation: str
    target: str
    source: dict[str, str] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    verification: str = "not-run"
    recovery: str = "not-needed"
    status: str = "failed"
    reason: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def value(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "operation": self.operation,
            "target": self.target,
            "source": dict(self.source),
            "completed_steps": list(self.completed_steps),
            "verification": self.verification,
            "recovery": self.recovery,
            "status": self.status,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        if self.detail:
            result["detail"] = self.detail
        return result


@dataclass(frozen=True)
class _PipelineResult:
    activation: dict[str, Any]
    verification: dict[str, Any]
    promotion: dict[str, Any]


class _PipelineError(DeployError):
    """Carry only safe public evidence from a failed activation pipeline."""

    def __init__(
        self,
        reason: str,
        code: int = 1,
        *,
        ambiguous: bool = False,
        activation_result: Mapping[str, Any] | None = None,
        verification_result: Mapping[str, Any] | None = None,
        operation_id: str | None = None,
        recovery: str = "not-needed",
    ) -> None:
        super().__init__(reason, code, ambiguous=ambiguous)
        self.activation_result = dict(activation_result) if activation_result is not None else None
        self.verification_result = (
            dict(verification_result) if verification_result is not None else None
        )
        self.operation_id = operation_id
        self.recovery = recovery


def _validate_service(service: Any) -> str:
    if not isinstance(service, str) or _SERVICE.fullmatch(service) is None:
        raise DeployError("invalid service identity", 2)
    return service


def _validate_revision(revision: Any) -> str:
    if not isinstance(revision, str) or _REVISION.fullmatch(revision.lower()) is None:
        raise DeployError("generation identity must be a full 40-hex Git revision", 2)
    return revision.lower()


def _validate_timeout(timeout: Any) -> float:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 1.0 <= float(timeout) <= 300.0
    ):
        raise DeployError("timeout must be between 1 and 300 seconds", 2)
    return float(timeout)


def _error(error: BaseException, fallback: str = "deployment operation failed") -> DeployError:
    """Translate a dependency error without retaining arbitrary exception text."""

    reason = getattr(error, "reason", None)
    code = getattr(error, "code", 3)
    ambiguous = bool(getattr(error, "ambiguous", False))
    if not isinstance(reason, str) or not reason or any(
        ord(char) < 32 or ord(char) == 127 for char in reason
    ):
        reason = fallback
    if type(code) is not int or code not in {1, 2, 3}:
        code = 3
    return DeployError(reason, code, ambiguous=ambiguous)


def _public_release(value: Any) -> dict[str, Any]:
    """Keep release evidence to the manifest's public identity fields."""

    if not isinstance(value, Mapping):
        return {}
    allowed = (
        "schema",
        "service",
        "revision",
        "source_tree",
        "source_tree_identity",
        "compose_input",
        "compose_input_identity",
        "env_git_input",
        "env_git_input_identity",
        "env_sops_input",
        "env_sops_ciphertext",
        "env_sops_input_identity",
        "env_sops_ciphertext_identity",
        "prepared_at",
        "prepared",
    )
    result: dict[str, Any] = {}
    for key in allowed:
        item = value.get(key)
        if isinstance(item, (str, int, float, bool)) or item is None:
            result[key] = item
        elif isinstance(item, Mapping):
            nested: dict[str, str] = {}
            for nested_key, nested_value in item.items():
                if (
                    isinstance(nested_key, str)
                    and _SAFE_KEY.fullmatch(nested_key)
                    and isinstance(nested_value, str)
                    and len(nested_value) <= 512
                ):
                    nested[nested_key] = nested_value
            result[key] = nested
    return result


def _public_runtime(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key in ("classification", "generation", "containers", "detail"):
        item = value.get(key)
        if isinstance(item, (str, int, float, bool)) or item is None:
            result[key] = item
    return result


def _public_activation(value: Any) -> dict[str, Any]:
    """Project an activation result to its non-secret JSON contract."""

    if hasattr(value, "value") and callable(value.value):
        value = value.value()
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key in (
        "operation_id",
        "service",
        "generation",
        "status",
        "active",
        "stable",
        "previous",
        "recovery",
        "reason",
    ):
        item = value.get(key)
        if isinstance(item, (str, int, float, bool)) or item is None:
            result[key] = item
    if "runtime" in value:
        result["runtime"] = _public_runtime(value["runtime"])
    return result


def _public_containers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            continue
        safe: dict[str, Any] = {}
        for key in ("id", "service", "health"):
            item = row.get(key)
            if isinstance(item, str):
                safe[key] = item
        if safe:
            rows.append(safe)
    return rows


def _public_verification(value: Any) -> dict[str, Any]:
    """Project verifier output; effective environment data has no report path."""

    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    scalar_keys = (
        "service",
        "expected_revision",
        "active_revision",
        "generation",
        "generation_path",
        "project_name",
        "container_count",
        "route_status",
        "outcome",
        "status",
        "verified",
        "reason",
    )
    for key in scalar_keys:
        item = value.get(key)
        if isinstance(item, (str, int, float, bool)):
            result[key] = item
    if "release" in value:
        result["release"] = _public_release(value["release"])
    for key in ("expected_services", "observed_services"):
        item = value.get(key)
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            result[key] = [entry for entry in item if isinstance(entry, str)]
    result["containers"] = _public_containers(value.get("containers"))
    routes = value.get("routes")
    if isinstance(routes, Sequence) and not isinstance(routes, (str, bytes)):
        safe_routes: list[dict[str, Any]] = []
        for route in routes:
            if not isinstance(route, Mapping):
                continue
            row: dict[str, Any] = {}
            for key in ("vhost", "http_code", "ssl_verify_result"):
                item = route.get(key)
                if isinstance(item, (str, int)):
                    row[key] = item
            if row:
                safe_routes.append(row)
        result["routes"] = safe_routes
    probe = value.get("route_probe")
    if isinstance(probe, Mapping):
        result["route_probe"] = {
            key: probe[key]
            for key in ("vantage", "image", "side_effect")
            if isinstance(probe.get(key), str)
        }
    return result


def _result_mapping(value: Any, *, activation_result: bool = False) -> dict[str, Any]:
    if activation_result:
        return _public_activation(value)
    if hasattr(value, "value") and callable(value.value):
        value = value.value()
    return dict(value) if isinstance(value, Mapping) else {}


def _emit(outcome: Outcome, *, json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(outcome.value(), sort_keys=True), file=stdout)
        return
    prefix = f"{outcome.operation}: {outcome.target}: {outcome.status}"
    if outcome.reason:
        prefix += f": {outcome.reason}"
    print(prefix, file=stdout)
    if outcome.source:
        print(
            "source: " + ", ".join(f"{key}={value}" for key, value in outcome.source.items()),
            file=stdout,
        )
    print(f"completed: {', '.join(outcome.completed_steps) or 'none'}", file=stdout)
    print(f"verification: {outcome.verification}; recovery: {outcome.recovery}", file=stdout)
    for key, value in outcome.detail.items():
        print(f"{key}: {value}", file=stdout)


def _read_migration_evidence(
    value: Path | Mapping[str, Any] | None,
    service: str,
) -> Mapping[str, Any] | None:
    """Read bounded, explicitly non-secret takeover evidence.

    The evidence contract is intentionally narrow.  Unknown keys are rejected so a credential
    assignment or an operator note cannot accidentally become part of an operation report.
    """

    if value is None:
        return None
    if isinstance(value, Mapping):
        parsed: Any = dict(value)
    elif isinstance(value, Path):
        try:
            file_stat = value.lstat()
            if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > MAX_MIGRATION_EVIDENCE:
                raise DeployError("migration evidence file is unavailable", 3)
            raw = value.read_bytes()
            if len(raw) > MAX_MIGRATION_EVIDENCE:
                raise DeployError("migration evidence file is unavailable", 3)
        except (OSError, ValueError):
            raise DeployError("migration evidence file is unavailable", 3) from None
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise DeployError("migration evidence is malformed", 2) from None
    else:
        raise DeployError("migration evidence is malformed", 2)
    if not isinstance(parsed, dict) or len(parsed) > len(_MIGRATION_KEYS):
        raise DeployError("migration evidence is malformed", 2)
    for key, item in parsed.items():
        if key not in _MIGRATION_KEYS:
            raise DeployError("migration evidence contains an unsupported field", 2)
        if key in {"schema"}:
            if type(item) is not int or item != 1:
                raise DeployError("migration evidence schema is malformed", 2)
        elif key in {"service"}:
            if item != service:
                raise DeployError("migration evidence service does not match target", 2)
        elif key in {
            "sync_present",
            "present",
            "auto_sync_disabled",
            "autoSyncDisabled",
            "drained",
            "sync_drained",
            "old_runtime_verified",
            "runtime_verified",
        }:
            if type(item) is not bool:
                raise DeployError("migration evidence boolean is malformed", 2)
        elif key in {"old_revision", "running_revision"}:
            _validate_revision(item)
        elif key == "old_services":
            if type(item) is not list or not item or len(item) > 128:
                raise DeployError("migration evidence service list is malformed", 2)
            service_names: list[str] = []
            for old_service in item:
                if not isinstance(old_service, str) or _SERVICE.fullmatch(old_service) is None:
                    raise DeployError("migration evidence service list is malformed", 2)
                service_names.append(old_service)
            if len(service_names) != len(set(service_names)):
                raise DeployError("migration evidence service list contains duplicates", 2)
        elif key == "legacy_working_dir":
            if not isinstance(item, str) or len(item) > 4096 or any(
                ord(char) < 33 or ord(char) == 127 for char in item
            ):
                raise DeployError("migration evidence path is malformed", 2)
        elif key == "recorded_at":
            if not isinstance(item, str) or len(item) > 128 or any(
                ord(char) < 32 or ord(char) == 127 for char in item
            ):
                raise DeployError("migration evidence timestamp is malformed", 2)
    return parsed


def _generation_host(host: str | None) -> str:
    """Convert the activation SSH spelling to generation's bare-host spelling."""

    if host is None:
        return generation.DEFAULT_HOST
    if host.startswith("svc-ops@"):
        return host.removeprefix("svc-ops@")
    return host


def _prepared_public(value: Any) -> tuple[str, str, str, dict[str, Any], bool]:
    if isinstance(value, Mapping):
        service = value.get("service")
        revision = value.get("revision")
        path = value.get("path", value.get("generation_path"))
        release = value.get("release", {})
        reused = value.get("reused", False)
    else:
        service = getattr(value, "service", None)
        revision = getattr(value, "revision", None)
        path = getattr(value, "path", getattr(value, "generation_path", None))
        release = getattr(value, "release", {})
        reused = getattr(value, "reused", False)
    if not isinstance(service, str) or not isinstance(revision, str) or not isinstance(path, str):
        raise DeployError("generation preparation result is malformed", 3)
    _validate_service(service)
    _validate_revision(revision)
    if type(reused) is not bool:
        raise DeployError("generation preparation result is malformed", 3)
    return service, revision, path, _public_release(release), reused


def prepare_service(
    service: str,
    *,
    repo: Path = Path.cwd(),
    branch: str = DEFAULT_BRANCH,
    age_key: Path = DEFAULT_AGE_KEY,
    host: str | None = None,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Prepare one exact local branch-head generation without changing Docker runtime."""

    outcome = Outcome("prepare", service, {"branch": branch})
    try:
        service = _validate_service(service)
        timeout = _validate_timeout(timeout)
        prepared = generation.prepare_generation(
            service,
            repo,
            branch=branch,
            host=_generation_host(host),
            state_root=str(state_root),
            age_key=age_key,
            timeout=timeout,
        )
        prepared_service, revision, generation_path, release, reused = _prepared_public(prepared)
        if prepared_service != service:
            raise DeployError("generation preparation service identity mismatch", 3)
        outcome.source["revision"] = revision
        outcome.completed_steps.extend(
            ["revision-resolved", "generation-reused" if reused else "generation-published"]
        )
        outcome.status = "success"
        outcome.verification = "compose-generation-prepared"
        outcome.detail.update(
            {"generation": revision, "generation_path": generation_path, "release": release, "reused": reused}
        )
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 0
    except (DeployError, generation.GenerationError) as error:
        safe = error if isinstance(error, DeployError) else _error(error, "generation preparation failed")
        outcome.reason = safe.reason
        outcome.recovery = "no-runtime-mutation"
        if safe.ambiguous:
            outcome.recovery = "generation-publication-outcome-ambiguous; inspect retained state before retry"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return safe.code
    except (OSError, TypeError, ValueError):
        outcome.reason = "generation preparation failed"
        outcome.recovery = "no-runtime-mutation"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3
    except Exception:
        outcome.reason = "generation preparation failed"
        outcome.recovery = "no-runtime-mutation"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3


def _normalise_verification(value: Any, generation_id: str) -> dict[str, Any]:
    if hasattr(value, "value") and callable(value.value):
        value = value.value()
    if not isinstance(value, Mapping):
        raise _PipelineError("independent verification returned malformed evidence", 3)
    evidence = _public_verification(value)
    observed_revision = evidence.get("active_revision") or evidence.get("expected_revision")
    if observed_revision is not None and observed_revision != generation_id:
        raise _PipelineError("independent verification generation identity mismatch", 1)
    observed_generation = evidence.get("generation")
    if observed_generation is not None and observed_generation != generation_id:
        if (
            isinstance(observed_generation, str)
            and observed_generation.endswith(f"/{generation_id}")
        ):
            evidence["generation_path"] = observed_generation
            evidence["generation"] = generation_id
        else:
            raise _PipelineError("independent verification generation identity mismatch", 1)
    # deployment.verify is the raising form and therefore represents success when it returns.
    evidence.setdefault("outcome", "success")
    evidence.setdefault("status", "verified")
    evidence.setdefault("verified", True)
    evidence.setdefault("generation", generation_id)
    return evidence


def _verification_passed(value: Mapping[str, Any]) -> bool:
    outcome = value.get("outcome", value.get("status"))
    if value.get("verified") is False or outcome in {"failure", "failed", "unavailable"}:
        return False
    return outcome in {"success", "verified", "passed"} or value.get("verified") is True


def _pipeline(
    service: str,
    revision: str,
    *,
    repo: Path,
    generation_path: str | None,
    host: str | None,
    state_root: str | Path,
    context: str,
    timeout: float,
    credentials_file: Path,
    environment_id: str | None,
    migration_evidence: Mapping[str, Any] | None,
    arcane: activation.ArcaneSource | None,
) -> _PipelineResult:
    """Activate, independently verify, and promote one already prepared generation."""

    try:
        activated = activation.activate_generation(
            service,
            revision,
            host=host or activation.DEFAULT_HOST,
            state_root=state_root,
            timeout=timeout,
            arcane=arcane,
            arcane_credentials=credentials_file,
            environment_id=environment_id,
            migration_evidence=migration_evidence,
        )
    except activation.ActivationError as error:
        raise _PipelineError(
            error.reason,
            error.code,
            ambiguous=error.ambiguous,
            operation_id=error.operation_id,
            recovery=(
                "activation outcome unresolved; inspect lock and Docker generation before retry"
                if error.ambiguous
                else "no runtime activation confirmed"
            ),
        ) from None
    except Exception:
        raise _PipelineError(
            "activation dependency failed",
            3,
            ambiguous=True,
            recovery="activation outcome unresolved; inspect lock and Docker generation before retry",
        ) from None
    activation_evidence = _public_activation(activated)
    operation_id = activation_evidence.get("operation_id")
    try:
        raw_verification = deployment.verify(
            service,
            revision,
            context,
            repo,
            timeout=timeout,
            state_root=state_root,
            host=host or deployment.DEFAULT_HOST,
            generation_dir=(
                generation_path
                or getattr(activated, "generation_path", None)
                or f"{state_root}/{service}/generations/{revision}"
            ),
        )
        verification = _normalise_verification(raw_verification, revision)
        if not _verification_passed(verification):
            raise _PipelineError(
                "independent verification failed",
                1,
                verification_result=verification,
            )
    except Exception as error:
        safe_error = (
            error
            if isinstance(error, _PipelineError)
            else _error(error, "independent verification failed")
        )
        prior_verification = getattr(safe_error, "verification_result", None)
        verification_failure = prior_verification or {
            "generation": revision,
            "outcome": "failure",
            "status": "failed",
            "verified": False,
            "reason": safe_error.reason,
        }
        recorded = False
        if isinstance(operation_id, str):
            try:
                activation.mark_verification(
                    service,
                    revision,
                    operation_id,
                    passed=False,
                    container_count=0,
                    route_status="failed",
                    host=host or activation.DEFAULT_HOST,
                    state_root=state_root,
                    timeout=timeout,
                )
                recorded = True
            except Exception:
                recorded = False
        stable_candidate = activation_evidence.get("stable")
        stable_retained = (
            isinstance(stable_candidate, str)
            and _REVISION.fullmatch(stable_candidate) is not None
        )
        if recorded and stable_retained:
            recovery = "rollback candidate retained"
        elif recorded:
            recovery = "failed candidate recorded but no stable rollback candidate"
        else:
            recovery = "verification failed; failed-candidate record could not be confirmed; inspect state"
        raise _PipelineError(
            safe_error.reason,
            safe_error.code,
            ambiguous=safe_error.ambiguous,
            activation_result=activation_evidence,
            verification_result=verification_failure,
            operation_id=operation_id,
            recovery=recovery,
        ) from None
    try:
        promoted = activation.promote(
            service,
            revision,
            operation_id if isinstance(operation_id, str) else "",
            verification,
            host=host or activation.DEFAULT_HOST,
            state_root=state_root,
            timeout=timeout,
        )
    except activation.ActivationError as error:
        raise _PipelineError(
            error.reason,
            error.code,
            ambiguous=error.ambiguous,
            activation_result=activation_evidence,
            verification_result=verification,
            operation_id=operation_id,
            recovery=(
                "promotion outcome unresolved; inspect stable metadata before retry"
                if error.ambiguous
                else "candidate remains unpromoted; inspect active and stable metadata"
            ),
        ) from None
    except Exception:
        raise _PipelineError(
            "promotion failed",
            3,
            ambiguous=True,
            activation_result=activation_evidence,
            verification_result=verification,
            operation_id=operation_id,
            recovery="promotion outcome unresolved; inspect stable metadata before retry",
        ) from None
    return _PipelineResult(activation_evidence, verification, _public_activation(promoted))


def deploy_service(
    service: str,
    *,
    repo: Path = Path.cwd(),
    branch: str = DEFAULT_BRANCH,
    credentials_file: Path = DEFAULT_ARCANE_CREDENTIALS,
    age_key: Path = DEFAULT_AGE_KEY,
    environment_id: str | None = None,
    migration_evidence: Path | Mapping[str, Any] | None = None,
    host: str | None = None,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    context: str = DEFAULT_CONTEXT,
    timeout: float = DEFAULT_TIMEOUT,
    arcane: activation.ArcaneSource | None = None,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Resolve once, prepare, activate, verify, and promote one service generation."""

    outcome = Outcome("deploy", service, {"branch": branch})
    try:
        service = _validate_service(service)
        timeout = _validate_timeout(timeout)
        evidence = _read_migration_evidence(migration_evidence, service)
        revision = generation.resolve_revision(repo, branch, timeout)
        revision = _validate_revision(revision)
        outcome.source["revision"] = revision
        outcome.completed_steps.append("revision-resolved")
        prepared = generation.prepare_generation(
            service,
            repo,
            branch=branch,
            host=_generation_host(host),
            state_root=str(state_root),
            age_key=age_key,
            timeout=timeout,
            revision=revision,
        )
        prepared_service, prepared_revision, generation_path, release, reused = _prepared_public(prepared)
        if prepared_service != service or prepared_revision != revision:
            raise DeployError("prepared generation identity mismatch", 3)
        outcome.completed_steps.append("generation-reused" if reused else "generation-published")
        outcome.detail.update(
            {"generation": revision, "generation_path": generation_path, "release": release, "reused": reused}
        )
        pipeline = _pipeline(
            service,
            revision,
            repo=repo,
            generation_path=generation_path,
            host=host,
            state_root=state_root,
            context=context,
            timeout=timeout,
            credentials_file=credentials_file,
            environment_id=environment_id,
            migration_evidence=evidence,
            arcane=arcane,
        )
        outcome.completed_steps.extend(
            ["generation-activated", "independent-verification-passed", "stable-promoted"]
        )
        outcome.verification = "passed"
        outcome.status = "success"
        prior_stable = pipeline.activation.get("stable")
        outcome.detail.update(
            {
                "activation": pipeline.activation,
                "verification_evidence": pipeline.verification,
                "promotion": pipeline.promotion,
                "rollback_candidate": (
                    prior_stable
                    if isinstance(prior_stable, str) and prior_stable != revision
                    else None
                ),
            }
        )
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 0
    except _PipelineError as error:
        outcome.reason = error.reason
        outcome.verification = (
            "failed"
            if error.verification_result is not None or error.activation_result is not None
            else "not-run"
        )
        outcome.recovery = error.recovery
        if error.activation_result is not None:
            outcome.detail["activation"] = error.activation_result
            observed_candidate = error.activation_result.get("stable")
            if isinstance(observed_candidate, str):
                outcome.detail["rollback_candidate"] = observed_candidate
        if error.verification_result is not None:
            outcome.detail["verification_evidence"] = _public_verification(error.verification_result)
        if error.operation_id is not None:
            outcome.detail["operation_id"] = error.operation_id
        _emit(outcome, json_output=json_output, stdout=stdout)
        return error.code
    except (DeployError, generation.GenerationError) as error:
        safe = error if isinstance(error, DeployError) else _error(error, "deployment failed")
        outcome.reason = safe.reason
        outcome.recovery = (
            "generation publication outcome ambiguous; inspect retained state before retry"
            if safe.ambiguous
            else "no runtime activation confirmed"
        )
        _emit(outcome, json_output=json_output, stdout=stdout)
        return safe.code
    except (activation.ActivationError, deployment.VerificationError) as error:
        safe = _error(error, "deployment failed")
        outcome.reason = safe.reason
        outcome.recovery = "activation outcome unresolved; inspect lock and Docker generation before retry" if safe.ambiguous else "no runtime activation confirmed"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return safe.code
    except (OSError, TypeError, ValueError):
        outcome.reason = "deployment inputs or dependency result are malformed"
        outcome.recovery = "inspect state before retry"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3
    except Exception:
        outcome.reason = "deployment failed"
        outcome.recovery = "inspect lock and Docker generation before retry"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3


def status_service(
    service: str,
    *,
    host: str | None = None,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Report filesystem-backed state and Docker's observed generation without mutation."""

    outcome = Outcome("status", service)
    try:
        service = _validate_service(service)
        timeout = _validate_timeout(timeout)
        snapshot = activation.status(
            service,
            host=host or activation.DEFAULT_HOST,
            state_root=state_root,
            timeout=timeout,
        )
        outcome.status = "success"
        outcome.verification = "report-only"
        outcome.completed_steps.append("state-and-runtime-observed")
        safe_snapshot = _public_activation(snapshot)
        for key in (
            "schema",
            "service",
            "host",
            "state_root",
            "initialized",
            "active",
            "stable",
            "previous",
            "prepared",
            "lock",
            "operation",
            "runtime",
        ):
            if isinstance(snapshot, Mapping) and key in snapshot:
                item = snapshot[key]
                if key == "runtime":
                    outcome.detail[key] = _public_runtime(item)
                elif key == "operation" and isinstance(item, Mapping):
                    outcome.detail[key] = {
                        field: item[field]
                        for field in ("id", "state", "requested_generation")
                        if isinstance(item.get(field), (str, type(None)))
                    }
                elif key == "prepared" and isinstance(item, list):
                    if all(isinstance(entry, str) and _REVISION.fullmatch(entry) for entry in item):
                        outcome.detail[key] = list(item)
                elif isinstance(item, (str, int, float, bool)) or item is None:
                    outcome.detail[key] = item
        if not outcome.detail:
            outcome.detail = safe_snapshot
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 0
    except (DeployError, activation.ActivationError) as error:
        safe = error if isinstance(error, DeployError) else _error(error, "deployment status unavailable")
        outcome.reason = safe.reason
        outcome.recovery = "report-only; no runtime mutation"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return safe.code
    except (OSError, TypeError, ValueError):
        outcome.reason = "deployment status unavailable"
        outcome.recovery = "report-only; no runtime mutation"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3
    except Exception:
        outcome.reason = "deployment status unavailable"
        outcome.recovery = "report-only; no runtime mutation"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3


def _rollback_candidate(snapshot: Mapping[str, Any], requested: str | None) -> str:
    active = snapshot.get("active")
    stable = snapshot.get("stable")
    previous = snapshot.get("previous")
    if requested is not None:
        revision = _validate_revision(requested)
        return revision
    # A failed candidate leaves active != stable.  The stable generation is the rollback target;
    # after a successful deployment, previous is the retained predecessor.
    if isinstance(active, str) and active != stable and isinstance(stable, str):
        return _validate_revision(stable)
    if isinstance(previous, str):
        return _validate_revision(previous)
    raise DeployError("no unambiguous retained rollback candidate", 1)


def _retained_generation(snapshot: Mapping[str, Any], revision: str) -> dict[str, Any]:
    """Confirm a requested generation is present in the bounded remote inventory.

    ``activation.status`` obtains the inventory through the report-only state script.  Keeping
    this check on that already validated list avoids constructing an arbitrary remote path and
    avoids reading a generation's ``.env`` or manifest into Skynet.  Activation validates the
    complete generation, including its manifest, again while holding the deployment lock.
    """

    revision = _validate_revision(revision)
    prepared = snapshot.get("prepared")
    if not isinstance(prepared, list) or len(prepared) > 1024:
        raise DeployError("deployment generation inventory is malformed", 3)
    if any(not isinstance(item, str) or _REVISION.fullmatch(item) is None for item in prepared):
        raise DeployError("deployment generation inventory is malformed", 3)
    if prepared != sorted(set(prepared)):
        raise DeployError("deployment generation inventory is malformed", 3)
    if revision not in prepared:
        raise DeployError("requested rollback generation is not retained", 1)
    return {"revision": revision, "retained": True}


def rollback_service(
    service: str,
    *,
    to: str | None = None,
    apply: bool = False,
    repo: Path = Path.cwd(),
    age_key: Path = DEFAULT_AGE_KEY,
    credentials_file: Path = DEFAULT_ARCANE_CREDENTIALS,
    environment_id: str | None = None,
    host: str | None = None,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    context: str = DEFAULT_CONTEXT,
    timeout: float = DEFAULT_TIMEOUT,
    arcane: activation.ArcaneSource | None = None,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Report or explicitly apply a retained runtime generation, without Git mutation."""

    outcome = Outcome("rollback", service)
    try:
        service = _validate_service(service)
        timeout = _validate_timeout(timeout)
        snapshot = activation.status(
            service,
            host=host or activation.DEFAULT_HOST,
            state_root=state_root,
            timeout=timeout,
        )
        if not isinstance(snapshot, Mapping):
            raise DeployError("deployment state observation is malformed", 3)
        outcome.completed_steps.append("state-observed")
        candidate = _rollback_candidate(snapshot, to)
        retained_generation = _retained_generation(snapshot, candidate)
        outcome.completed_steps.append("retained-generation-observed")
        outcome.source["revision"] = candidate
        outcome.detail.update(
            {
                "rollback_candidate": candidate,
                "retained_generation": retained_generation,
                "active": snapshot.get("active"),
                "stable": snapshot.get("stable"),
                "previous": snapshot.get("previous"),
            }
        )
        if not apply:
            outcome.status = "success"
            outcome.verification = "report-only"
            outcome.recovery = "use --apply to activate and verify the retained generation"
            _emit(outcome, json_output=json_output, stdout=stdout)
            return 0
        validated_generation = generation.validate_retained_generation(
            service,
            candidate,
            repo=repo,
            age_key=age_key,
            host=host or generation.DEFAULT_HOST,
            state_root=str(state_root),
            timeout=timeout,
        )
        outcome.completed_steps.append("retained-generation-revalidated")
        outcome.detail["retained_generation"] = {
            "revision": validated_generation.revision,
            "retained": True,
            "exact_git_revalidated": True,
        }
        pipeline = _pipeline(
            service,
            candidate,
            repo=repo,
            generation_path=None,
            host=host,
            state_root=state_root,
            context=context,
            timeout=timeout,
            credentials_file=credentials_file,
            environment_id=environment_id,
            migration_evidence=None,
            arcane=arcane,
        )
        outcome.completed_steps.extend(
            ["generation-activated", "independent-verification-passed", "stable-promoted"]
        )
        outcome.status = "success"
        outcome.verification = "passed"
        outcome.recovery = "runtime recovered; authored Git may intentionally diverge"
        outcome.detail.update(
            {
                "activation": pipeline.activation,
                "verification_evidence": pipeline.verification,
                "promotion": pipeline.promotion,
                "source_correction": "use the normal reviewed PR workflow",
            }
        )
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 0
    except _PipelineError as error:
        outcome.reason = error.reason
        outcome.verification = (
            "failed"
            if error.verification_result is not None or error.activation_result is not None
            else "not-run"
        )
        outcome.recovery = error.recovery
        if error.activation_result is not None:
            outcome.detail["activation"] = error.activation_result
            observed_candidate = error.activation_result.get("stable")
            if isinstance(observed_candidate, str):
                outcome.detail["rollback_candidate"] = observed_candidate
        if error.verification_result is not None:
            outcome.detail["verification_evidence"] = _public_verification(error.verification_result)
        _emit(outcome, json_output=json_output, stdout=stdout)
        return error.code
    except (DeployError, activation.ActivationError, generation.GenerationError) as error:
        safe = error if isinstance(error, DeployError) else _error(error, "runtime rollback failed")
        outcome.reason = safe.reason
        outcome.recovery = "inspect active/stable state before retry" if safe.ambiguous else "runtime unchanged or requires inspection"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return safe.code
    except (OSError, TypeError, ValueError):
        outcome.reason = "runtime rollback inputs or state are malformed"
        outcome.recovery = "inspect active/stable state before retry"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3
    except Exception:
        outcome.reason = "runtime rollback failed"
        outcome.recovery = "inspect active/stable state before retry"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3


prepare = prepare_service
deploy = deploy_service
status = status_service
rollback = rollback_service


__all__: Final = [
    "DEFAULT_AGE_KEY",
    "DEFAULT_ARCANE_CREDENTIALS",
    "DEFAULT_BRANCH",
    "DEFAULT_CONTEXT",
    "DEFAULT_HOST",
    "DEFAULT_STATE_ROOT",
    "DEFAULT_TIMEOUT",
    "DeployError",
    "Outcome",
    "deploy",
    "deploy_service",
    "prepare",
    "prepare_service",
    "rollback",
    "rollback_service",
    "status",
    "status_service",
]
