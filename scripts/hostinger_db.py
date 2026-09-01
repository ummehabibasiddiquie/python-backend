"""Connect to Hostinger (or any MySQL) from CMD without phpMyAdmin."""

from __future__ import annotations

import argparse
import getpass
import os

import mysql.connector


def parse_db_args(description: str) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--host", default=os.getenv("DB_HOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    p.add_argument("--user", default=os.getenv("DB_USERNAME", "root"))
    p.add_argument("--database", default=os.getenv("DB_DATABASE", "tfs_hrms"))
    p.add_argument(
        "--password",
        default=None,
        help="Optional. If omitted, you will be prompted (safer than typing in the command).",
    )
    return p.parse_args()


def connect(args: argparse.Namespace):
    password = args.password
    if password is None:
        env_pass = os.getenv("DB_PASSWORD")
        if args.host in ("localhost", "127.0.0.1") and env_pass is not None:
            password = env_pass
        else:
            password = getpass.getpass(f"MySQL password for {args.user}@{args.host}: ")
    conn = mysql.connector.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password or "",
        database=args.database,
    )
    print(f"connected {args.user}@{args.host}:{args.port}/{args.database}")
    return conn
