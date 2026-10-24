"""Inicia API e interface locais; Ctrl+C encerra os dois processos."""

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    children = []
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            creationflags=creationflags,
        )
        children.append(api)
        for _ in range(60):
            if api.poll() is not None:
                raise RuntimeError("A API não iniciou. Confira artefatos e disponibilidade da porta 8000.")
            try:
                if requests.get("http://127.0.0.1:8000/health", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("A API demorou para iniciar.")
        ui = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "ui/app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                "8501",
            ],
            cwd=ROOT,
            creationflags=creationflags,
        )
        children.append(ui)
        for _ in range(60):
            if ui.poll() is not None:
                raise RuntimeError("A interface não iniciou. Confira a porta 8501.")
            try:
                if requests.get("http://127.0.0.1:8501/_stcore/health", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        if not args.no_browser:
            webbrowser.open("http://127.0.0.1:8501")
        print("Radar: http://127.0.0.1:8501 | Swagger: http://127.0.0.1:8000/docs", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()


if __name__ == "__main__":
    main()
