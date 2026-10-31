import time
import random
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

from utils.stealth_browser import create_stealth_context
from utils.image_helper import prepare_image_for_account, cleanup_temp_images

SCREENSHOTS_DIR = Path("debug_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    time.sleep(random.uniform(min_sec, max_sec))

def find_first_element(page: Page, selectors: list, timeout: int = 4000):
    """Tries multiple selectors and returns the first one that appears and is visible/attached."""
    for sel in selectors:
        try:
            elem = page.locator(sel).first
            elem.wait_for(state="attached", timeout=timeout)
            if elem.is_visible():
                return elem
        except Exception:
            continue
    return None

def dismiss_popups(page: Page):
    """Dismisses introductory tooltips or overlays like 'Got it', drafts sidebar, etc."""
    try:
        got_it_btn = page.locator('button:has-text("Got it")')
        if got_it_btn.count() > 0 and got_it_btn.first.is_visible():
            got_it_btn.first.click()
            random_delay(0.5, 1.0)
    except Exception:
        pass

    try:
        collapse_drafts = page.locator('[data-test-id="collapse-drafts-sidebar-button"], [aria-label="Close drafts sidebar"]')
        if collapse_drafts.count() > 0 and collapse_drafts.first.is_visible():
            collapse_drafts.first.click()
            random_delay(0.5, 1.0)
    except Exception:
        pass

def select_board(page: Page, board_name: str = "") -> bool:
    """Selects target board by name or keeps the default first board."""
    if not board_name:
        print("    [Board] Using default pre-selected board.")
        return True

    # 1. Check if the target board is already selected
    existing_board = page.locator(f'button:has-text("{board_name}"), div:has-text("{board_name}"):not(:has(div))')
    if existing_board.count() > 0 and existing_board.first.is_visible():
        print(f"    [Board] Target board '{board_name}' is already active/selected.")
        return True

    # 2. Try clicking board dropdown selector
    board_dropdown_selectors = [
        'div:has-text("Board"):not(:has(div)) + div',
        'div[data-tutorial-id*="board"]',
        '[data-test-id="board-dropdown-select-button"]',
        '[data-test-id="board-selector"]',
        'button[aria-haspopup="listbox"]',
        'button:has-text("Choose a board")',
        'button:has-text("Select")'
    ]
    
    dropdown_btn = find_first_element(page, board_dropdown_selectors, timeout=4000)
    if dropdown_btn:
        try:
            dropdown_btn.click()
            random_delay(1.0, 1.5)
            
            # Search board
            search_input = find_first_element(
                page, 
                ['input[placeholder*="Search" i]', 'input[aria-label*="Search" i]', '[data-test-id="board-search-input"]'],
                timeout=3000
            )
            if search_input:
                search_input.fill(board_name)
                random_delay(0.8, 1.2)
                
                match = page.locator(f'text="{board_name}"').first
                if match.is_visible():
                    match.click()
                    print(f"    [Board] Selected matched board: '{board_name}'")
                    return True

            # Fallback: Click first row in list
            first_row = find_first_element(
                page,
                ['[data-test-id="board-row"]', '[role="listbox"] [role="option"]', 'div[data-test-id*="board"]'],
                timeout=2500
            )
            if first_row:
                first_row.click()
                print("    [Board] Selected first available board.")
                return True
        except Exception as e:
            print(f"    [Board Note] Selection fallback: {e}")

    return True

def add_tagged_topics(page: Page, hashtags: str):
    """Adds tags to Pinterest's official 'Tagged topics' section."""
    if not hashtags:
        return

    # Parse tags (remove #, split on space/comma)
    tags = [t.strip().strip('#').strip() for t in re.split(r'[,#\s]+', hashtags) if t.strip().strip('#').strip()]
    if not tags:
        return

    tag_input = find_first_element(
        page,
        [
            '#combobox-storyboard-interest-tags',
            'input[placeholder*="Search for a tag" i]',
            'input[aria-label*="Search for a tag" i]'
        ],
        timeout=3000
    )
    if not tag_input:
        return

    print(f"  -> Adding {len(tags[:5])} Tagged Topic(s)...")
    for tag in tags[:5]:  # Add top 5 tags
        try:
            tag_input.click()
            random_delay(0.2, 0.4)
            tag_input.fill(tag)
            random_delay(1.0, 1.5)
            
            option = page.locator('[role="listbox"] [role="option"], div[id*="suggestion"]').first
            if option.is_visible():
                option.click()
                print(f"    [Tagged Topic] Added: '{tag}'")
                random_delay(0.6, 1.0)
            else:
                # Press enter if no popup suggestion
                tag_input.press("Enter")
        except Exception:
            continue

def wait_for_live_publish_confirmation(page: Page, max_wait_sec: int = 90) -> bool:
    """
    Waits for Pinterest to fully upload media and publish the Pin.
    Actively tracks 'Publishing... X%' progress and prevents premature browser closure.
    """
    last_progress_log = 0
    for sec in range(1, max_wait_sec + 1):
        page.wait_for_timeout(1000)
        url = page.url

        # Check for error banners / toasts
        err_toast = page.locator(':has-text("Oops"), :has-text("Failed to save"), :has-text("Something went wrong"), :has-text("Upload failed")')
        if err_toast.count() > 0 and err_toast.first.is_visible():
            err_text = err_toast.first.inner_text().strip()
            raise RuntimeError(f"Pinterest reported an error while publishing: '{err_text}'")

        # Check for success indicators
        # 1. Post-publish extension modal ("Find it. Love it. Save it")
        ext_modal = page.locator(':has-text("Find it. Love it. Save it"), button:has-text("Install now")')
        if ext_modal.count() > 0 and ext_modal.first.is_visible():
            print(f"  [Live Confirmation] Pin successfully created & saved to public board (Detected at {sec}s)!")
            page.wait_for_timeout(2500)
            return True

        # 2. Success toast or notification
        toast = page.locator(':has-text("Your Pin is live"), :has-text("Your Pin has been published"), :has-text("See your Pin"), :has-text("View Pin"), :has-text("Saved to"), [data-test-id="toast"]')
        if toast.count() > 0 and toast.first.is_visible():
            print(f"  [Live Confirmation] Success toast: '{toast.first.inner_text().strip()}' (at {sec}s)!")
            page.wait_for_timeout(2500)
            return True

        # 3. URL redirect to live pin
        if "/pin/" in url and "pin-creation-tool" not in url and "pin-builder" not in url:
            print(f"  [Live Confirmation] Redirected to live public Pin URL: {url} (at {sec}s)!")
            page.wait_for_timeout(2500)
            return True

        # 4. Check if upload is actively in progress (e.g. "Publishing... 17%")
        publishing_prog = page.locator(':has-text("Publishing...")')
        if publishing_prog.count() > 0 and publishing_prog.first.is_visible():
            prog_text = publishing_prog.first.inner_text().strip()
            if sec - last_progress_log >= 3:
                print(f"    ...Pinterest media uploading actively: {prog_text} ({sec}s)...")
                last_progress_log = sec
            continue

        # 5. Check if 'Publishing' button is in busy state
        publishing_btn = page.locator('button:has-text("Publishing")')
        if publishing_btn.count() > 0 and publishing_btn.first.is_visible():
            if sec - last_progress_log >= 5:
                print(f"    ...Pinterest publish in flight ({sec}s)...")
                last_progress_log = sec
            continue

        # 6. Check if canvas reset back to empty 'Upload your media' after publish
        upload_dropzone = page.locator(':has-text("Upload your media")')
        publish_btn = page.locator('button:has-text("Publish")')
        if sec > 12 and upload_dropzone.count() > 0 and upload_dropzone.first.is_visible() and (publish_btn.count() == 0 or not publish_btn.first.is_enabled()):
            print(f"  [Live Confirmation] Form cleared & reset to new pin state (Detected at {sec}s)!")
            page.wait_for_timeout(2500)
            return True

        if sec % 5 == 0:
            print(f"    ...waiting for live publish confirmation ({sec}s/{max_wait_sec}s)...")

    # If timeout is reached without live confirmation
    raise RuntimeError(
        f"Publish confirmation timed out after {max_wait_sec} seconds. "
        "The Pin upload may have taken too long or the network was interrupted."
    )

def post_pin_for_account(
    browser,
    account_info: dict,
    account_index: int,
    post_data: dict,
    settings: dict
) -> dict:
    """
    Automates pin creation for a single account using Playwright stealth.
    """
    account_name = account_info.get("name", f"Account #{account_index + 1}")
    session_id = account_info.get("session_id", "").strip()
    board_name = account_info.get("board_name", "").strip()
    
    if not session_id or "PASTE_" in session_id:
        return {
            "account": account_name,
            "status": "SKIPPED",
            "message": "Session ID is empty or contains placeholder text."
        }

    print(f"\n=======================================================")
    print(f"[*] Processing: {account_name}")
    print(f"=======================================================")

    context = None
    page = None
    try:
        # 1. Prepare image copy if alter_image_hash is enabled
        image_to_upload = prepare_image_for_account(
            post_data["image_path"],
            account_index=account_index,
            alter_hash=settings.get("alter_image_hash", True)
        )

        # 2. Setup stealth context with session cookies
        context = create_stealth_context(browser, session_input=session_id)
        page = context.new_page()

        # 3. Navigate to Pinterest Pin Creation Tool
        print("  -> Navigating to Pinterest Pin Creation page...")
        page.goto("https://in.pinterest.com/pin-creation-tool/", timeout=60000, wait_until="domcontentloaded")
        random_delay(3.0, 5.0)

        # 4. Check if session is logged in or logged-out
        current_url = page.url
        login_btn = page.locator('button:has-text("Log in"), a[href*="/login"]').first
        if "login" in current_url.lower() or (login_btn.is_visible() and "pin-creation" not in current_url and "pin-builder" not in current_url):
            err_msg = f"Session ID for {account_name} is EXPIRED or INVALID (Showing login page)."
            print(f"  [!] ERROR: {err_msg}")
            screenshot_path = SCREENSHOTS_DIR / f"error_{account_name}_expired_session.png"
            page.screenshot(path=str(screenshot_path))
            return {"account": account_name, "status": "FAILED", "message": err_msg}

        # Dismiss any onboarding tooltip or drafts sidebar
        dismiss_popups(page)
        print("  -> Session validated! Account is logged in.")

        # 5. Upload Image
        print("  -> Uploading image...")
        file_input = page.locator('input[type="file"]')
        try:
            file_input.first.wait_for(state="attached", timeout=12000)
            file_input.first.set_input_files(image_to_upload)
            print("    [Image] File uploaded successfully.")
        except Exception:
            dropzone = page.locator('text="Upload your media", text="Drag and drop or click to upload"').first
            if dropzone.is_visible():
                with page.expect_file_chooser() as fc_info:
                    dropzone.click()
                file_chooser = fc_info.value
                file_chooser.set_files(image_to_upload)
                print("    [Image] File uploaded via file chooser.")
            else:
                raise RuntimeError("Could not find file upload input on Pin Creation Tool.")
        
        random_delay(3.0, 5.0)

        # 6. Fill Title
        title_text = post_data.get("title", "").strip()
        if title_text:
            print(f"  -> Filling Title: '{title_text[:40]}...'")
            title_elem = find_first_element(
                page,
                [
                    '#storyboard-selector-title',
                    'textarea[placeholder*="title" i]',
                    'input[placeholder*="title" i]',
                    '[id*="pin-draft-title"]'
                ],
                timeout=5000
            )
            if title_elem:
                title_elem.click()
                title_elem.fill(title_text)
                random_delay(0.4, 0.8)
                print("    [Title] Filled successfully.")

        # 7. Fill Description (Clean caption without messy hashtag pollution)
        desc_text = post_data.get("description", "").strip()
        if desc_text:
            print(f"  -> Filling Description ({len(desc_text)} chars)...")
            desc_elem = find_first_element(
                page,
                [
                    'div[contenteditable="true"][aria-label*="Describe your Pin" i]',
                    '.DraftEditor-root [contenteditable="true"]',
                    'div[role="combobox"][aria-label*="Describe your Pin" i]',
                    '[data-test-id*="description"] [contenteditable="true"]',
                    'div[contenteditable="true"]'
                ],
                timeout=5000
            )
            if desc_elem:
                try:
                    desc_elem.click()
                    random_delay(0.2, 0.4)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.insert_text(desc_text)
                    random_delay(0.4, 0.8)
                    print("    [Description] Filled successfully.")
                except Exception as e:
                    print(f"    [Description Warning] Error typing description: {e}")
            else:
                print("    [Warning] Description field locator not found, skipping description.")

        # 8. Fill Destination Link
        dest_link = post_data.get("destination_link", "").strip()
        if dest_link:
            print(f"  -> Setting Link: {dest_link}")
            link_elem = find_first_element(
                page,
                [
                    '#WebsiteField',
                    'input[placeholder*="Add a link" i]',
                    'textarea[placeholder*="destination" i]',
                    '[id*="pin-draft-link"] textarea'
                ],
                timeout=4000
            )
            if link_elem:
                link_elem.click()
                link_elem.fill(dest_link)
                random_delay(0.4, 0.8)
                print("    [Link] Filled successfully.")

        # 9. Configure Board
        print("  -> Configuring board...")
        select_board(page, board_name)
        random_delay(1.0, 2.0)

        # 10. Add Tagged Topics (Pinterest Official Tags)
        hashtags = post_data.get("hashtags", "").strip()
        if hashtags:
            add_tagged_topics(page, hashtags)
            random_delay(1.0, 2.0)

        # 11. Click Publish Button
        print("  -> Submitting Pin (Publishing)...")
        publish_btn = find_first_element(
            page,
            [
                'button:has-text("Publish")',
                '[data-test-id="pin-builder-publish-button"]',
                '[data-test-id="board-dropdown-save-button"]'
            ],
            timeout=8000
        )
        if not publish_btn:
            raise RuntimeError("Publish button not found.")
        
        publish_btn.click()

        # 12. Wait for Real Public Confirmation
        print("  -> Waiting for Pinterest live confirmation (allowing up to 90s for HD media upload)...")
        wait_for_live_publish_confirmation(page, max_wait_sec=90)

        success_screenshot = SCREENSHOTS_DIR / f"success_{account_name}.png"
        page.screenshot(path=str(success_screenshot))

        print(f"  [SUCCESS] Successfully published LIVE for {account_name}!")
        print(f"  [Screenshot saved]: {success_screenshot}")
        
        return {
            "account": account_name,
            "status": "SUCCESS",
            "message": f"Pin published live! Screenshot: {success_screenshot.name}"
        }

    except Exception as e:
        err_msg = str(e)
        print(f"  [!] FAILED for {account_name}: {err_msg}")
        if page:
            try:
                err_screenshot = SCREENSHOTS_DIR / f"error_{account_name}.png"
                page.screenshot(path=str(err_screenshot))
                print(f"  [Debug Screenshot]: {err_screenshot}")
            except Exception:
                pass
        return {
            "account": account_name,
            "status": "FAILED",
            "message": err_msg
        }
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
