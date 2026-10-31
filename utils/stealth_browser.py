import re
from typing import List, Dict, Any
from playwright_stealth import Stealth

stealth_handler = Stealth()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

def parse_pinterest_cookies(cookie_input: str) -> List[Dict[str, Any]]:
    """
    Parses various forms of session input:
    1. Raw session token (e.g. 'TWc9...') -> mapped to _pinterest_sess
    2. '_pinterest_sess=TWc9...' -> parsed
    3. Full cookie header string ('cookie1=val1; cookie2=val2')
    """
    cookie_input = cookie_input.strip()
    if not cookie_input:
        return []

    cookies = []
    
    # Check if user passed full header string with multiple cookies or explicit name
    if "_pinterest_sess=" in cookie_input or ";" in cookie_input:
        pairs = [p.strip() for p in cookie_input.split(";") if p.strip()]
        for p in pairs:
            if "=" in p:
                name, val = p.split("=", 1)
                name = name.strip()
                val = val.strip().strip('"\'')
                cookies.append({
                    "name": name,
                    "value": val,
                    "domain": ".pinterest.com",
                    "path": "/",
                    "httpOnly": (name == "_pinterest_sess"),
                    "secure": True,
                    "sameSite": "Lax"
                })
    else:
        # User passed raw session id (which may contain base64 '=' or '&' characters)
        val = cookie_input.strip('"\'')
        cookies.append({
            "name": "_pinterest_sess",
            "value": val,
            "domain": ".pinterest.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        })

    # Ensure _auth=1 is present so Pinterest client knows user is logged in
    has_auth = any(c["name"] == "_auth" for c in cookies)
    if not has_auth:
        cookies.append({
            "name": "_auth",
            "value": "1",
            "domain": ".pinterest.com",
            "path": "/",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        })

    return cookies

def create_stealth_context(browser, session_input: str, proxy: dict = None):
    """
    Creates an isolated browser context with stealth scripts, realistic user-agent,
    viewport, and injected Pinterest session cookies.
    """
    context_args = {
        "user_agent": USER_AGENT,
        "viewport": {"width": 1366, "height": 768},
        "device_scale_factor": 1,
        "locale": "en-US",
        "timezone_id": "Asia/Kolkata",
        "ignore_https_errors": True,
    }
    if proxy:
        context_args["proxy"] = proxy

    context = browser.new_context(**context_args)
    
    # Apply stealth evasions
    stealth_handler.apply_stealth_sync(context)

    # Inject cookies
    cookies = parse_pinterest_cookies(session_input)
    if cookies:
        context.add_cookies(cookies)

    return context
