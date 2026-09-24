# Evidence CSV output format

At the end of a research session, output the full evidence table as ONE csv code block using exactly this header (order matters):

```
brand,category,capability,status,maturity_score,advanced,short_description,how_it_works,customer_value,url,page_title,date_accessed,screenshot_status,screenshot_reference,limitations,confidence
```

## Column rules

- `brand` — brand name as commonly used, e.g. `Toyota`, `Honda`, `Mitsubishi`, `BYD`.
- `category` — one of the 14 taxonomy categories (see `capability-taxonomy.md`), in upper case, e.g. `CONFIGURE`, `PRICE & FINANCE`.
- `capability` — the specific capability name from the taxonomy, e.g. `Model configurator`, `Finance calculator`.
- `status` — exactly one of: `Confirmed`, `Partial`, `Not found`, `Unknown`.
- `maturity_score` — one of: `0`, `1`, `2`, `3`, `4`, `?`, `N/A`. Use `?` for unverified, not `0`.
- `advanced` — `yes` or `no`. `yes` only when you have specific, independently observed evidence of unusual functional depth (not just "the brand calls this innovative").
- `short_description` — one or two plain sentences: what the customer can do.
- `how_it_works` — the specific mechanism you observed (inputs → outputs, steps, gates).
- `customer_value` — one sentence on why this matters to a shopper (interpretation, kept separate from the observed facts above).
- `url` — the exact page you evaluated (no tracking parameters).
- `page_title` — the page's title as shown in the browser tab.
- `date_accessed` — `YYYY-MM-DD`, the date you actually checked it.
- `screenshot_status` — `captured`, `not captured`, or `unavailable`.
- `screenshot_reference` — a filename/description if you have one, else leave blank.
- `limitations` — anything you couldn't verify, any gate you hit (e.g. required login, required personal info), or scope you didn't cover.
- `confidence` — `High`, `Medium`, or `Low`.

## Formatting rules (important for the file to parse correctly)

- Any field containing a comma MUST be wrapped in double quotes.
- Any field containing a double-quote character must have that character doubled (`"` becomes `""`) and the whole field wrapped in quotes.
- One row per brand + capability. Do not merge multiple capabilities into one row.
- Leave `customer_value` blank rather than guessing when status is `Not found` or `Unknown`.
- Do not add extra columns and do not reorder columns — the local tool expects this exact header.
