"""Exercise backup file handling with mocked Docker commands; never touch live DBs."""
from pathlib import Path
import stat
import subprocess

import pytest

from scripts import papers_backup as module


@pytest.fixture
def docker(monkeypatch):
    calls = []
    def run(*args, **kwargs):
        calls.append(args)
        if "pg_dump" in args:
            kwargs["stdout"].write(b"fixture archive")
        if "pg_restore" in args:
            assert kwargs["stdin"].read() == b"fixture archive"
            assert args[-1] == "--file=/dev/null"
            assert "-d" not in args and "--dbname" not in args
    monkeypatch.setattr(module, "run", run)
    return calls


def test_unique_private_backups_are_checked_before_publication(tmp_path, docker):
    directory = tmp_path / "directory with spaces"
    first = module.backup(directory)
    second = module.backup(directory)
    assert first != second
    assert first.read_bytes() == second.read_bytes() == b"fixture archive"
    assert stat.S_IMODE(first.stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert not list(directory.glob("*.partial"))
    assert [call[3] for call in docker if "exec" in call] == ["pg_dump", "pg_restore"] * 2


@pytest.mark.parametrize("failure", ["start", "dump", "verify", "empty"])
def test_failure_never_publishes_a_completed_backup(tmp_path, monkeypatch, failure):
    existing = tmp_path / "papers-existing.dump"
    existing.write_bytes(b"keep this")
    def run(*args, **kwargs):
        if failure == "start" and "up" in args:
            raise subprocess.CalledProcessError(1, "docker")
        if "pg_dump" in args:
            if failure != "empty":
                kwargs["stdout"].write(b"partial or full")
            if failure == "dump":
                raise subprocess.CalledProcessError(1, "pg_dump")
        if "pg_restore" in args and failure == "verify":
            raise subprocess.CalledProcessError(1, "pg_restore")
    monkeypatch.setattr(module, "run", run)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        module.backup(tmp_path)
    assert list(tmp_path.glob("*.dump")) == [existing]
    assert existing.read_bytes() == b"keep this"


def test_listing_is_read_only_and_excludes_partials(tmp_path, monkeypatch, capsys):
    (tmp_path / "papers-complete.dump").write_bytes(b"archive")
    (tmp_path / "papers-failed.dump.partial").write_bytes(b"bad")
    monkeypatch.setattr(module, "run", lambda *a, **kw: pytest.fail("Listing must not run Docker"))
    module.list_backups(tmp_path)
    output = capsys.readouterr().out
    assert "papers-complete.dump" in output
    assert "partial" not in output
    module.list_backups(tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


def test_check_requires_explicit_file_and_never_restores(tmp_path, monkeypatch, docker):
    monkeypatch.delenv("PAPERS_BACKUP_FILE", raising=False)
    with pytest.raises(SystemExit):
        module.main(["check"])
    path = tmp_path / "backup.dump"
    path.write_bytes(b"fixture archive")
    monkeypatch.setenv("PAPERS_BACKUP_FILE", str(path))
    assert module.main(["check"]) == 0
    assert len(docker) == 1 and "pg_restore" in docker[0]
    assert path.read_bytes() == b"fixture archive"


def test_make_transmits_directory_with_spaces_without_shell_evaluation(tmp_path):
    root = Path(__file__).resolve().parents[2]
    directory = tmp_path / 'backups with spaces and "quotes"'
    # Listing needs neither Docker nor directory creation.
    result = subprocess.run(["make", "--no-print-directory", "papers-backups", f"BACKUP_DIR={directory}"],
        cwd=root, capture_output=True, text=True, check=True)
    assert str(directory) in result.stdout
    assert not directory.exists()
