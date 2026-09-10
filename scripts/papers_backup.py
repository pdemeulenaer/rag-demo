"""Local Compose catalogue backups; standard library only, no model dependencies."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "--project-directory", str(ROOT), "-f", str(ROOT / "docker-compose.yml")]


def run(*args, **kwargs):
    return subprocess.run([*COMPOSE, *args], cwd=ROOT, check=True, **kwargs)


def check_archive(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Backup must be a nonempty file")
    # Generate the entire SQL script into /dev/null INSIDE the container.
    # No --dbname: this reads/decompresses the archive but never executes SQL.
    with path.open("rb") as archive:
        run("exec", "-T", "postgres", "pg_restore", "--file=/dev/null",
            stdin=archive, stdout=subprocess.DEVNULL)


def backup(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Only the local catalogue service is needed; no API, worker or Airflow startup.
    run("--profile", "papers", "up", "-d", "--wait", "postgres")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    descriptor, name = tempfile.mkstemp(prefix=f"papers-{stamp}-", suffix=".dump.partial", dir=directory)
    partial = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            run("exec", "-T", "postgres", "pg_dump", "-U", "rag", "-d", "papers", "-Fc", stdout=output)
            output.flush()
            os.fsync(output.fileno())
        check_archive(partial)
        destination = partial.with_suffix("")
        # Publish only after validation; link is atomic and refuses to overwrite.
        os.link(partial, destination)
        partial.unlink()
        print(f"Backup created and archive checked: {destination}")
        print(f"Size: {destination.stat().st_size:,} bytes. PostgreSQL papers database only.")
        return destination
    except BaseException:
        print(f"Backup did not complete. Partial file retained (not a verified backup): {partial}", file=sys.stderr)
        raise


def list_backups(directory):
    archives = sorted((p for p in directory.glob("papers-*.dump") if p.is_file()), reverse=True)
    if not archives:
        print(f"No completed backups in {directory}")
    for path in archives:
        print(f"{path.stat().st_size:>12,} bytes  {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "list", "check"])
    args = parser.parse_args(argv)
    directory = Path(os.getenv("PAPERS_BACKUP_DIR") or Path.home() / "rag-demo-backups").expanduser().resolve()
    try:
        if args.action == "backup":
            backup(directory)
        elif args.action == "list":
            list_backups(directory)
        else:
            filename = os.getenv("PAPERS_BACKUP_FILE")
            if not filename:
                parser.error('Use make papers-backup-check FILE="/path/to/backup.dump"')
            path = Path(filename).expanduser().resolve()
            check_archive(path)
            print(f"Archive readable (no database restored): {path}")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Backup command failed ({type(exc).__name__}). Check Docker/PostgreSQL, disk space and file access.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
