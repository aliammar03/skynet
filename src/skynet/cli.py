"""The small command-line interface for Skynet."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from skynet import certs, installed_version, omada, routes
from skynet.collection import collect_all, collection_status
from skynet.dns import DEFAULT_CREDENTIALS as DNS_DEFAULT_CREDENTIALS, collect as collect_dns
from skynet.doctor import write_report
from skynet.docker import collect as collect_docker
from skynet.opnsense import DEFAULT_CREDENTIALS as OPNSENSE_DEFAULT_CREDENTIALS, collect as collect_opnsense
from skynet.pbs import DEFAULT_CREDENTIALS as PBS_DEFAULT_CREDENTIALS, collect as collect_pbs
from skynet.proxmox import DEFAULT_CREDENTIALS, collect, collect_acl


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser shared by both supported entry points."""
    parser = argparse.ArgumentParser(
        prog="skynet",
        description="Skynet operations engine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {installed_version()}")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="report the local application runtime")
    doctor.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="write one runtime report object as JSON",
    )
    collection = commands.add_parser("collect", help="collect observations, not service health")
    sources = collection.add_subparsers(dest="source", required=True)
    all_sources = sources.add_parser("all", help="refresh inventory with per-collector outcomes")
    all_sources.add_argument("--repo", type=Path, required=True)
    all_sources.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS["core"],
                             help="core Proxmox credential assignments")
    all_sources.add_argument("--network-credentials-file", type=Path,
                             default=DEFAULT_CREDENTIALS["network"],
                             help="network Proxmox credential assignments")
    all_sources.add_argument("--pbs-credentials-file", type=Path, default=PBS_DEFAULT_CREDENTIALS,
                             help="PBS credential assignments")
    all_sources.add_argument("--dns-credentials-file", type=Path, default=DNS_DEFAULT_CREDENTIALS,
                             help="Technitium DNS credential assignments")
    all_sources.add_argument("--opnsense-credentials-file", type=Path,
                             default=OPNSENSE_DEFAULT_CREDENTIALS,
                             help="OPNsense API credential assignments")
    all_sources.add_argument("--omada-credentials-file", type=Path,
                             default=omada.DEFAULT_CREDENTIALS,
                             help="Omada Viewer credential assignments")
    all_sources.add_argument("--json", action="store_true", dest="json_output")
    proxmox = sources.add_parser("proxmox", help="collect Proxmox observations")
    targets = proxmox.add_subparsers(dest="target", required=True)
    for target in ("core", "network"):
        node = targets.add_parser(
            target, help=f"collect {target}-node observations, not service health",
            description=f"Collect {target}-node observations; this does not verify service health.",
        )
        node.add_argument("--output", type=Path, required=True,
                          help="explicit snapshot destination; publish only on complete success")
        node.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS[target],
                          help="literal PVE_HOST/PVE_TOKEN/PVE_CACERT assignments")
        node.add_argument("--json", action="store_true", dest="json_output",
                          help="write one collection outcome object as JSON")
    acl = sources.add_parser("proxmox-acl", help="collect Proxmox operate-token ACL observations")
    acl_targets = acl.add_subparsers(dest="target", required=True)
    for target in ("core", "network"):
        node = acl_targets.add_parser(target, help=f"collect {target} operate-token permissions")
        node.add_argument("--output", type=Path, required=True,
                          help="explicit ACL snapshot destination; publish only on complete success")
        node.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS[target],
                          help="literal PVE_HOST/PVE_TOKEN_OPERATE/PVE_CACERT assignments")
        node.add_argument("--json", action="store_true", dest="json_output")
    pbs = sources.add_parser("pbs", help="collect PBS backup observations")
    pbs.add_argument("--output", type=Path, required=True,
                     help="explicit snapshot destination; publish only on complete success")
    pbs.add_argument("--credentials-file", type=Path, default=PBS_DEFAULT_CREDENTIALS,
                     help="literal PBS_HOST/PBS_TOKEN trust assignments")
    pbs.add_argument("--json", action="store_true", dest="json_output",
                     help="write one collection outcome object as JSON")
    docker = sources.add_parser("docker", help="collect Docker host observations")
    docker.add_argument("label", nargs="?", default="docker-dmz")
    docker.add_argument("--output", type=Path, required=True)
    docker.add_argument("--context", help="read-only Docker context; defaults to the host label")
    docker.add_argument("--json", action="store_true", dest="json_output")
    dns = sources.add_parser("dns", help="collect Technitium DNS zone observations")
    dns.add_argument("--output", type=Path, required=True,
                     help="explicit snapshot destination; publish only on complete success")
    dns.add_argument("--credentials-file", type=Path, default=DNS_DEFAULT_CREDENTIALS,
                     help="literal TECH_HOST/TECH_TOKEN/TECH_CACERT assignments")
    dns.add_argument("--json", action="store_true", dest="json_output",
                     help="write one collection outcome object as JSON")
    opnsense = sources.add_parser("opnsense", help="collect live OPNsense firewall and state observations")
    opnsense.add_argument("--firewall-output", type=Path, required=True,
                          help="explicit firewall-config destination; publish only on complete success")
    opnsense.add_argument("--state-output", type=Path, required=True,
                          help="explicit live-state destination; publish only on complete success")
    opnsense.add_argument("--credentials-file", type=Path, default=OPNSENSE_DEFAULT_CREDENTIALS,
                          help="literal OPN_HOST/OPN_KEY/OPN_SECRET/OPN_CACERT assignments")
    opnsense.add_argument("--json", action="store_true", dest="json_output",
                          help="write one collection outcome object as JSON")
    network_gear = sources.add_parser("omada", help="collect Omada network-gear observations")
    network_gear.add_argument("--output", type=Path, required=True,
                              help="explicit snapshot destination; publish only on complete success")
    network_gear.add_argument("--credentials-file", type=Path, default=omada.DEFAULT_CREDENTIALS,
                              help="literal OMADA_HOST/PORT/SNI/USER/PASS/CACERT assignments")
    network_gear.add_argument("--json", action="store_true", dest="json_output",
                              help="write one collection outcome object as JSON")
    certificates = sources.add_parser("certs", help="collect declared TLS certificate observations")
    certificates.add_argument("--output", type=Path, required=True,
                              help="explicit snapshot destination; publish only on complete success")
    certificates.add_argument("--json", action="store_true", dest="json_output",
                              help="write one collection outcome object as JSON")
    route_inventory = sources.add_parser("routes", help="statically collect committed Caddy routes")
    route_inventory.add_argument("--repo", type=Path, required=True,
                                 help="checkout containing compose and collected guest observations")
    route_inventory.add_argument("--output", type=Path, required=True,
                               help="explicit snapshot destination; publish only on complete success")
    route_inventory.add_argument("--json", action="store_true", dest="json_output",
                               help="write one collection outcome object as JSON")
    status = commands.add_parser("collect-status", help="require fresh successful inventory observations")
    status.add_argument("--repo", type=Path, required=True)
    status.add_argument("--since", default=os.environ.get("SKYNET_COLLECTION_SINCE"),
                        help="require an attempt at or after this timezone-aware timestamp")
    status.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Skynet's CLI and return its process exit status."""
    arguments = build_parser().parse_args(argv)
    if arguments.command == "doctor":
        write_report(json_output=arguments.json_output, stdout=sys.stdout)
        return 0
    if arguments.command == "collect":
        if arguments.source == "all":
            return collect_all(arguments.repo, arguments.credentials_file,
                               arguments.network_credentials_file, arguments.pbs_credentials_file,
                               arguments.dns_credentials_file, arguments.opnsense_credentials_file,
                               arguments.omada_credentials_file,
                               json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "pbs":
            return collect_pbs(arguments.output, arguments.credentials_file,
                               json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "dns":
            return collect_dns(arguments.output, arguments.credentials_file,
                               json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "docker":
            return collect_docker(arguments.label, arguments.output, arguments.context or arguments.label,
                                  json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "opnsense":
            return collect_opnsense(arguments.firewall_output, arguments.state_output,
                                    arguments.credentials_file,
                                    json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "omada":
            return omada.collect(arguments.output, arguments.credentials_file,
                                 json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "certs":
            return certs.collect(arguments.output, json_output=arguments.json_output, stdout=sys.stdout)
        if arguments.source == "routes":
            return routes.collect(arguments.repo, arguments.output,
                                  json_output=arguments.json_output, stdout=sys.stdout)
        function = collect_acl if arguments.source == "proxmox-acl" else collect
        return function(arguments.target, arguments.output, arguments.credentials_file,
                        json_output=arguments.json_output, stdout=sys.stdout)
    if arguments.command == "collect-status":
        return collection_status(arguments.repo, since=arguments.since,
                                 json_output=arguments.json_output, stdout=sys.stdout)
    return _unreachable_command(arguments.command)


def _unreachable_command(command: str) -> NoReturn:
    """Make an unexpected parser result a loud programming error."""
    raise RuntimeError(f"unhandled command: {command}")
