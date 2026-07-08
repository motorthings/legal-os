"""End-to-end test: login + KM page API calls."""
import os, sys
from playwright.sync_api import sync_playwright

BASE = "https://legal.sickofancy.ai"
EMAIL = "charlie@waifinder.org"
PASSWORD = os.environ.get("TEST_PASSWORD", "ButtButt")

results = {"pass": 0, "fail": 0, "checks": []}

def check(ok, name):
    results["checks"].append(f"{'PASS' if ok else 'FAIL'} — {name}")
    if ok: results["pass"] += 1
    else: results["fail"] += 1
    return ok

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Set up API response monitoring
    api_calls = []
    def on_response(resp):
        if "legal-os-api.fly.dev" in resp.url or "api/" in resp.url:
            api_calls.append({"url": resp.url, "status": resp.status})
    page.on("response", on_response)

    # 1. Navigate to login
    print("1. Navigating to login...")
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.wait_for_timeout(1000)
    check(page.is_visible("input[type='email']"), "Login form visible")

    # 2. Fill and submit
    print("2. Logging in...")
    page.fill("input[type='email']", EMAIL)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_timeout(3000)
    page.wait_for_url(f"{BASE}/", timeout=10000)
    check(page.url.rstrip("/") == BASE, f"Redirected to dashboard (now at {page.url})")

    # 3a. Navigate to KM page
    print("3a. Navigating to KM...")
    page.goto(f"{BASE}/km", wait_until="networkidle")
    page.wait_for_timeout(3000)

    # Check KM API calls
    km_calls = [c for c in api_calls if "/api/km/" in c["url"]]
    print(f"KM API calls: {km_calls}")
    if km_calls:
        stats_ok = any(c["status"] == 200 for c in km_calls if "/stats" in c.get("url", ""))
        check(stats_ok, "KM stats returns 200")
        evaded = any(c["status"] == 401 for c in km_calls)
        check(not evaded, "No 401 responses")
    else:
        check(False, "KM API calls detected")

    # 3b. Test KM search
    print("3b. Testing KM search...")
    page.fill("input[placeholder*='Search']", "indemnification clause")
    page.click("button:has-text('Search')")
    page.wait_for_timeout(3000)
    search_calls = [c for c in api_calls if "/api/km/search" in c["url"]]
    print(f"Search API calls: {search_calls}")
    search_200 = any(c["status"] == 200 for c in search_calls)
    check(search_200, "KM search returns 200")

    # 4. Navigate to Due Diligence
    print("4. Navigating to Due Diligence...")
    page.goto(f"{BASE}/due-diligence", wait_until="networkidle")
    page.wait_for_timeout(2000)
    dd_calls = [c for c in api_calls if "/api/due-diligence/" in c["url"]]
    print(f"DD API calls: {dd_calls}")
    dd_ok = any(c["status"] in (200, 404) for c in dd_calls)  # 200=has projects, 404=not found
    check(dd_ok, "DD projects loads")

    # 5. Navigate to Regulatory
    print("5. Navigating to Regulatory...")
    page.goto(f"{BASE}/regulatory", wait_until="networkidle")
    page.wait_for_timeout(2000)

    # 6. Navigate to Reporting
    print("6. Navigating to Reporting...")
    page.goto(f"{BASE}/reporting", wait_until="networkidle")
    page.wait_for_timeout(2000)
    report_calls = [c for c in api_calls if "/api/reporting/" in c["url"]]
    print(f"Reporting API calls: {report_calls}")
    report_ok = any(c["status"] == 200 for c in report_calls)
    check(report_ok, "Reporting loads")

    # Summary
    print("\n" + "=" * 50)
    for c in results["checks"]:
        print(c)
    print(f"\n{results['pass']} passed, {results['fail']} failed")
    screenshot = page.screenshot()
    with open("/tmp/legal-os-test.png", "wb") as f:
        f.write(screenshot)
    print("Screenshot: /tmp/legal-os-test.png")

    browser.close()
    sys.exit(0 if results["fail"] == 0 else 1)
