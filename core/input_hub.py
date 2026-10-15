"""Single stdin reader so typed commands and typed YES-confirmations never fight over input()."""
import queue
import sys
import threading


class InputHub:
    def __init__(self):
        self.line_q = queue.Queue()
        self.confirm_q = queue.Queue()
        self.confirming = threading.Event()
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            line = sys.stdin.readline()
            if line == "":
                self.line_q.put(None)
                return
            line = line.rstrip("\r\n")
            (self.confirm_q if self.confirming.is_set() else self.line_q).put(line)

    def next_line(self, timeout=0.2):
        """Returns a line, None on EOF, or raises queue.Empty on timeout."""
        return self.line_q.get(timeout=timeout)

    def confirm(self, prompt, timeout=60):
        while not self.confirm_q.empty():
            self.confirm_q.get_nowait()
        print(f"{prompt} Type YES to confirm: ", end="", flush=True)
        self.confirming.set()
        try:
            answer = self.confirm_q.get(timeout=timeout)
        except queue.Empty:
            print("(timed out - cancelled)")
            return False
        finally:
            self.confirming.clear()
        return answer.strip().upper() == "YES"
