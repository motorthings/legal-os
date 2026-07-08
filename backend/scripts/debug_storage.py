"""Quick debug: check localStorage after login."""
import os, sys, json
from playwright.sync_api import sync_playwright

BASE = "https://legal.sickofancy.ai"
EMAIL = "charlie@waifinder.org"
PASSWORD = os.environ.get("TEST_PASSWORD", "ButtButt")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Login
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill("input[type='email']", EMAIL)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE}/", timeout=10000)
    page.wait_for_timeout(2000)

    # Check localStorage
    keys = page.evaluate("() => Object.keys(localStorage)")
    print(f"localStorage keys: {keys}")

    for key in keys:
        val = page.evaluate("(k) => localStorage.getItem(k)", key)
        if len(val) > 500:
            print(f"  {key}: {val[:200]}...")
        else:
            print(f"  {key}: {val}")

    # Check if Supabase session exists
    sb_keys = page.evaluate("() => Object.keys(localStorage).filter(k => k.includes('supabase') || k.includes('sb-')))")
    print(f"\nSupabase keys: {sb_keys}")

    browser.close()
