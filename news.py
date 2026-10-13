import json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

TOPIC = '("money laundering" OR AML OR KYC OR sanctions OR "financial crime" OR compliance) (fine OR penalty OR regulation OR law OR rules OR guidance)'
GLOBAL1 = '("FATF" OR "Financial Action Task Force" OR "Egmont Group" OR "Basel Committee" OR Wolfsberg) ("money laundering" OR "terrorist financing" OR sanctions OR "grey list" OR guidance OR standards)'
GLOBAL2 = '("UN Security Council" OR "United Nations" OR UNODC OR OECD) ("sanctions list" OR "money laundering" OR "financial crime" OR "terrorist financing" OR "illicit finance")'
# tab name, country code, language, edition, extra search word, full search (only for Global)
# Global comes first, so global-body news is tagged Global instead of a country
FEEDS = [
    ("Global", "US", "en-US", "US:en", "", GLOBAL1),
    ("Global", "US", "en-US", "US:en", "", GLOBAL2),
    ("USA", "US", "en-US", "US:en", "USA", None),
    ("UK", "GB", "en-GB", "GB:en", "UK", None),
    ("India", "IN", "en-IN", "IN:en", "India", None),
    ("UAE", "AE", "en", "AE:en", "UAE", None),
    ("Singapore", "SG", "en-SG", "SG:en", "Singapore", None),
    ("Qatar", "QA", "en", "QA:en", "Qatar", None),
    ("Saudi Arabia", "SA", "en", "SA:en", "Saudi Arabia", None),
]

def kind(t):
    t = t.lower()
    if re.search(r"\b(fine[ds]?|penalt\w*|settle\w*|enforcement)\b", t):
        return "Fines"
    if re.search(r"\b(law|laws|rule|rules|regulation\w*|amend\w*|guidance|directive|bill|act|framework|circular|mandate\w*)\b", t):
        return "Law changes"
    return "Other"

def fetch(tab, gl, hl, ceid, term, full=None):
    base = full if full else TOPIC + " " + term
    q = urllib.parse.quote_plus((base + (" when:14d" if full else " when:7d")).strip())
    url = "https://news.google.com/rss/search?q=%s&hl=%s&gl=%s&ceid=%s" % (q, hl, gl, ceid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src = (it.findtext("source") or "News").strip()
        if title.endswith(" - " + src):
            title = title[: -len(src) - 3]
        try:
            d = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            d = datetime.now(timezone.utc)
        if title and link.startswith("http"):
            out.append({"title": title, "link": link, "source": src, "date": d.strftime("%Y-%m-%d"),
                        "ts": d.timestamp(), "country": tab, "type": kind(title)})
    return out[:25]

items, seen = [], set()
for f in FEEDS:
    try:
        for i in fetch(*f):
            k = i["title"].lower()
            if k not in seen:
                seen.add(k)
                items.append(i)
    except Exception as e:
        print("Feed failed:", f[0], e)

if items:
    items.sort(key=lambda i: i["ts"], reverse=True)
    for i in items:
        del i["ts"]
    with open("news.json", "w", encoding="utf-8") as fh:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(), "items": items[:80]}, fh, ensure_ascii=False, indent=1)
    print("Saved", len(items[:80]), "items")
    # Monthly archive: never allowed to break the daily update above
    try:
        import os
        os.makedirs("news-archive", exist_ok=True)
        by_month = {}
        for i in items:
            by_month.setdefault(i["date"][:7], []).append(i)
        for m, new_items in by_month.items():
            path = "news-archive/%s.json" % m
            old_items = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    old_items = json.load(fh).get("items", [])
            have = set(o["link"] for o in old_items)
            merged = old_items + [n for n in new_items if n["link"] not in have]
            merged.sort(key=lambda i: i["date"], reverse=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"month": m, "items": merged}, fh, ensure_ascii=False, indent=1)
        months = sorted((f[:-5] for f in os.listdir("news-archive") if re.match(r"\d{4}-\d{2}\.json$", f)), reverse=True)
        with open("news-archive/index.json", "w", encoding="utf-8") as fh:
            json.dump({"months": months}, fh)
        print("Archive updated:", months)
    except Exception as e:
        print("Archive step failed (daily news is fine):", e)
else:
    print("No items found, keeping the old file")
