"""The small command-line interface for Skynet."""

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from skynet import (cache, certs, deployment, entities, installed_version, memory, omada, planning,
                    recon, render, routes, scaffold)
from skynet.collection import CredentialFiles, collect_all, collection_status
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
    verification = commands.add_parser("verify", help="verify a live deployment without mutating it")
    verifiers = verification.add_subparsers(dest="verification", required=True)
    deploy = verifiers.add_parser(
        "deployment", aliases=("deploy",),
        help="verify one Arcane GitOps service, its containers, and declared ingress routes",
    )
    deploy.add_argument("service", help="Compose service/project name")
    deploy.add_argument("expected_revision", help="full 40-hex Git commit expected live")
    deploy.add_argument(
        "--credentials-file", "--arcane-credentials", "--arcane-credentials-file",
        type=Path, dest="credentials_file", default=deployment.DEFAULT_CREDENTIALS,
        help="literal ARCANE_URL/ARCANE_TOKEN[/ARCANE_AUTH_HEADER/ARCANE_ENV_ID] assignments",
    )
    deploy.add_argument(
        "--context", "--docker-context", dest="docker_context", default=deployment.DEFAULT_CONTEXT,
        help="read-only Docker context used for project and DMZ probes",
    )
    deploy.add_argument(
        "--environment-id", "--env-id", dest="environment_id",
        help="Arcane environment id (defaults to ARCANE_ENV_ID or 0)",
    )
    deploy.add_argument(
        "--repo", type=Path, default=Path.cwd(),
        help="checkout containing compose/caddy-apps/Caddyfile (default: current directory)",
    )
    deploy.add_argument(
        "--timeout", type=float, default=deployment.DEFAULT_TIMEOUT,
        help="per-observation timeout in seconds (1–300)",
    )
    deploy.add_argument("--json", action="store_true", dest="json_output")
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
    recon_command = commands.add_parser("recon", help="take a bounded T1 host snapshot")
    recon_command.add_argument("target", nargs="?", default="local",
                               help="local or a bare hostname/IP reached as unprivileged svc-ops")
    recon_command.add_argument("--json", action="store_true", dest="json_output")
    entity_audit = commands.add_parser("entities", help="audit committed entity identity and mappings")
    entity_audit.add_argument("--repo", type=Path, required=True,
                              help="checkout containing authored conventions and inventory")
    entity_audit.add_argument("--json", action="store_true", dest="json_output",
                              help="write one entity audit report object as JSON")
    query = commands.add_parser("query", help="build and query the disposable inventory cache")
    query.add_argument("statement", help="one SQL statement to execute")
    query.add_argument("--repo", type=Path, required=True,
                       help="checkout containing authored conventions and inventory")
    query.add_argument("--format", choices=("tabs", "plain"), default="plain",
                       help="query output format (default: plain)")
    query.add_argument("--no-header", action="store_true",
                       help="omit query column names")
    rendering = commands.add_parser("render", help="render generated views from repository truth")
    renderers = rendering.add_subparsers(dest="renderer", required=True)
    factual = renderers.add_parser("docs", help="render freshness-gated factual inventory pages")
    factual.add_argument("--repo", type=Path, required=True)
    factual.add_argument("--output", type=Path)
    factual.add_argument("--since", default=os.environ.get("SKYNET_COLLECTION_SINCE"))
    digest = renderers.add_parser("digest", help="render the recent-activity retrieval view")
    digest.add_argument("--repo", type=Path, required=True)
    digest.add_argument("--output", type=Path)
    digest.add_argument("--journal", type=Path)
    context = renderers.add_parser("context", help="render the on-demand context routing index")
    context.add_argument("--repo", type=Path, required=True)
    context.add_argument("--output", type=Path)
    catalog = renderers.add_parser(
        "runbook-catalog", help="render the runbook frontmatter catalog"
    )
    catalog.add_argument("--repo", type=Path, required=True)
    catalog.add_argument("--output", type=Path)
    recall = commands.add_parser("recall", help="rank canonical Markdown sources for a topic")
    recall.add_argument("--repo", type=Path, required=True)
    recall.add_argument("terms", nargs="+", help="case-insensitive regular expressions, OR-joined")
    status = commands.add_parser("collect-status", help="require fresh successful inventory observations")
    status.add_argument("--repo", type=Path, required=True)
    status.add_argument("--since", default=os.environ.get("SKYNET_COLLECTION_SINCE"),
                        help="require an attempt at or after this timezone-aware timestamp")
    status.add_argument("--json", action="store_true", dest="json_output")
    plan = commands.add_parser("plan", help="scaffold and move Skynet Directives (planning/README.md)")
    plan.add_argument("--repo", type=Path, default=Path.cwd(), help="checkout (default: cwd)")
    plans = plan.add_subparsers(dest="action", required=True)
    plans.add_parser("scratch", help="append a note to today's scratchpad").add_argument(
        "note", nargs="*")
    plan_idea = plans.add_parser("idea", help="mint the next SKY-### in ideas/ (title or scratch file)")
    plan_idea.add_argument("source", help="title, or a planning/scratchpad/ file to promote")
    plan_idea.add_argument("--long", action="store_const", const="long", default="short",
                           dest="horizon")
    plans.add_parser("service", help="sketch a planned service in services/").add_argument("name")
    plan_promote = plans.add_parser("promote", help="move a directive to another stage")
    plan_promote.add_argument("id")
    plan_promote.add_argument("stage", choices=planning.STAGES)
    plans.add_parser("start", help="promote to projects/ (in-progress)").add_argument("id")
    plan_archive = plans.add_parser("archive", help="move to archive/ (done, or --abandon)")
    plan_archive.add_argument("id")
    plan_archive.add_argument("--abandon", action="store_true")
    plans.add_parser("show", help="print a directive's path").add_argument("id")
    plans.add_parser("list", help="regenerate the roadmap table in planning/README.md")
    new = commands.add_parser("new", help="stamp an artifact from its templates/ golden template")
    new.add_argument("--repo", type=Path, default=Path.cwd(), help="checkout (default: cwd)")
    kinds = new.add_subparsers(dest="kind", required=True)
    kinds.add_parser("service", help="compose/<name>/").add_argument("name")
    kinds.add_parser("script", help="scripts/<name>.sh").add_argument("name")
    kinds.add_parser("runbook", help="runbooks/<slug>.md").add_argument("title")
    kinds.add_parser("adr", help="docs/decisions/NNNN-<slug>.md").add_argument("title")
    new_journal = kinds.add_parser("journal", help="journal/<YYYY>/<date>-<kind>-<slug>.md")
    new_journal.add_argument("episode", choices=scaffold.JOURNAL_KINDS)
    new_journal.add_argument("title")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Skynet's CLI and return its process exit status."""
    arguments = build_parser().parse_args(argv)
    if arguments.command == "doctor":
        write_report(json_output=arguments.json_output, stdout=sys.stdout)
        return 0
    if arguments.command == "verify":
        if arguments.verification in {"deployment", "deploy"}:
            return deployment.run(
                arguments.service,
                arguments.expected_revision,
                arguments.credentials_file,
                arguments.docker_context,
                arguments.repo,
                environment_id=arguments.environment_id,
                timeout=arguments.timeout,
                json_output=arguments.json_output,
                stdout=sys.stdout,
            )
        return _unreachable_command(arguments.verification)
    if arguments.command == "collect":
        if arguments.source == "all":
            files = CredentialFiles(
                core=arguments.credentials_file, network=arguments.network_credentials_file,
                pbs=arguments.pbs_credentials_file, dns=arguments.dns_credentials_file,
                opnsense=arguments.opnsense_credentials_file, omada=arguments.omada_credentials_file,
            )
            return collect_all(arguments.repo, files, json_output=arguments.json_output,
                               stdout=sys.stdout)
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
    if arguments.command == "recon":
        return recon.run(arguments.target, json_output=arguments.json_output, stdout=sys.stdout)
    if arguments.command == "entities":
        return entities.run_audit(arguments.repo, json_output=arguments.json_output, stdout=sys.stdout)
    if arguments.command == "query":
        return _run_query(arguments.repo, arguments.statement, arguments.format,
                          arguments.no_header)
    if arguments.command == "render":
        return _run_render(arguments)
    if arguments.command == "plan":
        return _run_plan(arguments)
    if arguments.command == "new":
        return _run_new(arguments)
    if arguments.command == "recall":
        try:
            return memory.print_recall(arguments.repo, arguments.terms, sys.stdout)
        except memory.MemoryError as error:
            print(f"recall: {error}", file=sys.stderr)
            return error.code
    return _unreachable_command(arguments.command)


