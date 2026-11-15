#!/usr/bin/env python3
"""Node 6: Qiskit Aer simulator — run the corrected circuit locally.

Simulates BOTH the original and the completed circuit on AerSimulator
(statevector, 1024 shots, fixed seed) and compares the output distributions
with Hellinger fidelity. The completed circuit must reproduce the original's
measurement statistics — that is the empirical proof the "fix" did not
change what the algorithm computes. No QPU involved; fully local and free.
"""
import math

from common import add_proof, arg_parser, load_record, parse_qasm, save_record

SHOTS = 1024


def hellinger_fidelity(counts_a, counts_b):
    keys = set(counts_a) | set(counts_b)
    na = sum(counts_a.values())
    nb = sum(counts_b.values())
    bc = sum(math.sqrt((counts_a.get(k, 0) / na) * (counts_b.get(k, 0) / nb))
             for k in keys)
    return round(bc * bc, 6)


def run_counts(circuit):
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    sim = AerSimulator()
    t = transpile(circuit, sim)
    job = sim.run(t, shots=SHOTS, seed_simulator=42)
    return job.result().get_counts()


def top_outcome(counts):
    return max(counts, key=counts.get) if counts else None


def main():
    args = arg_parser("Qiskit Aer simulator node").parse_args()
    rec = load_record(args.inp)
    orig = parse_qasm(rec["algorithm"])
    completed = parse_qasm(rec["completed_algorithm"] or rec["algorithm"])
    try:
        c0 = run_counts(orig)
        c1 = run_counts(completed)
        fid = hellinger_fidelity(c0, c1)
        t0, t1 = top_outcome(c0), top_outcome(c1)
        rec["simulation"] = {
            "shots": SHOTS,
            "fidelity": fid,
            "top_original": t0,
            "top_completed": t1,
            "counts_original": dict(sorted(c0.items(), key=lambda kv: -kv[1])[:5]),
            "counts_completed": dict(sorted(c1.items(), key=lambda kv: -kv[1])[:5]),
        }
        rec["score"]["fidelity"] = fid
        result = "pass" if fid >= 0.99 else "fail"
        add_proof(
            rec, "qiskit-aer", "simulation", result,
            f"Hellinger fidelity {fid} over {SHOTS} shots; "
            f"top outcome {t0} vs {t1}; "
            f"distributions match" if fid >= 0.99 else
            f"Hellinger fidelity {fid} over {SHOTS} shots; "
            f"top outcome {t0} vs {t1}; DISTRIBUTIONS DIVERGE",
        )
        print(f"aer: fidelity {fid}, top {t0} vs {t1}")
    except Exception as e:  # noqa: BLE001 - record, don't crash the run
        add_proof(rec, "qiskit-aer", "simulation", "error",
                  f"{type(e).__name__}: {e}"[:400])
        print(f"aer: error {type(e).__name__}: {e}")
    save_record(args.out, rec)


if __name__ == "__main__":
    main()
