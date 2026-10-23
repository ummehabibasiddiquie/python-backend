"""
Build the password-protected Credentials Register (handover document 06).

Usage (from backend-api, in your own terminal):
    python docs/handover/build_credentials_register.py
You are asked for the file password twice; it is never shown or stored.
Output: docs/handover/confidential/06 - Credentials Register (password protected).docx

Values written as "{backend-api:SMTP_PASS}" in handover_content_c.py are copied from that repository's
local .env. Nothing is printed except setting names that could not be found.
"""

from __future__ import annotations

import copy
import getpass
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # folder holding backend-api and qc-backend
sys.path.insert(0, str(HERE))

from build_handover_docs import build  # noqa: E402
from handover_content_c import CREDENTIALS_REGISTER  # noqa: E402

OUT = HERE / "confidential" / "06 - Credentials Register (password protected).docx"
MARKER = re.compile(r"\{([\w.-]+):(\w+)\}")

# Word encrypts the file; the password reaches PowerShell only through its environment.
WORD_ENCRYPT = r"""
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($env:REG_SRC)
    $doc.Password = $env:REG_PASSWORD
    $doc.SaveAs2($env:REG_DST, 16)
    $doc.Close()
} finally {
    $word.Quit()
}
"""


def read_env(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def fill(spec: dict) -> tuple[dict, list[str]]:
    envs: dict[str, dict[str, str]] = {}
    missing: list[str] = []

    def resolve(match: re.Match) -> str:
        repo, key = match.group(1), match.group(2)
        if repo not in envs:
            envs[repo] = read_env(ROOT / repo / ".env")
        value = envs[repo].get(key, "")
        if not value:
            missing.append(f"{repo}:{key}")
        return value

    def walk(item):
        if isinstance(item, str):
            return MARKER.sub(resolve, item)
        if isinstance(item, list):
            return [walk(x) for x in item]
        if isinstance(item, tuple):
            return tuple(walk(x) for x in item)
        return item

    filled = copy.deepcopy(spec)
    filled["blocks"] = walk(filled["blocks"])
    return filled, missing


def ask_password() -> str:
    from_env = os.environ.get("HANDOVER_REGISTER_PASSWORD")
    if from_env:
        return from_env
    while True:
        first = getpass.getpass("File password (min 8 characters): ")
        if len(first) < 8:
            print("Too short, try again.")
            continue
        if getpass.getpass("Repeat the password: ") != first:
            print("The two passwords differ, try again.")
            continue
        return first


def main() -> int:
    password = ask_password()
    spec, missing = fill(CREDENTIALS_REGISTER)

    work = Path(tempfile.mkdtemp(prefix="hrms_reg_"))
    plain = work / "register.docx"
    try:
        build(spec, plain)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        if OUT.exists():
            OUT.unlink()
        env = dict(os.environ, REG_SRC=str(plain), REG_DST=str(OUT.resolve()), REG_PASSWORD=password)
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", WORD_ENCRYPT],
            env=env, check=True, capture_output=True,
        )
    finally:
        if plain.exists():
            plain.write_bytes(b"\0" * plain.stat().st_size)
        shutil.rmtree(work, ignore_errors=True)

    with OUT.open("rb") as fh:
        protected = fh.read(4) == b"\xd0\xcf\x11\xe0"
    print("wrote", OUT.relative_to(ROOT))
    print("password protected:", "yes" if protected else "NO - do not share this file")
    if missing:
        print("not found in local .env (left empty):", ", ".join(sorted(set(missing))))
    return 0 if protected else 1


if __name__ == "__main__":
    sys.exit(main())
