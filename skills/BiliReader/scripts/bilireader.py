#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_REPO = "https://github.com/fool123/BiliReader_CodexSkill.git"
DONE = {"succeeded", "failed"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="bilireader", description="Install and use BiliReader video analysis.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("install", help="Clone/update the runtime repo and install backend dependencies.")
    sub.add_parser("serve", help="Start the local FastAPI backend.")

    status = sub.add_parser("status", help="List tasks or inspect a task.")
    status.add_argument("task_id", nargs="?")

    analyze = sub.add_parser("analyze", help="Analyze a video URL or local media file.")
    analyze.add_argument("source")
    analyze.add_argument("--platform")
    analyze.add_argument("--note-style", default="detailed")
    analyze.add_argument("--model")
    analyze.add_argument("--timeout", type=int, default=1800)
    analyze.add_argument("--interval", type=float, default=2.0)

    for name in ("note", "transcript"):
        cmd = sub.add_parser(name, help=f"Print task {name}.")
        cmd.add_argument("task_id")

    args = parser.parse_args()
    try:
        return {
            "install": install,
            "serve": serve,
            "status": status_cmd,
            "analyze": analyze_cmd,
            "note": note_cmd,
            "transcript": transcript_cmd,
        }[args.command](args)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def install(args: argparse.Namespace) -> int:
    repo = runtime_repo()
    repo_url = os.environ.get("BILIREADER_REPO_URL", DEFAULT_REPO)
    repo.parent.mkdir(parents=True, exist_ok=True)

    if (repo / ".git").exists():
        run(["git", "-C", str(repo), "fetch", "--all", "--tags"])
        ref = os.environ.get("BILIREADER_REF")
        if ref:
            run(["git", "-C", str(repo), "checkout", ref])
        else:
            default_ref = output(["git", "-C", str(repo), "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"])
            if default_ref:
                run(["git", "-C", str(repo), "checkout", "-B", default_ref.rsplit("/", 1)[-1], default_ref])
            else:
                run(["git", "-C", str(repo), "pull", "--ff-only"])
    elif repo.exists() and any(repo.iterdir()):
        raise RuntimeError(f"runtime repo exists but is not a git checkout: {repo}")
    else:
        run(["git", "clone", repo_url, str(repo)])
        if os.environ.get("BILIREADER_REF"):
            run(["git", "-C", str(repo), "checkout", os.environ["BILIREADER_REF"]])

    backend = backend_dir()
    venv = backend / ".venv"
    if not venv.exists():
        run([sys.executable, "-m", "venv", str(venv)])
    run([str(python_bin()), "-m", "pip", "install", "-r", str(backend / "requirements.txt")])
    print(f"installed: {backend}")
    return 0


def serve(args: argparse.Namespace) -> int:
    backend = require_backend()
    env = os.environ.copy()
    port = str(port_number())
    print(f"serving: http://127.0.0.1:{port}", file=sys.stderr)
    return subprocess.call(
        [str(python_bin()), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port],
        cwd=backend,
        env=env,
    )


def status_cmd(args: argparse.Namespace) -> int:
    path = f"/api/tasks/{args.task_id}" if args.task_id else "/api/tasks"
    print(json.dumps(api_json("GET", path), ensure_ascii=False, indent=2))
    return 0


def analyze_cmd(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser()
    if source.exists():
        created = create_local_file_task(source, args.note_style, args.model)
    else:
        created = api_json(
            "POST",
            "/api/tasks",
            {
                "url": args.source,
                "platform": args.platform,
                "note_style": args.note_style,
                "model": args.model,
            },
        )

    task_id = created["task_id"]
    print(f"task_id: {task_id}", file=sys.stderr)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        task = api_json("GET", f"/api/tasks/{task_id}")
        print(f"{task['status']}: {task.get('message') or ''}", file=sys.stderr)
        if task["status"] in DONE:
            if task["status"] == "failed":
                raise RuntimeError(task.get("message") or "task failed")
            print(api_json("GET", f"/api/tasks/{task_id}/note")["markdown"])
            return 0
        time.sleep(args.interval)
    raise RuntimeError(f"timeout waiting for task {task_id}")


def note_cmd(args: argparse.Namespace) -> int:
    print(api_json("GET", f"/api/tasks/{args.task_id}/note")["markdown"])
    return 0


def transcript_cmd(args: argparse.Namespace) -> int:
    data = api_json("GET", f"/api/tasks/{args.task_id}/transcript")
    print(data.get("full_text") or "\n".join(s["text"] for s in data.get("segments", [])))
    return 0


def create_local_file_task(path: Path, note_style: str, model: str | None) -> dict:
    boundary = f"----BiliReader{uuid.uuid4().hex}"
    fields = [("note_style", note_style)]
    if model:
        fields.append(("model", model))
    body = bytearray()
    for name, value in fields:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        (
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
    )
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return api_json("POST", "/api/tasks/local-file", bytes(body), f"multipart/form-data; boundary={boundary}")


def api_json(method: str, path: str, payload: dict | bytes | None = None, content_type: str = "application/json") -> dict:
    data = None
    headers = {}
    if isinstance(payload, dict):
        payload = {k: v for k, v in payload.items() if v is not None}
        data = json.dumps(payload).encode()
        headers["Content-Type"] = content_type
    elif isinstance(payload, bytes):
        data = payload
        headers["Content-Type"] = content_type
    request = Request(base_url() + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"backend is not reachable at {base_url()}; run `bilireader.py serve` first") from exc


def base_url() -> str:
    return f"http://127.0.0.1:{port_number()}"


def port_number() -> int:
    try:
        return int(os.environ.get("BILIREADER_PORT", "8787"))
    except ValueError as exc:
        raise RuntimeError("BILIREADER_PORT must be a number") from exc


def runtime_repo() -> Path:
    root = Path(os.environ.get("BILIREADER_RUNTIME_DIR", "~/.codex/bilireader-runtime")).expanduser()
    return root / "repo"


def backend_dir() -> Path:
    repo = runtime_repo()
    candidates = [repo / "video-analyzer" / "backend", repo / "backend"]
    for path in candidates:
        if (path / "app" / "main.py").exists() and (path / "requirements.txt").exists():
            return path
    raise RuntimeError(f"backend not found under {repo}; expected video-analyzer/backend or backend")


def require_backend() -> Path:
    backend = backend_dir()
    if not python_bin().exists():
        raise RuntimeError("backend .venv not found; run `bilireader.py install` first")
    return backend


def python_bin() -> Path:
    return backend_dir() / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"command not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"command failed: {' '.join(cmd)}") from exc


def output(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise RuntimeError(f"command not found: {cmd[0]}") from exc
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
