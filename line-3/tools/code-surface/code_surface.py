#!/usr/bin/env python3
"""Offline, proof-backed candidate function-selector inventory; not a call gate."""
import argparse
import json
from pathlib import Path
import re
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-ancestry'))
import code_ancestry as ancestry
sys.path.insert(0, str(TOOLS / 'code-opcodes'))
import code_opcodes as opcodes

proof, lens = ancestry.proof, ancestry.lens
require = lens.require
MAX_SIGNATURES = 64
MAX_PREVIEW = 64
MAX_HITS = 16


def signature_selector(signature):
    """Validate an explicit canonical ABI signature before Ethereum Keccak hashing.

    No aliases, parameter names, return types, source-level structs or whitespace.
    Tuple and array types are parsed rather than hashed as unchecked prose.
    """
    require(isinstance(signature, str) and 3 <= len(signature) <= 512
            and signature.isascii(), 'signature must be 3 to 512 ASCII characters')
    name = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*\(', signature)
    require(name is not None, 'invalid function name or opening parenthesis')
    pos = name.end()

    def group(depth):
        nonlocal pos
        require(depth <= 16, 'tuple nesting exceeds 16')
        if pos < len(signature) and signature[pos] == ')':
            pos += 1
            return
        while True:
            abi_type(depth)
            require(pos < len(signature), 'unterminated type list')
            char = signature[pos]
            pos += 1
            if char == ')':
                return
            require(char == ',', 'expected comma or closing parenthesis')

    def abi_type(depth):
        nonlocal pos
        require(pos < len(signature), 'missing type')
        if signature[pos] == '(':
            pos += 1
            group(depth + 1)
        else:
            match = re.match(r'[a-zA-Z0-9]+', signature[pos:])
            require(match is not None, 'missing ABI type')
            atom = match.group()
            pos += len(atom)
            integer = re.fullmatch(r'u?int([1-9][0-9]*)', atom)
            byte = re.fullmatch(r'bytes([1-9][0-9]*)', atom)
            fixed = re.fullmatch(r'u?fixed([1-9][0-9]*)x([1-9][0-9]*)', atom)
            valid = atom in {'address', 'bool', 'bytes', 'string', 'function'}
            if integer:
                width = int(integer[1])
                valid = 8 <= width <= 256 and width % 8 == 0
            if byte:
                valid = 1 <= int(byte[1]) <= 32
            if fixed:
                width, decimals = int(fixed[1]), int(fixed[2])
                valid = 8 <= width <= 256 and width % 8 == 0 and 1 <= decimals <= 80
            require(valid, 'noncanonical or unsupported ABI type: ' + atom)
        while pos < len(signature) and signature[pos] == '[':
            end = signature.find(']', pos + 1)
            require(end >= 0, 'unterminated array type')
            size = signature[pos + 1:end]
            require(size == '' or re.fullmatch(r'0|[1-9][0-9]*', size)
                    and len(size) <= 78 and int(size) < 2**256, 'invalid array dimension')
            pos = end + 1

    group(0)
    require(pos == len(signature), 'trailing signature text')
    return lens.digest(signature.encode('ascii'))[:10]


def validate_request(request):
    ancestry.keys(request, ('schema', 'chain_id', 'target', 'signatures'), 'surface request')
    require(request['schema'] == 'code-surface-request-v1'
            and type(request['chain_id']) is int and request['chain_id'] == 1,
            'wrong surface request schema or chain')
    signatures = request['signatures']
    require(isinstance(signatures, list) and 1 <= len(signatures) <= MAX_SIGNATURES,
            'request must contain 1 to 64 signatures')
    normalized = []
    seen = set()
    for signature in signatures:
        selector = signature_selector(signature)
        require(signature not in seen, 'duplicate signature')
        seen.add(signature)
        normalized.append({'signature': signature, 'selector': selector})
    return lens.address(request['target']), normalized


def instructions(code):
    """Decode full runtime, never treating PUSH operand bytes as opcodes."""
    require(isinstance(code, bytes) and len(code) <= lens.MAX_CODE, 'invalid runtime bytes')
    result, pc = [], 0
    while pc < len(code):
        opcode = code[pc]
        width = opcode - 0x5f if 0x60 <= opcode <= 0x7f else 0
        operand = code[pc + 1:pc + 1 + width]
        result.append((pc, opcode, operand, len(operand) == width))
        pc += width + 1
    return result


def scan(code):
    """Recognize PUSH0..4 EQ PUSH0..32 JUMPI, with a valid JUMPDEST.

    This is deliberately a syntactic pattern: no calldata dataflow or reachability
    is claimed. Metadata is annotated, never discarded as non-executable truth.
    """
    decoded = instructions(code)
    destinations = {pc for pc, op, _, _ in decoded if op == 0x5b}
    metadata = opcodes.solidity_metadata(code)
    candidates = []
    rejected = 0
    for index in range(len(decoded) - 3):
        constant, eq, target, jump = decoded[index:index + 4]
        if not (0x5f <= constant[1] <= 0x63 and constant[3]
                and eq[1] == 0x14 and 0x5f <= target[1] <= 0x7f
                and target[3] and jump[1] == 0x57):
            continue
        destination = int.from_bytes(target[2], 'big')
        if destination not in destinations:
            rejected += 1
            continue
        candidates.append({
            'selector': '0x' + int.from_bytes(constant[2], 'big').to_bytes(4, 'big').hex(),
            'constant_pc': constant[0], 'jumpi_pc': jump[0], 'destination_pc': destination,
            'pattern_overlaps_recognized_metadata': bool(metadata and jump[0] >= metadata['start']),
            'destination_in_recognized_metadata': bool(metadata and destination >= metadata['start']),
        })
    return metadata, candidates, rejected


def inspect(bundle, request, anchor_hash=None):
    target, requested = validate_request(request)
    checked = proof.verify(bundle, anchor_hash)
    observation = bundle['observation']
    require(target == lens.address(observation['target']), 'request and proof targets differ')
    runtimes, by_address = [], {}
    for node in observation['nodes']:
        for item, role in ((node, 'candidate-path'), (node.get('beacon'), 'beacon')):
            if item is None:
                continue
            address = lens.address(item['address'])
            if address in by_address:
                if role not in by_address[address]['roles']:
                    by_address[address]['roles'].append(role)
                continue
            runtime = {'address': address, 'code_hash': lens.fixed_hex(item['code_hash'], 32),
                       'roles': [role], 'code': lens.code_bytes(item['code'])}
            by_address[address] = runtime
            runtimes.append(runtime)
    matches = {entry['selector']: [] for entry in requested}
    inventory = []
    for runtime in runtimes:
        code = runtime['code']
        metadata, candidates, rejected = scan(code)
        for candidate in candidates:
            if candidate['selector'] in matches:
                matches[candidate['selector']].append({'address': runtime['address'], **candidate})
        inventory.append({key: runtime[key] for key in ('address', 'code_hash', 'roles')})
        inventory[-1].update({
            'runtime_bytes': len(code), 'recognized_solidity_metadata': metadata,
            'candidate_count': len(candidates), 'candidate_preview': candidates[:MAX_PREVIEW],
            'omitted_candidate_count': max(0, len(candidates) - MAX_PREVIEW),
            'invalid_jump_destination_pattern_count': rejected,
        })
    functions, collisions = [], {}
    for entry in requested:
        hits = matches[entry['selector']]
        functions.append({**entry, 'status': 'candidate-pattern-found' if hits else 'not-observed',
                          'match_count': len(hits), 'matches': hits[:MAX_HITS],
                          'omitted_match_count': max(0, len(hits) - MAX_HITS)})
        collisions.setdefault(entry['selector'], []).append(entry['signature'])
    normalized = {'schema': request['schema'], 'chain_id': 1, 'target': target,
                  'signatures': sorted(entry['signature'] for entry in requested)}
    return {
        'schema': 'code-surface-result-v1', 'chain_id': 1, 'target': target,
        'code_block': ancestry.block_identity(observation['block']),
        'request_digest': lens.digest(json.dumps(normalized, sort_keys=True,
                                               separators=(',', ':')).encode('ascii')),
        'proof': checked, 'runtimes': inventory, 'functions': functions,
        'requested_selector_collisions': [{'selector': selector, 'signatures': names}
                                         for selector, names in sorted(collisions.items()) if len(names) > 1],
        'anchor_authenticity_verified': False, 'reachability_verified': False,
        'interface_completeness_verified': False, 'semantic_safety_verified': False,
        'scope': 'Candidate equality/jump patterns in proven runtime bytes at code_block only. '
                 'Signatures come from the caller, not the bytecode. A match can be unrelated code '
                 'or a selector collision; absence can be an unsupported dispatcher or delegated route. '
                 'No call, ABI return type, argument decoding, routing, reachability, current state, '
                 'consensus, finality, safety, approval or permission to transact is verified.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, help='workspace-local raw Code Proof bundle')
    parser.add_argument('--request', required=True, help='workspace-local canonical signature request')
    parser.add_argument('--anchor-hash', help='independently trusted execution block hash')
    args = parser.parse_args()
    try:
        result = inspect(ancestry.read_json(args.bundle), ancestry.read_json(args.request), args.anchor_hash)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Surface: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
