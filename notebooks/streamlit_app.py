import os, sys, subprocess
from pathlib import Path

here = Path.cwd()
root = next((p for p in [here, *here.parents] if (p / "streamlit_app.py").exists()), None)
if root is None:
    raise SystemExit("streamlit_app.py not found - move this notebook into the project folder")
os.chdir(root)
print("Project folder:", root)

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "streamlit"])

!streamlit run streamlit_app.py