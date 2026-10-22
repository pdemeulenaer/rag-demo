"""Credential reminder with fake Docker and synthetic secrets only; no .env read."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("password", ["synthetic-only", "pw/a b$HOME;[]"])
@pytest.mark.parametrize("docker_exit", [0, 7])
def test_kg_password_uses_container_auth_and_does_not_mask_failure(tmp_path, password, docker_exit):
    docker = tmp_path / "docker"
    docker.write_text(
        f"#!{sys.executable}\n"
        "import os, subprocess, sys\n"
        "assert sys.argv[1:-1] == ['compose','-f','docker-compose.kg.yml','--profile','kg',"
        "'exec','-T','neo4j','sh','-c']\n"
        "failure = int(os.environ['FAKE_DOCKER_EXIT'])\n"
        "if failure: sys.exit(failure)\n"
        "env = os.environ | {'NEO4J_AUTH': os.environ['FAKE_NEO4J_AUTH']}\n"
        "sys.exit(subprocess.run(['sh','-c',sys.argv[-1]], env=env).returncode)\n"
    )
    docker.chmod(0o700)
    result = subprocess.run(
        ["make", "--no-print-directory", "kg-password"],
        cwd=Path(__file__).resolve().parents[2],
        env=os.environ | {"PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
                          "FAKE_DOCKER_EXIT": str(docker_exit),
                          "FAKE_NEO4J_AUTH": "neo4j/" + password},
        capture_output=True, text=True,
    )
    assert (result.returncode == 0) == (docker_exit == 0)
    if docker_exit == 0:
        assert result.stdout.splitlines()[:2] == ["Username: neo4j", "Password: " + password]
        assert "http://localhost:7474" in result.stdout
        assert "does not reset" in result.stdout and "Do not share" in result.stdout
    else:
        assert "Password:" not in result.stdout
        assert "Neo4j Browser:" not in result.stdout
