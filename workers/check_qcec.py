#!/usr/bin/env python3
"""Node 3: MQT QCEC — prove the optimized circuit is equivalent to the original.

Uses mqt.qcec.verify() (decision-diagram + ZX-calculus engines). Appends a
proof with result "equivalent" / "not-equivalent" / "unknown", plus which
checker engines decided it. If mqt.qcec is not installed the proof is
recorded as "skipped" and the pipeline continues.
"""
from common import add_proof, arg_parser, load_record, parse_qasm, save_record


def main():
    args = arg_parser("MQT QCEC equivalence node").parse_args()
    rec = load_record(args.inp)
    try:
        from mqt import qcec
    except ImportError:
        add_proof(rec, "mqt-qcec", "equivalence", "skipped",
                  "mqt.qcec not installed in this environment")
        save_record(args.out, rec)
        print("qcec: skipped (not installed)")
        return

    orig = parse_qasm(rec["algorithm"])
    completed = parse_qasm(rec["completed_algorithm"] or rec["algorithm"])
    try:
        res = qcec.verify(orig, completed)
        verdict = str(res.equivalence)
        if "not_equivalent" in verdict:
            result = "not-equivalent"
        elif "equivalent" in verdict:
            # includes "equivalent" and "equivalent_up_to_global_phase"
            # (global phase is physically indistinguishable)
            result = "equivalent"
        else:
            result = "unknown"
        # str(res) is JSON with a per-checker breakdown; summarize it.
        detail = f"QCEC verdict: {verdict}"
        try:
            import json as _json
            info = _json.loads(str(res))
            checkers = info.get("checkers", [])
            detail += "; " + ", ".join(
                f"{c.get('checker')}:{c.get('equivalence')}" for c in checkers
            )
        except Exception:
            pass
        add_proof(rec, "mqt-qcec", "equivalence", result, detail)
        print(f"qcec: {result} ({verdict})")
    except Exception as e:  # noqa: BLE001 - record the failure, don't crash the run
        add_proof(rec, "mqt-qcec", "equivalence", "error",
                  f"{type(e).__name__}: {e}"[:400])
        print(f"qcec: error {type(e).__name__}: {e}")
    save_record(args.out, rec)


if __name__ == "__main__":
    main()
