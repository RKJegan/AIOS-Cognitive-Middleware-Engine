import queue
import subprocess
import threading
import time

from config.settings import Settings
from core.logger import get_logger
from core.narrator import narrate, add_sink
from core import confirm
from core.input_hub import InputHub
from core.middleware_core import MiddlewareCore
from core.step_executor import StepExecutor
from core.voice_output import speak
from core.hotkey_listener import start_hotkey_listener
from core.wake_word import WakeWordListener
from ui.narration_hud import start_hud, show as hud_show

from ai.task_planner import TaskPlanner
from ai.llm_brain import LLMBrain
from ai.stt_engine import STTEngine

from security.safety_layer import SafetyLayer
from security.credential_vault import CredentialVault

from priority1_core.app_controller import AppController
from priority1_core.file_controller import FileController
from priority1_core.browser_controller import BrowserController
from priority1_core.system_monitor import SystemMonitor
from priority1_core.workflow_manager import WorkflowManager

from priority2_strong.system_control import SystemControl
from priority2_strong.notification_system import NotificationSystem
from priority2_strong.schedule_manager import ScheduleManager
from priority2_strong.clipboard_manager import ClipboardManager
from priority2_strong.screenshot_ocr import ScreenshotOCR
from priority2_strong.developer_operations import DeveloperOperations
from priority2_strong.web_automation import WebAutomation
from priority2_strong.code_agent import CodeAgent

from priority3_advanced.document_controller import DocumentController
from priority3_advanced.text_assistant import TextAssistant
from priority3_advanced.multi_monitor import MultiMonitor
from priority3_advanced.email_controller import EmailController

from plugins.plugin_system import PluginSystem
from memory.memory_manager import MemoryManager

log = get_logger()
EXIT_WORDS = {"exit", "quit", "q", "bye", "goodbye"}
STOP_LISTENING_WORDS = {"stop listening", "cancel", "never mind", "nothing", "that's all", "okay stop"}


def ensure_ollama_running(settings):
    import requests
    try:
        requests.get(f"{settings.ollama_host}/api/tags", timeout=2)
        return None
    except requests.exceptions.RequestException:
        print("Starting Ollama...")
        try:
            proc = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("(Ollama executable not found on PATH - start it yourself if this hangs)")
            return None
        time.sleep(3)
        return proc


class System:
    def __init__(self):
        self.settings = Settings.load()
        self.safety = SafetyLayer(self.settings)
        self.brain = LLMBrain(self.settings)
        self.planner = TaskPlanner(self.brain)

        self.ac = AppController(self.settings, self.safety)
        self.fc = FileController(self.safety)
        self.bc = BrowserController(self.settings, safety=self.safety)
        self.sm = SystemMonitor()
        self.sc = SystemControl(self.safety)
        self.ns = NotificationSystem()
        self.cm = ClipboardManager()
        self.ocr = ScreenshotOCR(self.settings)
        self.dev = DeveloperOperations(safety=self.safety)
        self.web = WebAutomation()
        self.code_agent = CodeAgent(self.settings, self.safety)
        self.docs = DocumentController()
        self.text_assistant = TextAssistant(self.brain, self.docs)
        self.monitors = MultiMonitor()
        self.vault = CredentialVault()
        self.email = EmailController(self.settings, self.vault, self.safety)
        self.plugins = PluginSystem()
        self.memory = MemoryManager()

        self.core = MiddlewareCore()
        self.core.register("app_control", self.ac.handle, self.ac.verify_open)
        self.core.register("file_operation", self.fc.handle, self.fc.verify_exists)
        self.core.register("browser_action", self.bc.handle)
        self.core.register("web_automation", self.web.handle)
        self.core.register("system_monitor", self.sm.handle)
        self.core.register("system_control", self.sc.handle)
        self.core.register("process_management", self.ac.handle)
        self.core.register("notification", self.ns.handle)
        self.core.register("clipboard", self.cm.handle)
        self.core.register("screenshot", self.ocr.handle)
        self.core.register("developer_operation", self.dev.handle)
        self.core.register("document", self.docs.handle)
        self.core.register("text_assistant", self.text_assistant.handle)
        self.core.register("multi_monitor", self.monitors.handle)
        self.core.register("email", self.email.handle)
        self.core.register("plugin", self.plugins.handle)
        self.core.register("memory", self.memory.handle)
        self.core.register("code_agent", self.code_agent.handle)

        self.wm = WorkflowManager(self.core)
        self.core.register("workflow", self.wm.handle)
        self.sched = ScheduleManager(self.wm)
        self.core.register("scheduling", self.sched.handle)

        self.executor = StepExecutor(self.core)
        self.stt = STTEngine(self.settings, hint_words_fn=self.hint_words)

        threading.Thread(target=lambda: self.brain.ask("warm up"), daemon=True).start()

    def hint_words(self):
        """Fed to the STT backend's prompt bias so it leans toward words your setup actually uses."""
        words = set(self.ac.settings.app_registry.keys()) | set(self.wm.workflows.keys())
        return list(words)[:20]

    def run_text(self, text):
        if not text:
            return None
        steps = self.planner.plan(text)
        result = self.executor.execute(steps, policy="continue_on_failure")
        results = (result.get("data") or {}).get("results") or []
        for step, r in zip(steps, results):
            self.memory.log_command(step, r)
            if step.get("intent") != "workflow" and r.get("status") == "success":
                self.wm.track_step(step)
        return result


