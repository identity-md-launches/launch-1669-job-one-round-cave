#!/usr/bin/env python3
"""Join proof-backed selector candidates and explicitly decoded call returns."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'code-surface'))
import code_surface as surface
sys.path.insert(0, str(HERE / 'return-lens'))
import return_lens as returns

SCHEMA = 'surface-return-context-v1'
LIMITS = ('Aligned historical evidence is not a verified ABI, routing or reachability proof, '
          'code approval, current-state check, permission to transact or execution guarantee. '
          'Return types and signature are caller choices. The code proof is unanchored unless '
          'the caller independently supplies an authentic block hash; call returns remain '
          'unproven RPC claims even when code inclusion verifies. Nothing is signed or sent.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def evaluate(bundle, observation, signature, types, anchor_hash=None):
    """Revalidate both raw inputs; release joined values only on exact alignment."""
    selector = surface.signature_selector(signature)
    decoded = returns.evaluate(observation, types)
    target = decoded['call']['to'].lower()
    request = {'schema': 'code-surface-request-v1', 'chain_id': 1,
               'target': bundle['observation']['target'], 'signatures': [signature]}
    inventory = surface.inspect(bundle, request, anchor_hash)
    _, fields = surface.ancestry.header_identity(bundle['header_rlp'])
    code_timestamp = hex(surface.proof.scalar(fields[11]))
    call_block = decoded['block']
    checks = {
        'same_target': target == inventory['target'],
        'same_block_number': call_block['number'] == inventory['code_block']['number'],
        'same_block_hash': call_block['hash'].lower() == inventory['code_block']['hash'],
        'same_block_timestamp': call_block['timestamp'] == code_timestamp,
        'call_selector_matches': decoded['call']['data'][:10].lower() == selector,
        # An implementation/beacon pattern does not establish routing at the target.
        'target_candidate_observed': any(m['address'] == target
                                        for m in inventory['functions'][0]['matches']),
        'return_decoded': decoded['verdict'] == 'decoded',
    }
    aligned = all(checks.values())
    choice = {'signature': signature, 'types': returns.layout(types), 'anchor_hash': anchor_hash}
    return {
        'schema': SCHEMA, 'verdict': 'aligned' if aligned else 'mismatch',
        'checks': checks, 'failed_checks': [key for key, passed in checks.items() if not passed],
        'chain_id': 1, 'target': target, 'signature': signature, 'selector': selector,
        'code_block': inventory['code_block'], 'call_block': call_block,
        'proof_anchor': inventory['proof']['anchor'],
        'state_inclusion_verified': inventory['proof']['state_inclusion_verified'],
        'target_pattern_matches': [m for m in inventory['functions'][0]['matches']
                                   if m['address'] == target],
        'decoded_values': decoded.get('values') if aligned else None,
        'return_verdict': decoded['verdict'],
        'input_sha256': {'proof_bundle': digest(bundle), 'call_observation': digest(observation),
                         'caller_choices': digest(choice)},
        'limits': LIMITS,
    }


def demo_inputs():
    return (surface.ancestry.read_json(HERE / 'zto-proof.json'),
            returns.changes.load_observation(HERE / 'zto-call.json'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='real saved ZTO code and call at the same block')
    parser.add_argument('--bundle')
    parser.add_argument('--observation')
    parser.add_argument('--signature')
    parser.add_argument('--types', help='explicit comma-separated flat return types')
    parser.add_argument('--anchor-hash', help='independently chosen trusted execution block hash')
    args = parser.parse_args(argv)
    try:
        selected = [args.bundle, args.observation, args.signature, args.types]
        surface.require((args.demo and not any(selected) and not args.anchor_hash) or
                        (not args.demo and all(selected)), 'choose --demo or all four explicit inputs')
        if args.demo:
            bundle, observation = demo_inputs()
            signature, types = 'totalSupply()', ['uint256']
        else:
            bundle = surface.ancestry.read_json(args.bundle)
            observation = returns.changes.load_observation(args.observation)
            signature, types = args.signature, args.types.split(',')
        report = evaluate(bundle, observation, signature, types, args.anchor_hash)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report['verdict'] == 'aligned' else 2
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'invalid', 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
