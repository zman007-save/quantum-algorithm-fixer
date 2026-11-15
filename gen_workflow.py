#!/usr/bin/env python3
"""Generate workflow.json — the importable n8n workflow (MERGED FINAL).

Base: Pipeline A (HTTP Request nodes -> server.py, n8n Cloud compatible).
Merged in from Pipeline B: per-node proof columns on the Master tab.
No Execute Command nodes: this workflow runs on n8n Cloud.

n8n Cloud cannot run Python, so every compute step is an HTTP Request node
pointing at the local worker service (server.py). Run server.py on the
machine with the workers, then point these URLs at it:
  - same machine: http://localhost:8000/...
  - Fartur's Wind over Tailscale: http://100.76.198.61:8000/...

Accounts: the n8n account is zachary@prohm.life (Google SSO). The Google
Sheets nodes use the personal Gmail account zacharylafer@gmail.com.
"""
import json
import uuid
from pathlib import Path

WORKER_URL = "https://farturs-wind.tail44ffde.ts.net"
LEDGER_ID = "10YVSSuDSKqThb0WdB-CILBr_Ez__wAtR6nAWl1QY4tM"
LEDGER_URL = f"https://docs.google.com/spreadsheets/d/{LEDGER_ID}/edit"


def nid():
    return str(uuid.uuid4())


def http_node(name, path, x):
    return {
        "parameters": {
            "method": "POST",
            "url": f"{WORKER_URL}{path}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($json) }}",
            "options": {"timeout": 180000, "response": {"response": {"responseFormat": "json"}}},
        },
        "id": nid(),
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [x, 300],
    }


def proof_expr(node):
    return ("={{ ($json.proofs || []).filter(p => p.node === '" + node +
            "').map(p => p.result + ': ' + p.detail).join(' | ') }}")


def proof_summary_expr():
    return ("={{ ($json.proofs || []).map(p => p.node + ': ' + p.result)"
            ".join(' · ') }}")


def sheets_node(name, sheet, columns, x):
    return {
        "parameters": {
            "operation": "append",
            "documentId": {
                "__rl": True,
                # "Quantum Algorithm Proof Ledger" workbook, created under
                # zacharylafer@gmail.com — ID 10YVSSuDSKqThb0WdB-CILBr_Ez__wAtR6nAWl1QY4tM.
                "value": "10YVSSuDSKqThb0WdB-CILBr_Ez__wAtR6nAWl1QY4tM",
                "mode": "url",
                "cachedResultUrl": "",
                "cachedResultName": "",
            },
            "sheetName": {
                "__rl": True,
                "value": sheet,
                "mode": "list",
                "cachedResultName": sheet,
            },
            "columns": {
                "mappingMode": "defineBelow",
                "value": columns,
                "matchingColumns": ["Algorithm ID"],
                "schema": [],
            },
            "options": {},
        },
        "id": nid(),
        "name": name,
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4,
        "position": [x, 300],
        # Google Sheets credential must be the personal Gmail account
        # zacharylafer@gmail.com (NOT the zachary@prohm.life n8n account).
        "credentials": {"googleSheetsOAuth2": {"id": None, "name": "zacharylafer@gmail.com"}},
    }


nodes = []

webhook = {
    "parameters": {
        "httpMethod": "POST",
        "path": "quantum-algorithm",
        "responseMode": "responseNode",
        "options": {},
    },
    "id": nid(),
    "name": "Submit Algorithm",
    "type": "n8n-nodes-base.webhook",
    "typeVersion": 2,
    "position": [0, 300],
    "webhookId": str(uuid.uuid4()),
}
nodes.append(webhook)

code = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": (
            "const body = $input.first().json.body || $input.first().json;\n"
            "const qasm = body.algorithm || body.qasm || '';\n"
            "const algorithm_id = body.algorithm_id || ('algo-' + Date.now());\n"
            "return [{ json: {\n"
            "  algorithm_id,\n"
            "  algorithm: qasm,\n"
            "  score: { overall: 0, depth: 0, gate_count: 0, fidelity: null },\n"
            "  completed_algorithm: null,\n"
            "  proofs: []\n"
            "}}];\n"
        ),
    },
    "id": nid(),
    "name": "Build Record",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [260, 300],
}
nodes.append(code)

