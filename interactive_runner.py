import os
import sys
import time
import random
from pathlib import Path
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright

# Force UTF-8 encoding for Windows CMD / PowerShell
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pinterest_poster import post_pin_for_account
from utils.image_helper import validate_image, cleanup_temp_images

ENV_FILE = Path(".env")

def get_accounts_from_env() -> list:
    """Reads SESSION_ID_1..7 and BOARD_NAME_1..7 from .env file."""
    if not ENV_FILE.exists():
        return []
    
    env_vars = dotenv_values(ENV_FILE)
    accounts = []
    
    # Check accounts 1 to 20
    for i in range(1, 21):
        sess_key = f"SESSION_ID_{i}"
        board_key = f"BOARD_NAME_{i}"
        
        session_id = env_vars.get(sess_key, "").strip()
        board_name = env_vars.get(board_key, "").strip()
        
        # Check if session_id is present and not default placeholder
        if session_id and not session_id.startswith("PASTE_"):
            accounts.append({
                "name": f"Account {i}",
                "session_id": session_id,
                "board_name": board_name
            })
            
    return accounts

def get_settings_from_env() -> dict:
    env_vars = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    return {
        "headless": env_vars.get("HEADLESS", "false").lower() == "true",
        "delay_between_accounts_seconds": int(env_vars.get("DELAY_BETWEEN_ACCOUNTS", 30)),
        "random_delay_jitter": int(env_vars.get("RANDOM_JITTER", 15)),
        "alter_image_hash": env_vars.get("ALTER_IMAGE_HASH", "true").lower() == "true",
        "save_debug_screenshots": True
    }

def prompt_clean(label: str, required: bool = True) -> str:
    """Prompts for input and cleans quotes and whitespace."""
    while True:
        val = input(f"{label}: ").strip()
        # Clean Windows drag-and-drop quotes
        val = val.strip('"\'')
        if not val and required:
            print("  [!] This field cannot be empty. Please enter a value.")
            continue
        return val

def prompt_image_path() -> str:
    """Prompts for image path and validates existence and format."""
    while True:
        path_str = prompt_clean("\n[1] Photo Path (Drag & drop photo here or type path)")
        try:
            validated = validate_image(path_str)
            print(f"    [OK] Valid image detected: {validated.name} ({validated.stat().st_size // 1024} KB)")
            return str(validated)
        except Exception as e:
            print(f"    [Error] {e}. Please try again.")

def countdown_delay(seconds: int):
    """Clean countdown timer between accounts."""
    print(f"\nWaiting {seconds} seconds before next account to protect against anti-spam bans...")
    for remaining in range(seconds, 0, -1):
        sys.stdout.write(f"\rNext post in: {remaining}s remaining... ")
        sys.stdout.flush()
        time.sleep(1)
    print("\rResuming automation now!               \n")

def main():
    print("=" * 68)
    print("         📌 PINTEREST 7-ACCOUNT INSTANT POST LAUNCHER         ")
    print("=" * 68)

    accounts = get_accounts_from_env()
    
    if not accounts:
        print("\n[!] ERROR: No active accounts found in '.env' file!")
        print("    Kripya '.env' file ko Notepad me open karein aur kam se kam")
        print("    apne accounts ki 'SESSION_ID_1', 'SESSION_ID_2'... paste karein.")
        print("    File Location: " + str(ENV_FILE.resolve()))
        print("=" * 68)
        input("\nPress Enter to exit...")
        sys.exit(1)

    print(f"[✓] Successfully detected {len(accounts)} configured account(s) in .env:")
    for acc in accounts:
        board_info = f"Board: '{acc['board_name']}'" if acc['board_name'] else "Default 1st Board"
        print(f"    • {acc['name']} ({board_info})")

    # Interactive Inputs
    image_path = prompt_image_path()
    title = prompt_clean("\n[2] Pin Title")
    description = prompt_clean("\n[3] Pin Description (Caption)", required=False)
    hashtags = prompt_clean("\n[4] Hashtags (e.g. #homedecor #aesthetic #diy)", required=False)
    link = prompt_clean("\n[5] Destination Link (Website/Product URL)", required=False)

    # Pre-Flight Review
    print("\n" + "=" * 68)
    print("                    PRE-FLIGHT CONFIRMATION                   ")
    print("=" * 68)
    print(f"  • Photo:       {Path(image_path).name}")
    print(f"  • Title:       {title}")
    desc_preview = description if len(description) < 60 else description[:57] + "..."
    print(f"  • Description: {desc_preview or '(None)'}")
    print(f"  • Hashtags:    {hashtags or '(None)'}")
    print(f"  • Target Link: {link or '(None)'}")
    print(f"  • Accounts:    Posting to ALL {len(accounts)} account(s) sequentially")
    print("=" * 68)

    confirm = input("\nReady to post on all accounts? (Y / N): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("\n[!] Posting cancelled by user. Nothing was posted.")
        input("\nPress Enter to exit...")
        sys.exit(0)

    post_data = {
        "image_path": image_path,
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "destination_link": link
    }
    settings = get_settings_from_env()

    print("\n[🚀] Starting Pinterest Automation Engine...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=settings.get("headless", False),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage"
            ]
        )

        try:
            for idx, account in enumerate(accounts):
                res = post_pin_for_account(
                    browser=browser,
                    account_info=account,
                    account_index=idx,
                    post_data=post_data,
                    settings=settings
                )
                results.append(res)

                # Delay between accounts (except after last account)
                if idx < len(accounts) - 1 and res["status"] == "SUCCESS":
                    delay = settings["delay_between_accounts_seconds"] + random.randint(0, settings["random_delay_jitter"])
                    countdown_delay(delay)

        finally:
            browser.close()
            cleanup_temp_images(image_path)

    # Final Summary
    print("\n" + "=" * 68)
    print("                     FINAL POSTING SUMMARY                     ")
    print("=" * 68)
    for r in results:
        status_symbol = "[✓ OK]" if r["status"] == "SUCCESS" else ("[SKIP]" if r["status"] == "SKIPPED" else "[✗ FAIL]")
        print(f"{status_symbol} {r['account']:<14} | Status: {r['status']:<8} | {r['message']}")
    print("=" * 68)
    print("All tasks completed successfully.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
