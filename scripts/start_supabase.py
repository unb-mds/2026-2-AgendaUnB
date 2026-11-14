"""Start local Supabase with the Google Auth settings from the repository .env."""
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
GOOGLE_AUTH_VARIABLES = (
    "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID",
    "SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET",
)


def main() -> int:
    env = os.environ.copy()
    config = dotenv_values(ROOT / ".env")
    for name in GOOGLE_AUTH_VARIABLES:
        if config.get(name):
            env.setdefault(name, config[name])

    npx = "npx.cmd" if os.name == "nt" else "npx"
    return subprocess.call([npx, "supabase", "start", *sys.argv[1:]], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
