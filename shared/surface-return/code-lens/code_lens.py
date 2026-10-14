#!/usr/bin/env python3
"""Read-only Ethereum runtime identity and bounded standard-proxy resolution."""

import argparse
import json
from pathlib import Path
import re
import sys
import urllib.request
from keccak import keccak256

PUBLIC_RPC = 'https://ethereum-rpc.publicnode.com'
ZTO = '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'
IMD = '0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7'
SCHEMA = 'code-lens-v1'  # Historical reports remain readable.
CURRENT_SCHEMA = 'code-lens-v2'
PUBLIC_SOURCES = {PUBLIC_RPC, 'https://eth.drpc.org'}
MAX_CODE = 24576
MAX_DEPTH = 4
MAX_RESPONSE = 100000
CLONE_PREFIX = '363d3d373d3d3d363d73'
CLONE_SUFFIX = '5af43d82803e903d91602b57fd5bf3'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fixed_hex(value, size):
    require(isinstance(value, str) and re.fullmatch(r'0x[0-9a-fA-F]{' + str(size * 2) + '}', value),
            'invalid fixed-width hex')
    return value.lower()


def address(value):
    value = fixed_hex(value, 20)
    require(int(value, 16) != 0, 'zero address is not a code target')
    return value


def quantity(value):
    require(isinstance(value, str) and re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)', value),
            'invalid RPC quantity')
    return int(value, 16)


def code_bytes(value):
    require(isinstance(value, str) and len(value) <= 2 + MAX_CODE * 2
            and re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', value), 'invalid or oversized runtime code')
    return bytes.fromhex(value[2:])


def digest(value):
    return '0x' + keccak256(value).hex()


def slot(label):
    return '0x' + (int.from_bytes(keccak256(label.encode('ascii')), 'big') - 1).to_bytes(32, 'big').hex()


SLOTS = {name: slot('eip1967.proxy.' + name) for name in ('implementation', 'beacon')}


def slot_address(value):
    value = fixed_hex(value, 32)
    require(value[2:26] == '0' * 24, 'proxy address word has nonzero padding')
    return None if int(value, 16) == 0 else address('0x' + value[-40:])


def clone_target(code):
    data = code_bytes(code).hex()
    if len(data) == 90 and data.startswith(CLONE_PREFIX) and data.endswith(CLONE_SUFFIX):
        return address('0x' + data[20:60])
    return None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('RPC redirects are refused')


class RPC:
    METHODS = {'eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_getStorageAt', 'eth_call'}

    def __init__(self, endpoint):
        require(endpoint in {PUBLIC_RPC, 'https://eth.drpc.org'} or
                re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{0,4}/rpc/1', endpoint),
                'use a documented public endpoint or the supplied loopback Ethereum relay')
        self.endpoint, self.counter = endpoint, 0
        # Explicitly no environment-derived proxy settings, credentials or redirects.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, method, params):
        require(method in self.METHODS, 'RPC method is not read-only allowlisted')
        if method == 'eth_call':
            require(params[0] == {'to': address(params[0]['to']), 'data': '0x5c60da1b'},
                    'only beacon implementation() may be called')
        self.counter += 1
        request = urllib.request.Request(self.endpoint, data=json.dumps({
            'jsonrpc': '2.0', 'id': self.counter, 'method': method, 'params': params,
        }).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'Pepeolithic-CodeLens/1.0'})
        with self.opener.open(request, timeout=25) as response:
            raw = response.read(MAX_RESPONSE + 1)
        require(len(raw) <= MAX_RESPONSE, 'RPC response exceeds bounded size')
        value = json.loads(raw)
        require(isinstance(value, dict) and value.get('jsonrpc') == '2.0'
                and type(value.get('id')) is int and value['id'] == self.counter,
                'RPC response envelope mismatch')
        require('error' not in value, 'RPC error: ' + json.dumps(value.get('error')))
        require('result' in value, 'RPC response has no result')
        return value['result']


