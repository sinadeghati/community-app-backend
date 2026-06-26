"""Run a Django management command against staging using the public database URL."""
import json
import os
import shutil
import subprocess
import sys


def _railway_executable() -> str:
    return shutil.which("railway") or shutil.which("railway.cmd") or "railway"


def main() -> int:
    result = subprocess.run(
        [
            _railway_executable(),
            "variables",
            "--json",
            "-s",
            "Postgres",
            "-e",
            "Staging",
        ],
        capture_output=True,
        text=True,
        check=True,
        shell=os.name == "nt",
    )
    variables = json.loads(result.stdout)
    public_url = variables.get("DATABASE_PUBLIC_URL") or variables.get("PGPUBLICURL")
    if not public_url:
        print("DATABASE_PUBLIC_URL not found in Railway variables.", file=sys.stderr)
        return 1
    os.environ["DATABASE_URL"] = public_url
    os.chdir(os.path.join(os.path.dirname(__file__), "..", "iranapp"))
    cmd = [sys.executable, "manage.py", *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
