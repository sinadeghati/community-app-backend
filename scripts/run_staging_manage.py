"""Run a Django management command against staging using the public database URL."""
import json
import os
import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        ["railway", "variables", "--json", "-s", "community-app-backend", "-e", "Staging"],
        capture_output=True,
        text=True,
        check=True,
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
