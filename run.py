import json
import time
import random
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

from pinterest_poster import post_pin_for_account
from utils.image_helper import validate_image, cleanup_temp_images

CONFIG_FILE = Path("config.json")
TEMPLATE_FILE = Path("config_template.json")

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        if TEMPLATE_FILE.exists():
            import shutil
            shutil.copy(TEMPLATE_FILE, CONFIG_FILE)
            print(f"\n[Info] 'config.json' not found. Created a fresh 'config.json' from template.")
            print(f"[Action Required] Open 'config.json', fill in your 7 session IDs, photo path, title, etc., then run this script again.\n")
            sys.exit(0)
        else:
            raise FileNotFoundError("Neither 'config.json' nor 'config_template.json' found.")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def countdown_delay(seconds: int):
    """Clean countdown timer between account postings."""
    print(f"\nWaiting {seconds} seconds before next account to protect against anti-spam bans...")
    for remaining in range(seconds, 0, -1):
        sys.stdout.write(f"\rNext post in: {remaining}s remaining... ")
        sys.stdout.flush()
        time.sleep(1)
    print("\rResuming automation now!               \n")

def main():
    print("=" * 65)
    print("      PINTEREST 7-ACCOUNT AUTOMATION SYSTEM (PLAYWRIGHT)      ")
    print("=" * 65)

    config = load_config()
    accounts = config.get("accounts", [])
    post_data = config.get("post_data", {})
    settings = config.get("settings", {})

    # Validate image path first
    image_path = post_data.get("image_path", "")
    try:
        validated_img = validate_image(image_path)
        print(f"[OK] Image verified: {validated_img.name} ({validated_img.stat().st_size // 1024} KB)")
    except Exception as e:
        print(f"\n[Error] Invalid image path: {e}")
        print("Please check 'image_path' in config.json.\n")
        sys.exit(1)

    print(f"[OK] Title: {post_data.get('title', '')[:50]}")
    print(f"[OK] Link: {post_data.get('destination_link', '')}")
    print(f"[OK] Total Accounts configured: {len(accounts)}")
    print("-" * 65)

    headless = settings.get("headless", False)
    delay_base = settings.get("delay_between_accounts_seconds", 30)
    delay_jitter = settings.get("random_delay_jitter", 15)

    results = []

    with sync_playwright() as p:
        # Launch Chromium browser with realistic flags
        browser = p.chromium.launch(
            headless=headless,
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
                    delay = delay_base + random.randint(0, delay_jitter)
                    countdown_delay(delay)

        finally:
            browser.close()
            cleanup_temp_images(image_path)

    # Print Final Summary
    print("\n" + "=" * 65)
    print("                    POSTING RUN SUMMARY                       ")
    print("=" * 65)
    for r in results:
        status_symbol = "[OK]" if r["status"] == "SUCCESS" else ("[SKIP]" if r["status"] == "SKIPPED" else "[FAIL]")
        print(f"{status_symbol} {r['account']:<15} | Status: {r['status']:<8} | {r['message']}")
    print("=" * 65)
    print("Automation completed.\n")

if __name__ == "__main__":
    main()
