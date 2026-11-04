"""
Dump the live HRMS MySQL database on the Hostinger VPS into a dated file.

Run this ON the Hostinger server (crontab), not on your laptop.
On the server it reads /root/tfshrms/hrms-backend/.env — that file already has
the live database (mytfs on 127.0.0.1). It does not use your Windows .env.

Filename example:
    hrms_mytfs_backup_2026-11-08_Sunday.sql.gz

Usage on the server:
    python backup_hrms_db.py --dir /root/hrms-db-backups
    python backup_hrms_db.py --dir /root/hrms-db-backups --keep 8

Crontab — 2nd Sunday of every month at 02:00 IST:
    0 2 8-14 * 0 cd /root/tfshrms/hrms-backend && venv/bin/python backup_hrms_db.py --dir /root/hrms-db-backups --keep 8 >> backup_hrms_db_cron.log 2>&1
"""

from __future__ import annotations

import argparse
import gzip
import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(dotenv_path=HERE / ".env")

logging.basicConfig(
    filename=HERE / "backup_hrms_db.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

IST = ZoneInfo("Asia/Kolkata")


def mysqldump_bin() -> str:
    found = shutil.which("mysqldump")
    if found:
        return found
    extras = [
        Path(r"C:\xampp\mysql\bin\mysqldump.exe"),
        Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"),
        Path("/usr/bin/mysqldump"),
        Path("/usr/local/bin/mysqldump"),
    ]
    for path in extras:
        if path.is_file():
            return str(path)
    raise FileNotFoundError(
        "mysqldump was not found. Install MySQL client tools or add mysqldump to PATH."
    )


def write_client_cnf(host: str, port: str, user: str, password: str) -> str:
    fd, path = tempfile.mkstemp(prefix="hrms_backup_", suffix=".cnf")
    os.close(fd)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    Path(path).write_text(
        "[client]\n"
        f"host={host}\n"
        f"port={port}\n"
        f"user={user}\n"
        f"password={password}\n",
        encoding="utf-8",
    )
    return path


def prune_old_backups(folder: Path, prefix: str, keep: int) -> None:
    if keep <= 0:
        return
    files = sorted(
        [p for p in folder.iterdir() if p.is_file() and p.name.startswith(prefix)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[keep:]:
        old.unlink()
        logging.info("removed old backup %s", old)
        print(f"removed old backup {old}")


def run_backup(folder: Path, gzip_file: bool, keep: int) -> Path:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    database = os.getenv("DB_DATABASE", "mytfs")
    user = os.getenv("DB_USERNAME", "root")
    password = os.getenv("DB_PASSWORD") or ""

    folder.mkdir(parents=True, exist_ok=True)

    now = datetime.now(IST)
    stamp = now.strftime("%Y-%m-%d_%A")
    prefix = f"hrms_{database}_backup_"
    filename = f"{prefix}{stamp}.sql"
    if gzip_file:
        filename += ".gz"
    dest = folder / filename

    dump = mysqldump_bin()
    cnf = write_client_cnf(host, port, user, password)
    cmd = [
        dump,
        f"--defaults-extra-file={cnf}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        database,
    ]
    try:
        logging.info("starting dump of %s:%s/%s to %s", host, port, database, dest)
        print(f"dumping {host}:{port}/{database}")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None
        if gzip_file:
            with gzip.open(dest, "wb") as out:
                shutil.copyfileobj(proc.stdout, out)
        else:
            with dest.open("wb") as out:
                shutil.copyfileobj(proc.stdout, out)
        _, err = proc.communicate()
        if proc.returncode != 0:
            dest.unlink(missing_ok=True)
            message = (err or b"").decode("utf-8", errors="replace").strip() or "mysqldump failed"
            raise RuntimeError(message)
        size_mb = dest.stat().st_size / (1024 * 1024)
        logging.info("backup written %s (%.1f MB)", dest, size_mb)
        print(f"backup written: {dest} ({size_mb:.1f} MB)")
        prune_old_backups(folder, prefix, keep)
        return dest
    finally:
        Path(cnf).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dir",
        default=os.getenv("HRMS_BACKUP_DIR", str(HERE / "db_backups")),
        help="folder to save the dump (created if missing)",
    )
    parser.add_argument("--no-gzip", action="store_true", help="write a plain .sql file instead of .sql.gz")
    parser.add_argument(
        "--keep",
        type=int,
        default=int(os.getenv("HRMS_BACKUP_KEEP", "0")),
        help="keep only the newest N dumps in that folder (0 = keep all)",
    )
    args = parser.parse_args()
    try:
        run_backup(Path(args.dir).expanduser(), gzip_file=not args.no_gzip, keep=args.keep)
        return 0
    except Exception:
        logging.exception("HRMS database backup failed")
        print("backup failed; see backup_hrms_db.log", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
