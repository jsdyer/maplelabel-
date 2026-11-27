import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { matching, selection } from "../web/model.mjs";
const data = JSON.parse(
  readFileSync(new URL("../web/data/catalogue.json", import.meta.url)),
);
const rules = new Map(data.rules.map((r) => [r.id, r]));
test("accent-independent search and simultaneous claim, category and province filters", () => {
  const hits = matching(
    data.products,
    {
      q: "QUEBEC espresso",
      province: "Quebec",
      category: "Drinks",
      rule: "qc-prepared",
    },
    rules,
  );
  assert.deepEqual(
    hits.map((r) => r.id),
    ["balanced-espresso"],
  );
  assert.equal(
    matching(data.products, { q: "espresso", rule: "qc-grown" }, rules).length,
    0,
  );
  assert.ok(
    matching(data.products, { province: "unspecified" }, rules).some(
      (p) => p.id === "veritas-block-plane",
    ),
  );
});
test("the finder restores a valid selection and substitutes a distinct comparison for invalid input", () => {
  const selected = selection(
    data.products,
    new URLSearchParams("product=fleur-de-sel&compare=maple-leaf-bottle"),
  );
  assert.deepEqual(
    selected.map((p) => p.id),
    ["fleur-de-sel", "maple-leaf-bottle"],
  );
  for (const query of [
    "product=missing",
    "product=oka-original&compare=oka-original",
  ]) {
    const [left, right] = selection(data.products, new URLSearchParams(query));
    assert.ok(left && right && left !== right);
  }
});
