"""Full-envelope regression checks with synthetic fixtures."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("governance_validator", ROOT / "governance/validate.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((ROOT / "governance/example.json").read_text())

    def test_provisional_example(self):
        self.assertEqual(validator.validate(self.fixture), [])

    def test_unaccepted_gap_blocks_validation(self):
        self.fixture["meta"]["status"] = "validated"
        self.assertIn("validated_has_unaccepted_missing_inputs", validator.validate(self.fixture))

    def test_per_item_explicit_override(self):
        self.fixture["meta"]["status"] = "validated"
        self.fixture["qa"]["accepted_missing_inputs"] = [{
            "name": "review_criteria", "accepted_by": "example_reviewer",
            "acceptance_timestamp": "2000-01-01T00:00:00Z",
            "acceptance_note": "Synthetic acceptance fixture, not real approval.",
            "impact": "The result remains illustrative only.",
        }]
        self.assertEqual(validator.validate(self.fixture), [])
        del self.fixture["qa"]["accepted_missing_inputs"][0]["impact"]
        self.assertIn("invalid_acceptance_record", validator.validate(self.fixture))

    def test_unrelated_override_does_not_accept_gap(self):
        self.fixture["meta"]["status"] = "validated"
        self.fixture["qa"]["accepted_missing_inputs"] = [{
            "name": "unrelated", "accepted_by": "example_reviewer",
            "acceptance_timestamp": "2000-01-01T00:00:00Z",
            "acceptance_note": "Synthetic only.", "impact": "None.",
        }]
        errors = validator.validate(self.fixture)
        self.assertIn("duplicate_or_unknown_accepted_input", errors)
        self.assertIn("validated_has_unaccepted_missing_inputs", errors)

    def test_incomplete_metadata_and_qa(self):
        del self.fixture["meta"]["scope"]
        self.fixture["qa"]["required_inputs"] = True
        self.assertTrue(validator.validate(self.fixture))

    def test_missing_list_cannot_hide_gap(self):
        self.fixture["qa"]["missing_inputs"] = []
        self.assertIn("missing_inputs_do_not_reconcile", validator.validate(self.fixture))

    def test_severity_cannot_be_downgraded(self):
        self.fixture["qa"]["missing_inputs"][0]["severity"] = "nice_to_have"
        self.assertIn("missing_input_severity_changed", validator.validate(self.fixture))

    def test_questions_and_false_string_check(self):
        self.fixture["qa"]["user_questions"] = []
        self.fixture["qa"]["checks"][0]["passed"] = "false"
        errors = validator.validate(self.fixture)
        self.assertIn("unresolved_inputs_need_questions", errors)
        self.assertIn("invalid_check_record", errors)

    def test_bad_types_fail_without_crash(self):
        for value in [None, [], True, 7, {"meta": {}}]:
            self.assertTrue(validator.validate(value))
        for location, field in [("meta", "status")]:
            for value in [[], {}, True]:
                bad = copy.deepcopy(self.fixture)
                bad[location][field] = value
                self.assertTrue(validator.validate(bad))

    def test_duplicate_inputs_and_nonfinite_numbers(self):
        self.fixture["qa"]["provided_inputs"] *= 2
        self.fixture["content"]["payload"]["value"] = float("nan")
        self.assertTrue(validator.validate(self.fixture))

    def test_cli_and_duplicate_json_keys(self):
        good = subprocess.run([sys.executable, str(ROOT / "governance/validate.py"),
                               str(ROOT / "governance/example.json")], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertFalse(json.loads(good.stdout)["authorization_granted"])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.json"
            path.write_text('{"meta":{},"meta":{}}')
            bad = subprocess.run([sys.executable, str(ROOT / "governance/validate.py"), str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertFalse(json.loads(bad.stdout)["structure_valid"])


if __name__ == "__main__":
    unittest.main()
