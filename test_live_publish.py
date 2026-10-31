import time
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from utils.stealth_browser import create_stealth_context

env = dotenv_values('.env')
sess = env['SESSION_ID_1']

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    c = create_stealth_context(b, sess)
    page = c.new_page()
    page.goto('https://in.pinterest.com/pin-builder/', wait_until='domcontentloaded')
    page.wait_for_timeout(4000)
    
    # Dismiss popup
    got_it = page.locator('button:has-text("Got it")')
    if got_it.count() > 0 and got_it.first.is_visible():
        got_it.first.click()
        page.wait_for_timeout(1000)
        
    # Upload image
    fi = page.locator('input[type="file"]').first
    fi.set_input_files(r'C:\Users\Dell\Downloads\iphone_30.png')
    page.wait_for_timeout(4000)
    
    # 1. Title
    t_el = page.locator('textarea[placeholder*="title" i], [id*="pin-draft-title"]').first
    t_el.fill('Best Iphone 2026')
    print("Title filled")
    
    # 2. Description (Clean - No hashtags appended!)
    d_el = page.locator('div[contenteditable="true"][aria-label*="about" i]').first
    d_el.click()
    page.keyboard.insert_text('An iphone is a line of touchscreen smartphones designed by Apple.')
    print("Description filled")
    
    # 3. Link
    l_el = page.locator('textarea[placeholder*="destination" i], [id*="pin-draft-link"]').first
    l_el.fill('https://jobrecruitment.in/jobs')
    print("Link filled")
    
    # 4. Tagged topics
    tag_inp = page.locator('#combobox-storyboard-interest-tags, input[placeholder*="Search for a tag" i]')
    if tag_inp.count() > 0 and tag_inp.first.is_visible():
        for tag in ['iphone', 'smartphone']:
            try:
                tag_inp.first.click()
                tag_inp.first.fill(tag)
                page.wait_for_timeout(1500)
                option = page.locator('[role="listbox"] [role="option"], div[id*="suggestion"]').first
                if option.is_visible():
                    option.click()
                    print(f"Added tag: {tag}")
                    page.wait_for_timeout(1000)
            except Exception as e:
                print(f"Tag error: {e}")
                
    # 5. Check Board
    # Check if 'Iphone' is already the current board text
    current_board_btn = page.locator('button:has-text("Publish")').first.locator('xpath=preceding-sibling::button | ../div//button').first
    if current_board_btn.is_visible():
        print("Current board button text:", current_board_btn.inner_text().strip())
    else:
        print("Board button not directly next to publish, checking board area...")
        
    # 6. Wait for publish button to be active
    publish_btn = page.locator('button:has-text("Publish")').first
    print("Initial publish button text:", publish_btn.inner_text())
    
    # Click publish
    print("Clicking Publish...")
    publish_btn.click()
    
    # Watch for 30 seconds for Pinterest response
    print("Watching for live publish confirmation...")
    for sec in range(1, 35):
        page.wait_for_timeout(1000)
        url = page.url
        # Check for success indicators
        see_pin = page.locator('text="See your Pin", text="Your Pin is live", text="Saved to", text="View Pin", [data-test-id="toast"]')
        if see_pin.count() > 0 and see_pin.first.is_visible():
            print(f"SUCCESS CONFIRMATION FOUND at second {sec}: '{see_pin.first.inner_text().strip()}'")
            break
        if "pin/" in url:
            print(f"SUCCESS REDIRECT to live pin URL at second {sec}: {url}")
            break
        if sec % 5 == 0:
            print(f"  ...waiting ({sec}s) - current URL: {url}")
            
    page.screenshot(path='debug_screenshots/live_publish_test.png')
    print("Saved screenshot to debug_screenshots/live_publish_test.png")
    b.close()
