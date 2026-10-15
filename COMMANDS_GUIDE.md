
# AIOS — Command Reference Guide

A practical guide to operating the Cognitive Middleware Engine using natural-language text or voice commands.

> **Important:** AIOS uses an LLM-based task planner. Commands in this guide are examples supported by the project's action vocabulary and controller design, but not every phrase is guaranteed to work. Actual behavior depends on the planner, configuration, operating system, dependencies, and safety policies.

---

## Table of Contents

1. [How to Use Commands](#1-how-to-use-commands)
2. [Application Control](#2-application-control)
3. [File Management](#3-file-management)
4. [Browser Control](#4-browser-control)
5. [Web Automation](#5-web-automation)
6. [System Monitoring](#6-system-monitoring)
7. [System Controls](#7-system-controls)
8. [Process Management](#8-process-management)
9. [Workflow Automation](#9-workflow-automation)
10. [Scheduling](#10-scheduling)
11. [Notifications and Reminders](#11-notifications-and-reminders)
12. [Clipboard Management](#12-clipboard-management)
13. [Screenshots and OCR](#13-screenshots-and-ocr)
14. [Developer Operations](#14-developer-operations)
15. [Document Operations](#15-document-operations)
16. [Text Assistant](#16-text-assistant)
17. [Memory Management](#17-memory-management)
18. [Calculator and Date-Time Plugins](#18-calculator-and-date-time-plugins)
19. [Email Operations](#19-email-operations)
20. [Multi-Monitor Operations](#20-multi-monitor-operations)
21. [Code Agent](#21-code-agent)
22. [Voice Commands](#22-voice-commands)
23. [Security and Safety](#23-security-and-safety)
24. [Troubleshooting](#24-troubleshooting)

---

## 1. How to Use Commands

Start AIOS from the project root:

```powershell
python main.py
```

Type a natural-language instruction into the running application.

For example:

```text
Open Notepad
```

The system attempts to interpret the instruction, generate a structured action, route it to the appropriate controller, and report the result.

### Command lifecycle

1. Submit a natural-language command.
2. The task planner interprets the request.
3. The action vocabulary validates or normalizes the selected action.
4. The middleware routes the action to its controller.
5. The controller performs the operation.
6. The system reports the outcome.

For voice input, use the configured shortcut, normally `Ctrl+Shift+Space`, or the configured wake-word mechanism if enabled.

Use `exit`, `quit`, or `bye` to leave the application.

---

## 2. Application Control

**Module:** `priority1_core/app_controller.py`

Application control manages supported application launching, closing, and related operations using the configured application registry.

| Goal | Example command |
|---|---|
| Open a browser | `Open Chrome` |
| Launch Notepad | `Open Notepad` |
| Launch Calculator | `Launch the calculator` |
| Open Excel | `Start Excel` |
| Close an application | `Close Chrome` |
| Close Notepad | `Close Notepad` |
| Close applications | `Close all open apps` |
| Uninstall an application | `Uninstall Spotify` |

### Example

```text
Open Notepad
```

Expected behavior: the planner selects an application-opening action, and the application controller attempts to launch the configured Notepad application.

**Limitations:** Application names must resolve through the controller's registry or supported application-discovery logic. Uninstallation is a sensitive operation and may require confirmation or additional permissions.

---

## 3. File Management

**Module:** `priority1_core/file_controller.py`

File management supports common file and folder operations.

### List and open folders

```text
List files in Downloads
List files on Desktop
Show me what is in Documents
Open Downloads folder
Open the Documents folder
```

### Create files and folders

```text
Create a folder named projects on Desktop
Create a folder named preprocessing in ML pipeline
Create a file called todo.txt
Create notes.txt on Desktop
```

### Copy and move files

```text
Copy report.docx from Documents to Desktop
Move report.docx from Downloads to Documents
```

### Rename and delete

```text
Rename draft.txt to final.txt on Desktop
Delete old.txt from Desktop
Remove notes.txt from Documents
```

### Search and compress

```text
Find report.pdf in Documents
Search for budget.xlsx on my computer
Compress the project folder on Desktop
Zip the folder photos in Pictures
```

### Important considerations

- Use explicit folder names or full paths when possible.
- Confirm source and destination paths before moving or deleting important data.
- File deletion and other sensitive operations may trigger safety checks.
- Actual support depends on the controller's path resolution and action implementation.

---

## 4. Browser Control

**Module:** `priority1_core/browser_controller.py`

Browser control launches a browser, opens URLs, searches the web, and handles supported browser-level operations.

### Launch a browser

```text
Open browser
Open Chrome
Open the web browser
```

### Open websites

```text
Open YouTube
Go to wikipedia.org
Open GitHub on Brave
Open Gmail on Edge
```

### Search the web

```text
Search Python tutorials
Google machine learning courses
Search WhatsApp Web on Brave
```

### Close browser windows or tabs

```text
Close the browser
Close all tabs
```

**Security note:** The native browser controller may launch your normal browser profile. That profile can contain logged-in sessions and private browsing data. Do not expose its profile directory, cookies, or credentials in Git.

---

## 5. Web Automation

**Module:** `priority2_strong/web_automation.py`

Web automation uses Playwright and a separate automation browser profile.

It is different from normal browser launching: it supports interaction with page elements.

### Open a page

```text
Go to wikipedia.org in the automation browser
```

### Read page content

```text
Read this page
What does this webpage say?
```

### Interact with page elements

```text
Click the Sign in button
Click on Search
Type hello world into the search box
Fill the email field with test@example.com
Press Enter
Scroll down
Scroll up
```

### Capture and close

```text
Take a webpage screenshot
Close the automation browser
```

### Example workflow

1. Open a page in the automation browser.
2. Ask the assistant to read the page.
3. Ask it to click a visible control or fill a supported field.
4. Review the browser's resulting state.

### Limitations

- Element matching depends on page text, labels, and placeholders.
- Websites may change their layout.
- Some websites block automated interactions.
- Login state is separate from your regular browser profile.
- Do not automate sensitive submissions or transactions without reviewing the action first.

---

## 6. System Monitoring

**Module:** `priority1_core/system_monitor.py`

Use these commands to inspect supported system information.

### CPU and memory

```text
What's my CPU usage?
How much RAM am I using?
How much memory is used?
```

### Battery and storage

```text
What is my battery level?
How much space is on my S drive?
How much storage is left on drive C?
```

### General status

```text
Show full system status
Get system status
How long has my PC been on?
```

### Processes

```text
Show top processes
Which programs use the most CPU?
```

The controller returns information available through its system-monitoring implementation. Battery and drive information may vary by hardware and operating system.

---

## 7. System Controls

**Module:** `priority2_strong/system_control.py`

These commands interact with supported Windows system controls.

### Volume

```text
Set volume to 40
Change the volume to 75 percent
Volume up
Turn the volume down
Mute the sound
Unmute the sound
```

### Display brightness

```text
Set brightness to 70
Make the screen brighter 90 percent
```

Brightness support depends on the display hardware and available Windows interfaces.

### Appearance

```text
Turn on dark mode
Switch to light mode
```

### Lock and power

```text
Lock the screen
Lock my computer
Shut down the computer
Turn off the PC
Cancel shutdown
```

**Warning:** Locking, shutting down, and other disruptive actions should be used carefully. Confirm that important work is saved before running them. Sensitive operations may require explicit confirmation.

---

## 8. Process Management

**Module:** `priority2_strong/process_manager.py`

The application also registers process-management requests through the application controller. Available operations depend on that controller's implementation.

### Inspect processes

```text
List running processes
Show running processes
Find process Chrome
Is VLC running?
```

### Control processes

```text
Kill VLC
End the process Notepad
Restart VLC
End all tasks
```

Process termination may cause unsaved work to be lost. Avoid broad commands such as `End all tasks` unless you understand their effect.

---

## 9. Workflow Automation

**Module:** `priority1_core/workflow_manager.py`

Workflows allow supported actions to be recorded and reused.

### List workflows

```text
List my workflows
Show my saved workflows
```

### Record a workflow

```text
Start recording workflow called dev session
Record a workflow named study mode
```

Perform the desired supported actions, then save the sequence:

```text
Stop recording
Save the workflow
```

### Execute workflows

```text
Run my dev session workflow
Start my morning routine workflow
```

### Delete workflows

```text
Delete workflow dev session
```

### Example

A developer repeatedly opens a project application and inspects a folder. They can record the supported sequence as `dev session` and later request:

```text
Run my dev session workflow
```

The workflow manager looks up the saved sequence and executes its steps in order. The current executor stops a workflow when a step fails.

### Storage

Saved workflows are stored in:

```text
data/workflows.json
```

This is user-specific runtime data and should normally be excluded from Git.

**Important:** Workflow recording captures supported assistant actions; it is not a universal recorder of every mouse movement and keyboard event. Actions requiring manual confirmation may be excluded from saved workflows.

---

## 10. Scheduling

**Module:** `priority2_strong/schedule_manager.py`

Scheduling can execute saved workflows at supported times.

### Schedule a one-time execution

```text
Run my morning routine in 30 minutes
```

### Schedule a daily workflow

```text
Schedule dev session workflow every day at 9am
```

Other examples:

```text
Schedule dev session workflow every day at 09:30
Schedule dev session workflow every day at 9:30 pm
```

### Inspect and cancel schedules

```text
List my schedules
Show scheduled jobs
Cancel schedule 2
```

### Limitations

- The scheduler supports a limited set of time phrases.
- One-time schedules accept intervals such as `in 10 minutes` or `in 2 hours`.
- Daily schedules use the `every day at ...` pattern.
- Scheduled jobs are maintained in process memory and are not a durable background service.
- Jobs may be lost when the application exits or the machine shuts down.

Keep AIOS running for scheduled tasks to execute.

---

## 11. Notifications and Reminders

**Module:** `priority2_strong/notification_system.py`

### Immediate notifications

```text
Show notification build finished
Notify me that the download is done
Send me a notification saying lunch time
```

### Timed reminders

```text
Remind me to submit report in 10 minutes
Remind me to drink water in 1 hour
Set a reminder to call mom in 5 minutes
```

The reminder parser supports intervals in seconds, minutes, or hours, using forms such as `in 10 minutes`.

Reminders use in-process timers. They are not guaranteed to survive application shutdown or a system restart.

---

## 12. Clipboard Management

**Module:** `priority2_strong/clipboard_manager.py`

### Copy text

```text
Copy hello to clipboard
Put the text meeting at 5 on the clipboard
```

### Read clipboard

```text
What is in my clipboard?
Paste from clipboard
```

### Clipboard history

```text
Show clipboard history
Select clipboard item 2
Clear the clipboard
```

Clipboard history is maintained in memory during the running session and is limited to a fixed number of entries.

**Privacy:** The clipboard can contain passwords, tokens, private messages, and other sensitive information. Do not copy sensitive data into logs or public workflow examples.

---

## 13. Screenshots and OCR

**Module:** `priority2_strong/screenshot_ocr.py`

### Capture a screenshot

```text
Take a screenshot
Capture my screen
```

### Read screen text

```text
Read the text on my screen
```

### OCR from an image file

```text
Read text from scan.png on Desktop
```

OCR requires compatible image-processing dependencies and, where configured, Tesseract OCR.

Results depend on image resolution, contrast, language, and text layout. Screenshots may contain personal information, so review their contents before sharing them.

---

## 14. Developer Operations

**Module:** `priority2_strong/developer_operations.py`

Developer operations support selected Git and Python environment commands.

### Git status

```text
Git status
What changed in my repo?
```

### Commit changes

```text
Commit changes with message fixed login bug
Git commit with message added tests
```

### Pull and push

```text
Git pull
Pull the latest changes
Git push
Push my code
```

### Python environment

```text
Create virtual environment venv
Make a Python virtual environment called env
```

### Install packages

```text
Install package requests
Pip install numpy
```

### Run supported commands

```text
Run python --version
Run the command pip list
```

### Safety considerations

- Git commits may stage and commit all changes in the configured working directory.
- Push operations may require confirmation.
- Package installation and script execution can change the environment.
- Commands are executed from the developer operations working directory.
- The command runner uses argument splitting rather than a full shell, so complex shell syntax, pipes, redirection, and chained commands may not work.
- Review Git status before committing or pushing.

---

## 15. Document Operations

**Module:** `priority3_advanced/document_controller.py`

The document controller supports text extraction from PDF, DOCX, and ordinary text-readable files.

### Read a document

```text
Read report.pdf on Desktop
Open and read the document notes.docx in Documents
```

### Search document content

```text
Search for the word budget in report.pdf
```

The exact interpretation of the search command depends on the planner's structured output.

The document reader currently returns a limited portion of extracted text. Scanned PDFs may require OCR, and complex layouts or images may not be extracted accurately.

---

## 16. Text Assistant

**Module:** `priority3_advanced/text_assistant.py`

The text assistant uses the configured language model for summarization, translation, drafting, and explanations.

### Summarization

```text
Summarize this text: Artificial intelligence is changing how software is developed.
```

### Translation

```text
Translate Hello, how are you? to Tamil
```

### Drafting

```text
Draft a professional email about requesting a project deadline extension
```

### Explanation

```text
Explain gradient descent in simple terms
Explain this code in simple language
```

The assistant uses the configured LLM, so output quality depends on model capability and context limits.

Do not assume that a drafted email has been sent. Drafting and sending are separate operations.

---

## 17. Memory Management

**Module:** `memory/memory_manager.py`

The memory manager stores application-level facts and preferences and records command history.

### Save information

```text
Remember that my project is called AIOS
```

### Recall information

```text
Recall my saved information
```

### Forget information

```text
Forget AIOS
```

### Inspect command history

```text
Show my recent command history
```

### Preferences

The memory controller also supports structured preference operations through its action interface, including setting and retrieving preferences.

Memory is stored in a local SQLite database:

```text
data/memory.db
```

The database may contain private commands and saved facts. Exclude it from Git.

**Limitation:** The memory manager is a small fact-and-preference store, not a complete autonomous learning system. It does not automatically fine-tune the LLM from every interaction.

---

## 18. Calculator and Date-Time Plugins

### Calculator plugin

**Module:** `plugins/calculator_plugin.py`

Examples:

```text
Calculate 25 plus 17
Calculate 100 divided by 4
Calculate 12 times 8
Calculate 2 to the power of 10
Calculate 25 mod 4
```

The calculator evaluates a restricted arithmetic expression. It does not execute arbitrary Python code.

### Date and time plugin

**Module:** `plugins/datetime_plugin.py`

Examples:

```text
What time is it?
What is today's date?
What day is it?
```

Results use the computer's local system clock.

### Weather plugin

**Module:** `plugins/weather_plugin.py`

The included weather plugin is a stub.

A request such as:

```text
What is the weather today?
```

cannot provide a real forecast until a weather service and valid API configuration are implemented.

---

## 19. Email Operations

**Module:** `priority3_advanced/email_controller.py`

The project includes an email controller with a credential-vault integration.

Example requests from the command example bank include:

```text
Read my emails
Check my inbox
Send email to Dr Ahmed saying project submitted
Email John that I will be late
```

Email access depends on the configured account, provider settings, credentials, and required permissions.

Do not assume email sending will work until the integration is configured and tested. Review recipients and message content before sending. Never commit email passwords, application passwords, access tokens, or refresh tokens.

---

## 20. Multi-Monitor Operations

**Module:** `priority3_advanced/multi_monitor.py`

The project includes a multi-monitor controller.

Example requests to try after verifying the controller's supported action vocabulary:

```text
Show my monitors
List connected displays
```

These are exploratory natural-language examples, not confirmed exact phrases from the command example bank. Use the module's actual supported actions before relying on them.

Display operations may depend on Windows APIs and connected monitor hardware.

---

## 21. Code Agent

**Module:** `priority2_strong/code_agent.py`

The project includes a code-agent module intended for developer-oriented assistance.

Possible task categories include explaining code, inspecting project files, and supporting coding workflows, depending on its implemented action vocabulary.

Before using code-modification features, verify the configured workspace boundary and allowed operations. Do not assume that the presence of a code-agent module guarantees safe or unrestricted project editing.

For development operations, start with the explicit commands in Section 14 and inspect the result before approving changes.

---

## 22. Voice Commands

Voice commands use the same underlying planner and controller pipeline as typed commands.

### Activate voice input

Use the configured keyboard shortcut, normally:

```text
Ctrl+Shift+Space
```

Or activate the configured wake word if wake-word support is enabled and its model files are available.

### Example spoken commands

```text
Open Notepad
What is my CPU usage?
Set volume to 40
List my workflows
Remind me to submit the report in 10 minutes
```

### End a voice session

The voice session recognizes phrases such as:

```text
Stop listening
Cancel
Never mind
That's all
Okay stop
```

The wake-word engine and speech-recognition backend require their corresponding dependencies and model assets. Voice recognition errors may produce a different command from the one intended, so sensitive actions should be confirmed before execution.

---

## 23. Security and Safety

AIOS has a safety layer and workspace guard, but no natural-language interface should be treated as inherently safe.

### Recommended practices

1. Review the action before executing destructive operations.
2. Keep browser cookies and session profiles out of Git.
3. Never commit API keys, passwords, or access tokens.
4. Exclude private workflow files and local memory databases.
5. Test file operations inside a disposable directory first.
6. Confirm Git changes before committing or pushing.
7. Review browser form submissions and email messages.
8. Keep code-agent operations restricted to the intended workspace.
9. Avoid running the application with elevated permissions unless absolutely necessary.
10. Review logs before sharing diagnostic output publicly.

### Runtime files to exclude

```gitignore
# Private AIOS runtime data
data/workflows.json
data/memory.db
data/logs/
data/automation_profile/
data/page_screenshot.png
data/user_examples.txt
config/settings.json
```

Add these rules to `.gitignore` if those files should remain local. If a sensitive file was already committed, remove it from tracking and rotate any exposed credentials.

---

## 24. Troubleshooting

### The assistant does not understand a command

Try a shorter phrase matching the command examples in `ai/examples.txt`.

For example, use:

```text
Open Notepad
```

instead of a long multi-part request. The planner and example retriever are more likely to map a familiar phrase to the intended action.

### The command is recognized but does not execute

Check:

- Whether the action exists in `ai/action_vocab.py`.
- Whether the intent is registered in `core/middleware_core.py`.
- Whether the controller implements the action.
- Whether the relevant dependencies are installed.
- Whether the safety layer requires confirmation.

### Browser automation fails

Verify that Chromium is installed:

```powershell
python -m playwright install chromium
```

Then test with a public page before attempting authenticated sites.

### Local LLM requests fail

Check the Ollama service and available models:

```powershell
ollama list
```

Ensure that the model configured in `config/settings.py` is available and that the local API is reachable.

### A scheduled task does not run

Confirm that AIOS is still running, the workflow exists, and the scheduling phrase uses a supported time format.

### A workflow fails partway through

Check the reported action and review the application logs. Workflows use a stop-on-failure execution policy, so a failed step can prevent subsequent steps from running.

---

## Final Notes

AIOS is a modular cognitive middleware project. The commands above are intended as a practical guide for interacting with the implemented controllers.

A command listed in this guide should be considered **implemented and verified** only after it has been tested against the actual application. Some modules are optional, some require external configuration, and some natural-language examples may need adjustment to match the action vocabulary.

For developers extending the system, the recommended process is to implement the controller action, register it with the middleware, add or update its action vocabulary, create a matching example, and test both successful and rejected execution paths.
