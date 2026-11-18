"""Run a repeatable live acceptance check with disposable operational state."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request(url: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as response:
        content = response.read().decode()
        return (
            json.loads(content)
            if response.headers.get_content_type() == "application/json"
            else content
        )


def wait_ready(url: str, process: subprocess.Popen) -> None:
    for _ in range(150):
        if process.poll() is not None:
            raise RuntimeError(f"Server exited before {url} was ready")
        try:
            request(url)
            return
        except (OSError, urllib.error.URLError):
            time.sleep(0.2)
    raise TimeoutError(f"Server did not become ready: {url}")


def main() -> None:
    api_port, web_port = free_port(), free_port()
    api_url, web_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{web_port}"
    with tempfile.TemporaryDirectory(prefix="geoops-verify-") as directory:
        env = {
            **os.environ,
            "APP_ENV": "test",
            "APPROVAL_STORE": "sqlite",
            "STATE_DATABASE_PATH": str(Path(directory) / "state.sqlite3"),
            "MODEL_PROVIDER": "local",
            "MAPS_PROVIDER": "mock",
            "EVENT_BUS": "memory",
            "CATALOG_PROVIDER": "json",
            "DOCUMENT_PROVIDER": "local",
            "VECTOR_PROVIDER": "memory",
            "EMBEDDING_PROVIDER": "local",
            "ANALYTICS_PROVIDER": "local",
            "WORKER_ENABLED": "true",
            "WORKER_POLL_SECONDS": "0.1",
            "API_TOKEN": "",
            "NEXT_PUBLIC_API_BASE_URL": "",
            "API_INTERNAL_BASE_URL": api_url,
            "API_USE_GOOGLE_ID_TOKEN": "false",
            "GEOOPS_API_TOKEN": "",
        }
        with open(Path(directory) / "servers.log", "w+") as log:
            api = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "geoops_api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            web = subprocess.Popen(
                [
                    "node",
                    "node_modules/next/dist/bin/next",
                    "dev",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(web_port),
                ],
                cwd=ROOT / "apps/web",
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                wait_ready(api_url + "/health", api)
                wait_ready(web_url + "/health", web)
                chat = request(
                    web_url + "/api/chat", {"message": "Assign James Chen to ticket 184"}
                )
                approval_id = chat["recommended_action"]["approval_id"]
                assert chat["requires_approval"]
                request(
                    web_url + f"/api/approvals/{approval_id}/approve",
                    {"decided_by": "acceptance-test"},
                )
                for _ in range(100):
                    proposal = request(web_url + f"/api/approvals/{approval_id}")
                    if proposal["status"] == "executed":
                        break
                    time.sleep(0.1)
                assert proposal["status"] == "executed", proposal
                ticket = request(web_url + "/api/tickets/184")
                assert ticket["assignments"][0]["technician_id"] == "T-001"
                run = request(web_url + "/api/evaluations/run", {})
                assert run["passed"], run
                for route, expected in (
                    ("/agent", "Agent workspace"),
                    ("/approvals", "Approval queue"),
                    ("/evaluations", "Evaluation runs"),
                ):
                    assert expected in request(web_url + route)
                print(
                    json.dumps(
                        {
                            "health": "ok",
                            "proxy": "ok",
                            "dispatch": proposal["status"],
                            "evaluation_cases": len(run["results"]),
                            "evaluation_passed": run["passed"],
                            "rendered_pages": 3,
                        }
                    )
                )
            except BaseException:
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                for process in (web, api):
                    process.terminate()
                for process in (web, api):
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    main()