def inspect_node(rpc, target, pinned):
    code = rpc.call('eth_getCode', [target, pinned])
    raw = code_bytes(code)
    require(raw, 'target has no runtime code: ' + target)
    storage = {name: fixed_hex(rpc.call('eth_getStorageAt', [target, key, pinned]), 32)
               for name, key in SLOTS.items()}
    node = {'address': target, 'code': '0x' + raw.hex(), 'code_hash': digest(raw),
            'code_bytes': len(raw), 'storage': storage}
    beacon = slot_address(storage['beacon'])
    if beacon:
        beacon_code = code_bytes(rpc.call('eth_getCode', [beacon, pinned]))
        require(beacon_code, 'beacon has no code')
        node['beacon'] = {'address': beacon, 'code': '0x' + beacon_code.hex(),
                          'code_hash': digest(beacon_code),
                          'implementation_result': fixed_hex(rpc.call('eth_call', [
                              {'to': beacon, 'data': '0x5c60da1b'}, pinned]), 32)}
    kind, next_target = resolve_node(node)
    node['kind'], node['next_address'] = kind, next_target
    return node


def resolve_node(node):
    implementation = slot_address(node['storage']['implementation'])
    beacon = slot_address(node['storage']['beacon'])
    clone = clone_target(node['code'])
    require(sum(bool(x) for x in (implementation, beacon, clone)) <= 1,
            'ambiguous proxy signals; refusing to select an implementation')
    if clone:
        return 'eip1167-exact', clone
    if implementation:
        return 'eip1967-implementation-candidate', implementation
    if beacon:
        evidence = node['beacon']
        require(address(evidence['address']) == beacon, 'beacon evidence address mismatch')
        raw = code_bytes(evidence['code'])
        require(raw and digest(raw) == fixed_hex(evidence['code_hash'], 32), 'invalid beacon code hash')
        target = slot_address(evidence['implementation_result'])
        require(target is not None, 'beacon returned zero implementation')
        return 'eip1967-beacon-candidate', target
    require('beacon' not in node, 'unexpected beacon evidence')
    return 'no-supported-proxy-signal', None


def provenance(report):
    """Describe source labels without claiming to authenticate an RPC provider."""
    if report['schema'] == SCHEMA:
        require(report['source'] == PUBLIC_RPC, 'unexpected legacy public source attribution')
        return {'transport_source': 'unknown-legacy', 'source': PUBLIC_RPC,
                'source_kind': 'legacy-attribution-only'}
    require(report['schema'] == CURRENT_SCHEMA, 'wrong report schema')
    source = report['source']
    transport = report['transport_source']
    kind = report['source_kind']
    require(source in PUBLIC_SOURCES, 'unexpected public source attribution')
    if transport == 'worker-provided-relay':
        require(kind == 'attribution-only', 'relay upstream cannot be verified')
    else:
        require(transport in PUBLIC_SOURCES and source == transport
                and kind == 'selected-public-endpoint', 'source and transport mismatch')
    return {'transport_source': transport, 'source': source, 'source_kind': kind}


def collection_provenance(rpc):
    endpoint = rpc.endpoint
    if endpoint in PUBLIC_SOURCES:
        return {'source': endpoint, 'transport_source': endpoint,
                'source_kind': 'selected-public-endpoint'}
    require(isinstance(endpoint, str) and re.fullmatch(
        r'http://127\.0\.0\.1:[1-9][0-9]{0,4}/rpc/1', endpoint), 'unknown RPC transport')
    return {'source': PUBLIC_RPC, 'transport_source': 'worker-provided-relay',
            'source_kind': 'attribution-only'}


