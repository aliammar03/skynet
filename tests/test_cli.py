"""The CLI builds and its runtime report works without a network."""

import io
import json
from contextlib import redirect_stdout

from skynet import cli


def test_every_subcommand_is_registered() -> None:
    parser = cli.build_parser()
    actions = [a for a in parser._actions if a.dest == "command"]
    assert {"collect", "verify", "render", "entities", "query", "recall"} <= set(actions[0].choices)


def test_doctor_reports_runtime() -> None:
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(["doctor", "--json"])
    assert code == 0
    assert json.loads(out.getvalue())["scope"] == "runtime"
