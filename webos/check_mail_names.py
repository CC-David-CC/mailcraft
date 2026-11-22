"""Check existing WebOS usernames before provisioning domain mailboxes."""
import argparse
from collections import Counter
from contextlib import closing
from pathlib import Path
import re
import sqlite3

USERNAME = re.compile(r"[a-z][a-z0-9]{2,27}")
RESERVED = {"admin", "root", "owner", "system"}
MAIL_ROLES = {"postmaster", "abuse", "security", "hostmaster", "webmaster",
              "dmarc", "quarantine", "mailer-daemon"}


def audit(path):
    uri = path.resolve(strict=True).as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        names = [row[0] for row in db.execute("SELECT username FROM accounts")]
    counts = Counter(name.casefold() for name in names)
    return {
        "accounts": len(names),
        "invalid": sum(not USERNAME.fullmatch(name) or name in RESERVED for name in names),
        "duplicate_folded_addresses": sum(1 for count in counts.values() if count > 1),
        "operational_alias_collisions": sum(counts[role] for role in MAIL_ROLES),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    result = audit(parser.parse_args().database)
    for label, count in result.items():
        print(f"{label}={count}")
    raise SystemExit(int(any(count for label, count in result.items() if label != "accounts")))
