#!/usr/bin/env python3
"""Postaví statický web Nadace OKD z content.json ve vizuálním stylu novasichta.cz.

Spuštění:
    python3 extract.py     # nejdřív vytěží obsah z archivu
    python3 build.py       # vygeneruje docs/ (kořen GitHub Pages)
"""
import csv
import html
import json
import os
import re
import shutil
from collections import Counter
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIV = os.path.expanduser("~/projects/nadaceokd-archiv/www.nadaceokd.cz")
DIST = os.path.join(HERE, "docs")  # docs/ = kořen GitHub Pages

NAV = [
    ("Nadace OKD", "nadace-okd/o-nadaci.html"),
    ("Granty", "granty.html"),
    ("Podpořené projekty", "podporene-projekty.html"),
    ("Aktuality", "novinky.html"),
    ("Ke stažení", "ke-stazeni.html"),
    ("Kontakty", "kontakty.html"),
]

PROGRAMY = [
    {
        "nazev": "Nadace OKD obcím",
        "slug": "granty/grantove-programy/nadace-okd-obcim.html",
        "popis": "Podpora obcí zasažených důlní činností. Peníze jdou na veřejná "
        "prostranství, dětská hřiště a občanskou vybavenost.",
        "img": "program-obcim.jpg",
    },
    {
        "nazev": "Pro region",
        "slug": "granty/grantove-programy/pro-region.html",
        "popis": "Granty pro neziskové organizace v Moravskoslezském kraji na "
        "sociální služby, kulturu, sport a životní prostředí.",
        "img": "program-region.jpg",
    },
    {
        "nazev": "Srdcovka",
        "slug": "granty/grantove-programy/srdcovka.html",
        "popis": "Program pro zaměstnance dárců, kteří ve volném čase dělají něco "
        "prospěšného pro své okolí.",
        "img": "program-srdcovka.jpg",
    },
]

OBRAZKY = {
    "hero.jpg": "files/IMG-8364.jpg",
    "program-obcim.jpg": "files/dokums_raw/tz_nadace_okd_rampa.jpg",
    "program-region.jpg": "files/dokums_raw/kyjovicti_rodaci1.jpg",
    "program-srdcovka.jpg": "files/IMG-8430-1-.jpg",
    "o-nadaci.jpg": "files/IMG-8419.jpg",
    "logo.png": "themes/default/images/nadace_okd_cs.png",
}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

# odkazy na přílohy a obrázky, které v obsahu zůstaly ukazovat do archivu
ASSET_RE = re.compile(
    r'(src|href)="((?:\.\./)*)((?:files|files_public|storage|themes)/[^"]+)"'
)
MANIFEST = os.path.join(
    os.path.expanduser("~/projects/nadaceokd-archiv"), "_prilohy", "manifest.csv"
)
OBRAZKOVE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"}
LIVE = "https://www.nadaceokd.cz/"
# dokumenty (PDF, DOC, ZIP) se do dist/ nekopírují — jen výroční zprávy mají
# přes 500 MB naskenovaných stran. Odkazují se na živý web.
DOKUMENTY_NA_ZIVY_WEB = True


def plain(fragment, limit=None):
    t = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()
    if limit and len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0] + "…"
    return t


def esc(s):
    return html.escape(s or "", quote=True)


# ---------------------------------------------------------------- šablony


def layout(title, body, depth=0, popis=""):
    up = "../" * depth
    nav = "\n".join(
        f'<a href="{up}{href}">{esc(label)}</a>' for label, href in NAV
    )
    return f"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | Nadace OKD</title>
<meta name="description" content="{esc(popis or title)}">
<link rel="stylesheet" href="{up}css/style.css">
</head>
<body>
<header class="hdr">
  <div class="wrap hdr-in">
    <a class="brand" href="{up}index.html">
      <img src="{up}img/logo.png" alt="Nadace OKD" height="44">
    </a>
    <nav class="nav">{nav}</nav>
    <a class="btn btn-sm" href="{up}granty/jak-pozadat-o-grant.html">Chci grant</a>
    <button class="burger" aria-label="Menu">&#9776;</button>
  </div>