def _run_query(repo: Path, statement: str, output_format: str, no_header: bool) -> int:
    """Build a current disposable cache, then delegate query formatting to its module."""
    try:
        result = cache.build(repo)
    except cache.CacheError as error:
        print(f"query: {error}", file=sys.stderr)
        return error.code
    arguments = [
        "--repo", str(repo), "--database", str(result.database), "--query", statement,
        "--format", output_format,
    ]
    if no_header:
        arguments.append("--no-header")
    return cache.main(arguments)


def _run_render(arguments: argparse.Namespace) -> int:
    """Dispatch one deterministic generated-view renderer."""
    try:
        if arguments.renderer == "docs":
            status = collection_status(
                arguments.repo, since=arguments.since, json_output=False, stdout=sys.stderr
            )
            if status != 0:
                return status
            result = render.render_docs(arguments.repo, arguments.output)
            print(f"render-docs: wrote {len(result.pages)} page(s) under {result.output}")
            return 0
        if arguments.renderer == "digest":
            path = memory.render_digest(arguments.repo, arguments.output, arguments.journal)
        elif arguments.renderer == "context":
            path = memory.render_context(arguments.repo, arguments.output)
        elif arguments.renderer == "runbook-catalog":
            path = memory.render_runbook_catalog(arguments.repo, arguments.output)
        else:
            return _unreachable_command(arguments.renderer)
        print(f"render-{arguments.renderer}: wrote {path}")
        return 0
    except (memory.MemoryError, render.RenderError) as error:
        print(f"render-{arguments.renderer}: {error}", file=sys.stderr)
        return error.code
    except (KeyError, OSError, OverflowError, TypeError, UnicodeError, ValueError):
        print(f"render-{arguments.renderer}: malformed or unavailable source", file=sys.stderr)
        return 3


