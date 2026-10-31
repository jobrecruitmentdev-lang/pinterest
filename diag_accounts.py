from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from utils.stealth_browser import create_stealth_context

env = dotenv_values('.env')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for i in range(1, 8):
        sess = env.get(f'SESSION_ID_{i}', '')
        if not sess:
            continue
        context = create_stealth_context(browser, sess)
        page = context.new_page()
        page.goto('https://in.pinterest.com/settings/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        
        # Check current URL or username on settings page
        username_el = page.locator('#username, input[name="username"]').first
        username_val = username_el.input_value() if username_el.is_visible() else "Unknown"
        print(f"Account {i}: Settings URL={page.url} | Username={username_val}")
        context.close()
    browser.close()
