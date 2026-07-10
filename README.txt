OpenToWork v1.4.0
Creado por Diego Lasso

What it is
- Desktop app in Python to search job offers from direct links and a few public APIs.
- The app uses CustomTkinter and runs on Windows as a normal desktop window.

Install dependencies
- Open a terminal in this folder.
- Run:
  python -m pip install -r requirements.txt

Run from Python
- Run:
  python opentowork_app.py

Build the EXE
- Run:
  python -m PyInstaller OpenToWork.spec --noconfirm
- Or use:
  build_exe_opentowork.bat

Where files are saved
- Configuration: %APPDATA%\OpenToWork\config.json
- Job states (favorites, applied, discarded, notes): %APPDATA%\OpenToWork\job_states.json
- Results: %APPDATA%\OpenToWork\results\
- Logs: %APPDATA%\OpenToWork\logs\opentowork.log
- Coming from OPentowork_app? Your config and job states migrate automatically on first run.

How to use
1. Choose roles, keywords, locations and sources in the sidebar.
2. Click "Buscar ofertas".
3. Review the results table and click a row to see its detail panel.
4. Open the link or fallback from the detail panel.
5. Export the results to TXT, CSV and HTML when needed.

Notes
- Some rows are real job offers from APIs.
- Other rows are direct search links for the selected source.
- If a source fails, the app shows a clear message and writes the error to the log.
- Custom job sources (name + domain) can be added from the sidebar.
