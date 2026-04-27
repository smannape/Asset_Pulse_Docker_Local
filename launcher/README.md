# Asset Pulse Windows launcher

Source for `AssetPulseLauncher.exe` — a single-file Windows launcher that
brings up the Docker Compose stack and opens the app in a browser.

- `asset_pulse_launcher.py` — launcher source (stdlib-only Python 3.10+).
- `build_windows_exe.ps1` — PyInstaller build script (run on Windows).
- `AssetPulseLauncher.bat` — fallback launcher when the .exe isn't shipped;
  invokes the Python source directly.

End-user instructions and full troubleshooting guide live in
[`../docs/windows-executable-distribution.pplx.md`](../docs/windows-executable-distribution.pplx.md).

The launcher resolves `docker-compose.yml` relative to its own location, so
the .exe (or .bat) must be placed in / called from the Asset Pulse project
folder that contains `docker-compose.yml`.
