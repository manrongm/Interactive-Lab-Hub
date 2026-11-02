
import os
import signal
import subprocess
import tkinter as tk
from pathlib import Path

base = Path(__file__).resolve().parent
process = None


def start():
    global process

    if process is not None and process.poll() is None:
        return

    log = open(base / "desk_guardian_output.log", "a")

    try:
        process = subprocess.Popen(
            [
                str(base / ".venv/bin/python"),
                str(base / "overnight.py"),
                "--interval", "15"
            ],
            cwd=base,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    finally:
        log.close()

    status.config(text="Starting Night Mode...", fg="#ffcf81")
    root.after(3000, check_started)


def check_started():
    if process is not None and process.poll() is None:
        status.config(text="Night Mode Active", fg="#64d6a4")
    else:
        status.config(text="Unable to Start Monitoring", fg="#ff9999")


def stop():
    global process

    if process is None or process.poll() is not None:
        status.config(text="Night Mode Inactive", fg="white")
        return

    os.kill(process.pid, signal.SIGINT)
    status.config(text="Stopping...", fg="#ffcf81")
    root.after(1000, check_stopped)


def check_stopped():
    if process.poll() is None:
        root.after(1000, check_stopped)
    else:
        status.config(text="Night Mode Stopped", fg="white")


root = tk.Tk()
root.title("Desk Guardian")
root.geometry("420x300")
root.configure(bg="#152338")

tk.Label(
    root, text="Desk Guardian",
    font=("Arial", 24, "bold"),
    bg="#152338", fg="white"
).pack(pady=(30, 8))

tk.Label(
    root, text="Your overnight desk monitor",
    bg="#152338", fg="#b9cbe3"
).pack()

status = tk.Label(
    root, text="Night Mode Inactive",
    font=("Arial", 15, "bold"),
    bg="#152338", fg="white"
)
status.pack(pady=30)

tk.Button(
    root, text="Start Night Mode",
    command=start,
    font=("Arial", 13),
    bg="#3069a4", fg="white",
    width=22
).pack(pady=5)

tk.Button(
    root, text="Stop Monitoring",
    command=stop,
    width=22
).pack(pady=5)

root.mainloop()