</header>
{body}
<footer class="ftr">
  <div class="wrap ftr-in">
    <div>
      <img src="{up}img/logo.png" alt="Nadace OKD" height="40" class="ftr-logo">
      <p class="ftr-adr">Karola Śliwky 149/17<br>733 01 Karviná &ndash; Fryštát<br>
      <a href="mailto:info@nadaceokd.cz">info@nadaceokd.cz</a></p>
    </div>
    <div>
      <h4>Granty</h4>
      <a href="{up}granty/grantove-programy/nadace-okd-obcim.html">Nadace OKD obcím</a>
      <a href="{up}granty/grantove-programy/pro-region.html">Pro region</a>
      <a href="{up}granty/grantove-programy/srdcovka.html">Srdcovka</a>
      <a href="{up}granty/jak-pozadat-o-grant.html">Jak požádat o grant</a>
    </div>
    <div>
      <h4>Nadace</h4>
      <a href="{up}nadace-okd/o-nadaci.html">O nadaci</a>
      <a href="{up}nadace-okd/spravni-a-dozorci-rada-nadace.html">Správní a dozorčí rada</a>
      <a href="{up}nadace-okd/vyrocni-zpravy.html">Výroční zprávy</a>
      <a href="{up}nadace-okd/statut-nadace.html">Statut nadace</a>
    </div>
  </div>
  <div class="wrap ftr-bot">
    <span>&copy; Nadace OKD</span>
    <span class="ftr-note">Ukázkový návrh &ndash; obsah převzatý z nadaceokd.cz</span>
  </div>
</footer>
<script>
document.querySelector('.burger').addEventListener('click',function(){{
  document.querySelector('.nav').classList.toggle('open');
}});
</script>
</body>
</html>
"""


def homepage(pages, stats, novinky):
    o_nadaci = pages.get("cs/nadace-okd/o-nadaci.html")
    lead = plain(o_nadaci["html"], 260) if o_nadaci else ""
    lead = lead.replace("O nadaci Nadace OKD ", "")

    karty = "\n".join(
        f"""      <a class="card" href="{p['slug']}">
        <div class="card-img" style="background-image:url(img/{p['img']})"></div>
        <div class="card-body">
          <h3>{esc(p['nazev'])}</h3>
          <p>{esc(p['popis'])}</p>
          <span class="card-more">Zjistit víc &rarr;</span>
        </div>
      </a>"""
        for p in PROGRAMY
    )

    novinky_html = "\n".join(
        f"""      <a class="np" href="{n['out']}">
        <span class="np-date">{esc(n['datum'] or '')}</span>
        <h3>{esc(n['nadpis'])}</h3>
        <p>{esc(plain(n['html'], 130))}</p>
      </a>"""
        for n in novinky[:6]
    )

    body = f"""
<section class="hero">
  <div class="wrap hero-in">
    <div class="hero-txt">
      <p class="eyebrow">Nadace OKD</p>
      <h1>Pomáháme tam,<br>kde se těžilo uhlí</h1>
      <p class="lead">{esc(lead)}</p>
      <div class="hero-cta">
        <a class="btn" href="granty/jak-pozadat-o-grant.html">Jak požádat o grant</a>
        <a class="btn btn-ghost" href="podporene-projekty.html">Podpořené projekty</a>
      </div>
    </div>
    <div class="hero-img" style="background-image:url(img/hero.jpg)"></div>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head">
      <h2>Naše grantové <span class="hl">programy</span></h2>
      <p>Tři cesty, jak se dostat k podpoře. Liší se tím, kdo může žádat a na co.</p>
    </div>
    <div class="cards">
{karty}
    </div>
  </div>
</section>

<section class="stats">
  <div class="wrap">
    <h2>Nadace <span class="hl">v číslech</span></h2>
    <div class="stat-grid">
      <div class="stat"><strong>{stats['projekty']}</strong><span>podpořených projektů</span></div>
      <div class="stat"><strong>{stats['miliony']}</strong><span>milionů korun rozděleno</span></div>
      <div class="stat"><strong>{stats['programy']}</strong><span>grantové programy</span></div>
      <div class="stat"><strong>{stats['roky']}</strong><span>let podpory regionu</span></div>
    </div>
    <p class="stat-note">Údaje vycházejí z databáze podpořených projektů na webu nadace.</p>
  </div>
</section>

