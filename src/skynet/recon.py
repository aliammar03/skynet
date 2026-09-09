"""Bounded T1 host reconnaissance through local or unprivileged SSH probes."""

from __future__ import annotations

import json
import re
import socket
import subprocess
from typing import TextIO

PROBE_TIMEOUT = 6
SESSION_TIMEOUT = 90
SSH_CONNECT_TIMEOUT = 8
TARGET = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
SECTIONS = (
    "Host", "Load / memory / CPU", "Disk — usage then inodes", "systemd — failed units",
    "Listening sockets (TCP/UDP)", "Containers (docker, unprivileged)",
    "Recent warnings/errors (journal, last boot)",
    "Recent config changes — /etc modified in last 7 days", "Recent package changes (last 20)",
)

# This contains only fixed read-only commands. User input is never interpolated into it.
PROBE = r'''
set +e
have() { command -v "$1" >/dev/null 2>&1; }
t() { if have timeout; then timeout 6 "$@"; else "$@"; fi; }
sec() { printf '@@SEC@@%s\n' "$1"; }
printf '@@META@@host\t%s\n' "$(hostname -f 2>/dev/null || hostname)"
printf '@@META@@collected\t%s\n' "$(date -Iseconds)"
printf '@@META@@as\t%s@%s\n' "$(id -un)" "$(hostname)"
sec 'Host'
printf 'kernel : %s\n' "$(uname -sr)"
printf 'uptime : %s\n' "$(uptime -p 2>/dev/null || uptime)"
sec 'Load / memory / CPU'
printf 'load   : %s   (cores: %s)\n' "$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)" "$(nproc 2>/dev/null)"
have free && t free -h 2>/dev/null
sec 'Disk — usage then inodes'
t df -hP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | (read -r h; echo "$h"; sort -k5 -hr)
printf -- '--- inodes ---\n'
t df -iP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | (read -r h; echo "$h"; sort -k5 -hr)
sec 'systemd — failed units'
if have systemctl; then f="$(t systemctl --failed --no-legend --plain --no-pager 2>/dev/null)"; [ -n "$f" ] && echo "$f" || echo '(none failed)'; else echo '(no systemd)'; fi
sec 'Listening sockets (TCP/UDP)'
if have ss; then t ss -tulnH 2>/dev/null | awk '{printf "%-5s %-6s %s\n",$1,$2,$5}' | sort -u; else echo '(ss unavailable)'; fi
sec 'Containers (docker, unprivileged)'
if have docker && t docker info >/dev/null 2>&1; then t docker ps --all --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null; else echo '(no docker access from this user)'; fi
sec 'Recent warnings/errors (journal, last boot)'
if have journalctl && journalctl -n0 >/dev/null 2>&1; then t journalctl -p warning -b --no-pager 2>/dev/null | tail -n 40; else echo '(journal not readable as this user)'; fi
sec 'Recent config changes — /etc modified in last 7 days'
changed="$(t find /etc -type f -mtime -7 2>/dev/null | sort)"; [ -n "$changed" ] && echo "$changed" | head -n 40 || echo '(none)'
sec 'Recent package changes (last 20)'
if [ -f /var/log/dpkg.log ]; then grep -hE ' (install|upgrade|remove) ' /var/log/dpkg.log /var/log/dpkg.log.1 2>/dev/null | tail -n 20; elif have rpm; then t rpm -qa --last 2>/dev/null | head -n 20; else echo '(no package history found)'; fi
'''


def command(target: str) -> list[str]:
    """Build a fixed local or svc-ops SSH invocation; never accept an SSH user or option."""
    if target in {"local", "localhost", socket.gethostname(), socket.gethostname().split(".")[0]}:
        return ["bash", "-s"]
    if not TARGET.fullmatch(target) or "@" in target:
        raise ValueError("target must be a bare hostname or IP address")
    return ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
            f"svc-ops@{target}", "bash", "-s"]


def _parse(raw: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    metadata: dict[str, str] = {}
    sections: list[tuple[str, str]] = []
    name: str | None = None
    lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("@@META@@"):
            key, separator, value = line.removeprefix("@@META@@").partition("\t")
            if separator and key in {"host", "collected", "as"} and value:
                metadata[key] = value
        elif line.startswith("@@SEC@@"):
            if name is not None:
                sections.append((name, "\n".join(lines).rstrip()))
            name, lines = line.removeprefix("@@SEC@@"), []
        elif name is not None:
            lines.append(line)
    if name is not None:
        sections.append((name, "\n".join(lines).rstrip()))
    if set(metadata) != {"host", "collected", "as"} or tuple(name for name, _ in sections) != SECTIONS:
        raise ValueError("incomplete probe output")
    return metadata, sections


def run(target: str, *, json_output: bool, stdout: TextIO) -> int:
    """Run the fixed read-only probe and render one JSON or Markdown snapshot."""
    try:
        result = subprocess.run(command(target), input=PROBE, text=True, capture_output=True,
                                timeout=SESSION_TIMEOUT, check=False)
        if result.returncode != 0:
            raise ValueError("probe unavailable")
        metadata, sections = _parse(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        report = {"target": "recon", "outcome": "unavailable", "host": target,
                  "reason": "unprivileged reconnaissance unavailable"}
        print(json.dumps(report) if json_output else "recon: unavailable", file=stdout)
        return 3
    if json_output:
        print(json.dumps({"target": "recon", "outcome": "success", **metadata,
                          "sections": dict(sections)}), file=stdout)
    else:
        print(f"# recon: {metadata['host']}\ncollected: {metadata['collected']}   as: {metadata['as']}",
              file=stdout)
        for name, contents in sections:
            print(f"\n## {name}\n\n```\n{contents}\n```", file=stdout)
        print("\n_recon complete — T1 read-only. Reason over this, then pick a diagnosis runbook._", file=stdout)
    return 0