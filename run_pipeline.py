#!/usr/bin/env python3
"""Run the full quantum-algorithm-fixer pipeline locally.

Builds a sample 3-qubit Grover circuit (marked state |111>, 2 iterations),
dumps it as OpenQASM 3, then runs every worker in order:
transpile -> QCEC -> transpile-verify -> Compact -> Aer -> score.
Writes sample-proof-record.json (the real proof record) and sample-grover.qasm.

Usage:
  python3 run_pipeline.py [--qasm FILE] [--id ALGO_ID] [--out FILE]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKERS = HERE / "workers"
PY = sys.executable

STEPS = [
    ("transpile.py", "qiskit-transpiler"),
    ("check_qcec.py", "mqt-qcec"),
    ("check_transpile_verify.py", "qiskit-transpile-verify"),
    ("optimize_compact.py", "compact"),
    ("simulate_aer.py", "qiskit-aer"),
    ("score.py", "score"),
]


def build_grover_3q():
    from qiskit import QuantumCircuit, qasm3

    qc = QuantumCircuit(3, 3)

    def grover_iteration(qc):
        # Oracle: phase-flip |111> via H-MCX-H on qubit 2
        qc.h(2)
        qc.mcx([0, 1], 2)
        qc.h(2)
        # Diffusion operator
        qc.h([0, 1, 2])
        qc.x([0, 1, 2])
        qc.h(2)
        qc.mcx([0, 1], 2)
        qc.h(2)
        qc.x([0, 1, 2])
        qc.h([0, 1, 2])

    qc.h([0, 1, 2])
    grover_iteration(qc)
    grover_iteration(qc)
    qc.measure([0, 1, 2], [0, 1, 2])
    return qasm3.dumps(qc)


def run_step(script, record_path):
    t0 = time.time()
    proc = subprocess.run(
        [PY, str(WORKERS / script), "--in", str(record_path), "--out", str(record_path)],
        capture_output=True, text=True, cwd=str(HERE),
    )
    dt = time.time() - t0
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    # Stamp the wall time onto the proof this step just appended.
    try:
        rec = json.loads(Path(record_path).read_text())
        if rec.get("proofs"):
            rec["proofs"][-1]["duration_s"] = round(dt, 3)
            Path(record_path).write_text(json.dumps(rec, indent=2))
    except Exception:
        pass
    status = "OK " if proc.returncode == 0 else "FAIL"
    print(f"[{status}] {script} ({dt:.1f}s) {out}")
    if proc.returncode != 0 and err:
        print(f"       stderr: {err[-500:]}")
    return proc.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qasm", help="OpenQASM file to fix (default: build sample Grover)")
    ap.add_argument("--id", default="grover-3q-v1", help="algorithm_id")
    ap.add_argument("--out", default="sample-proof-record.json", help="output record JSON")
    args = ap.parse_args()

    if args.qasm:
        qasm = Path(args.qasm).read_text()
        algo_id = args.id
    else:
        qasm = build_grover_3q()
        algo_id = "grover-3q-v1"
        (HERE / "sample-grover.qasm").write_text(qasm)
        print("sample circuit: 3-qubit Grover, marked |111>, 2 iterations")

    record = {
        "algorithm_id": algo_id,
        "algorithm": qasm,
        "score": {"overall": 0.0, "depth": 0, "gate_count": 0, "fidelity": None},
        "completed_algorithm": None,
        "proofs": [],
    }
    out_path = HERE / args.out
    out_path.write_text(json.dumps(record, indent=2))

    ok = True
    for script, _node in STEPS:
        if not run_step(script, out_path):
            ok = False
    rec = json.loads(out_path.read_text())
    print(f"\nDone. Score: {rec['score']}")
    print(f"Proofs: {len(rec['proofs'])}")
    for p in rec["proofs"]:
        print(f"  - {p['node']}: {p['result']} ({p.get('duration_s', '?')}s)")
    print(f"Record: {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
