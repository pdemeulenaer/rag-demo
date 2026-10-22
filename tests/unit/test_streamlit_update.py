"""Exercise the Make target with fake Docker; no containers or .env access."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("docker_exit", [0, 7])
@pytest.mark.parametrize("target", ["ui-update", "update-ui", "streamlit-update"])
def test_streamlit_update_is_ui_only_and_reports_success_only_after_docker(tmp_path, docker_exit, target):
    docker = tmp_path / "docker"
    docker.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "print('DOCKER_CALL=' + json.dumps(sys.argv[1:]))\n"
        "sys.exit(int(os.environ['FAKE_DOCKER_EXIT']))\n"
    )
    docker.chmod(0o700)
    result = subprocess.run(
        ["make", "--no-print-directory", target],
        cwd=Path(__file__).resolve().parents[2],
        env=os.environ | {"PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
                          "FAKE_DOCKER_EXIT": str(docker_exit)},
        capture_output=True, text=True,
    )
    calls = [json.loads(line.removeprefix("DOCKER_CALL="))
             for line in result.stdout.splitlines() if line.startswith("DOCKER_CALL=")]
    assert calls == [["compose", "up", "-d", "--build", "--no-deps", "--force-recreate",
                      "--wait", "streamlit-app"]]
    assert (result.returncode == 0) == (docker_exit == 0)
    assert ("Streamlit updated: http://localhost:8501" in result.stdout) == (docker_exit == 0)


@pytest.mark.parametrize("old,new", [
    ("build-ui", "ui-build"), ("run-ui", "ui-run"),
    ("tag-ui", "ui-tag"), ("push-ui", "ui-push"),
    ("build-fastapi", "fastapi-build"), ("run-fastapi", "fastapi-run"),
    ("tag-fastapi", "fastapi-tag"), ("push-fastapi", "fastapi-push"),
])
def test_image_aliases_keep_the_same_docker_commands(old, new):
    root = Path(__file__).resolve().parents[2]
    def dry_run(target):
        return subprocess.run(
            ["make", "--no-print-directory", "--dry-run", target], cwd=root,
            capture_output=True, text=True, check=True,
        ).stdout
    assert dry_run(old) == dry_run(new)
