"""
Replaces every hardcoded MongoDB connection string in api/*.py with
os.environ["MONGODB_URI"] and adds load_dotenv() so scripts read .env.

Run from the Animore repo root:  python fix_env.py
Then delete this file.
"""
import re
import pathlib

HEADER = "import os\nfrom dotenv import load_dotenv\nload_dotenv()\n"
pattern = re.compile(r'"mongodb(\+srv)?://[^"]*"')

api_dir = pathlib.Path("api")
if not api_dir.is_dir():
    raise SystemExit("Run this from the Animore repo root (the folder that contains api/).")

for path in api_dir.glob("*.py"):
    text = path.read_text()
    new = pattern.sub('os.environ["MONGODB_URI"]', text)
    new = new.replace("#uri = \n", 'uri = os.environ["MONGODB_URI"]\n')
    if new != text:
        if "load_dotenv()" not in new or "import os\n" not in new:
            new = HEADER + new
        path.write_text(new)
        print("updated", path)

print("Done. Check with: grep -rn \"mongodb+srv\" api")