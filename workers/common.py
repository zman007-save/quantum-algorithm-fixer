#!/usr/bin/env python3
"""Shared helpers for the quantum-algorithm-fixer workers.

Every worker reads a proof-record JSON, does one pipeline step, appends one
proof entry, and writes the record back out. Records follow schema.json.
"""
import argparse
import json


def load_record(path):
    with open(path) as f:
        return json.load(f)


def save_record(path, record):
    with open(path, "w") as f:
        json.dump(record, f, indent=2)


def new_record(algorithm_id, qasm):
    return {
        "algorithm_id": algorithm_id,
        "algorithm": qasm,
        "score": {"overall": 0.0, "depth": 0, "gate_count": 0, "fidelity": None},
        "completed_algorithm": None,
        "proofs": [],
    }


def add_proof(record, node, check, result, detail, certificate=None):
    entry = {"node": node, "check": check, "result": result, "detail": detail}
    if certificate is not None:
        entry["certificate"] = certificate
    record.setdefault("proofs", []).append(entry)
    return entry


def parse_qasm(qasm_str):
    """Parse OpenQASM 2 or 3 text into a QuantumCircuit."""
    from qiskit import qasm2, qasm3

    s = qasm_str.strip()
    if s.startswith("OPENQASM 3"):
        return qasm3.loads(s)
    try:
        return qasm3.loads(s)
    except Exception:
        return qasm2.loads(s)


def dump_qasm(circuit):
    from qiskit import qasm3

    return qasm3.dumps(circuit)


def circuit_stats(circuit):
    return {
        "depth": circuit.depth(),
        "gate_count": circuit.size(),
        "ops": dict(circuit.count_ops()),
    }


def arg_parser(desc):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--in", dest="inp", required=True, help="input record JSON")
    p.add_argument("--out", dest="out", required=True, help="output record JSON")
    return p


def main_argv():
    return None
