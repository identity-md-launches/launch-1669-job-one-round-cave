import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import draft_bundle as tool


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observation = tool.drafts.gate.load(tool.drafts.DEFAULT_OBSERVATION)
        cls.policy = tool.drafts.gate.load(tool.drafts.DEFAULT_POLICY)

    def setUp(self):
        self.bundle, _ = tool.expected_bundle(self.observation, self.policy)

    def result(self, bundle=None, policy=None):
        return tool.check(self.bundle if bundle is None else bundle, self.observation,
                          self.policy if policy is None else policy)

    def test_real_complete_bundle(self):
        report = self.result()
        self.assertEqual(report['expected_count'], 3)
        self.assertTrue(report['matches_reviewed_bundle'])
        self.assertFalse(report['complete_wallet_audit'])
        self.assertEqual(sum(row['balance_raw'] == '0' for row in self.bundle['drafts']), 2)

    def test_order_independent(self):
        self.bundle['drafts'].reverse()
        self.assertTrue(self.result()['matches_reviewed_bundle'])

    def test_omitted_candidate(self):
        row = self.bundle['drafts'].pop()
        report = self.result()
        self.assertFalse(report['matches_reviewed_bundle'])
        self.assertEqual(report['missing_count'], 1)
        self.assertEqual(report['missing_pairs'][0]['spender'], row['spender'])

    def test_duplicate_cannot_replace_another(self):
        self.bundle['drafts'][1] = copy.deepcopy(self.bundle['drafts'][0])
        report = self.result()
        self.assertFalse(report['matches_reviewed_bundle'])
        self.assertEqual((report['duplicate_count'], report['missing_count'], report['unexpected_count']), (1, 1, 1))

    def test_altered_transaction(self):
        for field, value in [('data', '0x095ea7b3'), ('value', '0x1'), ('gas', '0x5208')]:
            changed = copy.deepcopy(self.bundle)
            changed['drafts'][0]['transaction'][field] = value
            report = self.result(changed)
            self.assertFalse(report['matches_reviewed_bundle'])
            self.assertEqual((report['missing_count'], report['unexpected_count']), (1, 1))

    def test_anchor_types_and_identity(self):
        for key, value in [('chain_id', True), ('chain_id', 1.0), ('block_number', 1),
                           ('block_hash', '0x' + '1' * 64), ('schema', 'other')]:
            changed = copy.deepcopy(self.bundle)
            changed[key] = value
            self.assertEqual(self.result(changed)['status'], 'wrong_evidence_anchor')

    def test_insufficient_evidence_cannot_match_empty(self):
        policy = copy.deepcopy(self.policy)
        policy['minimum_block'] += 1
        policy['maximum_block'] += 1
        bundle, _ = tool.expected_bundle(self.observation, policy)
        self.assertEqual(self.result(bundle, policy)['status'], 'insufficient_evidence')
        self.assertFalse(self.result(bundle, policy)['matches_reviewed_bundle'])

    def test_pass_policy_can_have_no_candidates(self):
        policy = copy.deepcopy(self.policy)
        review = tool.drafts.gate.evaluate(self.observation, self.policy)
        policy['pairs'] = [{'owner': row['owner'], 'spender': row['spender'],
                            'maximum_allowance_raw': row['allowance_raw']}
                           for row in review['pairs']]
        bundle, _ = tool.expected_bundle(self.observation, policy)
        result = self.result(bundle, policy)
        self.assertEqual(result['status'], 'no_reviewed_candidates')
        self.assertTrue(result['matches_reviewed_bundle'])
        self.assertFalse(result['complete_wallet_audit'])

    def test_malformed_shape_and_size(self):
        for value in [None, [], {**self.bundle, 'extra': True},
                      {**self.bundle, 'drafts': {}}, {**self.bundle, 'drafts': [None] * 65}]:
            with self.assertRaises(ValueError):
                self.result(value if value is not None else [])

    def test_json_roundtrip_and_nonfinite_values(self):
        self.assertTrue(self.result(json.loads(json.dumps(self.bundle)))['matches_reviewed_bundle'])
        self.bundle['drafts'][0]['transaction']['gas'] = float('nan')
        with self.assertRaises(ValueError):
            self.result()

    def test_cli_and_file_guards(self):
        scratch = Path.cwd() / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            base = Path(directory)
            observation = base / 'observation.json'
            policy = base / 'policy.json'
            bundle = base / 'bundle.json'
            observation.write_text(json.dumps(self.observation))
            policy.write_text(json.dumps(self.policy))
            bundle.write_text(json.dumps(self.bundle))
            common = ['--observation', str(observation), '--policy', str(policy)]

            def invoke(args):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = tool.main(args)
                return code, out.getvalue(), err.getvalue()

            self.assertEqual(invoke(common + ['--bundle', str(bundle)])[0], 0)
            self.assertEqual(json.loads(invoke(common + ['--emit'])[1]), self.bundle)
            self.bundle['drafts'].pop()
            bundle.write_text(json.dumps(self.bundle))
            self.assertEqual(invoke(common + ['--bundle', str(bundle)])[0], 3)
            stale = copy.deepcopy(self.policy)
            stale['minimum_block'] += 1
            stale['maximum_block'] += 1
            policy.write_text(json.dumps(stale))
            self.assertEqual(invoke(common + ['--bundle', str(bundle)])[0], 4)
            self.assertEqual(invoke(common + ['--emit'])[0], 1)
            policy.write_text(json.dumps(self.policy))
            bundle.write_text('{"schema": "a", "schema": "b"}')
            code, _, err = invoke(common + ['--bundle', str(bundle)])
            self.assertEqual(code, 1)
            self.assertIn('duplicate JSON key', err)
            bundle.write_text(' ' * (tool.drafts.gate.LIMIT + 1))
            self.assertEqual(invoke(common + ['--bundle', str(bundle)])[0], 1)
            outside = str(Path.cwd().parent / 'not-read.json')
            code, _, err = invoke(common + ['--bundle', outside])
            self.assertEqual(code, 1)
            self.assertIn('inside the current workspace', err)
            self.assertEqual(invoke(['--bundle', str(bundle)])[0], 1)
            self.assertEqual(invoke(['--observation', str(observation)])[0], 1)


if __name__ == '__main__':
    unittest.main()