<section class="sec sec-alt">
  <div class="wrap split">
    <div class="split-img" style="background-image:url(img/o-nadaci.jpg)"></div>
    <div class="split-txt">
      <h2>Komu <span class="hl">pomáháme</span></h2>
      <p>Podpora míří do Moravskoslezského kraje, především na Karvinsko, Ostravsko
      a Frýdecko-Místecko &ndash; do míst, která ovlivnila důlní činnost.</p>
      <ul class="ticks">
        <li>neziskovým organizacím a spolkům</li>
        <li>obcím zasaženým těžbou</li>
        <li>zaměstnancům dárců, kteří pomáhají ve svém okolí</li>
      </ul>
      <a class="btn" href="nadace-okd/o-nadaci.html">O nadaci</a>
    </div>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head">
      <h2>Aktuality</h2>
      <p>Co je u nás nového.</p>
    </div>
    <div class="news">
{novinky_html}
    </div>
    <div class="center"><a class="btn btn-ghost" href="novinky.html">Všechny aktuality</a></div>
  </div>
</section>

<section class="cta">
  <div class="wrap cta-in">
    <div>
      <h2>Máte projekt, který dává smysl?</h2>
      <p>Ozvěte se nám, poradíme vám s žádostí.</p>
    </div>
    <div class="cta-btns">
      <a class="btn btn-light" href="granty/jak-pozadat-o-grant.html">Jak požádat o grant</a>
      <a class="btn btn-ghost-light" href="kontakty.html">Kontakty</a>
    </div>
  </div>
</section>
"""
    return layout("Pomáháme tam, kde se těžilo uhlí", body, 0, lead[:150])


def subpage(page, depth, drobky):
    body = f"""
<section class="ph">
  <div class="wrap">
    <nav class="crumbs">{drobky}</nav>
    <h1>{esc(page['nadpis'])}</h1>
  </div>
</section>
<section class="sec">
  <div class="wrap prose">
{page['html']}
  </div>
</section>
"""
    return layout(page["nadpis"], body, depth, plain(page["html"], 150))


def news_index(novinky, depth=0):
    items = "\n".join(
        f"""      <a class="np" href="{n['out']}">
        <span class="np-date">{esc(n['datum'] or '')}</span>
        <h3>{esc(n['nadpis'])}</h3>
        <p>{esc(plain(n['html'], 150))}</p>
      </a>"""
        for n in novinky
    )
    body = f"""
<section class="ph">
  <div class="wrap">
    <nav class="crumbs"><a href="index.html">Úvod</a> / Aktuality</nav>
    <h1>Aktuality</h1>
  </div>
</section>
<section class="sec">
  <div class="wrap"><div class="news">
{items}
  </div></div>
