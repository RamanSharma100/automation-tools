"""
Interactive Command Line Interface for Instagram Follower & Following Manager
"""

import getpass
import os
import sys
from typing import Dict, List, Optional, Tuple

import colorama
from colorama import Fore, Style
from tabulate import tabulate

import config
from analyzer import (
    AccountAuditor,
    add_to_whitelist,
    load_whitelist,
    remove_from_whitelist,
)
from instagram_client import InstagramManagerClient
from manager import InstagramAutomationManager

colorama.init(autoreset=True)


def banner():
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print(r"""
  ╔═══════════════════════════════════════════════════════════════╗
  ║          INSTAGRAM FOLLOWER & FOLLOWING MANAGER               ║
  ║           Clean Ghost Followers & Non-Followers Safely        ║
  ╚═══════════════════════════════════════════════════════════════╝
    """)


def print_info(msg: str):
    print(f"{Fore.CYAN}[i] {msg}")


def print_success(msg: str):
    print(f"{Fore.GREEN}[✓] {msg}")


def print_warning(msg: str):
    print(f"{Fore.YELLOW}[!] {msg}")


def print_error(msg: str):
    print(f"{Fore.RED}[✗] {msg}")


class InteractiveCLI:
    def __init__(self):
        self.client = InstagramManagerClient()
        self.automation = InstagramAutomationManager(self.client)
        self.followers = None
        self.following = None
        self.auditor = None

    def authenticate(self) -> bool:
        """Handle login interactively or through saved session / env vars."""
        banner()

        # Step 1: Check cached session
        print_info("Checking for saved session...")
        if self.client.load_cached_session():
            print_success(f"Restored active session for @{self.client.username}")
            return True

        # Step 2: Check INSTA_SESSIONID in .env
        if config.INSTA_SESSIONID:
            print_info("Logging in using INSTA_SESSIONID from .env...")
            try:
                if self.client.login_with_sessionid(config.INSTA_SESSIONID):
                    print_success(f"Logged in via sessionid as @{self.client.username}")
                    return True
            except Exception as e:
                print_error(f"Sessionid login failed: {e}")

        # Step 3: Check .env credentials
        username = config.INSTA_USERNAME
        password = config.INSTA_PASSWORD

        if not username or not password:
            print(f"\n{Fore.YELLOW}No active session found. Please enter your Instagram credentials.")
            print(f"{Fore.WHITE}(Credentials are kept local on your machine and never shared){Style.RESET_ALL}\n")
            print("Login Methods:")
            print(" [1] Username & Password (standard)")
            print(" [2] Browser sessionid cookie (bypasses password & 2FA prompts)")
            choice = input("\nSelect login method [1/2] (default: 1): ").strip()

            if choice == "2":
                sid = input("Paste your Instagram 'sessionid' cookie: ").strip()
                try:
                    return self.client.login_with_sessionid(sid)
                except Exception as e:
                    print_error(f"Cookie authentication failed: {e}")
                    return False
            else:
                username = input("Instagram Username: ").strip()
                password = getpass.getpass("Instagram Password: ").strip()

        try:
            return self.client.login_with_credentials(username, password)
        except Exception as e:
            print_error(f"Login failed: {e}")
            return False

    def ensure_data_loaded(self, force_refresh: bool = False):
        """Fetch followers and following if not already in memory."""
        if self.followers is None or self.following is None or force_refresh:
            print(f"\n{Fore.CYAN}Fetching your followers and following lists from Instagram...")
            print(f"{Fore.YELLOW}Depending on your account size, this may take a few seconds...")
            self.followers = self.client.fetch_followers()
            self.following = self.client.fetch_following()
            self.auditor = AccountAuditor(self.followers, self.following)
            print_success(f"Loaded {len(self.followers)} followers and {len(self.following)} following.")

    def run_audit(self):
        """Run a full account audit, display metrics, and export reports."""
        self.ensure_data_loaded()
        summary = self.auditor.generate_summary()

        print(f"\n{Fore.GREEN}{Style.BRIGHT}================ ACCOUNT AUDIT SUMMARY ================")
        table_data = [
            ["Total Followers", summary["total_followers"]],
            ["Total Following", summary["total_following"]],
            ["Mutual Friends (Follow Each Other)", summary["mutual_friends"]],
            ["Non-Followers (Don't Follow Back)", summary["total_non_followers"]],
            ["Protected by Whitelist / Verified", summary["whitelisted_protected"]],
            ["Actionable Non-Followers", summary["actionable_non_followers"]],
            ["Fans (Follow You, You Don't Follow)", summary["fans"]],
            ["Flagged Ghost/Bot Followers (Quick)", summary["quick_ghost_followers"]],
        ]
        print(tabulate(table_data, headers=["Metric", "Count"], tablefmt="fancy_grid"))

        # Export CSVs
        print_info("Exporting detailed CSV reports...")
        non_followers = self.auditor.get_non_followers(apply_whitelist=False)
        self.auditor.export_to_csv("non_followers.csv", non_followers)

        mutuals = self.auditor.get_mutuals()
        self.auditor.export_to_csv("mutuals.csv", mutuals)

        fans = self.auditor.get_fans()
        self.auditor.export_to_csv("fans.csv", fans)

        ghosts = self.auditor.detect_quick_ghost_followers(apply_whitelist=False)
        ghost_users = [u for u, _ in ghosts]
        ghost_reasons = {str(u.pk): r for u, r in ghosts}
        self.auditor.export_to_csv("ghost_followers.csv", ghost_users, extra_columns=ghost_reasons)

        print_success(f"Reports successfully saved to '{config.REPORTS_DIR}' directory:")
        print(f"  - reports/non_followers.csv")
        print(f"  - reports/ghost_followers.csv")
        print(f"  - reports/mutuals.csv")
        print(f"  - reports/fans.csv")

    def view_non_followers(self):
        """Display a list of users who don't follow back."""
        self.ensure_data_loaded()
        non_followers = self.auditor.get_non_followers(apply_whitelist=True)

        if not non_followers:
            print_success("Awesome! Everyone you follow follows you back (or are whitelisted).")
            return

        print(f"\n{Fore.CYAN}Found {len(non_followers)} actionable accounts who do not follow you back.")
        limit_str = input("How many accounts to preview? (default: 20, 'all' to show all): ").strip().lower()

        display_count = len(non_followers) if limit_str == "all" else (int(limit_str) if limit_str.isdigit() else 20)
        preview = non_followers[:display_count]

        rows = []
        for idx, u in enumerate(preview, 1):
            badge = " [Verified]" if u.is_verified else (" [Private]" if u.is_private else "")
            rows.append([idx, f"@{u.username}{badge}", u.full_name or "N/A", u.pk])

        print(tabulate(rows, headers=["#", "Username", "Name", "User ID"], tablefmt="simple"))
        if len(non_followers) > display_count:
            print(f"... and {len(non_followers) - display_count} more (full list in reports/non_followers.csv)")

    def unfollow_flow(self):
        """Guide user through safely unfollowing non-followers."""
        self.ensure_data_loaded()
        non_followers = self.auditor.get_non_followers(apply_whitelist=True)

        if not non_followers:
            print_success("No actionable non-followers found to unfollow.")
            return

        print(f"\n{Fore.YELLOW}Found {len(non_followers)} accounts who do NOT follow you back.")
        print(f"{Fore.WHITE}Accounts in whitelist.txt and verified accounts are automatically protected.")

        limit_input = input(f"\nHow many accounts to unfollow in this run? (Max recommended: 25-30, default: 20): ").strip()
        limit = int(limit_input) if limit_input.isdigit() else 20

        mode_input = input("\nRun in DRY-RUN mode first to simulate? [Y/n] (Recommended: Y): ").strip().lower()
        dry_run = mode_input != "n"

        if not dry_run:
            confirm = input(f"{Fore.RED}{Style.BRIGHT}WARNING: You are about to LIVE UNFOLLOW up to {limit} accounts. Proceed? [yes/NO]: ").strip()
            if confirm.lower() != "yes":
                print_info("Live unfollow cancelled.")
                return

        success, fail = self.automation.unfollow_users(
            targets=non_followers,
            limit=limit,
            dry_run=dry_run,
        )

        if dry_run:
            print_success(f"Dry run complete. Simulated {success} unfollows. Check console output above.")
            print_info("To execute for real, run again and answer 'n' to dry-run.")
        else:
            print_success(f"Completed! Successfully unfollowed: {success}, Failed: {fail}")
            # Refresh memory
            self.following = None

    def remove_ghosts_flow(self):
        """Guide user through detecting and removing spam/ghost followers."""
        self.ensure_data_loaded()
        ghosts = self.auditor.detect_quick_ghost_followers(apply_whitelist=True)

        if not ghosts:
            print_success("No obvious ghost/spam followers detected with default profile pictures or spam formats.")
            return

        print(f"\n{Fore.YELLOW}Detected {len(ghosts)} suspicious / ghost followers:")
        rows = []
        for idx, (u, reason) in enumerate(ghosts[:15], 1):
            rows.append([idx, f"@{u.username}", reason])
        print(tabulate(rows, headers=["#", "Account", "Reason Detected"], tablefmt="simple"))

        limit_input = input(f"\nHow many ghost followers to remove? (default: 15): ").strip()
        limit = int(limit_input) if limit_input.isdigit() else 15

        mode_input = input("\nRun in DRY-RUN mode first? [Y/n]: ").strip().lower()
        dry_run = mode_input != "n"

        if not dry_run:
            confirm = input(f"{Fore.RED}{Style.BRIGHT}WARNING: This will remove up to {limit} followers from your account. Proceed? [yes/NO]: ").strip()
            if confirm.lower() != "yes":
                print_info("Removal cancelled.")
                return

        success, fail = self.automation.remove_ghost_followers(
            targets=ghosts,
            limit=limit,
            dry_run=dry_run,
        )

        if dry_run:
            print_success(f"Dry run complete. Simulated removing {success} followers.")
        else:
            print_success(f"Completed! Removed {success} followers, Failed: {fail}")
            self.followers = None

    def strict_keep_purge_flow(self):
        """
        STRICT KEEP-LIST MODE:
        Keep ONLY accounts listed in whitelist.txt.
        All others in following or followers are removed.
        """
        self.ensure_data_loaded()
        stats = self.auditor.get_strict_keep_summary()

        print(f"\n{Fore.CYAN}{Style.BRIGHT}================ STRICT KEEP-LIST PURGE MODE ================")
        print(f"{Fore.WHITE}Target Keep-List (whitelist.txt): {Fore.YELLOW}{stats['whitelist_total']} accounts defined")

        table = [
            ["Current Following", stats["current_following"]],
            ["Following to KEEP (in whitelist.txt)", f"{Fore.GREEN}{stats['following_kept']}{Style.RESET_ALL}"],
            ["Following to UNFOLLOW (not in whitelist.txt)", f"{Fore.RED}{stats['following_to_unfollow']}{Style.RESET_ALL}"],
            ["Current Followers", stats["current_followers"]],
            ["Followers to KEEP (in whitelist.txt)", f"{Fore.GREEN}{stats['followers_kept']}{Style.RESET_ALL}"],
            ["Followers to REMOVE (not in whitelist.txt)", f"{Fore.RED}{stats['followers_to_remove']}{Style.RESET_ALL}"],
        ]
        print(tabulate(table, headers=["Metric", "Count"], tablefmt="fancy_grid"))

        print("\nChoose an action:")
        print(" [1] 🎯 Clean Following (Unfollow all accounts NOT in whitelist.txt)")
        print(" [2] 🗑️ Clean Followers (Remove all followers NOT in whitelist.txt)")
        print(" [3] ⚡ Clean BOTH Following & Followers")
        print(" [4] 📁 Export CSV preview of accounts to be removed")
        print(" [0] ⬅️ Back to Main Menu")

        sub_choice = input(f"\n{Fore.YELLOW}Select an option [0-4]: {Style.RESET_ALL}").strip()

        if sub_choice == "4":
            self.auditor.export_to_csv("following_to_unfollow_strict.csv", stats["following_to_unfollow_list"])
            follower_reasons = {str(u.pk): "Not in keep-list" for u in stats["followers_to_remove_list"]}
            self.auditor.export_to_csv("followers_to_remove_strict.csv", stats["followers_to_remove_list"], extra_columns=follower_reasons)
            print_success(f"CSV previews exported to '{config.REPORTS_DIR}':")
            print("  - reports/following_to_unfollow_strict.csv")
            print("  - reports/followers_to_remove_strict.csv")
            return

        if sub_choice not in ("1", "2", "3"):
            return

        limit_input = input(f"\nHow many accounts to process in this run? (Safe limit: 20-30, default: 25): ").strip()
        limit = int(limit_input) if limit_input.isdigit() else 25

        mode_input = input("\nRun in DRY-RUN mode first to simulate? [Y/n] (Highly recommended: Y): ").strip().lower()
        dry_run = mode_input != "n"

        if not dry_run:
            print(f"\n{Fore.RED}{Style.BRIGHT}" + "!" * 58)
            print("  CRITICAL SAFETY WARNING: LIVE REMOVAL MODE")
            print("  This will modify your live Instagram account.")
            print("!" * 58 + f"{Style.RESET_ALL}")
            confirm = input("Type 'CONFIRM' to proceed with live execution: ").strip()
            if confirm != "CONFIRM":
                print_info("Live execution cancelled.")
                return

        # Execute Following
        if sub_choice in ("1", "3"):
            to_unfollow = stats["following_to_unfollow_list"]
            if not to_unfollow:
                print_success("Your following already perfectly matches your keep-list!")
            else:
                print(f"\n{Fore.YELLOW}--- Processing Following (Unfollow) ---")
                success, fail = self.automation.unfollow_users(
                    targets=to_unfollow,
                    limit=limit,
                    dry_run=dry_run,
                )
                if not dry_run:
                    self.following = None

        # Execute Followers
        if sub_choice in ("2", "3"):
            to_remove = [(u, "Not in whitelist keep-list") for u in stats["followers_to_remove_list"]]
            if not to_remove:
                print_success("Your followers already match your keep-list!")
            else:
                print(f"\n{Fore.YELLOW}--- Processing Followers (Remove) ---")
                success, fail = self.automation.remove_ghost_followers(
                    targets=to_remove,
                    limit=limit,
                    dry_run=dry_run,
                )
                if not dry_run:
                    self.followers = None

    def whitelist_menu(self):
        """Manage accounts that should never be unfollowed or removed."""
        while True:
            wl = load_whitelist()
            print(f"\n{Fore.CYAN}{Style.BRIGHT}--- Whitelist Manager (Protected Accounts) ---")
            print(f"Total whitelisted accounts: {len(wl)}")
            if wl:
                print(f"Accounts: {', '.join(sorted(list(wl))[:20])}" + ("..." if len(wl) > 20 else ""))

            print("\nOptions:")
            print(" [1] Add username to Whitelist")
            print(" [2] Remove username from Whitelist")
            print(" [3] View all whitelisted accounts")
            print(" [0] Back to Main Menu")

            choice = input("\nSelect option [0-3]: ").strip()
            if choice == "1":
                uname = input("Enter Instagram username to whitelist: ").strip()
                if add_to_whitelist(uname):
                    print_success(f"Added @{uname} to whitelist.")
                else:
                    print_warning(f"@{uname} is already in the whitelist.")
            elif choice == "2":
                uname = input("Enter Instagram username to remove: ").strip()
                if remove_from_whitelist(uname):
                    print_success(f"Removed @{uname} from whitelist.")
                else:
                    print_warning(f"@{uname} was not found in the whitelist.")
            elif choice == "3":
                if not wl:
                    print_info("Whitelist is currently empty.")
                else:
                    print("\n" + "\n".join(f" - @{u}" for u in sorted(wl)))
            elif choice == "0":
                break

    def view_history(self):
        """Display recent executed actions from log."""
        if not config.ACTION_LOG_FILE.exists():
            print_info("No action history recorded yet.")
            return

        with open(config.ACTION_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) <= 1:
            print_info("No action history recorded yet.")
            return

        print(f"\n{Fore.CYAN}--- Recent Actions Log (Last 15 records) ---")
        recent = lines[-15:]
        for line in recent:
            print("  " + line.strip())

    def start(self):
        """Main Interactive Menu Loop."""
        if not self.authenticate():
            print_error("Authentication could not be completed. Exiting.")
            sys.exit(1)

        while True:
            print(f"\n{Fore.MAGENTA}{Style.BRIGHT}" + "=" * 58)
            print(f"  INSTAGRAM MANAGER | Logged in as: @{self.client.username}")
            print("=" * 58)
            print(" [1] 📊 Run Account Audit & Generate CSV Reports")
            print(" [2] 🔒 Strict Keep-List Mode (Keep ONLY whitelist names, remove all others)")
            print(" [3] 🔍 View Non-Followers (Who doesn't follow back)")
            print(" [4] 🎯 Unfollow Non-Followers (with Dry-Run safety)")
            print(" [5] 👻 Scan & Remove Ghost/Spam Followers")
            print(" [6] 🛡️ View & Manage Whitelist (Protected Accounts)")
            print(" [7] 📜 View Action History Log")
            print(" [8] 🔄 Refresh Data from Instagram")
            print(" [9] 🚪 Log Out & Clear Session")
            print(" [0] ❌ Exit")

            choice = input(f"\n{Fore.YELLOW}Select an option [0-9]: {Style.RESET_ALL}").strip()

            try:
                if choice == "1":
                    self.run_audit()
                elif choice == "2":
                    self.strict_keep_purge_flow()
                elif choice == "3":
                    self.view_non_followers()
                elif choice == "4":
                    self.unfollow_flow()
                elif choice == "5":
                    self.remove_ghosts_flow()
                elif choice == "6":
                    self.whitelist_menu()
                elif choice == "7":
                    self.view_history()
                elif choice == "8":
                    self.ensure_data_loaded(force_refresh=True)
                elif choice == "9":
                    self.client.clear_session()
                    print_success("Session cleared. Exiting.")
                    break
                elif choice == "0":
                    print(f"\n{Fore.GREEN}Goodbye! Stay safe on Instagram.{Style.RESET_ALL}")
                    break
                else:
                    print_warning("Invalid choice. Please select an option between 0 and 9.")
            except KeyboardInterrupt:
                print("\n\nOperation interrupted by user. Returning to menu.")
            except Exception as e:
                print_error(f"An unexpected error occurred: {e}")

