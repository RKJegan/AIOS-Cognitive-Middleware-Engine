
# AIOS — AN OFFLINE NATURAL LANGUAGE INTERFACE FOR INTELLIGENT OPERATING SYSTEM AUTOMATION AND CONTROL

**An AI-powered desktop automation system that connects natural-language instructions to operating-system actions through a local LLM, voice interaction, modular controllers, and a safety layer.**

AIOS is a Python-based cognitive middleware project designed to make desktop interaction more natural. Instead of manually navigating every application or repeating the same sequence of operations, users can issue text or voice commands and let the system interpret the request, plan the required actions, and route them to the appropriate controller.

The project follows a middleware-oriented architecture: the AI interprets the user's intent, the middleware dispatches actions to specialized modules, and security checks help govern what the system is allowed to execute.

The goal is to build an extensible desktop assistant that can run locally, support reusable workflows, interact with applications, and provide a foundation for more advanced agentic operating-system interaction.

---

## Table of Contents

- [Overview](#overview)
- [Project Goals](#project-goals)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Execution Workflow](#execution-workflow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running AIOS](#running-aios)
- [Command Examples](#command-examples)
- [Workflow Automation](#workflow-automation)
- [Browser Automation](#browser-automation)
- [Security and Privacy](#security-and-privacy)
- [Testing and Diagnostics](#testing-and-diagnostics)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Future Development](#future-development)
- [Contributing](#contributing)
- [Team](#team)
- [License](#license)

---

## Overview

Traditional desktop interaction requires users to operate applications, navigate menus, manage files, and repeat routine actions manually. AIOS explores a different approach: users express an intended outcome in natural language, and an AI-powered middleware layer translates that request into structured operations.

For example, a user might type:

- "Open Notepad."
- "List the files in my project folder."
- "Read this document."
- "Remember this information."
- "Run my saved workflow."

The system uses a local language model through Ollama to interpret instructions and plan actions. A collection of Python modules handles execution, including application control, file operations, browser interaction, system monitoring, document handling, notifications, scheduling, and workflow management.

AIOS is a desktop automation and middleware project, not a replacement operating system. It operates on top of the existing operating system and uses its applications, processes, files, and system interfaces.

### Core concept         

**Natural language → Intent interpretation → Task planning → Safety validation → Middleware dispatch → Action execution → Result reporting**

This separation makes it possible to extend individual capabilities without rewriting the entire assistant.

---

## Project Goals

1. **Natural-language interaction:** Allow users to describe tasks without memorizing every application-specific command.
2. **Local AI inference:** Use a locally hosted LLM through Ollama for intent interpretation and task planning.
3. **Voice-enabled operation:** Support speech input, wake-word detection, keyboard shortcuts, and spoken responses.
4. **Modular system control:** Separate application, file, browser, document, and other operations into dedicated controllers.
5. **Reusable workflows:** Record, save, execute, list, and delete sequences of supported actions.
6. **Safety-aware execution:** Apply validation and confirmation mechanisms to sensitive or dangerous operations.
7. **Extensibility:** Support plugins and new controllers as the project evolves.
8. **Context and memory:** Maintain application-level memory and command history to support contextual interaction.
9. **Developer assistance:** Provide an integration point for coding and developer-oriented operations.

---

## Key Features

### 1. Natural-language task interpretation

AIOS uses an LLM-backed interpretation and planning pipeline to convert user requests into structured actions.

The AI layer includes:

- Intent parsing
- Task planning
- Action vocabulary validation and repair
- Retrieval of relevant command examples using BM25
- Context processing
- LLM communication through Ollama

The retrieval mechanism selects relevant examples from a local text-based example bank instead of injecting every example into each request. This helps keep prompts compact while improving the relevance of action selection.

### 2. Voice interaction

The project includes modules for:

- Speech-to-text using faster-whisper
- Optional NVIDIA NeMo HTTP-based speech recognition
- Wake-word detection using openWakeWord
- Keyboard-triggered voice input
- Text-to-speech responses
- A narration HUD for displaying assistant feedback

The default wake-word configuration is `hey_jarvis`. Voice capabilities depend on compatible audio hardware, installed packages, and downloaded model assets.

### 3. Application and file control

The controller layer includes application launching and closing, file operations, and process management.

Potential command categories include:

- Opening and closing supported applications
- Listing and managing files
- Creating or moving files
- Inspecting supported system information
- Managing processes through supported operations

Actual supported commands depend on the registered controller actions, operating-system configuration, and safety policies.

### 4. Browser interaction and web automation

AIOS provides two separate browser approaches:

- **Native browser controller:** Opens a real installed browser through the operating system, potentially using its normal user profile and existing sign-in state.
- **Playwright web automation:** Opens a separate automation browser profile for supported page interactions, including clicking, filling fields, reading page content, and screenshots.

These are intentionally separate. Native browser launching does not itself provide automated page interaction, while the Playwright profile does not automatically inherit the user's normal browser logins.

### 5. Workflow recording and execution

The workflow manager supports:

- Starting workflow recording
- Recording supported actions
- Saving named workflows
- Listing saved workflows
- Executing workflows
- Deleting workflows
- Detecting repeated action sequences and suggesting workflow recording

Workflow execution uses a stop-on-failure policy. Certain dangerous actions are excluded from saved workflows so that sensitive operations cannot simply be replayed without the required safety checks.

### 6. System utilities

Additional modules provide capabilities for:

- System monitoring and control
- Clipboard operations
- Notifications
- Screenshot capture and OCR
- Scheduled tasks
- Document handling
- Text assistance
- Multi-monitor support
- Email operations
- Developer operations
- Plugin-based extensions

Each feature depends on its corresponding module, required packages, hardware, permissions, and configuration.

### 7. Credential storage

The credential vault uses Python `keyring` to store supported application credentials through the operating system's credential-storage backend. On Windows, this is intended to use Windows Credential Manager.

Credentials should not be stored in workflow definitions, source code, environment files committed to Git, or log messages.

---

## Architecture

AIOS is organized into layers so that language understanding, action routing, execution, and security can evolve independently.

```text
                 USER
                  |
          +-------+--------+
          |                |
      Text Input       Voice Input
          |                |
          |          Wake Word / STT
          |                |
          +-------+--------+
                  |
          AI Interpretation
                  |
       +----------+-----------+
       |          |           |
   LLM Brain   Retrieval   Context
       |       (BM25)      Engine
       +----------+-----------+
                  |
             Task Planner
                  |
           Structured Steps
                  |
        Safety and Validation
                  |
          Middleware Core
                  |
       +----------+-----------+
       |          |           |
   Application  File       Browser
   Controller  Controller  Controller
       |          |           |
       +----------+-----------+
                  |
       Other Registered Modules
                  |
       Result / Logs / Narration
                  |
          User Feedback
```

### Architectural components

| Layer | Responsibility |
|---|---|
| Input layer | Accept text, keyboard-triggered voice, and wake-word-triggered input |
| AI layer | Interpret intent, retrieve examples, and plan tasks |
| Middleware core | Dispatch structured intents to registered handlers |
| Controller layer | Perform application, file, browser, and other operations |
| Security layer | Validate sensitive actions and enforce applicable restrictions |
| Workflow layer | Save and replay supported sequences of actions |
| Memory layer | Store application-level command history and memory |
| Feedback layer | Provide narration, speech, logs, and HUD updates |

The diagram represents the architectural flow; it does not imply that every module is active in every execution.

---

## Execution Workflow

When a user submits a command, the application follows a pipeline similar to this:

1. **Input collection:** Receive the user's text or transcribed speech.
2. **Intent interpretation:** Use the AI layer to determine the intended action.
3. **Example retrieval:** Retrieve relevant examples from the command example bank.
4. **Task planning:** Convert the request into one or more structured steps.
5. **Action validation:** Validate the selected action and apply safety policies.
6. **Middleware dispatch:** Route each step to its registered controller.
7. **Execution:** Execute the requested operation using the relevant Python module or system interface.
8. **Feedback:** Return the result and provide narration or logging.
9. **Learning from repetition:** Track supported action sequences and suggest recording recurring workflows.

For example, a request to open a supported application should be interpreted as an application-control action, routed to the application controller, executed, and followed by a result. A request involving a dangerous operation may instead require confirmation or be rejected.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Primary implementation language |
| Ollama | Local LLM runtime and HTTP API |
| Qwen 3 4B Instruct | Default configured language model |
| faster-whisper | Local speech recognition |
| NVIDIA NeMo | Optional speech-recognition backend |
| openWakeWord | Wake-word detection |
| Playwright | Browser automation |
| keyring | Credential storage abstraction |
| psutil | System and process information |
| pyttsx3 | Text-to-speech |
| PyAudio / sounddevice | Audio input support |
| Tkinter | Narration HUD support |
| pytesseract | OCR integration |
| Pillow | Image and screenshot processing |
| python-docx / PyPDF2 | Document handling |
| Loguru | Application logging |
| pytest | Optional testing framework |

The project also integrates with Windows-specific libraries for volume control, application interaction, and other desktop capabilities.

---

## Project Structure

```text
AIOS/
│
├── main.py
├── requirements.txt
├── README.md
├── CHANGELOG_round2.md
│
├── ai/
│   ├── context_engine.py
│   ├── speech_to_text.py
│   ├── stt_engine.py
│   ├── intent_parser.py
│   ├── task_planner.py
│   ├── llm_brain.py
│   ├── action_vocab.py
│   ├── categories.py
│   ├── retriever.py
│   └── examples.txt
│
├── core/
│   ├── middleware_core.py
│   ├── input_hub.py
│   ├── step_executor.py
│   ├── paths.py
│   ├── logger.py
│   ├── confirm.py
│   ├── narrator.py
│   ├── voice_output.py
│   ├── wake_word.py
│   ├── hotkey_listener.py
│   └── winutil.py
│
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── security/
│   ├── safety_layer.py
│   ├── workspace_guard.py
│   ├── credential_vault.py
│   └── protected.py
│
├── memory/
│   └── memory_manager.py
│
├── priority1_core/
│   ├── app_controller.py
│   ├── file_controller.py
│   ├── browser_controller.py
│   ├── browser_automation.py
│   ├── system_monitor.py
│   ├── workflow_manager.py
│   └── web_automation.py
│
├── priority2_strong/
│   ├── system_control.py
│   ├── web_automation.py
│   ├── clipboard_manager.py
│   ├── process_manager.py
│   ├── volume_backend.py
│   ├── developer_operations.py
│   ├── screenshot_ocr.py
│   ├── notification_system.py
│   ├── schedule_manager.py
│   └── code_agent.py
│
├── priority3_advanced/
│   ├── document_controller.py
│   ├── text_assistant.py
│   ├── multi_monitor.py
│   ├── email_controller.py
│   ├── plugin_system.py
│   └── code_agent.py
│
├── plugins/
│   ├── plugin_system.py
│   ├── calculator_plugin.py
│   ├── plugin_calculator.py
│   ├── weather_plugin.py
│   └── datetime_plugin.py
│
├── ui/
│   └── narration_hud.py
│
├── scripts/
│   ├── check_setup.py
│   └── nemo_stt_server.py
│
├── tests/
│   └── test_sandbox_logic.py
│
└── data/                    # Runtime data; keep private data out of Git
    ├── logs/
    └── workflows.json
```

The tree highlights the major source modules. Actual runtime data files and optional configuration files may appear only after the application is executed.

---

## System Requirements

### Recommended environment

- Operating system: Windows 10 or Windows 11
- Python: A compatible Python 3 version; Python 3.12 is the environment used in recent development testing
- Git: Required for cloning and contributing
- Ollama: Required for the default local LLM workflow
- Microphone: Required for voice input
- Speakers or headphones: Recommended for spoken responses
- Internet connection: Required for initial installation and model downloads; the core local inference path is designed to run without a hosted LLM API after setup

Memory and GPU requirements depend on the selected LLM, speech-recognition backend, and other running applications. The default 4B model requires additional memory for model weights, context, and runtime overhead.

---

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the URL with the actual GitHub repository URL.

### 2. Create a virtual environment

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the appropriate execution-policy setting for your environment or invoke the virtual environment's Python executable directly.

Verify the interpreter:

```powershell
python --version
python -m pip --version
```

### 3. Install Python dependencies

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install project requirements:

```powershell
python -m pip install -r requirements.txt
```

Some packages require compatible system libraries, audio devices, or Windows-specific dependencies. Resolve any installation errors before enabling the corresponding feature.

### 4. Install the Playwright browser

```powershell
python -m playwright install chromium
```

This downloads the browser binary required by the Playwright automation module.

### 5. Install and configure Ollama

Install Ollama from its official website:

https://ollama.com/

Pull the model configured by default in `config/settings.py`:

```powershell
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

Verify the model:

```powershell
ollama list
```

Test inference:

```powershell
ollama run qwen3:4b-instruct-2507-q4_K_M
```

The model must match the `model_name` setting in your configuration.

Ollama normally exposes its local API at:

```text
http://localhost:11434
```

The application attempts to check or start the Ollama service when launched. If automatic startup does not work, start Ollama manually before running AIOS.

### 6. Install optional OCR support

OCR requires Tesseract OCR to be installed separately:

https://github.com/tesseract-ocr/tesseract

Set the executable path in the application settings if it is not available through the system PATH.

### 7. Check the installation

From the project root, run:

```powershell
python -m scripts.check_setup
```

Review the output for missing packages and external tools. Some checks are optional and may report missing dependencies even when the corresponding feature is not needed.

---

## Configuration

AIOS loads settings through `config/settings.py`.

When no settings file exists, the settings loader creates a default `config/settings.json` file.

Common configuration options include:

| Setting | Purpose |
|---|---|
| `model_name` | Ollama model used for language understanding |
| `ollama_host` | Ollama API address |
| `whisper_model_size` | Speech-recognition model |
| `whisper_device` | CPU or supported GPU execution |
| `stt_backend` | Speech-recognition backend |
| `enable_voice` | Enable voice-related input |
| `enable_wake_word` | Enable wake-word detection |
| `wake_word` | Configured pretrained wake word |
| `hotkey_voice` | Keyboard shortcut for voice input |
| `confirm_dangerous_actions` | Enable confirmation for dangerous actions |
| `hud_enabled` | Enable narration HUD |
| `speak_enabled` | Enable spoken responses |
| `dev_workspace` | Workspace setting for developer operations |
| `tesseract_cmd` | Optional Tesseract executable path |

Defaults are defined in the source. Check `config/settings.py` before changing settings, since supported options and values depend on the implementation.

**Important:** Do not commit private settings containing credentials, personal file paths, or other sensitive data. Keep safe example configuration separate from your local configuration.

---

## Running AIOS

From the project root with the virtual environment activated:

```powershell
python main.py
```

The application starts its input and assistant components, initializes the registered controllers, and accepts text commands.

### Available input methods

- Type a command into the application.
- Use `Ctrl+Shift+Space` to trigger voice input.
- Use the configured wake word, such as `hey_jarvis`, when the wake-word engine is available.
- Use supported text-input shortcuts when enabled.

To exit, use a supported exit command such as:

```text
exit
```

Some features may fall back to typed commands if their optional dependencies, models, or hardware are unavailable.

---

## Command Examples

The following are illustrative examples of supported command categories. Exact wording and behavior depend on the registered action vocabulary and task planner.

| Goal | Example request |
|---|---|
| Launch an application | `Open Notepad` |
| Inspect a folder | `List files in my project folder` |
| Manage files | `Create a folder named reports` |
| Browser launch | `Open Chrome` |
| Browser automation | `Read the current page` |
| Workflow management | `List my saved workflows` |
| Workflow execution | `Run my morning workflow` |
| Document assistance | `Summarize this document` |
| System information | `Show system status` |
| Memory interaction | `Recall my saved information` |

These examples describe intended command usage; they are not a guarantee that every natural-language variation will be interpreted correctly.

---

## Workflow Automation

Workflow automation is one of the core capabilities of AIOS.

The workflow manager records supported actions and stores them as reusable sequences. It also tracks consecutive actions and can suggest recording when it detects a repeated pattern.

### Typical workflow lifecycle

1. Start recording and provide a workflow name.
2. Perform supported actions through the assistant.
3. Stop recording to save the captured sequence.
4. List available workflows.
5. Run a saved workflow when required.
6. Delete a workflow when it is no longer needed.

### Example

Imagine that a user repeatedly opens an application and navigates to a project folder.

Instead of repeating the same steps manually, the user can record the supported sequence and save it under a name such as `project setup`.

Later, the user can ask the assistant to run that workflow. AIOS executes the saved steps in order and stops the workflow when a step fails.

### Workflow safety

Not every action is eligible for workflow recording. The workflow manager checks actions against the workflow safety policy and rejects steps that are not permitted to be automated.

Dangerous operations should retain their required confirmation behavior rather than being silently replayed.

### Workflow storage

The current workflow manager stores saved workflows in:

```text
data/workflows.json
```

This is runtime data, not source code. It can contain personal application names, paths, or other user-specific information.

Do not publish your personal workflow file unless it has been reviewed and sanitized.

---

## Browser Automation

AIOS separates normal browser launching from browser automation because they have different access and security characteristics.

### Native browser controller

The native controller launches an installed browser through the operating system.

Depending on the browser and its profile configuration, this may open a browser that already has the user's signed-in sessions.

This controller is intended for browser launching and should not be confused with Playwright-based page interaction.

### Playwright automation

The web automation module uses a separate automation browser profile, currently configured under:

```text
data/automation_profile/
```

It can interact with supported web pages using browser automation APIs.

Because this is a separate profile, it normally starts without the user's ordinary browser cookies and sign-in sessions.

### Credential handling

Never copy browser profile directories, cookies, authentication storage files, or browser password databases into the public repository.

If an automated task requires authentication, use a deliberate, secure authentication design. Do not assume that opening a real browser and automating a separate browser profile provide the same access.

---

## Security and Privacy

AIOS includes dedicated modules for action safety, workspace protection, credential storage, and application logging.

### Safety layer

The safety layer validates supported operations and can request user confirmation for dangerous actions. The precise behavior depends on the operation and the relevant controller.

### Workspace protection

The workspace guard checks certain sensitive paths and blocks configured operations against protected targets.

These safeguards are useful controls, but they should not be interpreted as a guarantee that every possible action is safe.

### Credential vault

The credential vault uses the `keyring` package to store credentials through the operating system's credential-storage backend. On Windows, the intended backend is Windows Credential Manager.

Credential values should never be added to source code or workflow JSON.

### Data privacy

AIOS is designed around local inference through Ollama, and the default speech-recognition backend is local. However, local inference does not automatically make every feature offline.

Features involving email servers, browser websites, weather services, package downloads, or other external systems may communicate over a network.

Review each integration before using it with private data.

### Git safety

Before pushing the repository, make sure `.gitignore` excludes local and sensitive data, including:

- `.env` files and credentials
- Browser profiles, cookies, and session data
- Private workflow definitions and runtime state
- Application logs and command history
- Local databases
- Downloaded models and generated artifacts
- Local settings containing personal information

The project's workflow file is located at `data/workflows.json`. Ensure that this exact file is ignored if your repository stores personal workflows there.

Useful checks:

```powershell
git status --short
git check-ignore -v data/workflows.json
git check-ignore -v config/settings.json
```

The second command should identify an ignore rule if the workflow file is correctly excluded. The third should identify a rule if local settings are intended to remain private.

If a secret was already committed, adding an ignore rule does not remove it from Git history. Remove it from tracking and revoke or rotate the exposed credential.

---

## Testing and Diagnostics

AIOS includes a setup diagnostic script and a sandbox-logic test module.

### Run setup checks

```powershell
python -m scripts.check_setup
```

### Run the sandbox-logic tests

```powershell
python -m unittest tests.test_sandbox_logic
```

### Test selected modules

The existing project README identifies these useful module checks:

```powershell
python -m config.settings
python -m core.logger
python -m security.safety_layer
python -m security.workspace_guard
python -m memory.memory_manager
python -m priority1_core.app_controller
python -m priority1_core.file_controller
python -m priority1_core.browser_controller
python -m priority2_strong.web_automation
python -m ai.llm_brain
python -m ai.task_planner
python -m core.voice_output
python -m ui.narration_hud
python -m core.hotkey_listener
python -m ai.speech_to_text
python -m core.wake_word
```

Some modules require Ollama, a microphone, a compatible audio device, or optional system software.

A module importing successfully does not necessarily prove that every real-world action it supports is working correctly.

---

## Known Limitations

AIOS is an actively developed project. Its behavior depends on model output, operating-system interfaces, configuration, and optional dependencies.

Known limitations include:

- **LLM interpretation:** Similar or ambiguous instructions may still produce incorrect action selection.
- **Voice input:** Speech recognition depends on microphone quality, model availability, and configuration.
- **Wake word:** The default implementation uses supported pretrained openWakeWord models. Arbitrary wake phrases require an appropriate model.
- **Browser profiles:** Playwright does not automatically share the user's normal browser login session.
- **Workflow safety:** Some actions are deliberately excluded from workflow recording.
- **Scheduling:** Supported schedule expressions are limited to the phrases and formats handled by the schedule manager.
- **Optional integrations:** OCR, email, audio, volume, brightness, and other features may require additional software or compatible hardware.
- **External dependencies:** Model downloads and package installation may fail if the network or download host is unavailable.
- **System-specific behavior:** Application launching, window handling, and system controls may differ across machines.

Treat AIOS as an extensible desktop automation prototype rather than a production-hardened autonomous operating system.

---

## Troubleshooting

### Ollama is unavailable

Verify that Ollama is installed and that the configured model is present:

```powershell
ollama list
```

Start the service if needed:

```powershell
ollama serve
```

Check that the API address in the settings matches the running Ollama service.

### Playwright cannot launch Chromium

Install the browser binary:

```powershell
python -m playwright install chromium
```

Run the command in the same Python environment used to launch AIOS.

### Wake-word model download fails

The openWakeWord package may be installed even when its pretrained model assets have not been downloaded.

If model downloads fail due to DNS or network errors, verify connectivity to the required download host and retry. Installing the Python package alone does not guarantee that the model files are present.

### Python imports are unresolved in VS Code

Select the interpreter belonging to the project's virtual environment:

```text
.venv\Scripts\python.exe
```

Then check installed packages using:

```powershell
python -m pip show faster-whisper sounddevice
```

### Voice input is unavailable

Check the microphone, audio dependencies, and the selected speech-recognition backend. If voice services are unavailable, use typed commands while diagnosing the environment.

---

## Future Development

Potential directions for future development include:

- More reliable intent interpretation and task planning
- Expanded automated workflow recording and editing
- Improved authentication handling for browser automation
- Stronger isolation of agent-executed actions
- More comprehensive safety tests
- Better recovery and reporting when workflow steps fail
- Expanded plugin interfaces
- Improved long-term context and memory management
- Additional offline voice and language-model options
- Cross-platform compatibility where supported by the underlying controllers

These are development directions, not claims that all of these features are already implemented.

---

## Contributing

Contributions are welcome from developers interested in local AI, desktop automation, workflow orchestration, natural-language interfaces, and AI safety.

### Suggested contribution process

1. Fork the repository.
2. Create a feature branch.
3. Make a focused change.
4. Test the affected module.
5. Verify that no credentials or personal data are included.
6. Submit a pull request describing the change and its limitations.

Example:

```powershell
git checkout -b feature/workflow-improvements
```

Follow the existing modular structure when adding new controllers or capabilities. Keep execution logic separate from intent interpretation where practical, and ensure that sensitive actions respect the applicable safety policy.

---

## Team

AIOS is developed collaboratively by three team members.

| Team member | Contribution |
|---|---|
| Team Member 1 | Update with actual name and responsibilities |
| Team Member 2 | Update with actual name and responsibilities |
| Team Member 3 | Update with actual name and responsibilities |

Replace these placeholders with the actual contributors and their roles before publishing the repository.

---

## License

This project is distributed under the MIT License.

See the [`LICENSE`](LICENSE) file for the full license terms and copyright attribution.

---

## Acknowledgements

AIOS builds on the Python ecosystem and integrates with tools and libraries including Ollama, Qwen, faster-whisper, openWakeWord, Playwright, and other open-source packages.

Refer to the respective projects' documentation and licenses for their usage conditions.

---

**AIOS — Bringing natural-language interaction, local AI, and desktop automation together through a modular cognitive middleware architecture.**
