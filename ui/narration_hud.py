"""Small always-on-top overlay (like a volume OSD) showing the latest narration. Optional:
degrades silently if tkinter/display isn't available (e.g. headless test runs)."""
import queue
import threading

_queue = queue.Queue()
_available = True


def _run_hud():
    try:
        import tkinter as tk
    except Exception:
        global _available
        _available = False
        return

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.0)
    except Exception:
        pass

    width, height = 460, 54
    x = (root.winfo_screenwidth() - width) // 2
    y = root.winfo_screenheight() - 140
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(bg="#1e1e1e")

    label = tk.Label(root, text="", fg="white", bg="#1e1e1e", font=("Segoe UI", 12), wraplength=420)
    label.pack(expand=True, fill="both")

    hide_job = [None]

    def show_text(text):
        label.config(text=text)
        try:
            root.attributes("-alpha", 0.92)
        except Exception:
            pass
        if hide_job[0]:
            root.after_cancel(hide_job[0])
        hide_job[0] = root.after(3000, lambda: root.attributes("-alpha", 0.0))

    def poll():
        try:
            while True:
                show_text(_queue.get_nowait())
        except queue.Empty:
            pass
        root.after(100, poll)

    root.after(100, poll)
    root.mainloop()


def start_hud():
    threading.Thread(target=_run_hud, daemon=True).start()


def show(text):
    if _available:
        _queue.put(text)


if __name__ == "__main__":
    import time
    start_hud()
    time.sleep(1)
    show("Opening Chrome")
    time.sleep(4)
