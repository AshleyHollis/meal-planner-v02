from pathlib import Path
import sys


WORKER_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = WORKER_ROOT.parents[0] / "api"

for root in (WORKER_ROOT, API_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
