"""
Instagram Automation Configuration and Safety Thresholds
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# File paths
SESSION_FILE = DATA_DIR / "session.json"
WHITELIST_FILE = BASE_DIR / "whitelist.txt"
ACTION_LOG_FILE = REPORTS_DIR / "action_history.csv"

# Instagram Credentials from environment or interactive prompt
INSTA_USERNAME = os.getenv("INSTA_USERNAME", "").strip()
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD", "").strip()
INSTA_SESSIONID = os.getenv("INSTA_SESSIONID", "").strip()
INSTA_PROXY = os.getenv("INSTA_PROXY", "").strip() or None

# Safety & Rate Limiting Settings
# Instagram has strict rate limits. Keeping these realistic prevents account action blocks.
DEFAULT_DELAY_MIN = int(os.getenv("DELAY_MIN", "20"))      # Minimum seconds between actions
DEFAULT_DELAY_MAX = int(os.getenv("DELAY_MAX", "40"))      # Maximum seconds between actions
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))             # Actions before taking a short rest break
BATCH_REST_MIN = int(os.getenv("BATCH_REST_MIN", "45"))    # Rest break minimum seconds
BATCH_REST_MAX = int(os.getenv("BATCH_REST_MAX", "90"))    # Rest break maximum seconds

# Operational Limits
DEFAULT_MAX_ACTIONS_PER_RUN = int(os.getenv("MAX_ACTIONS_PER_RUN", "25"))
SKIP_VERIFIED = os.getenv("SKIP_VERIFIED", "true").lower() in ("true", "1", "yes")
SKIP_PRIVATE = os.getenv("SKIP_PRIVATE", "false").lower() in ("true", "1", "yes")

# Ghost Follower Detection Thresholds
# Accounts meeting any of these criteria can be flagged as ghost/spam
GHOST_CRITERIA = {
    "no_profile_pic": True,          # True = flag accounts with default avatar
    "max_media_count": 0,            # Accounts with 0 posts
    "min_followers": 5,              # Accounts with fewer than 5 followers
    "max_following": 2500,           # Accounts following thousands of people
    "ratio_following_to_follower": 10.0, # Following/Follower ratio >= 10 (bot signal)
}

