PYTHON=.venv\Scripts\python.exe

.PHONY: test start start-debug example example-helper

test:
	$(PYTHON) -m pytest -q

start:
	$(PYTHON) -m streamlit run app.py --server.port 2000

start-debug:
	# Launch with debugpy listening on 5678, then attach from your IDE
	$(PYTHON) -m debugpy --listen 5678 -m streamlit run app.py --server.port 2000

example:
	$(PYTHON) examples\quick_start.py

example-helper:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-example.ps1 -script quick_start.py
