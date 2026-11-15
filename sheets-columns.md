# Google Sheets — master workbook layout ("Quantum Algorithm Proof Ledger")

One workbook, two levels. The n8n workflow writes to it twice per run:
once to the master tab, once to the algorithm's own tab.

The workbook is created under the personal Gmail account
**zacharylafer@gmail.com** (NOT the zachary@prohm.life n8n account).
Its ID is already in both Sheets nodes in `workflow.json`:
`10YVSSuDSKqThb0WdB-CILBr_Ez__wAtR6nAWl1QY4tM` —
https://docs.google.com/spreadsheets/d/10YVSSuDSKqThb0WdB-CILBr_Ez__wAtR6nAWl1QY4tM/edit

## Tab 1: `Master` (one row per algorithm)

The index. One row per `algorithm_id` — the latest state of each algorithm.
(n8n appends a row per run; de-dupe by Algorithm ID when reviewing, or sort
by Latest Run Time and take the newest row per algorithm.)

Merged from Pipeline B: the five per-node proof columns sit next to the
one-line Proof Summary, so a judge reading the Master tab sees every
node's verdict without opening the per-algorithm tab.

| # | Column | n8n expression | Example |
|---|--------|---------------|---------|
| A | Algorithm ID | `={{ $json.algorithm_id }}` | grover-3q-v1 |
| B | Algorithm | `={{ $json.algorithm }}` | OPENQASM 3.0; ... |
| C | Score | `={{ $json.score.overall }}` | 0.829 |
| D | Completed Algorithm | `={{ $json.completed_algorithm }}` | OPENQASM 3.0; ... |
| E | Proof Summary | `={{ ($json.proofs || []).map(p => p.node + ': ' + p.result).join(' · ') }}` | qiskit-transpiler: pass · mqt-qcec: equivalent · qiskit-transpile-verify: out-of-scope · compact: verified · qiskit-aer: pass |
| F | Proof: Transpiler | per-node filter on `qiskit-transpiler` | pass: depth 22 -> 10; gates 42 -> 21 ... |
| G | Proof: QCEC | per-node filter on `mqt-qcec` | equivalent: QCEC verdict ... |
| H | Proof: Transpile-Verify | per-node filter on `qiskit-transpile-verify` | out-of-scope: 43 passes checked ... |
| I | Proof: Compact | per-node filter on `compact` | verified: Compact verified its own rewrite ... |
| J | Proof: Simulator | per-node filter on `qiskit-aer` | pass: Hellinger fidelity 1.0 over 1024 shots ... |
| K | Runs | `={{ 1 }}` | 1 |
| L | Latest Run Time | `={{ $now.toISO() }}` | 2026-11-15T... |

## Tab 2+: one tab per algorithm (tab name = `algorithm_id`)

The history. Every run ever done on that algorithm appends one row here,
so the workbook accumulates history per algorithm across runs.

| # | Column | n8n expression |
|---|--------|---------------|
| A | Run ID | `={{ $json.algorithm_id + '-' + $now.toISO() }}` |
| B | Timestamp | `={{ $now.toISO() }}` |
| C | Score | `={{ $json.score.overall }}` |
| D | Depth | `={{ $json.score.depth }}` |
| E | Gate Count | `={{ $json.score.gate_count }}` |
| F | Fidelity | `={{ $json.score.fidelity }}` |
| G | Completed Algorithm | `={{ $json.completed_algorithm }}` |
| H | Proof: Transpiler | per-node filter on `qiskit-transpiler` |
| I | Proof: QCEC | per-node filter on `mqt-qcec` |
| J | Proof: Transpile-Verify | per-node filter on `qiskit-transpile-verify` |
| K | Proof: Compact | per-node filter on `compact` |
| L | Proof: Simulator | per-node filter on `qiskit-aer` |

## Setup notes

- Create the workbook once under zacharylafer@gmail.com, add a `Master`
  tab with the headers above — done, the workbook already exists and the
  workbook ID is already in the two Google Sheets nodes in
  `workflow.json`. Connect the zacharylafer@gmail.com Google
  account in n8n when the node asks for credentials.
- Per-algorithm tabs: auto-created by the workflow. The 'Create
  Algorithm Tab' step (Sheets API `spreadsheets.batchUpdate` with
  `addSheet`) runs after Score and before the appends, so a brand-new
  `algorithm_id` gets its own tab on its first run — no hand-made tab
  needed. The 'Set Tab URL' step then adds `tab_url` (ledger URL +
  `#gid=<new tab gid>`) to the response record. Headers for the new tab
  come from the column mapping in the 'Append to Algorithm Tab' node
  (see table above).
- The QASM cells are long. In Sheets, set the Algorithm / Completed
  Algorithm columns to wrap text.
- The JSON record (`sample-proof-record.json`, schema in `schema.json`) is
  the machine record; the Sheet is the human ledger. The front end reads
  the JSON record, not the Sheet.
