import json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

TOPIC = '("money laundering" OR AML OR KYC OR sanctions OR "financial crime" OR compliance) (fine OR penalty OR regulation OR law OR rules OR guidance)'
# tab name, country code, language, edition, extra search word
FEEDS = [
    ("USA", "US", "en-US", "US:en", "USA"),
    ("UK", "GB", "en-GB", "GB:en", "UK"),
    ("India", "IN", "en-IN", "IN:en", "India"),
    ("UAE", "AE", "en", "AE:en", "UAE"),
    ("Singapore", "SG", "en-SG", "SG:en", "Singapore"),
    ("Qatar", "QA", "en", "QA:en", "Qatar"),
    ("Saudi Arabia", "SA", "en", "SA:en", "Saudi Arabia"),
    ("Global", "US", "en-US", "US:en", ""),
]

def kind(t):
    t = t.lower()
    if re.search(r"\b(fine[ds]?|penalt\w*|settle\w*|enforcement)\b", t):
        return "Fines"
    if re.search(r"\b(law|laws|rule|rules|regulation\w*|amend\w*|guidance|directive|bill|act|framework|circular|mandate\w*)\b", t):
        return "Law changes"
    return "Other"

def fetch(tab, gl, hl, ceid, term):
    q = urllib.parse.quote_plus((TOPIC + " " + term + " when:7d").strip())
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
else:
    print("No items found, keeping the old file")
