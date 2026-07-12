# Free Daily Lead Generator (USA / Australia / Canada)

Finds local businesses in the US, Australia, and Canada that have **no website
or a poor-quality website**, and drops them into a Google Sheet every day —
completely free, no credit card, no paid API anywhere.

## How it works

1. **Data source: OpenStreetMap** (via the free Overpass API) — no signup, no key.
2. **Website check**: for every business found, the script checks if it has a
   website, and if so, whether it's HTTPS, mobile-friendly, and loads fast.
   Businesses with no website or a failing website become "leads."
3. **Output: Google Sheet** — updates automatically, shared across your devices.
4. **Scheduling: GitHub Actions** — runs once a day for free (public repos get
   unlimited free Action minutes; private repos get 2,000 free minutes/month,
   this job uses a few minutes/day, nowhere close to the limit).

No cost, anywhere, ever — as long as you use the free tiers described below.

---

## One-time setup (about 15-20 minutes)

### Step 1 — Create the Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com) → create a new blank sheet.
2. Name it whatever you like (e.g. "Web Design Leads").
3. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART_IS_THE_ID`**`/edit`

### Step 2 — Create a free Google service account (so the script can write to your sheet)
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new project (free).
2. In the search bar, enable **"Google Sheets API"** and **"Google Drive API"** for that project.
3. Go to **APIs & Services → Credentials → Create Credentials → Service Account**.
4. Give it any name, click through, then open the service account → **Keys → Add Key → JSON**.
5. This downloads a `.json` file — keep it safe, you'll need its contents in Step 4.
6. Open the JSON file, copy the `client_email` value (looks like
   `xxxx@xxxx.iam.gserviceaccount.com`).
7. Go back to your Google Sheet → click **Share** → paste that email → give it
   **Editor** access.

> This does NOT require enabling billing. Sheets/Drive API are free with no usage cap
> for this kind of workload.

### Step 3 — Put this code in a GitHub repo
1. Create a free GitHub account if you don't have one.
2. Create a new repository (can be private).
3. Upload all the files from this project into it.

### Step 4 — Add your secrets to GitHub
In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add these two secrets:
- `GOOGLE_SERVICE_ACCOUNT_JSON` → paste the **entire contents** of the JSON file from Step 2
- `GOOGLE_SHEET_ID` → paste the Sheet ID from Step 1

### Step 5 — Turn on the automation
The workflow file (`.github/workflows/daily-leads.yml`) is already set up to run
daily at 6:00 AM UTC. Once you push the code with the secrets set, it runs
automatically every day. You can also trigger it manually anytime from the
**Actions** tab → "Daily Lead Generation" → "Run workflow".

---

## Customizing

- **Add/remove cities**: edit the `cities:` section in `config.yaml`
- **Add/remove business categories**: edit the `categories:` section — each
  needs an OpenStreetMap tag (see [OSM Map Features](https://wiki.openstreetmap.org/wiki/Map_features)
  for the full list of tags if you want to add niches like "wedding photographer"
  or "car dealership")
- **Change daily target**: `daily_lead_target` in `config.yaml` (default 200)
- **Change run time**: edit the `cron` line in the workflow file

---

## Honest expectations (please read)

- **200/day is a target, not a guarantee.** Free OpenStreetMap data is
  community-maintained — coverage is strong in big cities (all the ones in the
  default config) but thinner in small towns. Some days you might get 100-150
  instead of 200. The script tells you in its log output when it falls short,
  and rotates through more categories/cities automatically the next run.
- **These are raw leads, not warm leads.** This tool finds businesses with a
  website problem — it does NOT contact them or qualify their interest. You
  (or a separate outreach tool) still need to reach out. I'm happy to help you
  build a free/cheap outreach step (cold email templates, etc.) next if useful.
- **Data completeness**: OSM businesses often don't have a phone number tagged,
  even when the business itself definitely has one. Website and address fields
  are more reliable than phone.
- **Be a good API citizen**: the script already includes delays to respect
  Overpass's and Nominatim's free usage policies. Don't remove those delays or
  run multiple copies simultaneously — the free endpoints are shared community
  infrastructure and can rate-limit or block abusive usage.

---

## Files in this project

| File | Purpose |
|---|---|
| `config.yaml` | Cities, categories, targets — edit this to customize |
| `geocode.py` | Free city name → lat/lon lookup (Nominatim) |
| `overpass_search.py` | Free business search (OpenStreetMap Overpass API) |
| `website_checker.py` | Checks if a business's website is missing/poor |
| `sheets_writer.py` | Writes new leads to your Google Sheet, avoids duplicates |
| `main.py` | Runs the whole daily pipeline |
| `state.json` | Tracks where the last run left off (auto-updated) |
| `city_coords_cache.json` | Cache of geocoded cities (auto-created after first run) |
| `.github/workflows/daily-leads.yml` | The free daily scheduler |

---

## Running it locally (to test before automating)

```bash
pip install -r requirements.txt
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat /path/to/your-service-account.json)"
export GOOGLE_SHEET_ID="your_sheet_id_here"
python main.py
```
