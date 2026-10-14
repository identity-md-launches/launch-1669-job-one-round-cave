#!/usr/bin/env python3
"""Try a bounded, read-only call at the saved ZTO code proof block."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd().resolve()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--one':
        sys.path.insert(0, str(ROOT / 'shared/surface-return'))
        import surface_return as tool
        bundle, saved = tool.demo_inputs()
        endpoint = sys.argv[2]
        obs = tool.returns.changes.capture(tool.returns.core.RPC(endpoint), saved['call'],
                                          'uint256', bundle['observation']['block']['number'])
        result = tool.evaluate(bundle, obs, 'totalSupply()', ['uint256'])
        tool.returns.changes.save_observation(ROOT / 'gathering/zto-surface-call.json', obs)
        (ROOT / 'gathering/zto-surface-context.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({'verdict': result['verdict'], 'block': obs['block']}))
        return 0 if result['verdict'] == 'aligned' else 2
    attempts = []
    for endpoint in ('https://ethereum-rpc.publicnode.com', 'https://eth.drpc.org'):
        try:
            r = subprocess.run([sys.executable, '-B', __file__, '--one', endpoint],
                               capture_output=True, text=True, timeout=45)
            attempts.append({'endpoint': endpoint, 'exit': r.returncode,
                             'stdout': r.stdout, 'stderr': r.stderr[-3000:]})
            if r.returncode == 0:
                break
        except subprocess.TimeoutExpired:
            attempts.append({'endpoint': endpoint, 'error': '45-second process deadline exceeded'})
    (ROOT / 'gathering/surface-live-attempts.json').write_text(json.dumps({
        'read_only': True, 'attempts': attempts, 'aligned': any(a.get('exit') == 0 for a in attempts)}, indent=2)+'\n')
    print(json.dumps(attempts))
    return 0

if __name__ == '__main__':
    sys.exit(main())
