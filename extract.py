#!/usr/bin/env python3
"""Vytáhne obsah ze staženého archivu nadaceokd.cz do content.json.

Archiv:  ~/projects/nadaceokd-archiv/www.nadaceokd.cz
Výstup:  content.json  (seznam stránek: sekce, slug, titulek, nadpis, HTML obsahu)
"""
import html
import json
import os
import re

ARCHIV = os.path.expanduser("~/projects/nadaceokd-archiv/www.nadaceokd.cz")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content.json")

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def text_of(fragment):
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def grab_div(text, class_name):
    """Vrátí vnitřek prvního <div class="...class_name..."> včetně vnořených divů."""
    m = re.search(r'<div[^>]*class="[^"]*\b' + re.escape(class_name) + r'\b[^"]*"[^>]*>', text)
    if not m:
        return None
    start = m.end()
    depth = 1
    pos = start
    tag = re.compile(r"</?div\b", re.I)
    while depth and pos < len(text):
        t = tag.search(text, pos)
        if not t:
            break
        depth += -1 if t.group(0).lower().startswith("</") else 1
        pos = t.end()
    return text[start : pos - len("</div")] if depth == 0 else text[start:]


def clean(fragment):
    """Vyhodí skripty, styly, widgety a prázdné obaly; nechá text, odkazy, obrázky, tabulky."""
    if not fragment:
        return ""
    f = re.sub(r"<script.*?</script>", "", fragment, flags=re.S | re.I)
    f = re.sub(r"<style.*?</style>", "", f, flags=re.S | re.I)
    f = re.sub(r"<!--.*?-->", "", f, flags=re.S)
    # sociální a vyhledávací widgety
    for cls in ("fb-widget", "search", "widget-uwaga", "more", "corner"):
        while True:
            inner = grab_div(f, cls)
            if inner is None:
                break
            f = f.replace(inner, "", 1)
            f = re.sub(r'<div[^>]*class="[^"]*\b' + cls + r'\b[^"]*"[^>]*>\s*</div>', "", f, count=1)
            break
    f = re.sub(r"\s*(class|id|style|onclick|rel|target)=\"[^\"]*\"", "", f)
    f = re.sub(r"<div[^>]*>|</div>", "", f)
    f = re.sub(r"(\s*<br\s*/?>\s*){3,}", "<br><br>", f, flags=re.I)
    f = re.sub(r"<p>\s*(&nbsp;|\s)*</p>", "", f, flags=re.I)
    f = WS_RE.sub(" ", f)
    return f.strip()


def parse(path, rel=None):
    rel = rel or os.path.relpath(path, ARCHIV).replace(os.sep, "/")
    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()

    title = ""
    m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    if m:
        title = text_of(m.group(1)).replace(" | Nadace OKD", "").strip()

    heading = ""
    head_div = grab_div(raw, "page-heading")
    if head_div:
        h = re.search(r"<h[12][^>]*>(.*?)</h[12]>", head_div, re.S | re.I)
        heading = text_of(h.group(1)) if h else text_of(head_div)
    if not heading:
        h = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S | re.I)
        heading = text_of(h.group(1)) if h else title

    body = clean(grab_div(raw, "page-content") or "")

    # datum u novinek
    date = ""
    nd = re.search(r'class="news-date">([^<]*)<', raw)
    d = re.search(
        r"(\d{1,2})\.\s?(\d{1,2})\.\s?(20\d{2})",
        (nd.group(1) if nd else "") + (head_div or "") + body[:400],
    )
    if d:
        date = f"{int(d.group(1))}. {int(d.group(2))}. {d.group(3)}"

    parts = rel[: -len(".html")].split("/")
    section = parts[1] if len(parts) > 1 else "home"

    return {
        "zdroj": rel,
        "sekce": section,
        "slug": parts[-1],
        "cesta": "/".join(parts[1:]) if len(parts) > 1 else "index",
        "titulek": title,
        "nadpis": heading,
        "datum": date,
        "html": body,
        "delka": len(text_of(body)),
    }


def main():
    pages = []
    videne = set()
    for dirpath, _d, filenames in os.walk(ARCHIV):
        # soubory bez „?“ napřed, ať má čistá kopie přednost před stránkovanou
        for fn in sorted(filenames, key=lambda f: ("?" in f, f)):
            if not fn.endswith(".html") or fn.endswith(".orig"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ARCHIV)
            if not (rel == "cs.html" or rel.startswith("cs" + os.sep)):
                continue
            if "?" in fn:
                # aktualita stažená jen přes stránkování výpisu
                # (clanek?FfNewsItem_page=N.html), jinak se stránkované kopie přeskočí
                if os.path.basename(dirpath) != "novinky":
                    continue
                rel = os.path.join(os.path.dirname(rel), fn.split("?")[0] + ".html")
            rel = rel.replace(os.sep, "/")
            if rel in videne:
                continue
            videne.add(rel)
            try:
                pages.append(parse(full, rel))
            except Exception as exc:  # noqa: BLE001
                print(f"  chyba {rel}: {exc}")

    pages.sort(key=lambda p: p["zdroj"])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(pages, fh, ensure_ascii=False, indent=1)

    print(f"stránek: {len(pages)}")
    prazdne = [p for p in pages if p["delka"] < 60]
    print(f"s obsahem: {len(pages) - len(prazdne)}   skoro prázdných: {len(prazdne)}")
    from collections import Counter

    for sec, n in Counter(p["sekce"] for p in pages).most_common():
        print(f"  {sec}: {n}")


if __name__ == "__main__":
    main()
