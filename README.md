# ⚡ Automation Scripts Suite

A modular collection of robust, production-grade automation scripts and tools designed to streamline routine tasks, manage social media presence, perform data audits, and eliminate repetitive workflows.

---

## 📂 Repository Overview

Each tool inside this repository is designed as an independent, self-contained automation module with its own environment dependencies, configurations, and documentation.

```text
automation scripts/
│
├── 📁 automation-insta/         # 📸 Instagram Follower & Account Management Suite
│   ├── analyzer.py             # Classification logic (non-followers, ghosts, mutuals, fans)
│   ├── cli.py                  # Interactive terminal dashboard & UI
│   ├── config.py               # Rate limits, jitter delays, and batch configurations
│   ├── instagram_client.py     # Instagrapi integration, 2FA, & session management
│   ├── main.py                 # Main entry point (interactive & headless CLI modes)
│   ├── manager.py              # Execution engine, safety limits, and logging
│   ├── requirements.txt        # Sub-project dependencies
│   ├── run.bat                 # Windows one-click launcher
│   └── README.md               # Dedicated documentation for the Instagram tool
│
└── 📄 README.md                # Root documentation (this file)
```

---

## 🛠️ Available Modules

| Module | Description | Key Features | Status |
| :--- | :--- | :--- | :--- |
| [**`automation-insta`**](./automation-insta) | Instagram Follower & Following Automation Manager | • Account relationship audits & CSV reports<br>• Safe non-follower cleanup with dry-run<br>• Ghost & spam bot follower detection<br>• Whitelist protection & Keep-List purge<br>• Anti-ban human jitter (20–40s delays) | 🟢 Active |

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.9+** installed on your system ([Download Python](https://www.python.org/downloads/))
- **Git** installed ([Download Git](https://git-scm.com/))

### 2. Environment Setup

It is recommended to run each automation module within its own dedicated Python virtual environment.

#### Clone the repository:
```bash
git clone <repository-url>
cd "automation scripts"
```

#### Choose a module (e.g., `automation-insta`):
```bash
cd automation-insta
```

#### Create and activate a virtual environment:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Install dependencies:
```bash
pip install -r requirements.txt
```

#### Run the tool:
- **Windows shortcut**: Double-click `run.bat` or execute `.\run.bat` in Command Prompt.
- **Direct CLI**:
  ```bash
  python main.py
  ```

For detailed setup, configuration, CLI flags, and safety guidelines for a specific script, refer to the module's own `README.md` (e.g., [`automation-insta/README.md`](./automation-insta/README.md)).

---

## 🏗️ Architectural Principles

All tools in this suite adhere to standard architectural guidelines:

1. **Safety & Rate Limit Compliance**:
   - All web and API automation includes conservative request throttling, human-like jitter, and batch rest pauses.
   - Destructive actions (unfollowing, deletions, bulk modifications) default to **Dry-Run (Simulation)** mode to prevent accidental data loss.

2. **Self-Contained Modularity**:
   - Every subfolder is standalone. Adding or removing a script does not break unrelated automations.
   - Modules maintain their own dependencies in `requirements.txt` and dedicated settings in `config.py` or `.env`.

3. **Dual Execution Modes**:
   - **Interactive Mode**: Guided terminal UI with menus, prompts, and visual feedback for manual operations.
   - **Headless / Flag Mode**: Command-line arguments for running via schedulers, cron jobs, or CI/CD pipelines.

4. **Security & Privacy First**:
   - Credentials, session tokens, cookies, and generated reports are strictly excluded via `.gitignore`.
   - Never commit `.env`, `*.session`, or personal data exports to version control.

---

## ➕ Adding New Automation Scripts

When contributing a new automation tool to this repository, follow this standardized structure:

```text
automation-<name>/
├── config.py              # Default parameters, constants, and limits
├── requirements.txt       # Pinned library dependencies
├── main.py                # Primary script entry point
├── .env.example           # Credential template (without sensitive values)
├── .gitignore             # Sub-project specific ignore rules
└── README.md              # Documentation, setup steps, and usage examples
```

---

## ⚠️ Disclaimer & Responsible Use

- The scripts provided in this repository are for **educational and personal workflow automation purposes only**.
- When automating third-party platforms (such as social networks or web services), ensure your use strictly complies with the respective platform's **Terms of Service (ToS)** and API usage policies.
- The repository authors and contributors accept no responsibility or liability for account restrictions, suspensions, or data loss resulting from the use or misuse of these tools. Always start with **Dry-Run Mode** and adhere to conservative rate limits.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) (or applicable open-source license).