def collect(rpc, target, expected=None):
    require(quantity(rpc.call('eth_chainId', [])) == 1, 'endpoint is not Ethereum mainnet')
    block = rpc.call('eth_getBlockByNumber', ['finalized', False])
    require(isinstance(block, dict), 'finalized block unavailable')
    block = {'number': hex(quantity(block['number'])), 'hash': fixed_hex(block['hash'], 32)}
    pinned = {'blockHash': block['hash'], 'requireCanonical': True}
    nodes, seen = [], set()
    current = address(target)
    for _ in range(MAX_DEPTH + 1):
        require(current not in seen, 'proxy cycle detected')
        seen.add(current)
        node = inspect_node(rpc, current, pinned)
        nodes.append(node)
        current = node['next_address']
        if current is None:
            break
    require(current is None, 'proxy depth exceeds four edges')
    after = rpc.call('eth_getBlockByNumber', [block['number'], False])
    require(isinstance(after, dict) and fixed_hex(after['hash'], 32) == block['hash'],
            'block changed during collection')
    report = {'schema': CURRENT_SCHEMA, 'chain_id': 1, **collection_provenance(rpc), 'block': block,
              'target': address(target), 'nodes': nodes,
              'effective_address': nodes[-1]['address'], 'effective_code_hash': nodes[-1]['code_hash'],
              'expected_effective_hash': fixed_hex(expected, 32) if expected else None}
    verify(report)
    return report


def verify(report):
    """Check report consistency, not RPC honesty or consensus inclusion."""
    require(report['schema'] in (SCHEMA, CURRENT_SCHEMA) and type(report['chain_id']) is int and report['chain_id'] == 1,
            'wrong report schema or chain')
    quantity(report['block']['number'])
    fixed_hex(report['block']['hash'], 32)
    provenance(report)
    nodes = report['nodes']
    require(isinstance(nodes, list) and 1 <= len(nodes) <= MAX_DEPTH + 1, 'invalid node count')
    current, seen = address(report['target']), set()
    for node in nodes:
        require(current is not None and address(node['address']) == current and current not in seen,
                'broken or cyclic code path')
        seen.add(current)
        raw = code_bytes(node['code'])
        require(raw and type(node['code_bytes']) is int and len(raw) == node['code_bytes'], 'code length mismatch')
        require(digest(raw) == fixed_hex(node['code_hash'], 32), 'runtime hash mismatch')
        require(set(node['storage']) == set(SLOTS), 'missing or extra proxy slots')
        kind, next_target = resolve_node(node)
        require(node['kind'] == kind and node['next_address'] == next_target, 'proxy interpretation mismatch')
        current = next_target
    require(current is None, 'report omits a proxy implementation')
    require(report['effective_address'] == nodes[-1]['address']
            and report['effective_code_hash'] == nodes[-1]['code_hash'], 'effective code mismatch')
    expected = report['expected_effective_hash']
    if expected is not None:
        require(fixed_hex(expected, 32) == report['effective_code_hash'], 'reviewed effective code hash does not match')
    return True


def read_report(filename):
    path = Path(filename).resolve()
    require(path.is_relative_to(Path.cwd().resolve()), 'report must be inside the current workspace')
    with path.open('rb') as stream:
        raw = stream.read(MAX_RESPONSE + 1)
    require(len(raw) <= MAX_RESPONSE, 'report exceeds 100000 bytes')
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rpc', default=PUBLIC_RPC)
    parser.add_argument('--token', choices=['ZTO', 'IMD'], default='ZTO')
    parser.add_argument('--address', help='explicit Ethereum contract address instead of token')
    parser.add_argument('--expect-effective-hash', help='reviewed Ethereum Keccak-256 hash; mismatch exits 1')
    parser.add_argument('--verify', metavar='REPORT', help='offline consistency check of a workspace report')
    args = parser.parse_args()
    try:
        if args.verify:
            require(not args.address and args.token == 'ZTO', '--verify cannot be combined with a target')
            report = read_report(args.verify)
            if args.expect_effective_hash:
                report['expected_effective_hash'] = fixed_hex(args.expect_effective_hash, 32)
            verify(report)
            print(json.dumps({'verified': True, 'effective_address': report['effective_address'],
                              'effective_code_hash': report['effective_code_hash'],
                              'provenance': provenance(report),
                              'scope': 'offline consistency only; not chain authenticity'}, indent=2))
        else:
            expected = fixed_hex(args.expect_effective_hash, 32) if args.expect_effective_hash else None
            target = address(args.address) if args.address else {'ZTO': ZTO, 'IMD': IMD}[args.token]
            print(json.dumps(collect(RPC(args.rpc), target, expected), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Code Lens: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
