"""
Account Relationship & Follower/Following Analyzer
Categorizes accounts into non-followers, fans, mutuals, and flags ghost/bot accounts.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from instagrapi.types import User, UserShort
import config

logger = logging.getLogger("Analyzer")


def load_whitelist() -> Set[str]:
    """Load list of usernames that should never be unfollowed or removed."""
    whitelist = set()
    if not config.WHITELIST_FILE.exists():
        return whitelist

    with open(config.WHITELIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip().lower()
            if clean_line and not clean_line.startswith("#"):
                whitelist.add(clean_line)
    return whitelist


def add_to_whitelist(username: str) -> bool:
    """Add a new username to the whitelist file."""
    username = username.strip().lower().lstrip("@")
    current = load_whitelist()
    if username in current:
        return False

    with open(config.WHITELIST_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{username}")
    return True


def remove_from_whitelist(username: str) -> bool:
    """Remove a username from the whitelist file."""
    username = username.strip().lower().lstrip("@")
    current = load_whitelist()
    if username not in current:
        return False

    current.remove(username)
    with open(config.WHITELIST_FILE, "w", encoding="utf-8") as f:
        f.write("# Protected accounts - will never be unfollowed or removed\n")
        for u in sorted(current):
            f.write(f"{u}\n")
    return True


class AccountAuditor:
    def __init__(self, followers: Dict[str, UserShort], following: Dict[str, UserShort]):
        self.followers = followers
        self.following = following
        self.whitelist = load_whitelist()

    def get_mutuals(self) -> List[UserShort]:
        """Users who follow you and you follow back."""
        mutual_ids = set(self.followers.keys()) & set(self.following.keys())
        return [self.following[uid] for uid in mutual_ids]

    def get_non_followers(self, apply_whitelist: bool = True) -> List[UserShort]:
        """Users you follow who DO NOT follow you back."""
        follower_ids = set(self.followers.keys())
        non_followers = []

        for uid, user in self.following.items():
            if uid not in follower_ids:
                if apply_whitelist:
                    if user.username.lower() in self.whitelist:
                        continue
                    if config.SKIP_VERIFIED and user.is_verified:
                        continue
                non_followers.append(user)

        return non_followers

    def get_fans(self) -> List[UserShort]:
        """Users who follow you, but you do not follow back."""
        following_ids = set(self.following.keys())
        return [user for uid, user in self.followers.items() if uid not in following_ids]

    def detect_quick_ghost_followers(self, apply_whitelist: bool = True) -> List[Tuple[UserShort, str]]:
        """
        Detect obvious ghost/bot accounts in followers using cached list data
        (e.g., default profile picture without making hundreds of API calls).
        """
        ghosts = []
        for uid, user in self.followers.items():
            username_lower = user.username.lower()
            if apply_whitelist and username_lower in self.whitelist:
                continue

            reason = []
            if getattr(user, "has_anonymous_profile_picture", False):
                reason.append("No profile picture (default avatar)")

            # Digits ratio in username (often generated bots have 5+ trailing digits)
            digits = sum(c.isdigit() for c in user.username)
            if digits >= 5 and len(user.username) >= 8:
                reason.append(f"Suspicious bot-like username ({digits} digits)")

            if reason:
                ghosts.append((user, " & ".join(reason)))

        return ghosts

    def evaluate_deep_ghost(self, user_info: User) -> Optional[str]:
        """
        Evaluate full profile details to determine if an account is inactive/ghost/spam.
        Returns a reason string if flagged, or None if legitimate.
        """
        if not user_info:
            return None

        username_lower = user_info.username.lower()
        if username_lower in self.whitelist:
            return None

        if config.SKIP_VERIFIED and user_info.is_verified:
            return None

        reasons = []

        # 1. No profile picture
        if getattr(user_info, "has_anonymous_profile_picture", False):
            reasons.append("No profile picture")

        # 2. 0 Posts
        if user_info.media_count == 0:
            reasons.append("0 posts")

        # 3. Mass-following bot (following thousands, barely followed by anyone)
        followers = getattr(user_info, "follower_count", 0) or 0
        following = getattr(user_info, "following_count", 0) or 0

        if following > 2000 and followers < 50:
            reasons.append(f"Bot-like ratio: following {following} vs {followers} followers")
        elif following > 1000 and followers == 0:
            reasons.append(f"Spam ratio: following {following} with 0 followers")

        if reasons:
            return ", ".join(reasons)

        return None

    def export_to_csv(self, filename: str, users: List[UserShort], extra_columns: Optional[Dict[str, str]] = None):
        """Export user list to a CSV file in reports directory."""
        filepath = config.REPORTS_DIR / filename
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["user_id", "username", "full_name", "is_private", "is_verified"]
            if extra_columns:
                fieldnames.append("reason")

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for user in users:
                row = {
                    "user_id": str(user.pk),
                    "username": user.username,
                    "full_name": user.full_name,
                    "is_private": user.is_private,
                    "is_verified": user.is_verified,
                }
                if extra_columns and str(user.pk) in extra_columns:
                    row["reason"] = extra_columns[str(user.pk)]
                writer.writerow(row)

        logger.info(f"Report exported to {filepath}")
        return filepath

    def generate_summary(self) -> dict:
        """Produce full audit analytics summary."""
        mutuals = self.get_mutuals()
        non_followers = self.get_non_followers(apply_whitelist=False)
        whitelisted_non_followers = [u for u in non_followers if u.username.lower() in self.whitelist]
        unprotected_non_followers = [u for u in non_followers if u.username.lower() not in self.whitelist]
        fans = self.get_fans()
        ghosts = self.detect_quick_ghost_followers(apply_whitelist=True)

        return {
            "total_followers": len(self.followers),
            "total_following": len(self.following),
            "mutual_friends": len(mutuals),
            "total_non_followers": len(non_followers),
            "whitelisted_protected": len(whitelisted_non_followers),
            "actionable_non_followers": len(unprotected_non_followers),
            "fans": len(fans),
            "quick_ghost_followers": len(ghosts),
            "timestamp": datetime.now().isoformat(),
        }

    def get_following_to_remove_strict(self) -> List[UserShort]:
        """
        STRICT KEEP-LIST MODE:
        Returns all accounts currently followed that are NOT in the whitelist.
        These must be UNFOLLOWED so only whitelisted accounts remain.
        """
        to_unfollow = []
        for uid, user in self.following.items():
            if user.username.lower() not in self.whitelist:
                to_unfollow.append(user)
        return to_unfollow

    def get_followers_to_remove_strict(self) -> List[UserShort]:
        """
        STRICT KEEP-LIST MODE:
        Returns all followers that are NOT in the whitelist.
        These must be REMOVED as followers so only whitelisted accounts remain.
        """
        to_remove = []
        for uid, user in self.followers.items():
            if user.username.lower() not in self.whitelist:
                to_remove.append(user)
        return to_remove

    def get_strict_keep_summary(self) -> dict:
        """Calculate statistics for the Strict Keep-Only mode."""
        self.whitelist = load_whitelist()
        following_usernames = {u.username.lower(): u for u in self.following.values()}
        follower_usernames = {u.username.lower(): u for u in self.followers.values()}

        following_to_keep = [u for uname, u in following_usernames.items() if uname in self.whitelist]
        following_to_unfollow = [u for uname, u in following_usernames.items() if uname not in self.whitelist]

        followers_to_keep = [u for uname, u in follower_usernames.items() if uname in self.whitelist]
        followers_to_remove = [u for uname, u in follower_usernames.items() if uname not in self.whitelist]

        return {
            "whitelist_total": len(self.whitelist),
            "current_following": len(self.following),
            "following_kept": len(following_to_keep),
            "following_to_unfollow": len(following_to_unfollow),
            "current_followers": len(self.followers),
            "followers_kept": len(followers_to_keep),
            "followers_to_remove": len(followers_to_remove),
            "following_to_unfollow_list": following_to_unfollow,
            "followers_to_remove_list": followers_to_remove,
        }

