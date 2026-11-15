# Quantum Algorithm Fixer

**Try it live: https://zman007-save.github.io/quantum-algorithm-fixer/**

Paste an OpenQASM algorithm and an n8n pipeline runs it through open-source quantum nodes — Qiskit transpiler, MQT QCEC equivalence check, transpile-verify, Compact, Qiskit Aer simulator, scorer — then returns the completed algorithm with a proof record. Every node proves its own work, and every run lands in a public ledger with its score and the reason behind each step's result.

- **Live site:** https://zman007-save.github.io/quantum-algorithm-fixer/
- **Proof ledger (public):** https://docs.google.com/spreadsheets/d/10YVSSuDSKqThb0WdB-CILBr_Ez__wAtR6nAWl1QY4tM/edit?usp=sharing
- Built at the n8n Buildathon, Santa Clara University, November 15, 2026.

## Verified runs (live, end to end)

| Algorithm | Score | Notes |
|---|---|---|
| grover-3q-v1 — 3-qubit Grover, marked state \|111⟩, 2 iterations | **0.829** | fidelity 1.0, depth 22→10, gates 42→21 |
| qft-4q-v1 — 4-qubit QFT | **0.445** | QCEC equivalence check errored (qubit mapping), so equivalence scored 0 — the reason shows on the site |

Scores vary by algorithm. Same input, same score — the pipeline is deterministic.

## How it works

```
submit (webhook) → transpile (Qiskit) → QCEC → transpile-verify
  → Compact → Aer → score → Google Sheets ledger → proof record back to the user
```

Each node appends one proof to the record. A step that can't run records why instead of faking it. The site shows the score breakdown (fidelity, equivalence, depth/gate reduction, proofs passing) and every step's result with its reason, and the screenplay PDF carries the same reasons.

Sim-only, no QPU: "simulated today, QPU-ready." No paid services anywhere in the chain.

## Files

- `index.html` — the public site (Blender hero loop, screenplay captions, PDF script download)
- `workflow.json` — the n8n workflow (import into n8n Cloud; webhook `POST /webhook/quantum-algorithm`)
- `workers/` — one Python script per pipeline node
- `server.py` — stdlib HTTP service so n8n can call the workers
- `run_pipeline.py` — run the full chain locally
- `sample-grover.qasm`, `sample-proof-record.json` — the verified Grover run
- `schema.json` — JSON Schema for the proof record
- `sheets-columns.md` — ledger layout (Master tab + one tab per algorithm)
- `requirements.txt` — pinned versions
- `gen_workflow.py` — regenerates `workflow.json`

## Run locally

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python run_pipeline.py
venv/bin/python server.py --port 8000
```

## Live deployment

Workers run on an RTX 5080 PC exposed via Tailscale Funnel; n8n Cloud instance `instancey5997`; the ledger lives under zacharylafer@gmail.com. The per-algorithm tab is created automatically on a new algorithm's first run, and every run gets its own row (`run-001`, `run-002`, …).

## Honest limitations

- transpile-verify is Clifford-fragment only — Grover's Toffoli gates are out of scope, so it reports out-of-scope rather than failing.
- No QPU is used. The D-Wave Leap Trial Plan has no solver access, so everything runs on local simulators.
- No product name yet — the builder names it himself.
