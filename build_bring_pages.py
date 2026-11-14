#!/usr/bin/env python3
"""Erzeugt statische Rezeptseiten mit schema.org/Recipe (JSON-LD) fuer den Bring!-Import.

Aufruf: python3 build_bring_pages.py <base_url> <data_dir> <out_dir>
  base_url  z. B. https://<github-name>.github.io/rezepte/
Ergebnis:   out_dir/r/<rezept-id>.html, out_dir/l/<batch>.html, out_dir/img/*.png,
            out_dir/index.html, out_dir/manifest.json
Kein robots.txt-Verbot: der Bring-Parser muss die Seiten abrufen duerfen; noindex haelt sie aus Suchmaschinen.
"""
import html, json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DROP_PARTS = {"roh", "trocken", "abgetropft"}


def clean_name(name: str) -> str:
    """Yazio-Bezeichnung -> einkaufstaugliche Bezeichnung fuer den Bring-Parser."""
    n = re.sub(r"\s*\([^)]*\)", "", name)          # Klammerzusaetze weg
    parts = [p.strip() for p in n.split(",")]
    keep = [parts[0]] + [p for p in parts[1:] if p and p not in DROP_PARTS and not re.search(r"\d", p)]
    return re.sub(r"\s+", " ", " ".join(keep)).strip()


def fmt_num(x) -> str:
    if isinstance(x, (int, float)):
        return (str(int(x)) if float(x).is_integer() else str(x)).replace(".", ",")
    return str(x)


def ingredient_line(z) -> str:
    unit = f" {z['einheit']}" if z.get("einheit") else ""
    return f"{fmt_num(z['menge'])}{unit} {clean_name(z['name'])}"


def list_line(artikel: str) -> str:
    """'Paprika rot – 4 Stück (600 g)' -> '4 Stück Paprika rot (600 g)'."""
    if " – " not in artikel:
        return artikel
    name, menge = artikel.split(" – ", 1)
    m = re.match(r"^(.*?)\s*(\(.*\))?$", menge.strip())
    main, extra = m.group(1), m.group(2) or ""
    if not re.match(r"^(ca\.\s*)?\d", main):        # Menge ohne Zahl, z. B. "1 Bund" hat Zahl; Fallback
        return f"{name} ({menge})"
    return f"{main} {name} {extra}".strip()


def make_image(path: Path, title: str, sub: str):
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), (47, 111, 79))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 120, W, H], fill=(36, 88, 62))
    f_big = ImageFont.truetype(FONT, 64)
    f_small = ImageFont.truetype(FONT, 36)
    words, lines, cur = title.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f_big) > W - 160:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    y = (H - 120 - len(lines) * 80) // 2
    for ln in lines:
        d.text((80, y), ln, font=f_big, fill=(255, 255, 255)); y += 80
    d.text((80, H - 85), sub, font=f_small, fill=(227, 239, 232))
    img.save(path, optimize=True)


def page(title, jsonld, body_html, base):
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(title)}</title>
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
<style>body{{font:16px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#1f2421}}
h1{{font-size:24px;line-height:1.2}}li{{margin:4px 0}}.m{{color:#6b726d;font-size:14px}}</style>
</head><body>{body_html}</body></html>
"""


def recipe_page(r, base):
    rid, p = r["id"], r["portionen"]
    img = f"{base}img/{rid}.png"
    nw = r.get("naehrwerte_portion", {})
    ingr = [ingredient_line(z) for z in r["zutaten"]]
    ld = {
        "@context": "https://schema.org", "@type": "Recipe",
        "name": r["titel"],
        "description": f"{r['titel']} – {p} {'Portion' if p == 1 else 'Portionen'}, {nw.get('kcal', 0)} kcal und {nw.get('eiweiss', 0)} g Eiweiß pro Portion.",
        "image": [img],
        "author": {"@type": "Person", "name": "Unser Rezeptbuch"},
        "recipeCategory": "Hauptgericht",
        "keywords": ", ".join(r.get("tags", [])),
        "recipeYield": [str(p), f"{p} {'Portion' if p == 1 else 'Portionen'}"],
        "prepTime": f"PT{r['arbeitszeit']}M",
        "totalTime": f"PT{r['gesamtzeit']}M",
        "nutrition": {"@type": "NutritionInformation", "calories": f"{nw.get('kcal', 0)} kcal",
                      "proteinContent": f"{nw.get('eiweiss', 0)} g", "carbohydrateContent": f"{nw.get('kh', 0)} g",
                      "fatContent": f"{nw.get('fett', 0)} g", "fiberContent": f"{nw.get('bst', 0)} g"},
        "recipeIngredient": ingr,
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in r.get("schritte", [])],
        "url": f"{base}r/{rid}.html",
    }
    body = (f"<h1>{html.escape(r['titel'])}</h1><p class='m'>{p} {'Portion' if p == 1 else 'Portionen'} · "
            f"Arbeitszeit {r['arbeitszeit']} min · {nw.get('kcal', 0)} kcal / Portion</p><h2>Zutaten</h2><ul>"
            + "".join(f"<li>{html.escape(i)}</li>" for i in ingr) + "</ul><h2>Zubereitung</h2><ol>"
            + "".join(f"<li>{html.escape(s)}</li>" for s in r.get("schritte", [])) + "</ol>")
    return page(r["titel"], ld, body, base), ingr


def list_page(l, base):
    lid = l["id"]
    items = [list_line(a) for s in l.get("rubriken", []) for a in s.get("artikel", [])]
    items += list(l.get("pruefen", []))
    ld = {
        "@context": "https://schema.org", "@type": "Recipe",
        "name": f"Einkauf {l['titel']}",
        "description": "Gesammelte Einkaufsliste der Woche; Vorräte bitte in Bring abwählen.",
        "image": [f"{base}img/{lid}.png"],
        "author": {"@type": "Person", "name": "Unser Rezeptbuch"},
        "recipeYield": ["1"],
        "recipeIngredient": items,
        "recipeInstructions": [{"@type": "HowToStep", "text": "Einkaufen."}],
        "url": f"{base}l/{lid}.html",
    }
    body = f"<h1>Einkauf {html.escape(l['titel'])}</h1><ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul>"
    return page(f"Einkauf {l['titel']}", ld, body, base), items


def main():
    base, data_dir, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if not base.endswith("/"):
        base += "/"
    rezepte = json.loads((data_dir / "rezepte.json").read_text("utf-8"))
    listen = json.loads((data_dir / "listen.json").read_text("utf-8"))
    for sub in ("r", "l", "img"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    manifest = {"rezepte": [], "listen": []}
    for r in rezepte:
        doc, _ = recipe_page(r, base)
        (out / "r" / f"{r['id']}.html").write_text(doc, "utf-8")
        make_image(out / "img" / f"{r['id']}.png", r["titel"], f"{r['portionen']} Port. · {r['naehrwerte_portion']['kcal']} kcal")
        manifest["rezepte"].append(r["id"])
    for l in listen:
        doc, _ = list_page(l, base)
        (out / "l" / f"{l['id']}.html").write_text(doc, "utf-8")
        make_image(out / "img" / f"{l['id']}.png", f"Einkauf {l['titel']}", "Wocheneinkauf")
        manifest["listen"].append(l["id"])
    (out / "index.html").write_text(page("Rezepte für Bring", {"@context": "https://schema.org", "@type": "WebPage", "name": "Rezepte für Bring"},
                                         "<h1>Rezepte für den Bring!-Import</h1><p>Technische Seiten für das Rezeptbuch.</p>", base), "utf-8")
    (out / ".nojekyll").write_text("", "utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
