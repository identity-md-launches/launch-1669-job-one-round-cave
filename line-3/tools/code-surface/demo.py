#!/usr/bin/env python3
"""Replay real ZTO then IMD evidence without granting an invented trust anchor."""
import json
from pathlib import Path
import code_surface as surface

FOLDER = Path(__file__).resolve().parent


def main():
    results = []
    for token in ('zto', 'imd'):
        bundle = surface.ancestry.read_json(FOLDER.parent / 'code-delta' / (token + '-later-proof.json'))
        request = surface.ancestry.read_json(FOLDER / (token + '-request.json'))
        result = surface.inspect(bundle, request)
        results.append({'token': token.upper(), 'target': result['target'],
                        'code_block': result['code_block'], 'anchor': result['proof']['anchor'],
                        'requested_signatures': len(result['functions']),
                        'requested_patterns_found': sum(item['match_count'] > 0 for item in result['functions']),
                        'runtime_candidate_count': sum(item['candidate_count'] for item in result['runtimes']),
                        'reachability_verified': result['reachability_verified']})
    return {'demonstration_passed': all(r['requested_patterns_found'] == 9
                                       and r['anchor'] == 'unanchored-rpc-header'
                                       and not r['reachability_verified'] for r in results),
            'results': results,
            'scope': 'Historical real proof replay and selector inventory, not an ABI or code approval.'}


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
