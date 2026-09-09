"""T1 Docker observations through an explicit read-only context."""

import ctypes
import json
import os
import re
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from skynet.proxmox import CollectionError, publish

TIMEOUT = 20
CLEANUP_TIMEOUT = 5.0


class CleanupError(Exception):
    """A Docker process group could not be confirmed stopped and reaped."""


def _label(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise CollectionError("invalid Docker host label", 3)
    return value


def _stop(process: subprocess.Popen[str]) -> None:
    """Kill this Docker command's session group and reap adopted descendants."""
    deadline = time.monotonic() + CLEANUP_TIMEOUT
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as error:
        raise CleanupError from error
    try:
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as error:
        raise CleanupError from error
    except OSError as error:
        raise CleanupError from error
    while True:
        try:
            while os.waitpid(-process.pid, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            pass
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        except OSError as error:
            raise CleanupError from error
        if time.monotonic() >= deadline:
            raise CleanupError
        time.sleep(0.01)


def _run(args: list[str]) -> str:
    """Run a bounded Docker command while owning and cleaning its process group."""
    process: subprocess.Popen[str] | None = None
    libc = ctypes.CDLL(None, use_errno=True)
    previous_subreaper = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(previous_subreaper), 0, 0, 0) != 0:  # PR_GET_CHILD_SUBREAPER
        raise CleanupError
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise CleanupError
    previous_int = signal.getsignal(signal.SIGINT)
    previous_term = signal.getsignal(signal.SIGTERM)

    def interrupted(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        # Block interruptions across spawn so the child always has an owned group.
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            process = subprocess.Popen(
                args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True,
            )
        except BaseException:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            raise
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        stdout, _ = process.communicate(timeout=TIMEOUT)
        if process.returncode:
            raise CollectionError("Docker context or command unavailable", 3)
        return stdout
    except CleanupError:
        raise
    except CollectionError:
        raise
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise CollectionError("Docker context or command unavailable", 3) from None
    finally:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            try:
                if process is not None:
                    _stop(process)
                    try:
                        process.communicate(timeout=CLEANUP_TIMEOUT)
                    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
                        raise CleanupError from error
            finally:
                if libc.prctl(36, previous_subreaper.value, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
                    raise CleanupError
        finally:
            signal.signal(signal.SIGINT, previous_int)
            signal.signal(signal.SIGTERM, previous_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def _lines(raw: str, required: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            raise CollectionError("malformed Docker JSON output") from None
        if not isinstance(row, dict) or not required <= row.keys() or any(
                not isinstance(key, str) or value is not None and not isinstance(value, str)
                for key, value in row.items()):
            raise CollectionError("malformed Docker JSON output")
        if any(not isinstance(row[key], str) for key in required) or any(
                not row[key] for key in required if key != "Labels"):
            raise CollectionError("malformed Docker JSON output")
        rows.append(row)
    return rows


def snapshot(label: str, context: str) -> dict[str, Any]:
    """Require a configured context plus complete container and image JSON-line responses."""
    label = _label(label)
    _label(context)
    _run(["docker", "context", "inspect", context])
    containers = _lines(_run(["docker", "--context", context, "ps", "--all", "--format", "{{json .}}"]),
                        {"ID", "Names", "Image", "State", "Status", "Labels"})
    images = _lines(_run(["docker", "--context", context, "image", "ls", "--format", "{{json .}}"]),
                    {"ID", "Repository", "Tag", "Size"})
    return {"host": label, "collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "containers": containers, "images": images}


def collect(label: str, output: Path, context: str, *, json_output: bool, stdout: TextIO,
            raise_cleanup: bool = False) -> int:
    """Collect one atomic Docker host snapshot; failure retains destination bytes."""
    report: dict[str, Any] = {"target": f"docker-{label}", "output": str(output)}
    try:
        data = snapshot(label, context)
        publish(output, data)
    except CleanupError:
        if raise_cleanup:
            raise
        report.update(outcome="recovery-required",
                      reason="Docker cleanup unconfirmed; inspect local processes")
        code = 1
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"],
                      counts={"containers": len(data["containers"]), "images": len(data["images"])})
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"{report['target']}: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
