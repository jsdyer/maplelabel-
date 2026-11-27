export function normal(value) {
  return (value || "")
    .toLocaleLowerCase("en-CA")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function matching(products, filters, rules) {
  const words = normal(filters.q).trim().split(/\s+/).filter(Boolean);
  return products.filter((product) => {
    const text = normal(
      [
        product.name,
        product.brand,
        product.category,
        product.province || "",
        product.claim,
        rules.get(product.rule).name,
        product.summary,
      ].join(" "),
    );
    return (
      (!filters.province ||
        (product.province || "unspecified") === filters.province) &&
      (!filters.category || product.category === filters.category) &&
      (!filters.rule || product.rule === filters.rule) &&
      words.every((word) => text.includes(word))
    );
  });
}

export function selection(products, params) {
  const byId = new Map(products.map((item) => [item.id, item]));
  const first =
    byId.get(params.get("product")) || byId.get("oka-original") || products[0];
  const requested = byId.get(params.get("compare"));
  const second =
    requested && requested !== first ? requested : byId.get(first.related[0]);
  return [first, second];
}
