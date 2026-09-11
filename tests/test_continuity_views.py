"""Keep the generated continuity views distinct from the normal agent-memory intake."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STALE_BOOT_LANGUAGE = re.compile(r"cold.?boot|cold.?start|reads first on a cold", re.IGNORECASE)


class ContinuityViewContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_digest_is_recent_activity_retrieval(self) -> None:
        digest = self.read("docs/generated/06-agent-digest.md")
        renderer = self.read("scripts/render-digest.sh")
        for text, name in ((digest, "generated digest"), (renderer, "digest renderer")):
            self.assertNotRegex(text, STALE_BOOT_LANGUAGE, name)
        self.assertIn("summary: Recent-activity, episodic, and open-thread retrieval view.", digest)
        self.assertIn("Normal fresh-session continuity starts with `agent_docs/`", digest)
        for heading in ("## 🧷 Recent decisions", "## 🧵 Open threads", "## 📓 Recent episodes"):
            self.assertIn(heading, digest)

    def test_context_map_is_on_demand_routing_index(self) -> None:
        context_map = self.read("docs/generated/07-context-map.md")
        renderer = self.read("scripts/render-context-map.sh")
        for text, name in ((context_map, "generated context map"), (renderer, "context-map renderer")):
            self.assertNotRegex(text, STALE_BOOT_LANGUAGE, name)
        self.assertNotIn("coldboot=", renderer)
        self.assertIn("summary: On-demand load-cost and context-routing index.", context_map)
        self.assertIn("Use this map after normal continuity intake", context_map)
        self.assertIn("On-demand corpus", context_map)
        self.assertNotIn("Cold-boot read:", context_map)

    def test_generated_catalog_names_both_distinct_views(self) -> None:
        catalog = self.read("docs/generated/README.md")
        renderer = self.read("scripts/render-docs.sh")
        for text, name in ((catalog, "generated catalog"), (renderer, "docs renderer")):
            self.assertIn("06-agent-digest", text, name)
            self.assertIn("07-context-map", text, name)
        self.assertIn("recent-activity / episodic / open-thread retrieval", catalog)
        self.assertIn("on-demand load-cost and context-routing index", catalog)


if __name__ == "__main__":
    unittest.main()
