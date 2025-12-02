Examples
========

This folder contains small example scripts showing how to use the library
programmatically. Each example is designed to be safe to run locally (no
network calls) by default — they monkeypatch `requests.post` to return
predictable replies. Use these as starting points for scripting your own
automation or testing flows.

Files
-----

- `quick_start.py` — Minimal quick-start script demonstrating:
  - Loading `agents_config.json` via `MultiAgentOrchestrator`.
  - Sending an addressed query (e.g., `Netty: ...`) and a broadcast query.
  - Using a fake `requests.post` mapping to simulate server responses.
  - Optional MemoryDB demo (runs only if DB env vars are configured).
  - Writing an `agents_config.example.json` copy as a safe example export.

Planned examples you can add
---------------------------

- `export_memories.py` — Export per-agent or full-table memories to CSV/JSON.
- `clear_memories.py` — Safe interactive script to export then clear memories.
- `batch_queries.py` — Run a set of scripted queries and save replies.

Running the examples (PowerShell)
--------------------------------

From the project root with the venv activated:

```powershell
Set-Location 'D:\Projects\Perry'
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe examples\quick_start.py
```

If you'd like a short PowerShell helper (example):

```powershell
# save as .\scripts\run-example.ps1
param([string]$script = 'quick_start.py')
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)\..  # project root
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe "examples\$script"
```

Tips
----

- The examples are intentionally small. Copy them into your own scripts and
  replace the fake `requests.post` with real network calls when you're ready.
- Use `orch.save_config('agents_config.example.json')` from `examples/quick_start.py`
  to generate a safe-to-edit copy of your current config.
