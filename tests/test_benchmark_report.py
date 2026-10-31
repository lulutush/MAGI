"""Offline consistency checks, not regrading or independent benchmark replication.

Only public numeric records are read. No model, network or private state access.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import re
from statistics import median
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/evaluations/2026-10-30-browsecomp.data.json'
USAGE = (
    'input_tokens', 'cached_input_tokens', 'uncached_input_tokens',
    'output_tokens', 'reasoning_tokens', 'total_tokens',
)


def wilson_percent(k, n):
    z = 1.959963984540054
    p = k / n
    divisor = 1 + z * z / n
    center = (p + z * z / (2 * n)) / divisor
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / divisor
    return [100 * (center - half), 100 * (center + half)]


class BenchmarkReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding='utf-8'))

    def test_reproducible_selection_and_disjoint_stages(self):
        protocol = self.data['protocol']
        source = protocol['source']
        selected = protocol['selection']
        expected = random.Random(source['seed']).sample(range(source['available_rows']), 10)
        self.assertEqual([x['source_index'] for x in selected], expected)
        self.assertEqual(len({x['id'] for x in selected}), 10)
        for index, item in enumerate(selected):
            self.assertEqual(item['id'], f"bc-{item['source_index']:04d}")
            self.assertEqual(item['stage'], 'calibration' if index < 2 else 'scored')
            self.assertEqual(item['order'], ['off', 'on'] if index % 2 == 0 else ['on', 'off'])

    def test_complete_pairs_and_per_run_accounting(self):
        for stage, phase in self.data['phases'].items():
            ids = {x['id'] for x in self.data['protocol']['selection'] if x['stage'] == stage}
            expected = {(item, mode) for item in ids for mode in ('off', 'on')}
            self.assertEqual({(row['id'], row['mode']) for row in phase['runs']}, expected)
            self.assertEqual(len(phase['runs']), len(expected))
            for row in phase['runs']:
                self.assertIs(type(row['correct']), bool)
                self.assertIn(row['status'], ('completed', 'budget_exhausted'))
                if row['status'] == 'budget_exhausted':
                    self.assertFalse(row['correct'])
                self.assertEqual(row['input_tokens'], row['cached_input_tokens'] + row['uncached_input_tokens'])
                self.assertLessEqual(row['reasoning_tokens'], row['output_tokens'])
                self.assertEqual(row['total_tokens'], row['input_tokens'] + row['output_tokens'])
                self.assertLessEqual(row['model_responses'], row['model_requests'])
                self.assertLessEqual(row['model_requests'], self.data['protocol']['limits_per_run']['model_requests_including_subagents'])
                for key in USAGE:
                    self.assertIs(type(row[key]), int)
                    self.assertGreaterEqual(row[key], 0)

    def test_condition_totals_medians_and_intervals(self):
        for phase in self.data['phases'].values():
            for mode, summary in phase['conditions'].items():
                rows = [row for row in phase['runs'] if row['mode'] == mode]
                n = len(rows)
                correct = sum(row['correct'] for row in rows)
                self.assertEqual(summary['n'], n)
                self.assertEqual(summary['correct'], correct)
                self.assertAlmostEqual(summary['accuracy_percent'], 100 * correct / n)
                self.assertAlmostEqual(summary['median_wall_seconds'], median(row['wall_seconds'] for row in rows))
                for actual, expected in zip(summary['wilson_95_percent'], wilson_percent(correct, n)):
                    self.assertAlmostEqual(actual, expected, places=6)
                for key in USAGE + ('model_requests', 'tool_calls'):
                    self.assertEqual(summary[key], sum(row[key] for row in rows))

    def test_paired_outcomes_and_exact_test(self):
        for phase in self.data['phases'].values():
            pairs = {}
            for row in phase['runs']:
                pairs.setdefault(row['id'], {})[row['mode']] = row['correct']
            both = sum(pair['off'] and pair['on'] for pair in pairs.values())
            neither = sum(not pair['off'] and not pair['on'] for pair in pairs.values())
            off_only = sum(pair['off'] and not pair['on'] for pair in pairs.values())
            on_only = sum(pair['on'] and not pair['off'] for pair in pairs.values())
            discordant = off_only + on_only
            p = 1.0 if not discordant else min(
                1.0, 2 * sum(math.comb(discordant, i) for i in range(min(off_only, on_only) + 1)) / 2 ** discordant
            )
            expected = {
                'n': len(pairs), 'both_correct': both, 'both_incorrect': neither,
                'off_only_correct': off_only, 'on_only_correct': on_only,
                'difference_percentage_points': 100 * (on_only - off_only) / len(pairs),
                'mcnemar_exact_two_sided_p': p,
            }
            self.assertEqual(phase['paired'], expected)

    def test_stage_usage_includes_recorded_overhead_without_double_counting(self):
        for phase in self.data['phases'].values():
            usage = self.data['recorded_solver_usage_by_stage'][phase['source_tag']]
            for key in USAGE:
                self.assertEqual(usage[key], sum(row[key] for row in phase['runs']))
            self.assertEqual(usage['request_records'], sum(row['model_requests'] for row in phase['runs']))
            self.assertEqual(usage['completed_response_records'], sum(row['model_responses'] for row in phase['runs']))
        self.assertIn('calibration-v1', self.data['recorded_solver_usage_by_stage'])
        for section in ('recorded_solver_usage_by_stage', 'recorded_grader_usage_by_stage'):
            for usage in self.data[section].values():
                self.assertEqual(usage['input_tokens'], usage['cached_input_tokens'] + usage['uncached_input_tokens'])
                self.assertEqual(usage['total_tokens'], usage['input_tokens'] + usage['output_tokens'])
                self.assertLessEqual(usage['reasoning_tokens'], usage['output_tokens'])

    def test_descriptive_counts_and_post_answer_scope(self):
        phase = self.data['phases']['scored']
        for mode, counts in self.data['descriptive_outcomes_scored'].items():
            summary = phase['conditions'][mode]
            self.assertEqual(sum(counts.values()), summary['n'])
            self.assertEqual(counts['correct'], summary['correct'])
            self.assertEqual(counts['budget_exhausted'], sum(row['status'] == 'budget_exhausted' for row in phase['runs'] if row['mode'] == mode))
        component = self.data['component_usage_scored']
        self.assertFalse(component['post_answer_steps_change_scored_answer'])
        self.assertEqual(component['magi_router_runs'], phase['conditions']['on']['n'])
        completed = sum(row['mode'] == 'on' and row['status'] == 'completed' for row in phase['runs'])
        self.assertEqual(component['post_answer_gate_runs'], completed)
        self.assertEqual(component['post_answer_artifact_runs'], completed)
        self.assertEqual(component['native_delegation_calls'], 0)

    def test_public_schema_provenance_and_no_raw_text_fields(self):
        self.assertEqual(self.data['schema_version'], 'magi.benchmark-summary.v1')
        protocol = self.data['protocol']
        self.assertFalse(protocol['public_preregistration'])
        self.assertEqual(protocol['solver']['requested_model'], 'gpt-6-astra')
        self.assertEqual(protocol['solver']['reasoning_effort'], 'low')
        hashes = self.data['publication']['source_file_sha256']
        for digest in hashes.values():
            self.assertRegex(digest, r'\A[0-9a-f]{64}\Z')
        for path in hashes:
            self.assertFalse(Path(path).is_absolute())
        allowed = {
            'id', 'mode', 'status', 'correct', 'wall_seconds', 'model_requests',
            'model_responses', 'tool_calls', 'initial_instructions_chars', *USAGE,
        }
        for phase in self.data['phases'].values():
            for row in phase['runs']:
                self.assertEqual(set(row), allowed)
                self.assertTrue(re.fullmatch(r'bc-\d{4}', row['id']))


if __name__ == '__main__':
    unittest.main()
