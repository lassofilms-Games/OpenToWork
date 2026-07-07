Job Finder Pro v1.3.0

What it is
- Desktop app in Python to search job offers from direct links and a few public APIs.
- The app uses Tkinter and runs on Windows as a normal desktop window.

Install dependencies
- Open a terminal in this folder.
- Run:
  python -m pip install -r requirements.txt

Run from Python
- Run:
  python job_finder_pro.py

Build the EXE
- Run:
  python -m PyInstaller --onefile --windowed --name JobFinderPro job_finder_pro.py
- Or use:
  build_exe_job_finder_pro.bat

Where files are saved
- Configuration: %APPDATA%\JobFinderPro\config.json
- Results: %APPDATA%\JobFinderPro\results\
- Logs: %APPDATA%\JobFinderPro\logs\job_finder_pro.log

How to use
1. Choose roles, keywords, locations and sources.
2. Click "Buscar ofertas".
3. Review the table on the right.
4. Select a result to open the link or fallback.
5. Export the results to TXT, CSV and HTML when needed.

Notes
- Some rows are real job offers from APIs.
- Other rows are direct search links for the selected source.
- If a source fails, the app now shows a clear message and writes the error to the log.