def _run_plan(arguments: argparse.Namespace) -> int:
    """Dispatch one directive lifecycle action; every move regenerates the roadmap."""
    repo = arguments.repo.resolve()
    try:
        if arguments.action == "scratch":
            print(planning.scratch(repo, " ".join(arguments.note)))
        elif arguments.action == "idea":
            directive, path = planning.idea(repo, arguments.source, arguments.horizon)
            print(f"minted {directive} → {path} (horizon: {arguments.horizon})\nroadmap updated.")
        elif arguments.action == "service":
            directive, path = planning.service(repo, arguments.name)
            print(f"sketched {directive} → {path}\nroadmap updated.")
        elif arguments.action in {"promote", "start"}:
            stage = "projects" if arguments.action == "start" else arguments.stage
            path = planning.promote(repo, arguments.id, stage)
            print(f"{arguments.id} → {stage} : {path}\nroadmap updated.")
        elif arguments.action == "archive":
            path = planning.promote(repo, arguments.id, "archive", abandon=arguments.abandon)
            print(f"{arguments.id} archived: {path}\nroadmap updated.")
        elif arguments.action == "show":
            print(planning.find(repo / "planning", arguments.id))
        elif arguments.action == "list":
            print(planning.roadmap(repo))
        else:
            return _unreachable_command(arguments.action)
    except (planning.PlanError, OSError, subprocess.CalledProcessError) as error:
        print(f"plan: {error}", file=sys.stderr)
        return 1
    return 0


def _run_new(arguments: argparse.Namespace) -> int:
    """Stamp one artifact skeleton and say what to fill in next."""
    repo = arguments.repo.resolve()
    try:
        if arguments.kind == "service":
            path = scaffold.service(repo, arguments.name)
            print(f"created {path}/ — fill every TODO, then deploy: "
                  f"scripts/gitops-deploy.sh {path.name}")
        elif arguments.kind == "script":
            path = scaffold.script(repo, arguments.name)
            print(f"created {path} — fill the header (purpose/tier/usage) and the body")
        elif arguments.kind == "runbook":
            path = scaffold.runbook(repo, arguments.title)
            print(f"created {path} — remember to list it in runbooks/README.md")
        elif arguments.kind == "adr":
            print(f"created {scaffold.adr(repo, arguments.title)}")
        elif arguments.kind == "journal":
            path = scaffold.journal(repo, arguments.episode, arguments.title)
            print(f"created {path} — write it RAW (journal/README.md); do not summarize at write time")
        else:
            return _unreachable_command(arguments.kind)
    except (scaffold.ScaffoldError, OSError) as error:
        print(f"new: {error}", file=sys.stderr)
        return 1
    return 0


def _unreachable_command(command: str) -> NoReturn:
    """Make an unexpected parser result a loud programming error."""
    raise RuntimeError(f"unhandled command: {command}")