steps = [
    ("Transpile (Qiskit)", "/transpile"),
    ("Check Equivalence (QCEC)", "/qcec"),
    ("Verify Passes", "/transpile-verify"),
    ("Optimize (Compact)", "/compact"),
    ("Simulate (Aer)", "/simulate"),
    ("Score", "/score"),
]
http_nodes = []
for i, (name, path) in enumerate(steps):
    n = http_node(name, path, 520 + i * 260)
    http_nodes.append(n)
    nodes.append(n)

# Master tab: one row per algorithm.
# Merged from Pipeline B: per-node proof columns sit next to the one-line
# Proof Summary, so a judge reading the Master tab sees every node's
# verdict without opening the per-algorithm tab.
master_columns = {
    "Algorithm ID": "={{ $json.algorithm_id }}",
    "Algorithm": "={{ $json.algorithm }}",
    "Score": "={{ $json.score.overall }}",
    "Completed Algorithm": "={{ $json.completed_algorithm }}",
    "Proof Summary": proof_summary_expr(),
    "Proof: Transpiler": proof_expr("qiskit-transpiler"),
    "Proof: QCEC": proof_expr("mqt-qcec"),
    "Proof: Transpile-Verify": proof_expr("qiskit-transpile-verify"),
    "Proof: Compact": proof_expr("compact"),
    "Proof: Simulator": proof_expr("qiskit-aer"),
    "Runs": "={{ 1 }}",
    "Latest Run Time": "={{ $now.toISO() }}",
}
x = 520 + len(steps) * 260

