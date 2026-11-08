"""
Automation Engine & Safety Runner
Executes unfollows and follower removals with rate-limiting, randomized delays, and safeguards.
"""

import csv
import logging
import random
import time
from datetime import datetime
from typing import List, Optional, Tuple

from instagrapi.exceptions import FeedbackRequired, PleaseWaitFewMinutes, RateLimitError
from instagrapi.types import UserShort

import config
from analyzer import load_whitelist
from instagram_client import InstagramManagerClient

logger = logging.getLogger("Manager")


def log_action_to_csv(action: str, username: str, user_id: str, status: str, note: str = ""):
    """Record all executed or simulated actions to a permanent audit log."""
    file_exists = config.ACTION_LOG_FILE.exists()
    with open(config.ACTION_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "action", "username", "user_id", "status", "note"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, username, user_id, status, note])


class InstagramAutomationManager:
    def __init__(self, client: InstagramManagerClient):
        self.client = client
        self.whitelist = load_whitelist()

    def unfollow_single(self, user: UserShort, dry_run: bool = False, delay_seconds: Optional[int] = None) -> bool:
        """Unfollow a single user safely with logging and delay."""
        uid = str(user.pk)
        uname = user.username

        if dry_run:
            print(f"  🔍 [DRY-RUN] Would unfollow: @{uname}")
            log_action_to_csv("UNFOLLOW", uname, uid, "SIMULATED", "Manual review dry-run")
            return True

        try:
            print(f"  🎯 Unfollowing @{uname}...", end="", flush=True)
            self.client.unfollow(uid)
            print(" OK.")
            log_action_to_csv("UNFOLLOW", uname, uid, "SUCCESS", "Manual review unfollow")
            sec = delay_seconds if delay_seconds is not None else random.randint(config.DEFAULT_DELAY_MIN, config.DEFAULT_DELAY_MAX)
            self.sleep_with_jitter(sec, sec + 5, "Safe delay")
            return True
        except Exception as e:
            print(f" FAILED: {e}")
            log_action_to_csv("UNFOLLOW", uname, uid, "FAILED", str(e))
            return False

    def sleep_with_jitter(self, min_seconds: int, max_seconds: int, message: str = "Waiting"):
        """Sleep with randomized jitter to emulate human behavior."""
        delay = round(random.uniform(min_seconds, max_seconds), 1)
        print(f"    ⏳ {message} ({delay}s)...", end="", flush=True)
        time.sleep(delay)
        print(" Done.")

    def unfollow_users(
        self,
        targets: List[UserShort],
        limit: int = config.DEFAULT_MAX_ACTIONS_PER_RUN,
        dry_run: bool = True,
        delay_min: int = config.DEFAULT_DELAY_MIN,
        delay_max: int = config.DEFAULT_DELAY_MAX,
    ) -> Tuple[int, int]:
        """
        Safely unfollow non-followers up to the specified limit.
        Returns: (success_count, failed_count)
        """
        self.whitelist = load_whitelist()
        actionable = []

        for user in targets:
            if user.username.lower() in self.whitelist:
                continue
            if config.SKIP_VERIFIED and user.is_verified:
                continue
            actionable.append(user)

        total_to_process = min(limit, len(actionable))
        if total_to_process == 0:
            print("\n[i] No eligible users to unfollow (all are protected by whitelist or criteria).")
            return 0, 0

        mode_str = "[DRY-RUN SIMULATION]" if dry_run else "[LIVE EXECUTION]"
        print(f"\n=======================================================")
        print(f" {mode_str} Unfollowing {total_to_process} Accounts")
        print(f" Safe delay between actions: {delay_min}s - {delay_max}s")
        print(f" Batch rest pause: every {config.BATCH_SIZE} actions")
        print(f"=======================================================\n")

        success_count = 0
        fail_count = 0

        for index, user in enumerate(actionable[:total_to_process], start=1):
            uid = str(user.pk)
            uname = user.username

            if dry_run:
                print(f"[{index}/{total_to_process}] 🔍 [DRY-RUN] Would unfollow: @{uname} (ID: {uid})")
                log_action_to_csv("UNFOLLOW", uname, uid, "SIMULATED", "Dry-run execution")
                success_count += 1
                time.sleep(0.3)  # Brief delay for smooth CLI display
                continue

            # Live Execution
            try:
                print(f"[{index}/{total_to_process}] 🎯 Unfollowing @{uname} (ID: {uid})...", end="", flush=True)
                self.client.unfollow(uid)
                print(" OK.")
                log_action_to_csv("UNFOLLOW", uname, uid, "SUCCESS", "Live unfollow completed")
                success_count += 1

                # If more actions remain, apply human delay
                if index < total_to_process:
                    # Check for batch rest pause
                    if index % config.BATCH_SIZE == 0:
                        print(f"\n    ☕ [Batch Pause] Completed {index} actions. Resting to keep account safe...")
                        self.sleep_with_jitter(config.BATCH_REST_MIN, config.BATCH_REST_MAX, "Resting batch pause")
                        print()
                    else:
                        self.sleep_with_jitter(delay_min, delay_max, "Cooldown interval")

            except FeedbackRequired as e:
                print(f"\n[!] ACTION BLOCKED by Instagram: {e}")
                print("[!] Instagram detected rapid actions. Halting immediately to protect your account!")
                log_action_to_csv("UNFOLLOW", uname, uid, "ACTION_BLOCKED", str(e))
                fail_count += 1
                break
            except (RateLimitError, PleaseWaitFewMinutes) as e:
                print(f"\n[!] Instagram rate limit reached: {e}")
                print("[!] Halting execution. Please wait a few hours before running again.")
                log_action_to_csv("UNFOLLOW", uname, uid, "RATE_LIMIT", str(e))
                fail_count += 1
                break
            except Exception as e:
                print(f" FAILED: {e}")
                log_action_to_csv("UNFOLLOW", uname, uid, "FAILED", str(e))
                fail_count += 1
                # Small pause after failure
                self.sleep_with_jitter(10, 20, "Error cooldown")

        return success_count, fail_count

    def remove_ghost_followers(
        self,
        targets: List[Tuple[UserShort, str]],
        limit: int = config.DEFAULT_MAX_ACTIONS_PER_RUN,
        dry_run: bool = True,
        delay_min: int = config.DEFAULT_DELAY_MIN,
        delay_max: int = config.DEFAULT_DELAY_MAX,
    ) -> Tuple[int, int]:
        """
        Safely remove ghost/spam followers from following your account.
        Returns: (success_count, failed_count)
        """
        self.whitelist = load_whitelist()
        actionable = [
            (user, reason) for user, reason in targets
            if user.username.lower() not in self.whitelist and not (config.SKIP_VERIFIED and user.is_verified)
        ]

        total_to_process = min(limit, len(actionable))
        if total_to_process == 0:
            print("\n[i] No ghost/spam followers found matching criteria.")
            return 0, 0

        mode_str = "[DRY-RUN SIMULATION]" if dry_run else "[LIVE EXECUTION]"
        print(f"\n=======================================================")
        print(f" {mode_str} Removing {total_to_process} Ghost/Bot Followers")
        print(f" Safe delay between actions: {delay_min}s - {delay_max}s")
        print(f" Batch rest pause: every {config.BATCH_SIZE} actions")
        print(f"=======================================================\n")

        success_count = 0
        fail_count = 0

        for index, (user, reason) in enumerate(actionable[:total_to_process], start=1):
            uid = str(user.pk)
            uname = user.username

            if dry_run:
                print(f"[{index}/{total_to_process}] 🔍 [DRY-RUN] Would remove follower: @{uname} (Reason: {reason})")
                log_action_to_csv("REMOVE_FOLLOWER", uname, uid, "SIMULATED", reason)
                success_count += 1
                time.sleep(0.3)
                continue

            # Live Execution
            try:
                print(f"[{index}/{total_to_process}] 🗑️ Removing follower @{uname} (Reason: {reason})...", end="", flush=True)
                self.client.remove_follower(uid)
                print(" OK.")
                log_action_to_csv("REMOVE_FOLLOWER", uname, uid, "SUCCESS", f"Removed: {reason}")
                success_count += 1

                if index < total_to_process:
                    if index % config.BATCH_SIZE == 0:
                        print(f"\n    ☕ [Batch Pause] Completed {index} actions. Resting to protect account...")
                        self.sleep_with_jitter(config.BATCH_REST_MIN, config.BATCH_REST_MAX, "Resting batch pause")
                        print()
                    else:
                        self.sleep_with_jitter(delay_min, delay_max, "Cooldown interval")

            except FeedbackRequired as e:
                print(f"\n[!] ACTION BLOCKED by Instagram: {e}")
                print("[!] Instagram detected rapid actions. Halting immediately to protect your account!")
                log_action_to_csv("REMOVE_FOLLOWER", uname, uid, "ACTION_BLOCKED", str(e))
                fail_count += 1
                break
            except (RateLimitError, PleaseWaitFewMinutes) as e:
                print(f"\n[!] Instagram rate limit reached: {e}")
                print("[!] Halting execution. Please wait before running again.")
                log_action_to_csv("REMOVE_FOLLOWER", uname, uid, "RATE_LIMIT", str(e))
                fail_count += 1
                break
            except Exception as e:
                print(f" FAILED: {e}")
                log_action_to_csv("REMOVE_FOLLOWER", uname, uid, "FAILED", str(e))
                fail_count += 1
                self.sleep_with_jitter(10, 20, "Error cooldown")

        return success_count, fail_count

