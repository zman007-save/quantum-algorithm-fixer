#!/usr/bin/env python3
"""Node 2: Qiskit transpiler — optimize the submitted circuit.

Reads record.algorithm (OpenQASM), transpiles at optimization_level=3,
stores the optimized QASM as record.completed_algorithm, and appends a proof
with before/after depth and gate counts.
"""
from common import add_proof, arg_parser, circuit_stats, dump_qasm, load_record, parse_qasm, save_record


def main():
    args = arg_parser("Qiskit transpiler node").parse_args()
    rec = load_record(args.inp)
    from qiskit import transpile

    orig = parse_qasm(rec["algorithm"])
    before = circuit_stats(orig)
    opt = transpile(orig, optimization_level=3)
    after = circuit_stats(opt)
    rec["completed_algorithm"] = dump_qasm(opt)
    add_proof(
        rec,
        "qiskit-transpiler",
        "optimization",
        "pass",
        f"depth {before['depth']} -> {after['depth']}; "
        f"gates {before['gate_count']} -> {after['gate_count']}; "
        f"ops {before['ops']} -> {after['ops']}",
    )
    save_record(args.out, rec)
    print(f"transpile: depth {before['depth']}->{after['depth']}, "
          f"gates {before['gate_count']}->{after['gate_count']}")


if __name__ == "__main__":
    main()