def build_hud_speech_sink(settings):
    def sink(message, do_speak):
        if settings.hud_enabled:
            hud_show(message)
        if settings.speak_enabled and do_speak:
            speak(message)
    return sink


def main():
    print("---- COGNITIVE MIDDLEWARE ENGINE ----")
    print("Type a command. Ctrl+Shift+Space / wake word for voice. 'exit' quits.\n")

    temp_settings = Settings.load()
    ollama_proc = ensure_ollama_running(temp_settings)

    system = System()
    settings = system.settings

    hub = InputHub()
    hub.start()
    confirm.set_handler(lambda prompt: hub.confirm(prompt))

    if settings.hud_enabled:
        start_hud()
    add_sink(build_hud_speech_sink(settings))

    busy = threading.Event()
    session_active = threading.Event()
    result_box = {}

    def run_sync(text):
        busy.set()
        try:
            return system.run_text(text)
        except Exception as e:
            log.error(f"Command failed: {e}")
            return {"status": "error", "message": str(e), "data": None}
        finally:
            busy.clear()

    def voice_session():
        if session_active.is_set() or busy.is_set():
            return
        session_active.set()
        narrate("Listening", speak=False)
        hud_show("Listening...")
        last_activity = time.time()
        session_start = time.time()
        try:
            while True:
                if time.time() - last_activity > settings.session_idle_timeout:
                    narrate("Going quiet, press the shortcut again when you need me", speak=False)
                    break
                if time.time() - session_start > settings.session_max_seconds:
                    narrate("Session timed out", speak=False)
                    break

                remaining_start = max(1.0, settings.session_idle_timeout - (time.time() - last_activity))
                audio = system.stt.listen(start_timeout=min(remaining_start, settings.session_start_timeout))
                if audio is None:
                    continue
                text = system.stt.transcribe(audio)
                if not text:
                    continue
                if text.lower().strip(" .!?") in STOP_LISTENING_WORDS:
                    narrate("Okay", speak=False)
                    break

                print(f"[voice] {text}")
                result = run_sync(text)
                print(result)
                last_activity = time.time()
                hud_show("Listening...")
        finally:
            session_active.clear()

    def on_voice_trigger():
        if session_active.is_set() or busy.is_set():
            return
        threading.Thread(target=voice_session, daemon=True).start()

    hotkey_ok = False
    if settings.enable_hotkeys:
        hotkey_ok = start_hotkey_listener(on_voice_trigger, settings.hotkey_voice)

    wake_listener = None
    if settings.enable_wake_word:
        wake_listener = WakeWordListener(on_voice_trigger, settings)
        if wake_listener.available:
            threading.Thread(target=wake_listener.start, daemon=True).start()

    if not hotkey_ok and not (wake_listener and wake_listener.available):
        print("(voice triggers unavailable on this machine - typed commands still work)")

    try:
        while True:
            try:
                line = hub.next_line(timeout=0.2)
            except queue.Empty:
                continue
            if line is None or line.strip().lower() in EXIT_WORDS:
                break
            if not line.strip():
                continue
            if busy.is_set() or session_active.is_set():
                print("(still working on the previous command)")
                continue
            print(run_sync(line.strip()))
    except KeyboardInterrupt:
        pass
    finally:
        if wake_listener:
            wake_listener.stop()
        system.bc.close()
        system.web.close()
        if ollama_proc:
            ollama_proc.terminate()
        print("Goodbye :)")


if __name__ == "__main__":
    main()
