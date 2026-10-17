"""Keep every advertised template and fenced JSON envelope compatible with the CLI."""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from magi import validate_artifact

ROOT = Path(__file__).resolve().parents[1]


class DocumentedExamplesTests(unittest.TestCase):
    def test_empty_templates_are_valid_and_empty(self):
        for path in sorted((ROOT / "templates").glob("*.json")):
            with self.subTest(template=path.name):
                data = json.loads(path.read_text())
                self.assertEqual(validate_artifact(data), [])
                self.assertEqual(data["meta"]["status"], "draft")
                if path.name == "memory.json":
                    self.assertEqual(data["content"]["payload"]["entries"], [])
                elif path.name == "project-registry.json":
                    self.assertEqual(data["content"]["payload"]["projects"], [])

    def test_adapter_and_protocol_json_examples(self):
        paths = [ROOT / "protocol/MAGI.md", ROOT / "skills/magi/SKILL.md",
                 ROOT / "adapters/claude-code/CLAUDE.md", ROOT / "adapters/gpt/INSTRUCTIONS.md"]
        for path in paths:
            with self.subTest(path=path.name):
                snippets = re.findall(r"```json\s*\n(.*?)\n```", path.read_text(), re.DOTALL)
                self.assertTrue(snippets)
                for text in snippets:
                    self.assertEqual(validate_artifact(json.loads(text)), [])


if __name__ == "__main__":
    unittest.main()
