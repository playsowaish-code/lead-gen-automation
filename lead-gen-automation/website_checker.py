"""
website_checker.py
Decides whether a business is a "lead" (needs a website / has a bad one)
or should be skipped (already has a solid website — not your prospect).
"""

import re
import time
import requests

USER_AGENT = "Mozilla/5.0 (compatible; LeadGenBot/1.0; +https://example.com/bot)"


def check_website(url: str, config: dict) -> dict:
    """
    Returns a dict:
      {
        "status": "no_website" | "poor_website" | "good_website" | "unreachable",
        "reasons": [list of why it's poor],
        "load_seconds": float or None
      }
    """
    if not url:
        return {"status": "no_website", "reasons": ["no website listed"], "load_seconds": None}

    reasons = []
    load_seconds = None

    try:
        start = time.time()
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            allow_redirects=True,
        )
        load_seconds = round(time.time() - start, 2)
    except requests.exceptions.RequestException:
        return {"status": "unreachable", "reasons": ["site did not load / timed out"], "load_seconds": None}

    final_url = resp.url

    # Check 1: HTTPS
    if config["website_quality"]["require_https"] and not final_url.startswith("https://"):
        reasons.append("no SSL (not HTTPS)")

    # Check 2: mobile viewport meta tag present?
    if config["website_quality"]["require_mobile_viewport"]:
        html = resp.text[:200000]  # cap how much we scan
        has_viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE))
        if not has_viewport:
            reasons.append("not mobile-friendly (no viewport meta tag)")

    # Check 3: load time
    max_load = config["website_quality"]["max_acceptable_load_seconds"]
    if load_seconds is not None and load_seconds > max_load:
        reasons.append(f"slow load time ({load_seconds}s)")

    # Check 4: obviously broken / placeholder pages
    if resp.status_code >= 400:
        reasons.append(f"returns HTTP {resp.status_code}")

    if reasons:
        return {"status": "poor_website", "reasons": reasons, "load_seconds": load_seconds}

    return {"status": "good_website", "reasons": [], "load_seconds": load_seconds}
