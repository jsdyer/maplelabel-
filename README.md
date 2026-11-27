# Maple Label

[Open the Made in Canada finder](https://coolcode.ca/maplelabel/) · [Browse the saved records](https://coolcode.ca/maplelabel/records/)

<!-- coolcode:guide -->
Compare OKA Original cheese with Hortus espresso roasted in Laval. One Québec mark documents where the main ingredients come from and the other documents processing. Each product record separates ingredient or material origin, manufacturing and company ownership, with a link to the original evidence.
<!-- /coolcode:guide -->

## Where the records come from

The curated edition covers specific named products or, where labelled, a product family. It combines Aliments du Québec, Buy BC, Ontario Made and direct producer material. The Canadian Food Inspection Agency and Competition Bureau supply the federal definitions. Unknown fields stay open. A registered business address, a GS1 prefix or a regional mark alone cannot establish a company’s ultimate ownership, a component’s origin or compliance with a federal label. Comparison links connect products for reading evidence and do not imply interchangeability.

The [side-by-side Québec example](https://coolcode.ca/maplelabel/records/quebec-cheese-and-coffee/) and the full product directory work without scripts. Search, filters and comparison run locally in the browser. Share the URL to reopen your selection. [Label Compare](https://coolcode.ca/labelcompare/) handles barcode, nutrition and ingredient-list comparisons. Prices, availability and retailer coverage are outside this edition.

## Expand or customize

Edit `web/data/catalogue.json`. Add a unique product ID, the precise claim, its applicable rule, the classified province (null if unspecified), evidence in each supported field, and at least one real related record. Add named HTTPS sources and short text anchors supporting the claim. Each product’s first source identifies the product itself. A rule source explains the criteria. Preserve unknowns as JSON null. When an editor has actually checked the full edition, set its `reviewed_at` to the review date. Every valid record automatically appears in the filter menus, public directory, JSON download and native sitemap.

The checker is scheduled for the sixth of every month at 13:26 UTC. It can also be run manually. It checks selected text on program, official and producer pages, including image alternative text where a claim appears as a label. It detects missing or changed wording, without reinterpreting new claims or dates. Ontario Made records and eligibility currently require editorial review because the public site restricts automated requests. These sources are labelled editorial in each affected record. The product evidence review and the last successful automated check have separate dates.

A failed fetch or changed anchor preserves the product records and the previous full-check date. The status receipt identifies sources requiring review and the check workflow signals failure after saving that receipt to the source repository. Review the source document and package specifics before changing an anchor, label or interpretation. A successful retry can replace the receipt on the same day.

```sh
python3 scripts/check_sources.py
python3 -m unittest discover -s tests -v
node --test tests/*.test.mjs
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

To run the browser journey, install `tests/browser-requirements.txt` and Playwright Chromium, then run `python3 tests/browser_smoke.py`. The build reads the saved data offline. The public JSON in `data/catalogue.json` contains the product fields, rules, references and proof anchors. `data/status.json` provides the review date, check status and product count without personal data.

## Publication

The source repository is [jsdyer/maplelabel](https://github.com/jsdyer/maplelabel). Its Pages workflow builds the site, runs unit and browser tests and retains a preview artifact for pushes to main, pull requests and manual dispatches. Successful main builds deploy to [Maple Label](https://coolcode.ca/maplelabel/) through GitHub Pages. The monthly check dispatches the same publication workflow after recording the source status.
