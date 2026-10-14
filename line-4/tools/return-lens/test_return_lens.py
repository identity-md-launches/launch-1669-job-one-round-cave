import copy
import io
import json
from contextlib import redirect_stdout, redirect_stderr
import unittest

import return_lens as lens


def word(number):
    return number.to_bytes(32, 'big', signed=number < 0)


def dynamic(data):
    return word(len(data)) + data + bytes((-len(data)) % 32)


def raw(data):
    return '0x' + data.hex()


class ReturnLensTests(unittest.TestCase):
    def setUp(self):
        self.obs = lens.changes.load_observation(
            lens.HERE.parent / 'call-rehearsal' / 'zto-observation.json')

    def test_saved_real_zto_and_context(self):
        result = lens.evaluate(self.obs, ['uint256'])
        self.assertEqual(result['verdict'], 'decoded')
        self.assertEqual(result['values'][0]['value'], '1000000000000000000000000000')
        self.assertEqual(result['call'], self.obs['call'])
        self.assertEqual(result['block'], self.obs['block'])
        self.assertEqual(result['raw'], self.obs['outcome']['result'])

    def test_static_tuple(self):
        address = bytes.fromhex(lens.core.TOKENS['ZTO'][2:])
        payload = word(255) + word(-128) + word(1) + bytes(12) + address + b'abc' + bytes(29)
        values = lens.decode(raw(payload), ['uint8', 'int8', 'bool', 'address', 'bytes3'])
        self.assertEqual([v['value'] for v in values],
                         ['255', '-128', True, lens.core.TOKENS['ZTO'], '0x616263'])

    def test_dynamic_tuple_and_utf8_byte_length(self):
        text = 'seed 🐸'.encode()
        first = dynamic(text)
        payload = word(96) + word(7) + word(96 + len(first)) + first + dynamic(b'\x01\xff')
        values = lens.decode(raw(payload), ['string', 'uint256', 'bytes'])
        self.assertEqual([v['value'] for v in values], ['seed 🐸', '7', '0x01ff'])

    def test_empty_dynamic_and_int256_boundaries(self):
        self.assertEqual(lens.decode(raw(word(32) + word(0)), ['string'])[0]['value'], '')
        for number in (-2**255, 2**255 - 1):
            self.assertEqual(lens.decode(raw(word(number)), ['int256'])[0]['value'], str(number))

    def test_static_noncanonical_values(self):
        for kind, payload in [('uint8', word(256)), ('int8', word(128)),
                              ('int8', word(255)), ('bool', word(2)),
                              ('address', word(2**160)), ('bytes3', b'abc' + bytes(28) + b'x')]:
            with self.subTest(kind=kind, payload=payload), self.assertRaises(ValueError):
                lens.decode(raw(payload), [kind])

    def test_dynamic_corruption(self):
        cases = [word(0) + word(0), word(33) + word(0), word(64) + word(0),
                 word(32), word(32) + word(2**256 - 1),
                 word(32) + word(1) + b'x' + bytes(30) + b'y',
                 word(64) + word(64) + dynamic(b'a') + dynamic(b'b'),
                 word(32) + dynamic(b'a') + word(0)]
        for index, payload in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                lens.decode(raw(payload), ['bytes', 'bytes'] if index == 6 else ['bytes'])

    def test_invalid_utf8_is_inconclusive(self):
        obs = copy.deepcopy(self.obs)
        obs['returns'] = 'raw'
        obs['outcome'] = {'result': raw(word(32) + dynamic(b'\xff'))}
        self.assertEqual(lens.evaluate(obs, ['string'])['verdict'], 'inconclusive')

    def test_wrong_layout_extra_and_truncated_bytes(self):
        for payload in (b'', bytes(31), bytes(33), bytes(64)):
            with self.subTest(length=len(payload)), self.assertRaises(ValueError):
                lens.decode(raw(payload), ['uint256'])
        self.assertEqual(lens.evaluate(self.obs, ['string'])['verdict'], 'inconclusive')

    def test_revert_transport_and_invalid_saved_interpretation(self):
        for outcome in ({'error': {'code': 3, 'message': 'execution reverted'}},
                        {'error': {'code': -32000, 'message': 'unavailable'}},
                        {'result': '0x'}):
            obs = copy.deepcopy(self.obs)
            obs['outcome'] = outcome
            self.assertEqual(lens.evaluate(obs, ['uint256'])['verdict'], 'inconclusive')

    def test_invalid_type_lists(self):
        for types in ([], ['uint'], ['uint7'], ['int264'], ['bytes0'], ['bytes33'],
                      ['string[]'], ['(bool)'], ['uint256'] * 33, [None], 'uint256'):
            with self.subTest(types=types), self.assertRaises(ValueError):
                lens.layout(types)

    def test_evidence_validation(self):
        obs = copy.deepcopy(self.obs)
        obs['chain_id'] = 5
        with self.assertRaises(ValueError):
            lens.evaluate(obs, ['uint256'])

    def test_cli_demo_and_invalid_layout(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(lens.main(['demo']), 0)
        self.assertEqual(json.loads(out.getvalue())['verdict'], 'decoded')
        with redirect_stderr(err):
            self.assertEqual(lens.main(['check', 'not-read.json', '--types', 'address[]']), 2)
        self.assertIn('unsupported ABI type', err.getvalue())


if __name__ == '__main__':
    unittest.main()
