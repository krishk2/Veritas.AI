import os
import sys

# Ensure src is discoverable on python path
sys.path.insert(0, os.path.abspath("src"))

import uvicorn
from veritas.api import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("veritas.api:app", host="0.0.0.0", port=port)
