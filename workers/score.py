#!/usr/bin/env python3
"""Node 7: Scoring — overall score 0-1 plus the raw numbers.

overall = 0.30 * simulation fidelity
        + 0.25 * equivalence (QCEC: 1.0 equivalent, 0.5 skipped/unknown, 0.0 not-equivalent)
        + 0.20 * depth reduction (clamped >= 0)
        + 0.10 * gate-count reduction (clamped >= 0)
        + 0.15 * fraction of proofs that passed

score.depth / score.gate_count describe the COMPLETED circuit.
"""
from common import arg_parser, circuit_stats, load_record, parse_qasm, save_record


def main():
    args = arg_parser("Scoring node").parse_args()
    rec = load_record(args.inp)
    orig = parse_qasm(rec["algorithm"])
    comp = parse_qasm(rec["completed_algorithm"] or rec["algorithm"])
    s0, s1 = circuit_stats(orig), circuit_stats(comp)
    fidelity = (rec.get("simulation") or {}).get("fidelity")
    if fidelity is None:
        fidelity = rec.get("score", {}).get("fidelity") or 0.0
    proofs = rec.get("proofs", [])
    passing = {"pass", "equivalent", "verified"}
    pass_frac = (sum(1 for p in proofs if p.get("result") in passing)
                 / max(1, len(proofs)))
    qcec = next((p for p in proofs if p.get("node") == "mqt-qcec"), None)
    if qcec is None:
        equiv = 0.0
    elif qcec["result"] == "equivalent":
        equiv = 1.0
    elif qcec["result"] in ("skipped", "unknown", "out-of-scope"):
        equiv = 0.5
    else:
        equiv = 0.0
    depth_red = max(0.0, (s0["depth"] - s1["depth"]) / s0["depth"]) if s0["depth"] else 0.0
    gate_red = max(0.0, (s0["gate_count"] - s1["gate_count"]) / s0["gate_count"]) if s0["gate_count"] else 0.0
    overall = (0.30 * fidelity + 0.25 * equiv + 0.20 * depth_red
               + 0.10 * gate_red + 0.15 * pass_frac)
    rec["score"] = {
        "overall": round(min(1.0, max(0.0, overall)), 3),
        "depth": s1["depth"],
        "gate_count": s1["gate_count"],
        "fidelity": round(fidelity, 6),
    }
    rec["score_breakdown"] = {
        "fidelity": round(fidelity, 6),
        "equivalence": equiv,
        "depth_reduction": round(depth_red, 3),
        "gate_reduction": round(gate_red, 3),
        "proofs_pass_fraction": round(pass_frac, 3),
        "original_depth": s0["depth"],
        "original_gate_count": s0["gate_count"],
    }
    save_record(args.out, rec)
    print(f"score: overall {rec['score']['overall']} "
          f"(fidelity {fidelity}, equiv {equiv}, depth_red {depth_red:.2f}, "
          f"gate_red {gate_red:.2f}, pass_frac {pass_frac:.2f})")


if __name__ == "__main__":
    main()
