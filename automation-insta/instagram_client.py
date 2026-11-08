"""
Instagram Client Manager
Handles authentication, session caching, 2FA, challenges, proxy, and rate-safe requests.
"""

import json
import logging
import os
import sys
import time
from typing import Dict, Optional, Tuple

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    FeedbackRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    RateLimitError,
    TwoFactorRequired,
)
from instagrapi.mixins.challenge import ChallengeChoice
from instagrapi.types import User, UserShort

import config

logger = logging.getLogger("InstagramClient")


def interactive_challenge_handler(username: str, choice: ChallengeChoice) -> str:
    """Prompt user interactively in the terminal for challenge verification codes."""
    if choice == ChallengeChoice.SMS:
        print(f"\n[!] Instagram sent an SMS security code to the phone on account '{username}'.")
    elif choice == ChallengeChoice.EMAIL:
        print(f"\n[!] Instagram sent an email security code to the address on account '{username}'.")
    else:
        print(f"\n[!] Instagram requires security verification for '{username}'.")

    code = input(">> Enter verification code: ").strip()
    return code


class InstagramManagerClient:
    def __init__(self, proxy: Optional[str] = None):
        self.client = Client()
        self.proxy = proxy or config.INSTA_PROXY
        if self.proxy:
            logger.info(f"Setting proxy: {self.proxy}")
            self.client.set_proxy(self.proxy)

        # Register challenge handler for SMS / Email checkpoints
        self.client.challenge_code_handler = interactive_challenge_handler
        self.user_id = None
        self.username = None

    def load_cached_session(self) -> bool:
        """Attempt to restore an existing login session from file without re-authenticating."""
        if not config.SESSION_FILE.exists():
            return False

        try:
            logger.info("Found existing session. Attempting to restore...")
            self.client.load_settings(config.SESSION_FILE)
            if self.proxy:
                self.client.set_proxy(self.proxy)

            # Validate whether the session is still active
            user_info = self.client.account_info()
            self.user_id = str(user_info.pk)
            self.username = user_info.username
            logger.info(f"Successfully restored session for @{self.username} (ID: {self.user_id})")
            return True
        except (LoginRequired, Exception) as e:
            logger.warning(f"Cached session was expired or invalid: {e}")
            if config.SESSION_FILE.exists():
                try:
                    os.remove(config.SESSION_FILE)
                except OSError:
                    pass
            return False

    def save_session(self):
        """Save active session cookies and state to disk."""
        try:
            self.client.dump_settings(config.SESSION_FILE)
            logger.info(f"Saved session configuration to {config.SESSION_FILE}")
        except Exception as e:
            logger.error(f"Failed to save session settings: {e}")

    def login_with_credentials(self, username: str, password: str, verification_code: str = "") -> bool:
        """Authenticate with username and password, handling 2FA if required."""
        self.username = username
        try:
            logger.info(f"Logging in as @{username}...")
            self.client.login(username, password, verification_code=verification_code)
            self.user_id = str(self.client.user_id)
            self.save_session()
            logger.info(f"Login successful for @{self.username}!")
            return True
        except TwoFactorRequired:
            print("\n[!] Instagram Security Checkpoint / 2FA Triggered!")
            print("[i] Even if you didn't enable 2FA in settings, Instagram sends a 6-digit verification")
            print("    code via SMS to your phone number or to your registered email for new device logins.")
            code = input(">> Enter 6-digit verification code from SMS or Email: ").strip()
            try:
                self.client.login(username, password, verification_code=code)
                self.user_id = str(self.client.user_id)
                self.save_session()
                logger.info(f"Verification login successful for @{self.username}!")
                return True
            except Exception as e2fa:
                logger.error(f"Verification code authentication failed: {e2fa}")
                raise
        except BadPassword:
            logger.error("Incorrect password provided.")
            raise
        except FeedbackRequired as e:
            logger.error(f"Instagram Action Block / Feedback Required: {e}")
            raise
        except ChallengeRequired as e:
            logger.error(f"Instagram Checkpoint Challenge triggered: {e}")
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise

    def login_with_sessionid(self, sessionid: str) -> bool:
        """Authenticate using raw sessionid cookie (useful if 2FA or passkeys bypass is needed)."""
        try:
            logger.info("Attempting login via sessionid cookie...")
            self.client.login_by_sessionid(sessionid.strip())
            user_info = self.client.account_info()
            self.user_id = str(user_info.pk)
            self.username = user_info.username
            self.save_session()
            logger.info(f"Successfully authenticated via sessionid as @{self.username}!")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with sessionid: {e}")
            raise

    def get_my_info(self) -> User:
        """Get account profile info for the logged-in user."""
        if not self.user_id:
            raise LoginRequired("You must be logged in.")
        return self.client.user_info(self.user_id)

    def fetch_followers(self, amount: int = 0) -> Dict[str, UserShort]:
        """
        Fetch account followers.
        amount=0 fetches all followers.
        """
        if not self.user_id:
            raise LoginRequired("You must be logged in.")
        logger.info(f"Fetching followers for @{self.username} (amount={'ALL' if amount == 0 else amount})...")
        followers = self.client.user_followers(self.user_id, amount=amount)
        logger.info(f"Successfully fetched {len(followers)} followers.")
        return followers

    def fetch_following(self, amount: int = 0) -> Dict[str, UserShort]:
        """
        Fetch accounts followed by current user.
        amount=0 fetches all following.
        """
        if not self.user_id:
            raise LoginRequired("You must be logged in.")
        logger.info(f"Fetching following for @{self.username} (amount={'ALL' if amount == 0 else amount})...")
        following = self.client.user_following(self.user_id, amount=amount)
        logger.info(f"Successfully fetched {len(following)} following.")
        return following

    def fetch_user_info(self, target_user_id: str) -> Optional[User]:
        """Fetch detailed info for a single user."""
        try:
            return self.client.user_info(target_user_id)
        except Exception as e:
            logger.warning(f"Could not fetch full user info for ID {target_user_id}: {e}")
            return None

    def unfollow(self, target_user_id: str) -> bool:
        """Unfollow a target user."""
        try:
            return self.client.user_unfollow(str(target_user_id))
        except FeedbackRequired as e:
            logger.critical(f"Instagram Action Block detected on unfollow: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to unfollow user {target_user_id}: {e}")
            raise

    def remove_follower(self, target_user_id: str) -> bool:
        """Remove a follower from following your account (without blocking them)."""
        try:
            return self.client.user_remove_follower(str(target_user_id))
        except FeedbackRequired as e:
            logger.critical(f"Instagram Action Block detected on remove follower: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to remove follower {target_user_id}: {e}")
            raise

    def clear_session(self):
        """Clear local session file."""
        if config.SESSION_FILE.exists():
            try:
                os.remove(config.SESSION_FILE)
                logger.info("Session file removed.")
            except OSError as e:
                logger.error(f"Could not remove session file: {e}")

