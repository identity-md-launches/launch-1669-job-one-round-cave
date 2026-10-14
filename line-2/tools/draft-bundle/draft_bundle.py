#!/usr/bin/env python3
"""Check a whole unsigned revoke handoff against reviewed ERC-20 evidence.

Offline, standard library only. No network, signing, sending or wallet access.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'approval-draft'))
import approval_draft as drafts

SCHEMA = 'permission-draft-bundle-v1'
ANCHORS = ('schema', 'chain_id', 'token_address', 'block_number', 'block_hash')


def canonical(value):
    """JSON comparison preserves types (unlike Python's True == 1)."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def expected_bundle(observation, policy):
    reviewed = drafts.build(observation, policy)
    bundle = {key: reviewed[key] for key in ANCHORS if key != 'schema'}
    bundle['schema'] = SCHEMA
    bundle['drafts'] = reviewed['drafts']
    return bundle, reviewed


def check(bundle, observation, policy):
    expected, reviewed = expected_bundle(observation, policy)
    drafts.gate.exact_keys(bundle, (*ANCHORS, 'drafts'), 'bundle')
    drafts.gate.lens.require(type(bundle['drafts']) is list and len(bundle['drafts']) <= 64,
                             'drafts must be a list of at most 64 candidates')
    wanted = Counter(canonical(row) for row in expected['drafts'])
    received = Counter(canonical(row) for row in bundle['drafts'])
    missing = wanted - received
    unexpected = received - wanted
    duplicates = sum(count - 1 for count in received.values() if count > 1)
    anchors_match = all(canonical(bundle[key]) == canonical(expected[key]) for key in ANCHORS)
    sufficient = reviewed['permission_gate_decision'] != 'insufficient_evidence'
    matched = sufficient and anchors_match and not missing and not unexpected
    status = ('insufficient_evidence' if not sufficient else
              'wrong_evidence_anchor' if not anchors_match else
              'bundle_mismatch' if not matched else
              'complete_reviewed_bundle' if wanted else 'no_reviewed_candidates')
    return {
        'schema': 'permission-draft-bundle-report-v1',
        'status': status, 'matches_reviewed_bundle': matched,
        'permission_gate_decision': reviewed['permission_gate_decision'],
        'chain_id': expected['chain_id'], 'token_address': expected['token_address'],
        'block_number': expected['block_number'], 'block_hash': expected['block_hash'],
        'anchors_match': anchors_match, 'expected_count': sum(wanted.values()),
        'received_count': sum(received.values()), 'missing_count': sum(missing.values()),
        'unexpected_count': sum(unexpected.values()), 'duplicate_count': duplicates,
        'missing_pairs': [{'owner': json.loads(key)['owner'],
                           'spender': json.loads(key)['spender'], 'count': count}
                          for key, count in sorted(missing.items())],
        'complete_wallet_audit': False,
        'limitations': [
            'Completeness means only the optional candidates derived from supplied evidence and policy.',
            'A matching empty bundle means no reviewed candidates, never a complete wallet audit.',
            'Historical RPC evidence is trusted; unknown spenders, Permit2 and signatures are omitted.',
            'No age, canonicality or future-state guarantee; refresh evidence before owner review.',
            'No owner authorization, signature, simulation, transaction submission or execution is provided.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='workspace reviewed raw observation/inventory')
    parser.add_argument('--policy', help='workspace explicit Permission Gate policy')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--bundle', help='workspace bundle JSON to check')
    action.add_argument('--emit', action='store_true', help='print the expected unsigned bundle only')
    args = parser.parse_args(argv)
    try:
        drafts.gate.lens.require((args.observation is None) == (args.policy is None),
                                 'provide observation and policy together')
        drafts.gate.lens.require(not args.bundle or args.observation is not None,
                                 'external bundle requires explicit observation and policy')
        observation = drafts.gate.load(args.observation or drafts.DEFAULT_OBSERVATION)
        policy = drafts.gate.load(args.policy or drafts.DEFAULT_POLICY)
        expected, reviewed = expected_bundle(observation, policy)
        if args.emit:
            drafts.gate.lens.require(reviewed['permission_gate_decision'] != 'insufficient_evidence',
                                     'cannot emit a bundle from insufficient evidence')
            print(json.dumps(expected, indent=2))
            return 0
        result = check(drafts.gate.load(args.bundle) if args.bundle else expected, observation, policy)
        result['demonstration'] = args.observation is None
        print(json.dumps(result, indent=2))
        return 0 if result['matches_reviewed_bundle'] else (4 if result['status'] == 'insufficient_evidence' else 3)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
