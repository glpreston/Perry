Peacemaker Guild
=================

Developer notes:

- `agents.py` — Agent data class (name, host, model, persona).
- `orchestrator.py` — `MultiAgentOrchestrator` (main logic). Uses `Router` and `PromptBuilder`.
- `router.py` — routing helpers to determine addressed vs broadcast queries.
- `prompt_builder.py` — builds prompts with optional memory injection and sanitization.
- `memory.py` — MySQL-backed memory store (QA storage and retrieval).
- `server_utils.py` — helpers for checking server status and available models.

Refactor notes:

The previous `config.py` was split into modules to improve maintainability. `config.py`
remains as a small compatibility shim that re-exports the primary symbols (`Agent`,
`MultiAgentOrchestrator`, `get_models_for_server`, `check_server_status`).

Run tests:

```powershell
Set-Location 'D:\Projects\Perry'
.\.venv\Scripts\python.exe -m pytest -q
```

Public API & Developer Guide
----------------------------

Quick start (Windows PowerShell):

```powershell
Set-Location 'D:\Projects\Perry'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# run tests
.\.venv\Scripts\python.exe -m pytest -q
# run app
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 2000
```

`agents_config.json` format
--------------------------

Minimal example (UTF-8, supports emoji in names/personas):

```json
{
	"servers": {
		"local": "http://localhost:11434",
		"gamer": "http://gamer:11434"
	},
	"agent_styles": {
		"Netty": {"emoji": "🧠", "color": "#2a9d8f"},
		"Rex": {"emoji": "🦖", "color": "#e76f51"}
	},
	"agents": [
		{"name": "Netty", "server": "local", "model": "gpt-4-mini", "personality": "A calm, analytical assistant."},
		{"name": "Rex", "server": "gamer", "model": "gpt-3.5-small", "personality": "Short, enthusiastic gamer style."}
	],
	"use_moderator": true,
	"moderator": {"server": "local", "model": "gpt-4-mini", "personality": "You are the moderator."}
}
```

Using `MultiAgentOrchestrator` programmatically
-----------------------------------------------

Example: load config, send an addressed query, and inspect replies.

```python
from config import MultiAgentOrchestrator

orch = MultiAgentOrchestrator()
orch.load_config('agents_config.json')

# Send an addressed query to Netty
replies = orch.chat('Netty: Summarize the plan for today.', messages=None)
print(replies)

# Send a broadcast (goes to all agents)
replies = orch.chat("Hello all, what's new?", messages=None)
print(replies)

# Toggle memory injection off
orch.set_memory_usage(False)

# Save config (writes back servers and agents)
orch.save_config('agents_config.json')
```

Prompt builder and routing internals
-----------------------------------

- `router.py` exposes `Router.route(query, agent_names)` returning `(target_agent, pattern)` used to decide addressed vs broadcast.
- `prompt_builder.py` exposes `PromptBuilder.build_prompt(...)` which centralizes memory injection and sanitization.

Contributing and tests
----------------------

- Add unit tests under `tests/` and keep them fast and hermetic (mock network calls).
- When editing orchestrator internals, keep `config.py` shim in place to avoid breaking imports.

Contributing
------------

We welcome contributions. Follow these minimal guidelines to keep the codebase tidy and make reviews fast.

- Branching: create feature branches from `main` named `feat/<short-desc>` or `fix/<short-desc>`.
- Tests: add or update unit tests under `tests/` for any changes to logic. Keep tests deterministic and avoid contacting real servers — mock `requests.post` / `requests.get`.
- Formatting: use `black` for Python formatting where possible. A quick local formatting command:

```powershell
.# from project root
.\.venv\Scripts\pip install black
.\.venv\Scripts\python -m black .
```

- Commit messages: short subject line (50 chars), blank line, longer explanation if needed.

Developer workflow (example)
----------------------------

1. Create a branch: `git checkout -b feat/refactor-orch`.
2. Run tests locally: `./.venv/Scripts/python.exe -m pytest -q`.
3. Make changes, add tests.
4. Run tests again and ensure all pass.
5. Push branch and open a PR.

Adding or editing agents
------------------------

- The `agents_config.json` file controls available servers and agents. Before editing through the UI or by hand, make a quick backup:

```powershell
copy agents_config.json agents_config.json.bak
```

- If you add a new server, include a key under `servers` and point `agents[].server` to that key as in the README examples.

Memory DB notes
---------------

- Memory is backed by the MySQL instance configured for `MemoryDB`. During tests we use a real DB instance if available; unit tests should mock DB calls where possible.
- Group memory is stored using the special group key (`__group__`). The UI lets you export memories before clearing them.

Recommended models (guidance)
-----------------------------

- For local testing and low-cost development: small/fast models like `gpt-3.5-small` or community open-source models.
- For higher-quality responses and moderation duties: `gpt-4-mini` or equivalent higher-capacity models.
- Map models per agent by capability and cost. The `agents_config.json` example shows how to assign them.

Support
-------

If something breaks after the refactor, run the full test suite and check for missing imports. The `config.py` shim is in place to avoid most breakages while refactoring.

API Reference
-------------

This section describes the primary classes and functions you'll use when integrating
programmatically with the project.

Agent
~~~~~

`Agent(name: str, host: str, model: str, persona: str)`

- Simple container for agent metadata. Use `orch.add_agent(name, host, model, persona)`
	to add programmatically.

MultiAgentOrchestrator
~~~~~~~~~~~~~~~~~~~~~~

Class: `MultiAgentOrchestrator()`

Key methods:

