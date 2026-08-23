import os
import subprocess
import sys
import threading
import time
import urllib.request
import webview
import uvicorn

from src.ui.server import app


def kill_existing_port_8000():
    """Frees port 8000 if occupied by a previous process on Windows."""
    try:
        cmd = 'powershell -Command "$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }"'
        subprocess.run(cmd, shell=True, capture_output=True)
        time.sleep(0.5)
    except Exception as e:
        print(f"[APP WINDOW] Notice freeing port 8000: {e}")


def run_server():
    """Runs the FastAPI server in background thread."""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def wait_for_server(url="http://127.0.0.1:8000/health", timeout=15):
    """Waits until server is up and returning HTTP 200."""
    start_time = time.time()
    print("[APP WINDOW] Waiting for JARVIS server to initialize...")
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Launcher"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    print("[APP WINDOW] Server is online and ready!")
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    # 1. Kill old server instances on port 8000
    kill_existing_port_8000()

    # 2. Dedicated storage path to avoid WebView2 0x800700AA file lock (black screen) bug
    storage_dir = os.path.join(os.path.expanduser("~"), ".jarvis_ui_storage")
    os.makedirs(storage_dir, exist_ok=True)

    # 3. Start server in daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 4. Wait until server is 100% online before launching GUI
    if not wait_for_server():
        print("[APP WINDOW ERROR] Server failed to start in time!")
        return

    # 5. Create PyWebView Window (Native Desktop Software)
    window = webview.create_window(
        title="JARVIS System Interface",
        url="http://127.0.0.1:8000",
        width=1100,
        height=720,
        resizable=True,
        frameless=False,
        easy_drag=True,
        background_color="#070a0f"
    )

    # 6. Start Desktop GUI loop with dedicated storage_path
    webview.start(storage_path=storage_dir, private_mode=False)


if __name__ == "__main__":
    main()
