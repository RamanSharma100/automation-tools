"""
Instagram Follower & Following Manager - Main Entry Point
Supports both Interactive Terminal GUI and CLI Automation Mode (for cron/scripts).
"""

import argparse
import sys

from analyzer import add_to_whitelist, load_whitelist
from cli import InteractiveCLI, banner, print_error, print_info, print_success
from instagram_client import InstagramManagerClient
from manager import InstagramAutomationManager
from analyzer import AccountAuditor
import config


def run_cli_mode(args):
    """Run non-interactive command-line automation."""
    client = InstagramManagerClient()

    # Attempt login via cached session or environment credentials
    if not client.load_cached_session():
        if config.INSTA_SESSIONID:
            try:
                client.login_with_sessionid(config.INSTA_SESSIONID)
            except Exception as e:
                print_error(f"Automated login via sessionid failed: {e}")
                sys.exit(1)
        elif config.INSTA_USERNAME and config.INSTA_PASSWORD:
            try:
                client.login_with_credentials(config.INSTA_USERNAME, config.INSTA_PASSWORD)
            except Exception as e:
                print_error(f"Automated login failed: {e}")
                sys.exit(1)
        else:
            print_error("No saved session or .env credentials found. Run 'python main.py' interactively first to log in.")
            sys.exit(1)

    automation = InstagramAutomationManager(client)
    print_info(f"Connected as @{client.username}")

    print_info("Fetching account relationship data...")
    followers = client.fetch_followers()
    following = client.fetch_following()
    auditor = AccountAuditor(followers, following)

    if args.mode == "audit":
        summary = auditor.generate_summary()
        print_info(f"Audit Complete: Followers={summary['total_followers']}, Following={summary['total_following']}, Non-Followers={summary['total_non_followers']}")
        auditor.export_to_csv("non_followers.csv", auditor.get_non_followers(apply_whitelist=False))
        auditor.export_to_csv("mutuals.csv", auditor.get_mutuals())
        auditor.export_to_csv("fans.csv", auditor.get_fans())
        ghosts = auditor.detect_quick_ghost_followers(apply_whitelist=False)
        auditor.export_to_csv("ghost_followers.csv", [u for u, _ in ghosts], extra_columns={str(u.pk): r for u, r in ghosts})
        print_success(f"CSV reports updated in '{config.REPORTS_DIR}'")

    elif args.mode == "unfollow":
        non_followers = auditor.get_non_followers(apply_whitelist=True)
        dry_run = not args.live
        limit = args.limit or config.DEFAULT_MAX_ACTIONS_PER_RUN
        print_info(f"Targeting up to {limit} non-followers. Dry Run = {dry_run}")
        success, failed = automation.unfollow_users(non_followers, limit=limit, dry_run=dry_run)
        print_success(f"Unfollow job completed. Success: {success}, Failed: {failed}")

    elif args.mode == "remove-ghosts":
        ghosts = auditor.detect_quick_ghost_followers(apply_whitelist=True)
        dry_run = not args.live
        limit = args.limit or config.DEFAULT_MAX_ACTIONS_PER_RUN
        print_info(f"Targeting up to {limit} ghost followers. Dry Run = {dry_run}")
        success, failed = automation.remove_ghost_followers(ghosts, limit=limit, dry_run=dry_run)
        print_success(f"Ghost removal job completed. Success: {success}, Failed: {failed}")

    elif args.mode in ("strict-following", "strict-followers", "strict-all"):
        stats = auditor.get_strict_keep_summary()
        dry_run = not args.live
        limit = args.limit or config.DEFAULT_MAX_ACTIONS_PER_RUN
        print_info(f"=== STRICT KEEP-LIST MODE (Keep {stats['whitelist_total']} names in whitelist.txt) ===")
        print_info(f"Following: {stats['current_following']} total | Kept: {stats['following_kept']} | To Unfollow: {stats['following_to_unfollow']}")
        print_info(f"Followers: {stats['current_followers']} total | Kept: {stats['followers_kept']} | To Remove: {stats['followers_to_remove']}")

        if args.mode in ("strict-following", "strict-all"):
            to_unfollow = stats["following_to_unfollow_list"]
            print_info(f"Processing up to {limit} excess following. Dry Run = {dry_run}")
            s_u, f_u = automation.unfollow_users(to_unfollow, limit=limit, dry_run=dry_run)
            print_success(f"Following purge completed. Success: {s_u}, Failed: {f_u}")

        if args.mode in ("strict-followers", "strict-all"):
            to_remove = [(u, "Not in whitelist keep-list") for u in stats["followers_to_remove_list"]]
            print_info(f"Processing up to {limit} excess followers. Dry Run = {dry_run}")
            s_r, f_r = automation.remove_ghost_followers(to_remove, limit=limit, dry_run=dry_run)
            print_success(f"Followers purge completed. Success: {s_r}, Failed: {f_r}")


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Follower & Following Automation Manager",
        epilog="Run without arguments for interactive menu mode."
    )
    parser.add_argument(
        "--mode",
        choices=["audit", "unfollow", "remove-ghosts", "strict-following", "strict-followers", "strict-all"],
        help="Automation mode to run non-interactively."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=config.DEFAULT_MAX_ACTIONS_PER_RUN,
        help=f"Maximum number of accounts to process per run (default: {config.DEFAULT_MAX_ACTIONS_PER_RUN})."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute real actions on Instagram. If omitted, runs safely in simulation (DRY-RUN) mode."
    )
    parser.add_argument(
        "--add-whitelist",
        type=str,
        help="Add a username to the protected whitelist."
    )

    args = parser.parse_args()

    # Quick command: Add to whitelist
    if args.add_whitelist:
        if add_to_whitelist(args.add_whitelist):
            print_success(f"Added @{args.add_whitelist} to whitelist.txt")
        else:
            print_info(f"@{args.add_whitelist} is already whitelisted.")
        return

    # Non-interactive CLI Mode
    if args.mode:
        run_cli_mode(args)
        return

    # Default: Interactive Terminal UI
    app = InteractiveCLI()
    app.start()


if __name__ == "__main__":
    main()

