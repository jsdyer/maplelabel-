import { matching, selection } from "./model.mjs";
const $ = (id) => document.getElementById(id);
function node(tag, text) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  return n;
}
function link(text, href) {
  const a = node("a", text);
  a.href = href;
  return a;
}
function options(id, entries) {
  $(id).replaceChildren(
    ...entries.map(([value, label]) => new Option(label, value)),
  );
}
function unique(rows, field) {
  return [...new Set(rows.map((r) => r[field]).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  );
}
async function boot() {
  const response = await fetch("./data/catalogue.json");
  if (!response.ok) throw new Error("Catalogue unavailable");
  const { products, rules: ruleList } = await response.json();
  const rules = new Map(ruleList.map((r) => [r.id, r]));
  const byId = new Map(products.map((p) => [p.id, p]));
  const query = new URLSearchParams(location.search);
  const [first, second] = selection(products, query);
  const listings = products.map((p) => [p.id, p.name + " · " + p.brand]);
  options("province", [
    ["", "All provinces"],
    ...unique(products, "province").map((s) => [s, s]),
    ...(products.some((p) => !p.province)
      ? [["unspecified", "Province unspecified"]]
      : []),
  ]);
  options("category", [
    ["", "All categories"],
    ...unique(products, "category").map((s) => [s, s]),
  ]);
  options("rule", [
    ["", "All claims and programs"],
    ...ruleList
      .filter((r) => products.some((p) => p.rule === r.id))
      .map((r) => [r.id, r.name]),
  ]);
  options("product", listings);
  $("product").value = first.id;
  $("query").value = query.get("q") || "";
  for (const id of ["province", "category", "rule"]) {
    if ([...$(id).options].some((o) => o.value === query.get(id)))
      $(id).value = query.get(id);
  }
  function drawCards(preferred = $("compare").value) {
    const left = byId.get($("product").value);
    const right =
      byId.get(preferred) && preferred !== left.id
        ? byId.get(preferred)
        : byId.get(left.related[0]);
    options(
      "compare",
      listings.filter(([id]) => id !== left.id),
    );
    $("compare").value = right.id;
    $("comparison-cards").replaceChildren(
      ...[left, right].map((p) => {
        const box = node("article");
        box.className = "card";
        const h = node("h3");
        h.append(link(p.name, "./records/" + p.id + "/"));
        const tag = node("p", p.claim);
        tag.className = "origin-label";
        box.append(h, node("p", p.brand), tag);
        const dl = node("dl");
        dl.className = "facts";
        for (const [key, title] of [
          ["inputs", "Ingredients or materials"],
          ["processing", "Manufacturing"],
          ["ownership", "Ownership"],
        ]) {
          const row = node("div");
          row.append(
            node("dt", title),
            node("dd", p[key] || "Not specified in the cited sources."),
          );
          dl.append(row);
        }
        box.append(
          dl,
          link("Sources and product record", "./records/" + p.id + "/"),
        );
        return box;
      }),
    );
  }
  function state() {
    return {
      q: $("query").value.trim(),
      province: $("province").value,
      category: $("category").value,
      rule: $("rule").value,
    };
  }
  function address() {
    const url = new URL(location.href);
    for (const [k, v] of Object.entries(state())) {
      if (v) url.searchParams.set(k, v);
      else url.searchParams.delete(k);
    }
    url.searchParams.set("product", $("product").value);
    url.searchParams.set("compare", $("compare").value);
    history.replaceState(null, "", url);
  }
  function showResults() {
    const hits = matching(products, state(), rules);
    $("count").textContent = hits.length
      ? hits.length + " of " + products.length + " product records"
      : "No matching products. Clear a filter or try another name.";
    $("matches").replaceChildren(
      ...hits.map((p) => {
        const row = node("li"),
          main = node("div"),
          select = node("button", "Compare"),
          name = link(p.name, "./records/" + p.id + "/");
        main.append(name, node("span", p.brand + " · " + p.claim));
        select.type = "button";
        select.setAttribute("aria-label", "Compare " + p.name);
        select.addEventListener("click", () => {
          $("product").value = p.id;
          drawCards();
          address();
          $("comparison").scrollIntoView({ block: "start" });
          $("product").focus({ preventScroll: true });
        });
        row.append(main, select);
        return row;
      }),
    );
  }
  $("filters").addEventListener("input", () => {
    showResults();
    address();
  });
  $("filters").addEventListener("submit", (e) => e.preventDefault());
  $("filters").addEventListener("reset", () => {
    queueMicrotask(() => {
      showResults();
      address();
    });
  });
  for (const id of ["product", "compare"])
    $(id).addEventListener("change", () => {
      drawCards();
      address();
    });
  drawCards(second.id);
  showResults();
  for (const id of ["finder", "filters", "results", "comparison"])
    $(id).hidden = false;
  if (location.hash === "#comparison") $("comparison").scrollIntoView();
}
boot().catch(() => {
  $("finder").hidden = false;
  const message = node("p", "The interactive finder could not load. ");
  message.append(link("Browse all saved product records.", "./records/"));
  $("finder").append(message);
});
