#!/usr/bin/env python3
"""Inspect verified Ethereum runtime bytes for delegation-related opcodes."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code-lens'))
import code_lens as lens


INTERESTING = {
    0x3b: 'EXTCODESIZE', 0x3c: 'EXTCODECOPY', 0x3f: 'EXTCODEHASH',
    0xf0: 'CREATE', 0xf2: 'CALLCODE', 0xf4: 'DELEGATECALL',
    0xf5: 'CREATE2', 0xff: 'SELFDESTRUCT',
}
DELEGATION = {'CALLCODE', 'DELEGATECALL'}


def cbor_length(data, offset):
    """Read a definite CBOR length, with no indefinite or tagged forms."""
    if offset >= len(data):
        raise ValueError('truncated CBOR head')
    head = data[offset]
    major, additional = head >> 5, head & 31
    if additional < 24:
        return major, additional, offset + 1
    sizes = {24: 1, 25: 2, 26: 4, 27: 8}
    if additional not in sizes:
        raise ValueError('unsupported CBOR length')
    width = sizes[additional]
    end = offset + 1 + width
    if end > len(data):
        raise ValueError('truncated CBOR length')
    return major, int.from_bytes(data[offset + 1:end], 'big'), end


def solidity_metadata(code):
    """Return start and version only for a fully parsed Solidity CBOR map."""
    if len(code) < 4:
        return None
    size = int.from_bytes(code[-2:], 'big')
    start = len(code) - size - 2
    if size < 5 or start < 0:
        return None
    data = code[start:-2]
    try:
        major, pairs, offset = cbor_length(data, 0)
        if major != 5 or not 1 <= pairs <= 8:
            return None
        entries = {}
        for _ in range(pairs):
            major, length, offset = cbor_length(data, offset)
            if major != 3 or not 1 <= length <= 32 or offset + length > len(data):
                return None
            key = data[offset:offset + length].decode('ascii')
            offset += length
            major, length, offset = cbor_length(data, offset)
            if major != 2 or length > 256 or offset + length > len(data) or key in entries:
                return None
            entries[key] = data[offset:offset + length]
            offset += length
        version = entries.get('solc')
        if offset != len(data) or version is None or len(version) != 3:
            return None
        return {'start': start, 'bytes': size + 2,
                'solc_version': '.'.join(str(x) for x in version)}
    except (ValueError, UnicodeDecodeError):
        return None


def scan(code):
    """Linear, PUSH-aware scan; offsets are from the first runtime byte."""
    metadata = solidity_metadata(code)
    end = metadata['start'] if metadata else len(code)
    findings = []
    offset = 0
    while offset < end:
        opcode = code[offset]
        if opcode in INTERESTING:
            findings.append({'offset': offset, 'opcode': INTERESTING[opcode]})
        offset += 1 + (opcode - 0x5f if 0x60 <= opcode <= 0x7f else 0)
    return metadata, findings


def inspect(report):
    lens.verify(report)
    nodes = []
    for node in report['nodes']:
        raw = lens.code_bytes(node['code'])
        metadata, findings = scan(raw)
        delegate = [item for item in findings if item['opcode'] in DELEGATION]
        nodes.append({
            'address': node['address'], 'code_hash': node['code_hash'],
            'candidate_kind': node['kind'], 'runtime_bytes': len(raw),
            'recognized_solidity_metadata': metadata,
            'findings': findings, 'delegation_opcode_offsets': [x['offset'] for x in delegate],
            'unresolved_delegation_signal': bool(delegate) and node['kind'] == 'no-supported-proxy-signal',
        })
    return {
        'schema': 'code-opcodes-v1', 'chain_id': 1, 'target': report['target'],
        'block': report['block'], 'nodes': nodes,
        'scope': 'Verified report consistency and PUSH-aware linear opcode inventory only; '
                 'presence does not prove reachability, and absence does not prove safety.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, help='workspace-local Code Lens observation')
    args = parser.parse_args()
    try:
        result = inspect(lens.read_report(args.report))
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Code Opcodes: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
