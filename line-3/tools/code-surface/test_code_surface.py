"""Real proof replay plus explicitly synthetic instruction-boundary adversaries."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import code_surface as surface

FOLDER = Path(__file__).resolve().parent


def evidence(token='zto'):
    return surface.ancestry.read_json(FOLDER.parent / 'code-delta' / (token + '-later-proof.json'))


def request(token='zto'):
    return surface.ancestry.read_json(FOLDER / (token + '-request.json'))


def pattern(selector=b'\xa9\x05\x9c\xbb', destination=10):
    return b'\x63' + selector + b'\x14\x61' + destination.to_bytes(2, 'big') + b'\x57'


class SurfaceTests(unittest.TestCase):
    def test_real_proofs(self):
        for token, count in (('zto', 9), ('imd', 45)):
            result = surface.inspect(evidence(token), request(token))
            self.assertEqual(result['runtimes'][0]['candidate_count'], count)
            self.assertTrue(all(f['match_count'] == 1 for f in result['functions']))
            self.assertEqual(result['proof']['anchor'], 'unanchored-rpc-header')
            self.assertFalse(result['reachability_verified'])
            self.assertFalse(result['interface_completeness_verified'])
            self.assertFalse(result['semantic_safety_verified'])

    def test_known_keccak_vectors(self):
        vectors = {'transfer(address,uint256)': '0xa9059cbb',
                   'approve(address,uint256)': '0x095ea7b3',
                   'balanceOf(address)': '0x70a08231',
                   'bar(bytes3[2])': '0xfce353f6', 'baz(uint32,bool)': '0xcdcd77c0'}
        for signature, selector in vectors.items():
            self.assertEqual(surface.signature_selector(signature), selector)

    def test_nested_canonical_types(self):
        for signature in ('f((uint256,address)[][2],bytes32)', 'f(())', 'f(uint8[0])',
                          'f(function,fixed128x18,ufixed256x80)', 'f(int256,bool,string)',
                          '_f$1((bytes,(bool,uint256)[])[])'):
            self.assertEqual(len(surface.signature_selector(signature)), 10)

    def test_noncanonical_and_malformed_signatures(self):
        for signature in ('f(uint)', 'f(int)', 'f(bytes33)', 'f(uint7)', 'f(uint264)',
                          'f(uint08)', 'f(fixed)', 'f(ufixed8x81)', 'f(fixed7x1)',
                          'f(address payable)', 'f(bytes memory)', 'f(tuple)',
                          'f(uint256 x)', 'f(uint256)returns(bool)', 'f(uint256,)',
                          'f(,uint256)', 'f(uint256[01])', 'f(uint256[-1])',
                          'f(uint256[1)', 'f(uint256))', 'f((uint256)', 'f(é)',
                          'f( uint256)', '1f()', 'f(uint256[1 2])', 'f(uint256[0x1])'):
            with self.subTest(signature=signature), self.assertRaises(ValueError):
                surface.signature_selector(signature)

    def test_signature_bounds(self):
        for value in (None, 12, 'a' * 513, 'f(' + '(' * 17 + ')' * 18,
                      'f(uint8[' + str(2**256) + '])'):
            with self.assertRaises(ValueError):
                surface.signature_selector(value)

    def test_selector_collision_is_preserved(self):
        query = request()
        query['signatures'] = ['burn(uint256)', 'collate_propagate_storage(bytes16)']
        result = surface.inspect(evidence(), query)
        self.assertEqual(result['requested_selector_collisions'], [
            {'selector': '0x42966c68', 'signatures': query['signatures']}])
        self.assertEqual(len(result['functions']), 2)

    def test_no_pattern_is_not_a_denial_of_interface(self):
        query = request()
        query['signatures'] = ['burn(uint256)']
        result = surface.inspect(evidence(), query)
        self.assertEqual(result['functions'][0]['status'], 'not-observed')
        self.assertNotIn('decision', result)
        self.assertFalse(result['interface_completeness_verified'])

    def test_push_data_is_not_dispatch(self):
        embedded = pattern() + b'\x5b'
        code = b'\x7f' + embedded.ljust(32, b'\x00') + b'\x00'
        self.assertEqual(surface.scan(code)[1], [])

    def test_jumpdest_inside_push_data_is_not_valid(self):
        code = pattern(destination=11) + b'\x60\x5b'
        self.assertEqual(surface.scan(code)[1:], ([], 1))

    def test_invalid_out_of_bounds_and_non_jumpdest_targets(self):
        for target in (0, 11, 65535):
            self.assertEqual(surface.scan(pattern(destination=target) + b'\x5b')[1:], ([], 1))

    def test_short_and_zero_selector_pushes(self):
        for width in range(5):
            code = bytes([0x5f + width]) + b'\x01' * width + b'\x14\x60' + bytes([width + 5]) + b'\x57\x5b'
            candidate = surface.scan(code)[1][0]
            self.assertEqual(candidate['selector'], '0x' + (b'\x01' * width).rjust(4, b'\x00').hex())
        # PUSH0 destination is valid if offset zero is an actual JUMPDEST.
        self.assertEqual(surface.scan(b'\x5b\x5f\x14\x5f\x57')[1][0]['destination_pc'], 0)

    def test_truncated_push_does_not_smuggle_instructions(self):
        self.assertEqual(surface.scan(b'\x7f' + pattern() + b'\x5b')[1], [])
        for cut in range(10):
            self.assertEqual(surface.scan(pattern()[:cut])[1], [])

    def test_gt_binary_search_branch_is_not_eq_candidate(self):
        code = pattern().replace(b'\x14', b'\x11') + b'\x5b'
        self.assertEqual(surface.scan(code)[1], [])

    def test_unreachable_pattern_is_explicitly_only_a_candidate(self):
        code = b'\x00' + pattern(destination=11) + b'\x5b'
        self.assertEqual(len(surface.scan(code)[1]), 1)

    def test_metadata_does_not_hide_code(self):
        # Valid Solidity CBOR with a byte-string payload containing a real pattern.
        prefix = bytes.fromhex('a264736f6c63430008196469706673') + bytes([0x4b])
        start = 1 + len(prefix)
        metadata = prefix + pattern(destination=start + 10) + b'\x5b'
        code = b'\x00' + metadata + len(metadata).to_bytes(2, 'big')
        result = surface.scan(code)
        self.assertIsNotNone(result[0])
        self.assertEqual(len(result[1]), 1)
        self.assertTrue(result[1][0]['pattern_overlaps_recognized_metadata'])
        self.assertTrue(result[1][0]['destination_in_recognized_metadata'])

    def test_request_target_chain_fields_and_duplicates(self):
        for field, value in (('target', surface.lens.IMD), ('chain_id', True),
                             ('schema', 'other'), ('signatures', []),
                             ('signatures', ['name()'] * 2), ('signatures', ['name()'] * 65)):
            query = request()
            query[field] = value
            with self.assertRaises(ValueError):
                surface.inspect(evidence(), query)
        query = request()
        query['trusted'] = True
        with self.assertRaises(ValueError):
            surface.inspect(evidence(), query)

    def test_request_digest_ignores_order_but_commits_to_signatures(self):
        query = request()
        original = surface.inspect(evidence(), query)['request_digest']
        query['signatures'].reverse()
        self.assertEqual(surface.inspect(evidence(), query)['request_digest'], original)
        query['signatures'].pop()
        self.assertNotEqual(surface.inspect(evidence(), query)['request_digest'], original)

    def test_corruption_and_forged_consistent_observation(self):
        for mutation in ('proof', 'header', 'runtime'):
            bundle = evidence()
            if mutation == 'proof':
                bundle['proofs'][0]['accountProof'].pop()
            elif mutation == 'header':
                bundle['header_rlp'] = bundle['header_rlp'][:-2] + 'ff'
            else:
                node = bundle['observation']['nodes'][0]
                node.update(code='0x00', code_bytes=1, code_hash=surface.lens.digest(b'\0'))
                bundle['observation']['effective_code_hash'] = node['code_hash']
                bundle['proofs'][0]['codeHash'] = node['code_hash']
            with self.assertRaises(ValueError):
                surface.inspect(bundle, request())

    def test_anchor_equality_does_not_authenticate_anchor(self):
        bundle = evidence()
        observed_hash = bundle['observation']['block']['hash']
        result = surface.inspect(bundle, request(), observed_hash)
        self.assertEqual(result['proof']['anchor'], 'caller-supplied-block-hash')
        self.assertFalse(result['anchor_authenticity_verified'])
        wrong = surface.ancestry.read_json(FOLDER.parent / 'code-proof/zto-proof.json')['observation']['block']['hash']
        with self.assertRaises(ValueError):
            surface.inspect(bundle, request(), wrong)

    def test_bounded_previews_keep_full_match_count(self):
        # Rebuild a synthetic proof, never save it as real chain evidence.
        spec = importlib.util.spec_from_file_location('delta_fixture', FOLDER.parent / 'code-delta/test_code_delta.py')
        sys.path.insert(0, str(FOLDER.parent / 'code-delta'))
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        code = b'\x5b' + pattern(destination=0) * 200
        result = surface.inspect(fixture.synthetic_runtime(code), request())
        runtime = result['runtimes'][0]
        self.assertEqual(runtime['candidate_count'], 200)
        self.assertEqual(len(runtime['candidate_preview']), 64)
        self.assertEqual(runtime['omitted_candidate_count'], 136)
        transfer = next(f for f in result['functions'] if f['selector'] == '0xa9059cbb')
        self.assertEqual(transfer['match_count'], 200)
        self.assertEqual(len(transfer['matches']), 16)
        self.assertEqual(transfer['omitted_match_count'], 184)

    def test_runtime_bound(self):
        with self.assertRaises(ValueError):
            surface.scan(b'\0' * (surface.lens.MAX_CODE + 1))

    def test_beacon_and_path_runtime_deduplicated_without_claiming_routing(self):
        spec = importlib.util.spec_from_file_location('proof_fixture', FOLDER.parent / 'code-proof/test_code_proof.py')
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        result = surface.inspect(fixture.synthetic_beacon_bundle(), request())
        self.assertEqual(len(result['runtimes']), 2)
        implementation = next(r for r in result['runtimes'] if r['address'] == surface.lens.IMD)
        self.assertEqual(set(implementation['roles']), {'beacon', 'candidate-path'})
        self.assertEqual(result['proof']['unproven_beacon_call_results'], [surface.lens.IMD])
        self.assertFalse(result['reachability_verified'])

    def test_json_boundary_and_duplicate_keys(self):
        with self.assertRaises(ValueError):
            surface.ancestry.read_json(Path.cwd().parent / 'not-read.json')
        with self.assertRaises(ValueError):
            json.loads('{"schema":1,"schema":2}', object_pairs_hook=surface.ancestry.no_duplicates)

    def test_cli_success_and_failure_no_partial_result(self):
        command = [sys.executable, '-B', str(FOLDER / 'code_surface.py'), '--bundle',
                   str(FOLDER.parent / 'code-delta/zto-later-proof.json'), '--request']
        for token, status in (('zto', 0), ('imd', 1)):
            run = subprocess.run(command + [str(FOLDER / (token + '-request.json'))],
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, status)
            if status:
                self.assertEqual(run.stdout, '')
            else:
                self.assertEqual(json.loads(run.stdout)['schema'], 'code-surface-result-v1')

    def test_demo(self):
        import demo
        self.assertTrue(demo.main()['demonstration_passed'])


if __name__ == '__main__':
    unittest.main()
