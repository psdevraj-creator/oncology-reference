"""
Oncology Interactive Handbook — Desktop Launcher
Double-click this file (or the .exe) to start the app.
Opens browser automatically. Works 100% offline.
"""

from __future__ import annotations

import os
import sys
import webbrowser
import threading
import time

os.environ["DESKTOP_MODE"] = "1"

_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "oncology_handbook.log")

_sys_stdout = sys.stdout
_sys_stderr = sys.stderr


def _setup_logging():
    log_fh = open(_LOG_FILE, "w", encoding="utf-8", buffering=1)
    sys.stdout = log_fh
    sys.stderr = log_fh
    return log_fh


def _restore_logging(log_fh):
    sys.stdout = _sys_stdout
    sys.stderr = _sys_stderr
    log_fh.close()


def _open_browser(port: int, delay: float = 2.0):
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main():
    log_fh = _setup_logging()
    try:
        port = int(os.environ.get("PORT", 8080))
        print(f"Oncology Interactive Handbook — Desktop Edition")
        print(f"Starting server on port {port}...")

        from app.main import app, server

        threading.Thread(target=_open_browser, args=(port, 1.5), daemon=True).start()

        print(f"Server ready. Opening browser to http://localhost:{port}")
        print("Close this window or click 'Stop Server' in the app to exit.")
        server.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        _restore_logging(log_fh)
        print(f"\nAn error occurred. Check {_LOG_FILE} for details.")
        input("Press Enter to exit...")
        sys.exit(1)
    finally:
        _restore_logging(log_fh)


if __name__ == "__main__":
    main()
