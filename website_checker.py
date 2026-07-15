"""
website_checker.py
Decides whether a business is a "lead" (needs a website / has a bad one)
or should be skipped (already has a solid website — not your prospect).

Also extracts email/phone from the website itself when one exists, since
OpenStreetMap's own phone/email tags are often missing or outdated.
"""

import re
import time
import requests
from urllib.parse import urljoin

USER_AGENT = "Mozilla/5.0 (compatible; LeadGenBot/1.0; +https://example.com/bot)"

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(\+?\d[\d\-\.\(\)\s]{7,}\d)')

# Generic addresses that are junk (webmaster@, no-reply@, image filenames that look like emails, etc.)
EMAIL_JUNK_PATTERNS = [
    "example.com", "sentry.io", "wixpress.com", "godaddy.com",
    "yourdomain", "domain.com", "email.com", "noreply", "no-reply",
]

CONTACT_PAGE_PATHS = ["/contact", "/contact-us", "/contactus", "/about", "/about-us"]


def _extract_email(html: str) -> str:
    candidates = EMAIL_REGEX.findall(html)
    for email in candidates:
        low = email.lower()
        if any(junk in low for junk in EMAIL_JUNK_PATTERNS):
            continue
        if re.search(r'\.(png|jpg|jpeg|gif|svg|webp)$', low):
            continue
        return email
    return ""


def _extract_phone(html: str) -> str:
    tel_match = re.search(r'href=["\']tel:([+\d\-\.\(\)\s]+)["\']', html, re.IGNORECASE)
    if tel_match:
        return tel_match.group(1).strip()

    match = PHONE_REGEX.search(html)
    if match:
        return match.group(1).strip()
    return ""


def _try_fetch(url: str):
    try:
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=8, allow_redirects=True)
    except requests.exceptions.RequestException:
        return None


def extract_contact_info(homepage_html: str, homepage_url: str) -> dict:
    """
    Looks for an email/phone on the homepage first; if missing, tries one
    common contact-page path. Returns {"email": ..., "phone": ...} (either may be "").
    """
    email = _extract_email(homepage_html)
    phone = _extract_phone(homepage_html)

    if email and phone:
        return {"email": email, "phone": phone}

    for path in CONTACT_PAGE_PATHS:
        if email and phone:
            break
        contact_url = urljoin(homepage_url, path)
        resp = _try_fetch(contact_url)
        if resp is None or resp.status_code >= 400:
            continue
        page_html = resp.text[:200000]
        if not email:
            email = _extract_email(page_html)
        if not phone:
            phone = _extract_phone(page_html)
        break

    return {"email": email, "phone": phone}


def check_website(url: str, config: dict) -> dict:
    """
    Returns a dict:
      {
        "status": "no_website" | "poor_website" | "good_website" | "unreachable",
        "reasons": [list of why it's poor],
        "load_seconds": float or None,
        "email": str,
        "phone": str
      }
    """
    if not url:
        return {"status": "no_website", "reasons": ["no website listed"], "load_seconds": None,
                "email": "", "phone": ""}

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
        return {"status": "unreachable", "reasons": ["site did not load / timed out"], "load_seconds": None,
                "email": "", "phone": ""}

    final_url = resp.url
    html = resp.text[:200000]

    if config["website_quality"]["require_https"] and not final_url.startswith("https://"):
        reasons.append("no SSL (not HTTPS)")

    if config["website_quality"]["require_mobile_viewport"]:
        has_viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE))
        if not has_viewport:
            reasons.append("not mobile-friendly (no viewport meta tag)")

    max_load = config["website_quality"]["max_acceptable_load_seconds"]
    if load_seconds is not None and load_seconds > max_load:
        reasons.append(f"slow load time ({load_seconds}s)")

    if resp.status_code >= 400:
        reasons.append(f"returns HTTP {resp.status_code}")

    contact = extract_contact_info(html, final_url)

    if reasons:
        return {"status": "poor_website", "reasons": reasons, "load_seconds": load_seconds, **contact}

    return {"status": "good_website", "reasons": [], "load_seconds": load_seconds, **contact}
