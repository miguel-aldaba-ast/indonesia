"""Turn a snapshot's evidence.csv into the JSON documents the Benchmark Hub stores."""
import csv, json, re, sys, pathlib
from benchmark.taxonomy import TAXONOMY

SITES = {
 "Toyota": "https://www.toyota.astra.co.id/", "Honda": "https://www.honda-indonesia.com/",
 "Suzuki": "https://www.suzuki.co.id/", "Daihatsu": "https://daihatsu.co.id/",
 "Wuling": "https://wuling.id/en", "Mitsubishi": "https://www.mitsubishi-motors.co.id/",
 "Hyundai": "https://www.hyundai.com/id/en", "Isuzu": "https://isuzu-astra.com/",
 "BYD": "https://www.byd.com/id", "Chery": "https://chery.co.id/en", "Geely": "https://www.geelyauto.id/",
 "Jaecoo": "https://jaecoo.id/en", "MG": "https://www.mgmotor.id/", "VinFast": "https://vinfastauto.id/en",
}
HINTS = {
 "Model finder": "Can a shopper narrow the range (by body type, price, powertrain) instead of scrolling a flat list?",
 "Vehicle comparison": "Can a shopper pick two or three models and see a side-by-side spec table?",
 "Colour visualisation": "Click a colour swatch: does the car image change to that colour?",
 "Model configurator": "Can a shopper build a car (variant, colour, options) and see a running price, and does it carry into a quote or dealer step?",
 "Public pricing": "Are prices shown on the site per model or variant, or only 'contact dealer'?",
 "Finance calculator": "Can a shopper enter a down payment or tenor and get an instalment on the page, or is it only a lead form?",
 "Request quote": "Is there a form to ask for a price offer or purchase consultation tied to a model and dealer?",
 "Test-drive booking": "Is there a booking form for a test drive with model and location, or only a phone number?",
 "Online reservation": "Can a shopper reserve or pre-order a car online, ideally with a deposit or confirmation?",
 "Dealer locator": "Is there a dealer finder with search or filters and a map or results list?",
 "Trade-in information": "Is there a trade-in or used-car page, and is there a valuation or appraisal request?",
 "Service booking": "Can an owner book a workshop appointment online (form, app or portal)?",
 "Mobile application": "Is there an owner or connected-car app, and what does it document (remote control, service, status)?",
 "Fleet telematics": "Is there a fleet-management or telematics product for businesses?",
 "Charging map": "For EVs: is there a station locator or map, or just an article?",
 "Cost-of-ownership calculator": "Is there an interactive tool to compare running or ownership costs, especially EV versus petrol?",
 "Chatbot": "Is there a chat widget, and does it let you type freely or force a contact form first?",
 "Customer account": "Can an owner register or log in to a personal account or membership?",
 "Vehicle subscription": "Is there a subscription or lease-as-a-service offer with a monthly fee?",
}

def method_of(r):
    lim = (r.get("limitations") or "").lower()
    if "sitemap" in lim: return "Sitemap and navigation"
    if "navigation review only" in lim or "navigation only" in lim or "navigation of the main" in lim: return "Navigation only"
    if "http fetch" in lim or "not an interactive browser" in lim: return "Page fetch (not rendered)"
    if "documentation" in lim or "web search" in lim or "press release" in lim: return "Documentation or press"
    return "Tested in browser"

def build(csv_path, out_dir, country="Indonesia"):
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    by_brand = {}
    for r in rows:
        by_brand.setdefault(r["brand"], []).append({
            "category": r["category"], "capability": r["capability"], "status": r["status"],
            "score": r["maturity_score"], "advanced": r["advanced"].strip().lower() in ("yes", "y", "true", "1"),
            "description": r["short_description"], "how": r["how_it_works"], "value": r["customer_value"],
            "url": r["url"], "title": r["page_title"], "date": r["date_accessed"],
            "limitations": r["limitations"], "confidence": r["confidence"], "method": r.get("method") or method_of(r),
        })
    for brand, rs in by_brand.items():
        doc = {"country": country, "brand": brand, "url": SITES.get(brand, ""), "rows": rs,
               "updatedAt": "2026-09-28T00:00:00Z", "updatedBy": "seed"}
        (out / f"site__{slug(country)}__{slug(brand)}.json").write_text(json.dumps(doc, ensure_ascii=False))
    tax = {c: list(v) for c, v in TAXONOMY.items()}
    tracked = []
    for r in rows:
        k = (r["category"], r["capability"])
        if k not in tracked: tracked.append(k)
        if r["capability"] not in tax.setdefault(r["category"], []): tax[r["category"]].append(r["capability"])
    (out / "meta__taxonomy.json").write_text(json.dumps({"categories": [{"name": c, "capabilities": v} for c, v in tax.items()]}, ensure_ascii=False))
    (out / "meta__scope.json").write_text(json.dumps({"items": [{"category": c, "capability": k} for c, k in tracked]}, ensure_ascii=False))
    (out / "meta__hints.json").write_text(json.dumps({"hints": HINTS}, ensure_ascii=False))
    (out / "country__indonesia.json").write_text(json.dumps({"name": country, "createdBy": "seed"}))
    print(len(by_brand), "brands,", len(tracked), "tracked capabilities,", len(rows), "rows")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