</section>
"""
    return layout("Aktuality", body, depth)


# ---------------------------------------------------------------- přílohy


def nacti_manifest():
    """Mapa cesta v archivu -> jméno souboru s doplněnou příponou."""
    if not os.path.isfile(MANIFEST):
        return {}
    with open(MANIFEST, encoding="utf-8") as fh:
        return {
            r["cesta_v_archivu"].replace("www.nadaceokd.cz/", "", 1): r["nazev_v_prilohach"]
            for r in csv.DictReader(fh)
        }


def cil_prilohy(cesta, manifest):
    """Kam se soubor z archivu uloží v dist/."""
    if cesta.startswith("storage/"):
        jmeno = manifest.get(cesta) or os.path.basename(cesta)
        return f"soubory/{jmeno}"
    return cesta


def je_obrazek(cesta, manifest):
    jmeno = manifest.get(cesta, cesta)
    return os.path.splitext(jmeno)[1].lower() in OBRAZKOVE


def zkopiruj_prilohy():
    """Přenese přílohy a obrázky z archivu do dist/ a přepíše na ně odkazy."""
    manifest = nacti_manifest()
    prenesene, chybejici, upravene = {}, Counter(), 0
    na_zivy = 0

    for koren, _, soubory in os.walk(DIST):
        for jmeno in soubory:
            if not jmeno.endswith(".html"):
                continue
            plna = os.path.join(koren, jmeno)
            rel = os.path.relpath(plna, DIST)
            up = "../" * rel.count(os.sep)
            with open(plna, encoding="utf-8") as fh:
                text = fh.read()

            def nahrad(m):
                nonlocal na_zivy
                cesta = unquote(m.group(3)).split("?")[0].split("#")[0]
                zdroj = os.path.join(ARCHIV, cesta)
                if not os.path.isfile(zdroj):
                    chybejici[cesta] += 1
                    return m.group(0)
                if DOKUMENTY_NA_ZIVY_WEB and not je_obrazek(cesta, manifest):
                    na_zivy += 1
                    return f'{m.group(1)}="{LIVE}{m.group(3)}"'
                cil = cil_prilohy(cesta, manifest)
                prenesene[cil] = zdroj
                return f'{m.group(1)}="{up}{cil}"'

            novy = ASSET_RE.sub(nahrad, text)
            if novy != text:
                with open(plna, "w", encoding="utf-8") as fh:
                    fh.write(novy)
                upravene += 1

    for cil, zdroj in prenesene.items():
        full = os.path.join(DIST, cil)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        shutil.copy(zdroj, full)

    velikost = sum(os.path.getsize(os.path.join(DIST, c)) for c in prenesene)
    print(f"obrázků přeneseno: {len(prenesene)} ({velikost / 1_048_576:.1f} MB)")
    print(f"dokumentů odkázaných na živý web: {na_zivy}")
    print(f"stránek s přepsanými odkazy: {upravene}")
    if chybejici:
        print(f"chybí v archivu: {sum(chybejici.values())} odkazů")
        for cesta, poc in chybejici.most_common(10):
            print(f"  {poc}× {cesta}")


# ---------------------------------------------------------------- build


def main():
    with open(os.path.join(HERE, "content.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    pages = {p["zdroj"]: p for p in data}

    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "img"), exist_ok=True)
    os.makedirs(os.path.join(DIST, "css"), exist_ok=True)

    # obrázky z archivu
    for cil, zdroj in OBRAZKY.items():
        src = os.path.join(ARCHIV, zdroj)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(DIST, "img", cil))
        else:
            print(f"  chybí obrázek: {zdroj}")

    shutil.copy(os.path.join(HERE, "style.css"), os.path.join(DIST, "css", "style.css"))

    # statistiky z databáze podpořených projektů
    pp = pages.get("cs/podporene-projekty.html")
    projekty, celkem, roky = 0, 0, []
    if pp:
        t = html.unescape(TAG_RE.sub("|", pp["html"]))
        castky = [int(re.sub(r"\s", "", c)) for c in re.findall(r"(\d[\d\s]{2,9})\s*Kč", t)]
        projekty, celkem = len(castky), sum(castky)
        roky = [int(r) for r in re.findall(r"\b(20[0-2]\d)\b", t)]
    rozsah = (max(roky) - min(roky)) if roky else 0
    stats = {
        "projekty": f"{projekty:,}".replace(",", " "),
        "miliony": f"{round(celkem / 1_000_000)}",
        "programy": len(PROGRAMY),
        "roky": rozsah or "—",
    }

    # novinky
    novinky = [
        p for p in data
        if p["sekce"] == "novinky" and p["slug"] != "novinky" and p["delka"] > 60
    ]
    for n in novinky:
        n["out"] = f"novinky/{n['slug']}.html"
    novinky.sort(key=lambda n: n["datum"] or "", reverse=True)

    napsano = 0

    def zapis(relpath, text):
        nonlocal napsano
        full = os.path.join(DIST, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        napsano += 1

    zapis("index.html", homepage(pages, stats, novinky))
    zapis("novinky.html", news_index(novinky))

    for n in novinky:
        crumbs = '<a href="../index.html">Úvod</a> / <a href="../novinky.html">Aktuality</a>'
        zapis(n["out"], subpage(n, 1, crumbs))

    # ostatní obsahové stránky
    preskoc = {"novinky", "pro-media", "sitemap"}
    for p in data:
        if p["sekce"] in preskoc or p["delka"] < 60 or p["zdroj"] == "cs.html":
            continue
        rel = p["zdroj"][len("cs/"):]
        depth = rel.count("/")
        crumbs = f'<a href="{"../" * depth}index.html">Úvod</a> / {esc(p["nadpis"])}'
        zapis(rel, subpage(p, depth, crumbs))

    zkopiruj_prilohy()

    print(f"vygenerováno stránek: {napsano}")
    print(f"statistiky: {stats['projekty']} projektů, {stats['miliony']} mil. Kč, rozsah {rozsah} let")
    print(f"novinek: {len(novinky)}")
    print(f"výstup: {DIST}")


if __name__ == "__main__":
    main()
