"""Asset Pulse — Windows launcher.

Boots the Docker Compose stack (PostgreSQL + FastAPI + Nginx/React),
waits for the backend to report healthy, and opens the browser at
http://localhost:8080.

Designed to be packaged into `AssetPulseLauncher.exe` with PyInstaller
(see launcher/build_windows_exe.ps1). Also runnable as a plain script:
    python launcher/asset_pulse_launcher.py
"""

from __future__ import annotations

import os
import secrets
import shutil
import string
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "Asset Pulse"
FRONTEND_URL = "http://localhost:8080"
BACKEND_HEALTH_URLS = (
    "http://localhost:8080/api/health",
    "http://localhost:8000/api/health",
)
HEALTH_TIMEOUT_SEC = 240
HEALTH_POLL_INTERVAL_SEC = 3


def project_root() -> Path:
    """Folder that contains docker-compose.yml.

    When frozen with PyInstaller (`--onefile`) the executable lives next to
    the project files, so the parent of the .exe is the project root.
    During `python launcher/asset_pulse_launcher.py` development runs the
    parent of *this* file's parent is the repo root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def banner() -> None:
    print("=" * 64)
    print(f"  {APP_NAME} — local launcher")
    print("=" * 64)


def info(msg: str) -> None:
    print(f"[INFO]  {msg}")


def warn(msg: str) -> None:
    print(f"[WARN]  {msg}")


def err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def run(cmd: list[str], cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=True,
        text=True,
    )


def docker_available() -> tuple[bool, str]:
    """Return (ok, message). Verifies CLI presence + daemon reachability."""
    if shutil.which("docker") is None:
        return False, "Docker CLI not found on PATH. Install Docker Desktop."
    proc = run(["docker", "--version"])
    if proc.returncode != 0:
        return False, "`docker --version` failed. Is Docker Desktop installed?"
    proc = run(["docker", "compose", "version"])
    if proc.returncode != 0:
        return False, "`docker compose version` failed. Update Docker Desktop (Compose v2 required)."
    proc = run(["docker", "info"])
    if proc.returncode != 0:
        return False, "Docker daemon is not running. Start Docker Desktop and try again."
    return True, "Docker is available."


def generate_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_env_file(root: Path) -> None:
    env_path = root / ".env"
    example_path = root / ".env.docker.example"
    if env_path.exists():
        info(".env already present — leaving it untouched.")
        return
    if not example_path.exists():
        warn(".env.docker.example missing; cannot bootstrap .env. Stack may fail to start.")
        return
    info("No .env found — creating one from .env.docker.example with a generated POSTGRES_PASSWORD.")
    password = generate_password()
    lines: list[str] = []
    replaced = False
    for raw in example_path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("POSTGRES_PASSWORD="):
            lines.append(f"POSTGRES_PASSWORD={password}")
            replaced = True
        else:
            lines.append(raw)
    if not replaced:
        lines.append(f"POSTGRES_PASSWORD={password}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    info(f"Wrote {env_path} (POSTGRES_PASSWORD generated; edit if you need a custom value).")


def docker_compose_up(root: Path) -> int:
    info("Starting Docker Compose stack (this can take a few minutes on first run)...")
    # Stream output live instead of capturing — users want to see build progress.
    proc = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=str(root),
    )
    return proc.returncode


def wait_for_health() -> bool:
    info("Waiting for backend health check...")
    deadline = time.monotonic() + HEALTH_TIMEOUT_SEC
    last_err: str | None = None
    while time.monotonic() < deadline:
        for url in BACKEND_HEALTH_URLS:
            try:
                with urllib.request.urlopen(url, timeout=4) as resp:
                    if 200 <= resp.status < 300:
                        info(f"Backend healthy at {url}")
                        return True
            except urllib.error.URLError as exc:
                last_err = f"{url}: {exc.reason}"
            except Exception as exc:  # noqa: BLE001
                last_err = f"{url}: {exc}"
        time.sleep(HEALTH_POLL_INTERVAL_SEC)
    if last_err:
        warn(f"Last health probe error: {last_err}")
    return False


def open_browser() -> None:
    info(f"Opening {FRONTEND_URL} in your default browser...")
    try:
        webbrowser.open(FRONTEND_URL, new=2)
    except Exception as exc:  # noqa: BLE001
        warn(f"Could not auto-open browser: {exc}. Visit {FRONTEND_URL} manually.")


def print_help(root: Path) -> None:
    print()
    print("-" * 64)
    print("  Stack is running.")
    print(f"  App:        {FRONTEND_URL}")
    print("  Backend:    http://localhost:8000/api/health")
    print()
    print("  Useful commands (run from a terminal in this folder):")
    print(f"    cd \"{root}\"")
    print("    docker compose ps                 # show service status")
    print("    docker compose logs -f backend    # tail backend logs")
    print("    docker compose logs -f frontend   # tail frontend logs")
    print("    docker compose down               # stop the stack (data preserved)")
    print("    docker compose down -v            # stop AND DELETE the database volume")
    print("                                       (warning: erases all scenarios/assets)")
    print("-" * 64)
    print()


def pause_before_exit() -> None:
    """Keep the console window open when launched by double-click on Windows."""
    if os.environ.get("ASSET_PULSE_NO_PAUSE"):
        return
    try:
        input("Press Enter to close this window...")
    except EOFError:
        pass


def main() -> int:
    banner()
    root = project_root()
    info(f"Project folder: {root}")

    if not (root / "docker-compose.yml").exists():
        err("docker-compose.yml not found next to the launcher.")
        err("Make sure the executable is in the Asset Pulse distribution folder.")
        pause_before_exit()
        return 2

    ok, msg = docker_available()
    if not ok:
        err(msg)
        err("Install Docker Desktop from https://www.docker.com/products/docker-desktop/")
        err("then start it, wait for the whale icon to settle, and re-run this launcher.")
        pause_before_exit()
        return 3

    info(msg)
    ensure_env_file(root)

    rc = docker_compose_up(root)
    if rc != 0:
        err(f"`docker compose up` exited with status {rc}.")
        err("Run `docker compose logs` in this folder to investigate.")
        pause_before_exit()
        return rc

    if wait_for_health():
        open_browser()
    else:
        warn("Backend did not report healthy within the timeout.")
        warn(f"Try opening {FRONTEND_URL} anyway, or check `docker compose logs backend`.")

    print_help(root)
    pause_before_exit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