# New-tab step: create the per-algorithm tab if it does not exist yet.
# Google Sheets API spreadsheets.batchUpdate with addSheet, via an HTTP
# Request node authenticated with the same Google Sheets OAuth2 credential
# as the Sheets nodes. If the tab already exists the API answers 400
# ("already exists") — onError continueRegularOutput lets the run carry
# on instead of failing.
create_tab = {
    "parameters": {
        "method": "POST",
        "url": f"https://sheets.googleapis.com/v4/spreadsheets/{LEDGER_ID}:batchUpdate",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "googleSheetsOAuth2",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": ("={{ JSON.stringify({ requests: [{ addSheet: "
                    "{ properties: { title: $json.algorithm_id } } }] }) }}"),
        "options": {"timeout": 30000,
                    "response": {"response": {"responseFormat": "json"}}},
    },
    "id": nid(),
    "name": "Create Algorithm Tab",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [x, 300],
    "onError": "continueRegularOutput",
    # Same credential as the Sheets nodes: personal Gmail account
    # zacharylafer@gmail.com (NOT the zachary@prohm.life n8n account).
    "credentials": {"googleSheetsOAuth2": {"id": None, "name": "zacharylafer@gmail.com"}},
}
nodes.append(create_tab)
x += 260

# The Sheets API response replaces $json, so the record (algorithm_id,
# score, proofs, completed_algorithm) would be lost downstream. This Code
# node rebuilds it from the Score node's output and attaches the new
# tab's gid + tab_url. On a duplicate tab the create step errors, there
# is no gid in the response, and tab_url falls back to the plain ledger
# URL — the front end then links to the workbook instead of the tab.
set_tab_url = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": (
            "const create = $input.first().json;\n"
            "const record = $('Score').first().json;\n"
            "let gid = null;\n"
            "const reply = (create.replies || [])[0];\n"
            "if (reply && reply.addSheet && reply.addSheet.properties "
            "&& typeof reply.addSheet.properties.sheetId === 'number') {\n"
            "  gid = reply.addSheet.properties.sheetId;\n"
            "}\n"
            "const ledger = '" + LEDGER_URL + "';\n"
            "record.tab_gid = gid;\n"
            "record.tab_url = gid !== null ? ledger + '#gid=' + gid : ledger;\n"
            "return [{ json: record }];\n"
        ),
    },
    "id": nid(),
    "name": "Set Tab URL",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [x, 300],
}
nodes.append(set_tab_url)
x += 260

nodes.append(sheets_node("Append to Master", "Master", master_columns, x))
x += 260

# Per-algorithm tab: one row per run (tab name = algorithm_id).
run_columns = {
    "Run ID": "={{ $json.algorithm_id + '-' + $now.toISO() }}",
    "Timestamp": "={{ $now.toISO() }}",
    "Score": "={{ $json.score.overall }}",
    "Depth": "={{ $json.score.depth }}",
    "Gate Count": "={{ $json.score.gate_count }}",
    "Fidelity": "={{ $json.score.fidelity }}",
    "Completed Algorithm": "={{ $json.completed_algorithm }}",
    "Proof: Transpiler": proof_expr("qiskit-transpiler"),
    "Proof: QCEC": proof_expr("mqt-qcec"),
    "Proof: Transpile-Verify": proof_expr("qiskit-transpile-verify"),
    "Proof: Compact": proof_expr("compact"),
    "Proof: Simulator": proof_expr("qiskit-aer"),
}
nodes.append(sheets_node("Append to Algorithm Tab", "={{ $json.algorithm_id }}",
                         run_columns, x))
x += 260

respond = {
    "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify($json) }}",
        "options": {},
    },
    "id": nid(),
    "name": "Return Proof Record",
    "type": "n8n-nodes-base.respondToWebhook",
    "typeVersion": 1.4,
    "position": [x, 300],
}
nodes.append(respond)

sticky = {
    "parameters": {
        "content": "## Quantum Algorithm Fixer — setup (merged final build)\n\n1. Import into n8n at instancey5997 (https://instancey5997.app.n8n.cloud), signed in as zachary@prohm.life via Google SSO. Workflows → Import from file → workflow.json.\n2. Run the worker service: `python3 server.py` (venv) on Fartur's Wind. It is exposed to n8n Cloud via Tailscale Funnel at https://farturs-wind.tail44ffde.ts.net and every HTTP node already points there — do not change the URLs back to localhost.\n3. Google Sheets: the master workbook ('Quantum Algorithm Proof Ledger') is created under the personal Gmail account zacharylafer@gmail.com — that is the account for the Sheets nodes, NOT the zachary@prohm.life n8n account. The workbook ID is already in both Sheets nodes; just connect the zacharylafer@gmail.com Google account. Per-algorithm tabs are now AUTO-CREATED: the 'Create Algorithm Tab' step calls the Sheets API (spreadsheets.batchUpdate addSheet) after Score and before the appends, so a brand-new algorithm_id gets its own tab on its first run. If the tab already exists the API answers 400 and the step is configured to continue anyway (onError: continueRegularOutput). 'Set Tab URL' reads the new tab's gid from the create response and adds tab_url (ledger URL + #gid=<gid>) and tab_gid to the response record; when the tab already existed, tab_url falls back to the plain ledger URL. Connect the same zacharylafer@gmail.com Google Sheets OAuth2 credential on the 'Create Algorithm Tab' HTTP node too.\n4. POST {\"algorithm_id\": \"grover-3q-v1\", \"algorithm\": \"<OpenQASM 3>\"} to the webhook. The response is the full proof record, now including tab_url and tab_gid.\n\nSim-only: no QPU, no paid services. Simulated today, QPU-ready.",
        "height": 320,
        "width": 420,
        "color": 5,
    },
    "id": nid(),
    "name": "Sticky Note",
    "type": "n8n-nodes-base.stickyNote",
    "typeVersion": 1,
    "position": [0, 80],
}
nodes.append(sticky)

chain = [webhook["name"], code["name"]] + [n["name"] for n in http_nodes] + \
    ["Create Algorithm Tab", "Set Tab URL",
     "Append to Master", "Append to Algorithm Tab", "Return Proof Record"]
connections = {}
for a, b in zip(chain, chain[1:]):
    connections[a] = {"main": [[{"node": b, "type": "main", "index": 0}]]}

workflow = {
    "name": "Quantum Algorithm Fixer",
    "nodes": nodes,
    "connections": connections,
    "active": False,
    "settings": {"executionOrder": "v1"},
    "pinData": {},
}

out = Path(__file__).resolve().parent / "workflow.json"
out.write_text(json.dumps(workflow, indent=2))
print(f"wrote {out} ({len(nodes)} nodes)")
