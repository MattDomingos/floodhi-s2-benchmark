"""Run every analysis script (python/01-09) and, optionally, the figure scripts.

Usage (from the repository folder):
    python run_all.py              # analyses only: rewrites the tables in results/
    python run_all.py --figures    # analyses, then Figs. 2, 3 and 8 in figures/output/

Each script's printed output is saved next to it in logs/. The run stops at the
first script that fails and shows its error.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ANALYSES = sorted((ROOT / "python").glob("0*.py"))
FIGURES = [ROOT / "figures" / f for f in
           ("fig02_data.py", "fig02_workflow.py", "fig03_observations.py", "fig08_expected_recall.py")]

scripts = ANALYSES + (FIGURES if "--figures" in sys.argv else [])
logs = ROOT / "logs"
logs.mkdir(exist_ok=True)
env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", MPLBACKEND="Agg")

for script in scripts:
    start = time.time()
    print(f"{script.parent.name}/{script.name} ...", end=" ", flush=True)
    run = subprocess.run([sys.executable, script.name], cwd=script.parent, env=env,
                         capture_output=True, text=True, encoding="utf-8")
    (logs / f"{script.stem}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    if run.returncode != 0:
        print("FAILED\n")
        print(run.stderr)
        sys.exit(1)
    print(f"ok ({time.time() - start:.0f} s)")

print("\nAll scripts finished. Tables are in results/, printed output in logs/.")
