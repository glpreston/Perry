Contributing to Peacemaker Guild
================================

Thanks for helping improve Peacemaker Guild! This document explains how to get set up, run tests, and make changes safely.

Developer setup (Windows PowerShell)
-----------------------------------

1. Clone repository and enter project dir:

```powershell
git clone <repo-url>
Set-Location 'D:\Projects\Perry'
```

2. Create and activate virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Coding & testing guidelines
---------------------------

- Write small, focused commits and tests.
- Use mocking for network calls (e.g., patch `requests.post`) so tests run offline.
- Add unit tests for any new module or behavior.

Style & formatting
------------------

- Use `black` for formatting. Keep code simple and readable.

Working with `agents_config.json`
--------------------------------

- Always back up the file before editing in the UI or manually:

```powershell
copy agents_config.json agents_config.json.bak
```

- Validate JSON (there's no strict schema enforced, but follow the example in `README.md`).

Running the Streamlit app (development)
--------------------------------------

Start the app locally and open `http://localhost:2000`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 2000
```

Submitting changes
------------------

1. Push your branch to origin and open a Pull Request.
2. Ensure tests pass and include a short description of the change.
3. If the change modifies user-visible behavior (UI or memory handling), include migration notes in `CHANGELOG.md`.

Contact
-------

If you have questions about architecture or design decisions, open an issue or ping the maintainer in the project chat.
