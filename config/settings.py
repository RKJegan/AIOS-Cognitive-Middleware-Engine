import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).parent / "settings.json"


@dataclass
class Settings:
    # --- AI ---
    model_name: str = "qwen3:4b-instruct-2507-q4_K_M"
    ollama_host: str = "http://localhost:11434"
    whisper_model_size: str = "distil-small.en"
    whisper_language: str = "en"
    whisper_device: str = "cpu"          # keep "cpu" so the LLM keeps the 4 GB of VRAM
    whisper_compute: str = "int8"
    stt_backend: str = "faster_whisper"  # "faster_whisper" | "nemo_http" | "auto"
    nemo_server_port: int = 8765
    nemo_python: str = ""                # path to python.exe of your 3.12 NeMo env (optional auto-start)
    nemo_model: str = "nvidia/parakeet-tdt-0.6b-v3"
    nemo_device: str = "cpu"
    rag_top_k: int = 8
    # --- logging / safety ---
    log_dir: str = "data/logs"
    log_level: str = "INFO"
    confirm_dangerous_actions: bool = True
    max_history_items: int = 1000
    # --- apps / browser ---
    app_registry: dict = field(default_factory=dict)
    default_browser: str = "chrome"
    # --- triggers / voice ---
    enable_voice: bool = True
    enable_wake_word: bool = True
    wake_word_model_path: str = ""       # custom-trained .onnx overrides wake_word
    enable_hotkeys: bool = True
    wake_word: str = "weather"
    wake_threshold: float = 0.5
    hotkey_voice: str = "ctrl+shift+space"
    hotkey_text: str = "ctrl+alt+space"
    session_start_timeout: float = 6.0   # wait this long for the next phrase
    session_idle_timeout: float = 30.0   # session ends after this long with no command
    session_max_seconds: float = 120.0
    utterance_silence_seconds: float = 1.0
    utterance_max_seconds: float = 15.0
    vad_energy_floor: float = 0.012
    print_raw_results: bool = False
    speak_enabled: bool = True
    hud_enabled: bool = True
    # --- tools ---
    tesseract_cmd: str = ""
    clipboard_history: bool = True
    contacts: dict = field(default_factory=dict)
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 465
    email_imap_host: str = "imap.gmail.com"
    dev_workspace: str = ""
    claude_command: str = "claude"
    claude_extra_args: list = field(default_factory=lambda: ["--permission-mode", "acceptEdits"])
    code_agent_timeout: int = 600

    @classmethod
    def load(cls, path=DEFAULT_CONFIG_PATH):
        path = Path(path)
        if not path.exists():
            default = cls()
            default.save(path)
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path=DEFAULT_CONFIG_PATH):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


if __name__ == "__main__":
    for k, v in asdict(Settings.load()).items():
        print(f"  {k}: {v}")
