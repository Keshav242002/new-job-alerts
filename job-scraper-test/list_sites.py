"""Print a library's supported sites, classified by how each scraper fetches data.

Usage:  venv-jobspy/bin/python list_sites.py jobspy
        venv-jobdrop/bin/python list_sites.py jobdrop
"""
import importlib
import pathlib
import re
import sys

BROWSER_RE = re.compile(r"camoufox|selenium_driverless|zendriver|playwright")
CRED_RE = re.compile(r"_get\(\d+\)")  # jobdrop's bundled-API-key lookup

lib = sys.argv[1]
pkg = importlib.import_module(lib)
Site = importlib.import_module(f"{lib}.model").Site
root = pathlib.Path(pkg.__file__).parent

# module dir names don't always match enum values (zip_recruiter -> ziprecruiter)
dirs = {p.name.replace("_", ""): p for p in root.iterdir() if p.is_dir() and p.name != "__pycache__"}

print(f"{lib}: {len(Site)} sites")
for s in Site:
    d = dirs.get(s.value.replace("_", ""))
    src = "".join(f.read_text() for f in d.glob("*.py")) if d else ""
    if CRED_RE.search(src):
        kind = "API key (bundled credential)"
    elif BROWSER_RE.search(src):
        kind = "headless browser" + (" (fallback only)" if "fallback" in src.lower() and s.value == "hiring_cafe" else "")
    else:
        kind = "plain HTTP"
    print(f"  {s.value:<16} {kind}")
