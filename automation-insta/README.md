# 📸 Instagram Follower & Following Automation Manager

A safe, modular, and feature-rich Python automation tool to manage Instagram followers and following. It helps you identify who doesn't follow you back, detect ghost/spam/bot followers, and safely clean up your account while strictly respecting Instagram's anti-spam thresholds.

---

## 🌟 Key Features

- **🔍 Full Account Relationship Audit**:
  - Automatically classifies all connections into **Non-Followers**, **Mutual Friends**, **Fans** (who follow you, but you don't follow back), and **Ghost/Bot Followers**.
  - Automatically exports clean CSV reports to the `reports/` folder.
- **🎯 Safe Non-Follower Cleaner**:
  - Automatically unfollows accounts that do not follow you back.
- **🔒 Strict Keep-List Mode (Purge Unwanted Accounts)**:
  - Treats `whitelist.txt` as your **exclusive Keep-List**.
  - Automatically compares your followers and following against this list.
  - Keeps **ONLY** the accounts in `whitelist.txt` and unfollows/removes all other accounts!
- **👻 Ghost & Bot Follower Remover**:
  - Detects spam/bot followers (no profile picture, bot username format, 0 posts with thousands of followings).
  - Removes them from your follower list using Instagram's official `user_remove_follower` endpoint (no blocking required).
- **🛡️ Multi-Tier Safety & Anti-Ban System**:
  - **Dry-Run Mode (Simulation)**: Enabled by default! Preview exactly which accounts will be touched without making any modifications.
  - **Randomized Human Jitter**: 20–40s random delays between actions so your activity looks 100% human.
  - **Batch Rest Pauses**: Automatically takes a 45–90s coffee break every 5 actions.
  - **Action Block Protection**: Gracefully halts execution immediately if Instagram returns an action block warning.
- **📝 Whitelist Protection**:
  - Protects your friends, family, and favorite creators from ever being unfollowed or removed.
  - Automatically skips verified accounts (celebrities, brands, public figures).
- **🔑 Smart Session Management & 2FA**:
  - Saves your session cookies securely in `data/session.json`—you only need to log in once!
  - Full support for Two-Factor Authentication (2FA) and Instagram SMS/Email verification checkpoints.
  - Supports browser `sessionid` cookie login if you prefer not to enter your password.

---

## 📁 Project Structure

```text
automation-insta/
│── config.py            # Safety thresholds, delays, batch settings
│── instagram_client.py  # Instagrapi wrapper with session caching & 2FA handling
│── analyzer.py          # Detection logic for non-followers, ghosts, mutuals, fans
│── manager.py           # Core safe execution engine with rate-limiting & logging
│── cli.py               # Interactive CLI terminal UI
│── main.py              # CLI entry point (interactive & scriptable modes)
│── whitelist.txt        # List of protected usernames (never touched)
│── .env.example         # Template for login credentials and proxy
│── requirements.txt     # Python dependencies
└── reports/             # Output directory for CSV reports and action logs
    ├── non_followers.csv
    ├── ghost_followers.csv
    ├── mutuals.csv
    ├── fans.csv
    └── action_history.csv
```

---

## 🚀 Quick Setup & Installation

### 1. Install Dependencies
Make sure you have Python 3.9+ installed, then run:

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials (Optional)
You can configure your credentials ahead of time by creating a `.env` file:

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your details:
```env
INSTA_USERNAME=your_username
INSTA_PASSWORD=your_password
```
*(If you leave `.env` empty, the tool will simply ask you securely when you start it).*

---

## 💻 How to Use

### Mode 1: Interactive Terminal Menu (Recommended)

Simply run:

```bash
python main.py
```

You will see an interactive dashboard:

```text
==========================================================
  INSTAGRAM MANAGER | Logged in as: @your_username
==========================================================
 [1] 📊 Run Account Audit & Generate CSV Reports
 [2] 🔍 View Non-Followers (Who doesn't follow back)
 [3] 🎯 Unfollow Non-Followers (with Dry-Run safety)
 [4] 👻 Scan & Remove Ghost/Spam Followers
 [5] 🛡️ Manage Whitelist (Protected Accounts)
 [6] 📜 View Action History Log
 [7] 🔄 Refresh Data from Instagram
 [8] 🚪 Log Out & Clear Session
 [0] ❌ Exit
```

### Mode 2: Command-Line Automation (For Cron / Scripts)

You can also run tasks directly via flags:

#### 1. Audit Account & Export CSV Reports:
```bash
python main.py --mode audit
```

#### 2. Dry-Run Unfollow (Simulation, doesn't unfollow anyone):
```bash
python main.py --mode unfollow --limit 20
```

#### 3. Live Unfollow (Actually unfollows up to 20 non-followers):
```bash
python main.py --mode unfollow --limit 20 --live
```

#### 4. Clean Ghost / Bot Followers:
```bash
# Preview ghost followers that would be removed:
python main.py --mode remove-ghosts --limit 15

# Live removal:
python main.py --mode remove-ghosts --limit 15 --live
```

#### 5. Add an Account to the Whitelist:
```bash
python main.py --add-whitelist best_friend_username
```

---

## 🛡️ Instagram Safety Best Practices

Instagram is very sensitive to automated actions. To keep your account completely safe:

1. **Start Slow**: When running the tool on an account for the first time, limit actions to **15–20 per day**.
2. **Never Exceed Daily Limits**: We recommend keeping total unfollows under **50–80 actions per 24-hour window**.
3. **Use Dry-Run First**: Always inspect the dry-run output and check `reports/non_followers.csv` before executing a live cleanup.
4. **Maintain Whitelist**: Add your close friends, colleagues, and favorite creators to `whitelist.txt` so they are never accidentally removed.
5. **Batch Pauses**: Keep the default delay settings in `config.py` (20–40 seconds between actions + rest breaks). Do not shorten delays to "speed it up", as rapid requests trigger Instagram's temporary Action Block.