- `load_config(path: str = "agents_config.json")` — load servers, agents, styles and moderator from JSON.
- `save_config(path: str = "agents_config.json")` — write current config back to disk.
- `add_agent(name: str, host: str, model: str, persona: str)` — add an agent at runtime.
- `chat(user_query: str, messages)` — route the `user_query` to a single agent (if addressed) or broadcast to all agents. Returns `dict[name->reply]`.
- `set_memory_usage(use_memory: bool)` — enable/disable memory injection for prompts.
- `set_moderator()` — ensure moderator agent is present when `use_moderator` is True.

Example
~~~~~~~

```python
from config import MultiAgentOrchestrator

orch = MultiAgentOrchestrator()
orch.load_config('agents_config.json')
replies = orch.chat('Netty: Give me a short summary', messages=None)
print(replies)
```

PromptBuilder
~~~~~~~~~~~~~

`PromptBuilder` centralizes prompt construction and memory injection.

Key methods:

- `PromptBuilder.build_prompt(original_query, agent_name, agent_obj, memory_db, use_memory, use_group_memory, target_agent)` — returns a string prompt ready to send to a model server.
- `PromptBuilder.strip_leading_agent_name(q: str)` — removes prefixes like `AgentName:` from a question.
- `PromptBuilder.is_error_text(s: str)` — heuristic to detect timeouts/errors so they are not injected as memory answers.

Router
~~~~~~

`Router.route(original_query: str, agent_names: List[str]) -> (target_agent, pattern)`

- Decides whether a query addresses a single agent or is a broadcast. Returns the target agent name and the regex pattern that matched, or `(None, None)` for broadcast.

MemoryDB
~~~~~~~~

Located in `memory.py`. Key methods:

- `MemoryDB()` — constructor reads DB config from environment variables (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`) and ensures the `agent_memory` table exists.
- `save_memory(agent_name: str, memory_text: str)` — save a simple memory_text entry.
- `save_qa(agent_name: str, question: str, answer: str, conv_id: Optional[str] = None)` — save structured QA pair.
- `load_recent_qa(agent_name: Optional[str] = None, limit: int = 10) -> List[dict]` — returns recent QA entries for an agent or group (agent_name `None` means group memory). Dict entries contain `{'q','a','ts'}`.
- `get_recent_memories(agent_name: Optional[str], limit: int)` — returns recent memory_text entries.
- `save_group_memory(memory_text: str)` — save a memory under the special `__group__` key.
- `clear_memory(agent_name: str)` and `clear_all()` — destructive operations to remove memory rows.
- `is_connected()` — check DB connectivity.

Example: saving/loading a QA pair
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

```python
from memory import MemoryDB
db = MemoryDB()
db.save_qa('Netty', 'How many projects?', 'Three')
rows = db.load_recent_qa('Netty', limit=5)
print(rows)
```

Debugging tips
--------------

- If the Streamlit UI won't start, check for leftover Streamlit sessions or port binds; Streamlit prints the local URL on startup.
- Use `print()` and small unit tests to isolate orchestrator behavior; the test suite runs quickly and can be executed with `pytest -q`.



# Python venv environment (minimal)

Recommended Python version: 3.11+.

Quick start (PowerShell):

```powershell
# Create virtual environment
python -m venv .venv

# Install dependencies (use venv's python to be explicit)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Run the app
.\.venv\Scripts\python.exe app.py

# Run tests
.\.venv\Scripts\python.exe -m pytest -q
```

Files added:

- `app.py` — minimal example reading `NAME` from `.env`
- `requirements.txt` — dependencies
- `.env.example` — example environment file
- `tests/test_app.py` — pytest tests

Memory tests
----------------
This project includes tests that exercise the MemoryDB and orchestrator memory behavior.

- Unit test: `tests/test_memory.py` — verifies the memory filtering heuristic (error/timeouts are ignored).
- Integration test: `tests/test_memory_integration.py` — saves an agent QA pair and a group question-only entry, then asserts they can be loaded.

Run tests (PowerShell, from project root):

```powershell
Set-Location 'D:\Projects\Perry'
.\.venv\Scripts\Activate
.\.venv\Scripts\python.exe -m pytest tests/test_memory.py tests/test_memory_integration.py -q
```

Create a `.env` file from `.env.example` and edit `NAME` as needed.

DB configuration & precautions
-----------------------------
The application can optionally persist memories to a MySQL-compatible database. Configure the database connection using environment variables (for example in your `.env` file).

Recommended `.env` variables:

```env
# Database (MySQL/MariaDB)
DB_HOST=192.168.50.114
DB_PORT=3306
DB_USER=hal
DB_PASS=yourpassword
DB_NAME=perry_memory
```

Notes and precautions:

- The `MemoryDB` layer will attempt to connect to the DB and create the `agent_memory` table if it does not exist. Ensure the database user has CREATE and INSERT privileges.
- The `clear_memory(agent_name)` and `clear_all()` operations remove rows permanently. Do NOT run these in production without a backup — they are destructive and irreversible.
- Consider exporting or backing up your `agent_memory` table before running clear operations. Example (MySQL):

```powershell
# Export table to SQL (example)
mysqldump -h $env:DB_HOST -P $env:DB_PORT -u $env:DB_USER -p$env:DB_PASS $env:DB_NAME agent_memory > agent_memory_backup.sql
```

- For local development, keep your `.env` out of version control. Do not commit production credentials to the repo.
- If you want to inspect rows, use a DB client (MySQL Workbench, `mysql` CLI, or an admin UI). The `agent_memory` table stores structured QA rows with columns similar to: `id`, `agent_name`, `memory_text`, `question`, `answer`, `conv_id`, `timestamp`.

If you want, I can add a small script to export or list memories safely before clear operations.
