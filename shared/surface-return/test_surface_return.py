"""Real saved evidence and explicitly synthetic mutations; no RPC calls."""
import copy
import io
import json
from contextlib import redirect_stdout, redirect_stderr
import unittest
from unittest.mock import patch
import surface_return as tool


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.bundle, self.call = tool.demo_inputs()

    def aligned_fixture(self):
        # Synthetic call only: use the proof's actual header identity to exercise
        # alignment logic. This is never saved or described as a real call.
        call = copy.deepcopy(self.call)
        _, fields = tool.surface.ancestry.header_identity(self.bundle['header_rlp'])
        call['block'] = dict(self.bundle['observation']['block'],
                             timestamp=hex(tool.surface.proof.scalar(fields[11])))
        return call

    def evaluate(self, call=None, signature='totalSupply()', types=None, bundle=None):
        return tool.evaluate(bundle or self.bundle, call or self.call, signature, types or ['uint256'])

    def test_real_saved_mismatch_withholds_values(self):
        other = tool.returns.changes.load_observation(tool.HERE / 'zto-other-block-call.json')
        result = self.evaluate(other)
        self.assertEqual(result['verdict'], 'mismatch')
        self.assertTrue(result['state_inclusion_verified'])
        self.assertTrue(result['checks']['call_selector_matches'])
        self.assertEqual(result['proof_anchor'], 'unanchored-rpc-header')
        self.assertIn('same_block_hash', result['failed_checks'])
        self.assertIsNone(result['decoded_values'])

    def test_real_aligned_call_decodes_without_approval(self):
        result = self.evaluate(self.call)
        self.assertEqual(result['verdict'], 'aligned')
        self.assertEqual(result['decoded_values'][0]['value'], '1000000000000000000000000000')
        self.assertIn('unproven RPC claims', result['limits'])
        self.assertEqual(len(result['input_sha256']['proof_bundle']), 64)

    def test_each_identity_dimension_is_required(self):
        for key, value, check in [('number', '0x1', 'same_block_number'),
                                  ('hash', tool.returns.changes.load_observation(tool.HERE / 'zto-other-block-call.json')['block']['hash'], 'same_block_hash'),
                                  ('timestamp', '0x1', 'same_block_timestamp')]:
            call = self.aligned_fixture()
            call['block'][key] = value
            with self.subTest(key=key):
                result = self.evaluate(call)
                self.assertFalse(result['checks'][check])
                self.assertIsNone(result['decoded_values'])

    def test_wrong_target_refuses(self):
        call = self.aligned_fixture()
        call['call']['to'] = tool.returns.core.TOKENS['IMD']
        result = self.evaluate(call)
        self.assertFalse(result['checks']['same_target'])
        self.assertIsNone(result['decoded_values'])

    def test_wrong_signature_and_wrong_layout_refuse(self):
        self.assertFalse(self.evaluate(self.aligned_fixture(), 'decimals()')['checks']['call_selector_matches'])
        result = self.evaluate(self.aligned_fixture(), types=['string'])
        self.assertFalse(result['checks']['return_decoded'])
        self.assertIsNone(result['decoded_values'])

    def test_no_target_pattern_refuses(self):
        result = self.evaluate(self.aligned_fixture(), 'unknownFunction()')
        self.assertFalse(result['checks']['target_candidate_observed'])

    def test_revert_is_not_decoded(self):
        call = self.aligned_fixture()
        call['outcome'] = {'error': {'code': 3, 'message': 'execution reverted'}}
        result = self.evaluate(call)
        self.assertFalse(result['checks']['return_decoded'])
        self.assertIsNone(result['decoded_values'])

    def test_raw_proof_tamper_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['observation']['nodes'][0]['code_hash'] = '0x' + 'ab' * 32
        with self.assertRaises(ValueError):
            self.evaluate(self.aligned_fixture(), bundle=bundle)

    def test_chain_and_signature_inputs_rejected(self):
        call = self.aligned_fixture()
        call['chain_id'] = True
        with self.assertRaises(ValueError):
            self.evaluate(call)
        with self.assertRaises(ValueError):
            self.evaluate(signature='transfer(address,uint)')

    def test_demo_no_network_and_invalid_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(tool.returns.core, 'RPC', side_effect=AssertionError('network forbidden')):
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(tool.main(['--demo']), 0)
                self.assertEqual(tool.main(['--demo', '--signature', 'totalSupply()']), 1)
        self.assertEqual(json.loads(out.getvalue())['verdict'], 'aligned')

    def test_copied_sources_match_provenance(self):
        from pathlib import Path
        import hashlib
        p = json.loads((tool.HERE / 'provenance.json').read_text())
        for entry in p['files']:
            self.assertEqual(hashlib.sha256(Path(entry['copy']).read_bytes()).hexdigest(), entry['sha256'])


if __name__ == '__main__':
    unittest.main()
