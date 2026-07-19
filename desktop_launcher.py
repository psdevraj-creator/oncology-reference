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


def _show_fatal_error(msg: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "Oncology Handbook — Fatal Error", 0x10)
    except Exception:
        pass


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
        import traceback
        err_msg = f"An error occurred starting the Oncology Handbook:\n\n{type(e).__name__}: {e}\n\nDetails written to: {_LOG_FILE}"
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        traceback.print_exc()
        _restore_logging(log_fh)
        _show_fatal_error(err_msg)
        sys.exit(1)
    finally:
        _restore_logging(log_fh)


if __name__ == "__main__":
    main()
