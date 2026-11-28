"""Set a new login password for the local Langfuse user (keeps all traces and settings).

Langfuse stores bcrypt hashes ("$2a$12$..."), so the new password is hashed with the
bcryptjs library inside the running langfuse-web container (the same code Langfuse checks
passwords with) and written to Postgres. The password is read with getpass (not echoed)
and sent to the container on stdin, never as a command-line argument (visible to other
processes). infra/.env is updated so it keeps matching the real password.

Usage (Langfuse running):
    uv run python infra/set_langfuse_password.py
"""

import getpass
import re
import subprocess
import sys
from pathlib import Path

INFRA_ENV = Path(__file__).parent / ".env"
WEB, POSTGRES = "infra-langfuse-web-1", "infra-postgres-1"
BCRYPT = "/app/node_modules/.pnpm/bcryptjs@2.4.3/node_modules/bcryptjs"  # inside the image
MIN_LENGTH = 8  # Langfuse sign-up minimum


def run(cmd: list[str], stdin: str = "") -> str:
    result = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd[:4])}...\n{result.stderr.strip()}")
    return result.stdout.strip()


def bcrypt_hash(password: str) -> str:
    js = (
        f"const b=require('{BCRYPT}');let s='';process.stdin.on('data',d=>s+=d);"
        "process.stdin.on('end',()=>process.stdout.write(b.hashSync(s,12)));"
    )
    hashed = run(["docker", "exec", "-i", WEB, "node", "-e", js], stdin=password)
    if not re.fullmatch(r"\$2[ab]\$12\$[./A-Za-z0-9]{53}", hashed):
        sys.exit("unexpected hash format; nothing changed")
    return hashed


def main() -> None:
    env = INFRA_ENV.read_text(encoding="utf-8")
    email = re.search(r"^LANGFUSE_INIT_USER_EMAIL=(.+)$", env, re.M).group(1).strip()
    password = getpass.getpass(f"new password for {email}: ")
    if len(password) < MIN_LENGTH or password != password.strip() or "\n" in password:
        sys.exit(f"use at least {MIN_LENGTH} characters, no leading/trailing spaces")
    if getpass.getpass("repeat: ") != password:
        sys.exit("passwords differ; nothing changed")

    hashed = bcrypt_hash(password)
    # the hash only contains [$./A-Za-z0-9]: safe inside the SQL string literal
    sql = f"UPDATE users SET password = '{hashed}' WHERE email = '{email}';"
    if run(["docker", "exec", "-i", POSTGRES, "psql", "-U", "postgres", "-d", "postgres",
            "-t", "-c", sql]) != "UPDATE 1":  # fmt: skip
        sys.exit("user not found; nothing changed")

    new_env = re.sub(
        r"^LANGFUSE_INIT_USER_PASSWORD=.*$",
        lambda _: f"LANGFUSE_INIT_USER_PASSWORD={password}",
        env,
        flags=re.M,
    )
    INFRA_ENV.write_text(new_env, encoding="utf-8")
    print(f"password changed for {email}; infra/.env updated. Log in at http://localhost:3000")


if __name__ == "__main__":
    main()
