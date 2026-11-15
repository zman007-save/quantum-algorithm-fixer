#!/usr/bin/env python3
"""Local HTTP service wrapping the quantum-algorithm-fixer workers.

n8n Cloud cannot run Python (no Execute Command node), so n8n talks to this
service over HTTP instead. Each endpoint takes a proof-record JSON, runs one
worker, and returns the updated record. Run it on the machine that has the
Python workers installed (your laptop, or Fartur's Wind over Tailscale).

  python3 server.py [--port 8000]

Endpoints:
  GET  /health                  -> {"status": "ok", ...}
  POST /transpile               -> qiskit transpiler node
  POST /qcec                    -> MQT QCEC equivalence node
  POST /transpile-verify        -> qiskit-transpile-verify node
  POST /compact                 -> Compact verified-optimizer node
  POST /simulate                -> Qiskit Aer simulator node
  POST /score                   -> scoring node
  POST /run                     -> full pipeline; body may be a record or
                                   {"algorithm_id": ..., "algorithm": "<QASM>"}
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKERS = HERE / "workers"
PY = sys.executable

ROUTES = {
    "/transpile": "transpile.py",
    "/qcec": "check_qcec.py",
    "/transpile-verify": "check_transpile_verify.py",
    "/compact": "optimize_compact.py",
    "/simulate": "simulate_aer.py",
    "/score": "score.py",
}

FULL_PIPELINE = ["transpile.py", "check_qcec.py", "check_transpile_verify.py",
                 "optimize_compact.py", "simulate_aer.py", "score.py"]


def run_worker(script, record):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(record, f)
        path = f.name
    t0 = time.time()
    proc = subprocess.run(
        [PY, str(WORKERS / script), "--in", path, "--out", path],
        capture_output=True, text=True, cwd=str(HERE),
    )
    dt = time.time() - t0
    try:
        rec = json.loads(Path(path).read_text())
    except Exception as e:  # noqa: BLE001
        return {"error": f"worker {script} produced no record: {e}",
                "stdout": proc.stdout, "stderr": proc.stderr}, 500
    if rec.get("proofs"):
        rec["proofs"][-1]["duration_s"] = round(dt, 3)
    if proc.returncode != 0:
        rec.setdefault("errors", []).append(
            {"worker": script, "stderr": (proc.stderr or "")[-500:]})
    return rec, 200


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "workers": sorted(ROUTES),
                             "pipeline": FULL_PIPELINE})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", 0))
            record = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:  # noqa: BLE001
            self._send(400, {"error": f"bad JSON: {e}"})
            return
        if self.path == "/run":
            if "algorithm" not in record:
                self._send(400, {"error": "body needs 'algorithm' (OpenQASM) "
                                 "or a full proof record"})
                return
            record.setdefault("algorithm_id",
                              f"algo-{int(time.time())}")
            record.setdefault("score", {"overall": 0.0, "depth": 0,
                                        "gate_count": 0, "fidelity": None})
            record.setdefault("completed_algorithm", None)
            record.setdefault("proofs", [])
            for script in FULL_PIPELINE:
                record, code = run_worker(script, record)
                if code != 200:
                    self._send(code, record)
                    return
            self._send(200, record)
            return
        script = ROUTES.get(self.path)
        if not script:
            self._send(404, {"error": "unknown endpoint"})
            return
        if "algorithm" not in record:
            self._send(400, {"error": "body must be a proof record JSON"})
            return
        record, code = run_worker(script, record)
        self._send(code, record)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"quantum worker service on http://{args.host}:{args.port}")
    print("endpoints:", ", ".join(["/health"] + sorted(ROUTES) + ["/run"]))
    srv.serve_forever()


if __name__ == "__main__":
    main()
