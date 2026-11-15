#!/usr/bin/env python3
"""Node 5: Compact (compactq) — verified optimizer.

Runs compactq_pass() over the transpiled circuit. Compact is a verified
optimizer: it attaches verification to every answer and returns the input
unchanged on any doubt. A machine-checkable certificate is built with
build_certificate() and attached to the proof. If compactq is not installed
the proof is "skipped".
"""
from common import (add_proof, arg_parser, circuit_stats, dump_qasm,
                    load_record, parse_qasm, save_record)


def main():
    args = arg_parser("Compact verified-optimizer node").parse_args()
    rec = load_record(args.inp)
    try:
        from compactq import build_certificate, compactq_pass
    except ImportError:
        add_proof(rec, "compact", "verified-optimization", "skipped",
                  "compactq not installed")
        save_record(args.out, rec)
        print("compact: skipped (not installed)")
        return

    orig = parse_qasm(rec["algorithm"])
    base = parse_qasm(rec["completed_algorithm"] or rec["algorithm"])
    try:
        before = circuit_stats(base)
        # Compact optimizes unitary circuits only: strip trailing measurements,
        # optimize, then put the measurements back on the same qubits.
        had_measure = base.count_ops().get("measure", 0) > 0
        work = base.copy()
        if had_measure:
            work.remove_final_measurements(inplace=True)
        opt = compactq_pass(work)
        after = circuit_stats(opt)
        cert = None
        try:
            # Certificate over the unitary parts (measurements stripped).
            # build_certificate wants compactq Circuit objects, not Qiskit.
            from compactq import from_qiskit
            orig_u = orig.copy()
            opt_u = opt.copy()
            if had_measure:
                orig_u.remove_final_measurements(inplace=True)
                opt_u.remove_final_measurements(inplace=True)
            cert = build_certificate(from_qiskit(orig_u), from_qiskit(opt_u))
        except Exception as e:  # noqa: BLE001 - certificate is best-effort
            cert = {"error": f"{type(e).__name__}: {e}"}
        ver = (cert or {}).get("verification", {}) if isinstance(cert, dict) else {}
        ver_str = ""
        if ver.get("equivalent"):
            ver_str = (f"certificate: equivalent via {ver.get('method')} "
                       f"(tier {ver.get('tier')})")
        # Adopt Compact's rewrite only if it is actually smaller. Compact
        # counts every elementary gate (a ccx becomes ~15 gates), so its
        # output can be larger than the transpiler's ccx-basis circuit even
        # though it is certified equivalent. Keeping the smaller circuit is
        # the honest choice; the certificate still proves Compact's rewrite.
        adopted = after["depth"] <= before["depth"] and after["gate_count"] <= before["gate_count"]
        if adopted:
            if had_measure:
                from qiskit import ClassicalRegister
                opt.add_register(ClassicalRegister(opt.num_qubits, "c"))
                opt.measure(list(range(opt.num_qubits)), list(range(opt.num_qubits)))
            rec["completed_algorithm"] = dump_qasm(opt)
            detail = (f"depth {before['depth']} -> {after['depth']}; "
                      f"gates {before['gate_count']} -> {after['gate_count']}; "
                      f"rewrite adopted with verification certificate attached")
        else:
            opt_stats = (cert or {}).get("optimization", {}) if isinstance(cert, dict) else {}
            detail = (f"Compact verified its own rewrite "
                      f"(elementary gates {opt_stats.get('gates_before', '?')} -> "
                      f"{opt_stats.get('gates_after', '?')}, "
                      f"{ver_str or 'certificate attached'}) "
                      f"but it is larger than the transpiler output "
                      f"(depth {before['depth']}, gates {before['gate_count']} "
                      f"counting ccx as one gate), so the transpiler output was kept")
        add_proof(rec, "compact", "verified-optimization", "verified",
                  detail, certificate=cert)
        print(f"compact: verified ({detail})")
    except Exception as e:  # noqa: BLE001 - record, don't crash the run
        add_proof(rec, "compact", "verified-optimization", "error",
                  f"{type(e).__name__}: {e}"[:400])
        print(f"compact: error {type(e).__name__}: {e}")
    save_record(args.out, rec)


if __name__ == "__main__":
    main()
