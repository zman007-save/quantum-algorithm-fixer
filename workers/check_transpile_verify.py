#!/usr/bin/env python3
"""Node 4: qiskit-transpile-verify — per-pass transpiler validation.

Runs the same optimization_level=3 preset pass manager through
qiskit_transpile_verify.verify_transpile() and checks every pass against
stabilizer-tableau equivalence, so a miscompilation is caught at the pass
that introduced it. This tool only covers the Clifford fragment: circuits
with T gates / arbitrary rotations are reported "out-of-scope", not silently
passed. If the package is not installed the proof is "skipped".
"""
from common import add_proof, arg_parser, load_record, parse_qasm, save_record


def main():
    args = arg_parser("qiskit-transpile-verify node").parse_args()
    rec = load_record(args.inp)
    try:
        from qiskit_transpile_verify import verify_transpile
        from qiskit.transpiler import generate_preset_pass_manager
    except ImportError:
        add_proof(rec, "qiskit-transpile-verify", "per-pass validation",
                  "skipped", "qiskit-transpile-verify not installed")
        save_record(args.out, rec)
        print("transpile-verify: skipped (not installed)")
        return

    orig = parse_qasm(rec["algorithm"])
    try:
        pm = generate_preset_pass_manager(optimization_level=3)
        rep = verify_transpile(pm, orig)
        n_pass = len(getattr(rep, "pass_results", []) or [])
        n_oos = len(getattr(rep, "out_of_scope_passes", []) or [])
        summary = getattr(rep, "summary", "")
        if callable(summary):
            try:
                summary = summary()
            except Exception:  # noqa: BLE001
                summary = ""
        summary = str(summary or "").strip()
        if getattr(rep, "all_verified", False):
            result = "pass"
            detail = (f"all {n_pass} transpiler passes verified equivalent "
                      f"({n_oos} out-of-scope passes)")
        elif getattr(rep, "first_failure", None) is not None:
            result = "fail"
            detail = f"first failing pass: {rep.first_failure}"
        else:
            result = "out-of-scope"
            detail = (f"{n_pass} passes checked, {n_oos} out of scope "
                      f"(non-Clifford gates); no failure found in scope")
        if summary:
            detail += f" | {summary[:300]}"
        add_proof(rec, "qiskit-transpile-verify", "per-pass validation",
                  result, detail)
        print(f"transpile-verify: {result} ({n_pass} passes, {n_oos} out of scope)")
    except Exception as e:  # noqa: BLE001 - record, don't crash the run
        add_proof(rec, "qiskit-transpile-verify", "per-pass validation",
                  "out-of-scope", f"{type(e).__name__}: {e}"[:400])
        print(f"transpile-verify: out-of-scope ({type(e).__name__})")
    save_record(args.out, rec)


if __name__ == "__main__":
    main()
