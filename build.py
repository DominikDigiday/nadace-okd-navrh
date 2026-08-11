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
        "kratce": "Podpora obcí zasažených důlní činností.",
        "img": "program-obcim.jpg",
        "ikona": "ico-obcim.svg",
    },
    {
        "nazev": "Pro region",
        "slug": "granty/grantove-programy/pro-region.html",
        "popis": "Granty pro neziskové organizace v Moravskoslezském kraji na "
        "sociální služby, kulturu, sport a životní prostředí.",
        "kratce": "Granty pro neziskové organizace v Moravskoslezském kraji.",
        "img": "program-region.jpg",
        "ikona": "ico-region.svg",
    },
    {
        "nazev": "Srdcovka",
        "slug": "granty/grantove-programy/srdcovka.html",
        "popis": "Program pro zaměstnance dárců, kteří ve volném čase dělají něco "
        "prospěšného pro své okolí.",
        "kratce": "Program pro zaměstnance dárců, kteří pomáhají ve svém okolí.",
        "img": "program-srdcovka.jpg",
        "ikona": "ico-srdcovka.svg",
    },
]

# boxy „komu pomáháme“ na úvodní stránce (šablona je ukazuje s hover překryvem)
KOMU = [
    {
        "nazev": "Neziskovým organizacím",
        "popis": "Spolkům a neziskovkám na sociální služby, kulturu, sport "
        "a životní prostředí v Moravskoslezském kraji.",
        "ikona": "ico-region.svg",
    },
    {
        "nazev": "Obcím zasaženým těžbou",
        "popis": "Na veřejná prostranství, dětská hřiště a občanskou vybavenost "
        "v obcích ovlivněných důlní činností.",
        "ikona": "ico-obcim.svg",
    },
    {
        "nazev": "Zaměstnancům dárců",
        "popis": "Lidem, kteří ve svém volném čase dělají něco prospěšného "
        "pro své okolí.",
        "ikona": "ico-srdcovka.svg",
    },
]

SEKCE_NAZVY = {
    "granty": "Granty",
    "nadace-okd": "Nadace OKD",
    "ke-stazeni": "Ke stažení",
    "novinky": "Aktuality",
    "kontakty": "Kontakty",
    "podporene-projekty": "Podpořené projekty",
    "inkubator": "Nadace OKD",
    "sidliste-zije": "Programy",
    "zazitky-bez-barier": "Programy",
    "prohlaseni-o-pristupnosti": "Nadace OKD",
}

# ikony pro page-boxy a boxy „komu pomáháme“; šablona je má jako SVG,
# barví je na bílou přes filter: brightness(0) invert(1)
IKONY = {
    "ico-obcim.svg": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none' "
        "stroke='#96bf0d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M6 30 32 10l26 20'/><path d='M12 28v26h40V28'/>"
        "<path d='M26 54V38h12v16'/></svg>"
    ),
    "ico-region.svg": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none' "
        "stroke='#96bf0d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        "<circle cx='22' cy='20' r='9'/><circle cx='44' cy='24' r='7'/>"
        "<path d='M6 52c0-9 7-16 16-16s16 7 16 16'/>"
        "<path d='M40 40c9 0 18 5 18 12'/></svg>"
    ),
    "ico-srdcovka.svg": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none' "
        "stroke='#96bf0d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M32 54S8 40 8 24a12 12 0 0 1 24-5 12 12 0 0 1 24 5c0 16-24 30-24 30z'/>"
        "</svg>"
    ),
}

OBRAZKY = {
    "hero-1.jpg": "files/IMG-8364.jpg",
    "hero-2.jpg": "files/IMG-8419.jpg",
    "hero-3.jpg": "files/IMG-8430-1-.jpg",
    "program-obcim.jpg": "files/dokums_raw/tz_nadace_okd_rampa.jpg",
    "program-region.jpg": "files/dokums_raw/kyjovicti_rodaci1.jpg",
    "program-srdcovka.jpg": "files/IMG-8430-1-.jpg",
    "logo.png": "themes/default/images/nadace_okd_cs.png",
}

# snímky v hlavičce – šablona je má jako carousel se třemi slidy
HERO = ["hero-1.jpg", "hero-2.jpg", "hero-3.jpg"]

# fotky z archivu jsou v plném rozlišení (i 3,5 MB), pro web se zmenší
MAX_SIRKA = 1920

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
H1_RE = re.compile(r"\s*<h1[^>]*>(.*?)</h1>\s*", re.S | re.I)

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


def datum_klic(datum):
    """Datum ve tvaru „4. 12. 2025“ na (rok, měsíc, den) kvůli řazení."""
    m = re.match(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", datum or "")
    if not m:
        return (0, 0, 0)
    d, mes, r = (int(x) for x in m.groups())
    return (r, mes, d)


# ---------------------------------------------------------------- šablony


def priprav(page):
    """Skutečný název stránky je <h1> v obsahu, pole 'nadpis' nese název sekce.
    Titulek se vytáhne ven, aby se v šabloně neopakoval dvakrát."""
    m = H1_RE.search(page["html"])
    if m:
        page["titul"] = plain(m.group(1))
        page["html"] = H1_RE.sub("", page["html"], count=1)
    else:
        page["titul"] = page["nadpis"]
    page["sekce_nazev"] = SEKCE_NAZVY.get(page["sekce"], page["nadpis"])
    return page


def zeleny_zacatek(nadpis):
    """První slovo nadpisu zeleně, jak to dělá šablona přes <em>."""
    casti = (nadpis or "").split(" ", 1)
    if len(casti) == 1:
        return f"<em>{esc(nadpis)}</em>"
    return f"<em>{esc(casti[0])}</em> {esc(casti[1])}"


def layout(title, body, depth=0, popis=""):
    up = "../" * depth
    menu = "\n".join(
        f'<li class="menu-item"><a href="{up}{href}" class="nav-link">{esc(label)}</a></li>'
        for label, href in NAV
    )
    menu += (
        f'\n<li class="button menu-item">'
        f'<a href="{up}granty/jak-pozadat-o-grant.html" class="nav-link">Chci grant</a></li>'
    )
    mob_menu = "\n".join(
        f'<li class="menu-item"><a href="{up}{href}">{esc(label)}</a></li>'
        for label, href in NAV
    ) + (
        f'\n<li class="menu-item">'
        f'<a href="{up}granty/jak-pozadat-o-grant.html">Chci grant</a></li>'
    )

    boxy = "\n".join(
        f"""      <a class="page-box" href="{up}{p['slug']}">
        <img src="{up}img/{p['ikona']}" alt="{esc(p['nazev'])}">
        <h2>{esc(p['nazev'])}</h2>
        <p>{esc(p['kratce'])}</p>
      </a>"""
        for p in PROGRAMY
    )

    slidy = "\n".join(
        f'        <div class="carousel-item{" active" if i == 0 else ""}">'
        f'<img src="{up}img/{jm}" alt="Nadace OKD"></div>'
        for i, jm in enumerate(HERO)
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
<header id="site-header">
  <div id="header-fixed">
    <div class="container">
      <div class="header-row">
        <a id="logo" href="{up}index.html"><img src="{up}img/logo.png" alt="Nadace OKD"></a>
        <ul class="nav main-menu">
{menu}
        </ul>
        <div id="main-menu-toggler"><span></span><span></span><span></span></div>
      </div>
    </div>
  </div>
</header>
<div id="expanded-menu">
  <ul>
{mob_menu}
  </ul>
</div>
<div id="header-spacer"></div>

<section>
  <div class="container" id="header-carousel">
    <div id="introCarousel">
      <div class="carousel-inner">
{slidy}
      </div>
      <button class="carousel-control-prev" type="button" aria-label="Předchozí">
        <span class="carousel-control-prev-icon"></span>
      </button>
      <button class="carousel-control-next" type="button" aria-label="Další">
        <span class="carousel-control-next-icon"></span>
      </button>
    </div>
    <div class="header-pages">
{boxy}
    </div>
  </div>
</section>

<main>
  <section id="content" class="main-content">
    <div class="container">
      <div class="content-col">
{body}
      </div>
    </div>
  </section>
</main>

<footer>
  <div class="container">
    <div class="text-center pb-5 mb-5">
      <a href="{up}index.html" id="footer-logo"><img src="{up}img/logo.png" alt="Nadace OKD" height="54"></a>
    </div>
    <div class="footer-kontakty pb-5 mb-5">
      <p>Karola &Sacute;liwky 149/17, 733 01 Karvin&aacute; &ndash; Fry&scaron;t&aacute;t</p>
      <p><a href="mailto:info@nadaceokd.cz">info@nadaceokd.cz</a></p>
    </div>
    <div class="footer-menus">
      <div>
        <h2>Menu</h2>
        <ul>
          <li><a href="{up}nadace-okd/o-nadaci.html">Nadace OKD</a></li>
          <li><a href="{up}granty.html">Granty</a></li>
          <li><a href="{up}podporene-projekty.html">Podpo&rcaron;en&eacute; projekty</a></li>
          <li><a href="{up}novinky.html">Aktuality</a></li>
          <li><a href="{up}ke-stazeni.html">Ke sta&zcaron;en&iacute;</a></li>
          <li><a href="{up}kontakty.html">Kontakty</a></li>
        </ul>
      </div>
      <div>
        <h2>Granty</h2>
        <ul>
          <li><a href="{up}granty/grantove-programy/nadace-okd-obcim.html">Nadace OKD obc&iacute;m</a></li>
          <li><a href="{up}granty/grantove-programy/pro-region.html">Pro region</a></li>
          <li><a href="{up}granty/grantove-programy/srdcovka.html">Srdcovka</a></li>
          <li><a href="{up}granty/jak-pozadat-o-grant.html">Jak po&zcaron;&aacute;dat o grant</a></li>
          <li><a href="{up}granty/zpusob-vyberu-projektu.html">Zp&uring;sob v&yacute;b&ecaron;ru projekt&uring;</a></li>
        </ul>
      </div>
      <div>
        <h2>Nadace</h2>
        <ul>
          <li><a href="{up}nadace-okd/o-nadaci.html">O nadaci</a></li>
          <li><a href="{up}nadace-okd/spravni-a-dozorci-rada-nadace.html">Spr&aacute;vn&iacute; a dozor&ccaron;&iacute; rada</a></li>
          <li><a href="{up}nadace-okd/vyrocni-zpravy.html">V&yacute;ro&ccaron;n&iacute; zpr&aacute;vy</a></li>
          <li><a href="{up}nadace-okd/statut-nadace.html">Statut nadace</a></li>
          <li><a href="{up}nadace-okd/zrizovatele-darci-a-partneri.html">Z&rcaron;izovatel&eacute; a d&aacute;rci</a></li>
        </ul>
      </div>
    </div>
    <div id="footer-copy">
      <span>&copy; Nadace OKD</span>
      <span>Uk&aacute;zkov&yacute; n&aacute;vrh &ndash; obsah p&rcaron;evzat&yacute; z nadaceokd.cz</span>
    </div>
  </div>
</footer>

<script>
(function () {{
  var hdr = document.getElementById('site-header');
  window.addEventListener('scroll', function () {{
    hdr.classList.toggle('scrolled', window.scrollY > 40);
  }});
  var tog = document.getElementById('main-menu-toggler');
  var exp = document.getElementById('expanded-menu');
  tog.addEventListener('click', function () {{
    tog.classList.toggle('active-menu');
    exp.classList.toggle('active-menu');
  }});
  var slidy = document.querySelectorAll('#introCarousel .carousel-item');
  if (slidy.length > 1) {{
    var akt = 0, timer;
    var jdi = function (smer) {{
      slidy[akt].classList.remove('active');
      akt = (akt + smer + slidy.length) % slidy.length;
      slidy[akt].classList.add('active');
    }};
    var start = function () {{ timer = setInterval(function () {{ jdi(1); }}, 6000); }};
    var reset = function () {{ clearInterval(timer); start(); }};
    document.querySelector('.carousel-control-prev').addEventListener('click', function () {{ jdi(-1); reset(); }});
    document.querySelector('.carousel-control-next').addEventListener('click', function () {{ jdi(1); reset(); }});
    start();
  }}
  var io = new IntersectionObserver(function (es) {{
    es.forEach(function (e) {{ if (e.isIntersecting) {{ e.target.classList.add('moved-done'); io.unobserve(e.target); }} }});
  }}, {{ rootMargin: '0px 0px -80px 0px' }});
  document.querySelectorAll('.moved').forEach(function (el) {{ io.observe(el); }});
}})();
</script>
</body>
</html>
"""


def homepage(pages, stats, novinky):
    o_nadaci = pages.get("cs/nadace-okd/o-nadaci.html")
    lead = plain(o_nadaci["html"], 260) if o_nadaci else ""
    lead = lead.replace("O nadaci Nadace OKD ", "")

    komu = "\n".join(
        f"""        <div class="box-content">
          <img src="img/{k['ikona']}" alt="">
          <p>{esc(k['nazev'])}</p>
          <div class="box-hover"><p>{esc(k['popis'])}</p></div>
        </div>"""
        for k in KOMU
    )

    programy = "\n".join(
        f"""        <a class="box" href="{p['slug']}">
          <img src="img/{p['img']}" alt="{esc(p['nazev'])}">
          <div class="box-content"><h3>{esc(p['nazev'])}</h3></div>
        </a>"""
        for p in PROGRAMY
    )

    cisla = "\n".join(
        f"""        <div>
          <p>{esc(popisek)}</p>
          <p class="large-number">{hodnota}</p>
        </div>"""
        for hodnota, popisek in [
            (stats["projekty"], "podpořených projektů"),
            (stats["miliony"], "milionů korun rozděleno"),
            (stats["roky"], "let podpory regionu"),
        ]
    )

    slides = "\n".join(
        f"""        <a class="slide" href="{n['out']}">
          <span class="date">{esc(n['datum'] or '')}</span>
          <h3>{esc(n['titul'])}</h3>
          <p>{esc(plain(n['html'], 150))}</p>
        </a>"""
        for n in novinky[:6]
    )

    return layout(
        "Pomáháme tam, kde se těžilo uhlí",
        f"""
<div class="section moved">
  <p class="subtitle text-center">Nadace OKD</p>
  <h2 class="text-center"><em>Pomáháme</em> tam, kde se těžilo uhlí</h2>
  <p class="large-text text-center">{esc(lead)}</p>
  <div class="rotating-boxes mt-5">
{komu}
  </div>
</div>

<div class="section moved">
  <p class="subtitle text-center">Granty</p>
  <h2 class="text-center">Na&scaron;e grantov&eacute; <em>programy</em></h2>
  <div class="boxes mt-5">
{programy}
  </div>
  <div class="text-center mt-5">
    <a class="btn btn-primary" href="granty/jak-pozadat-o-grant.html">Jak po&zcaron;&aacute;dat o grant</a>
  </div>
</div>

<div class="section moved">
  <p class="subtitle text-center">V &ccaron;&iacute;slech</p>
  <h2 class="text-center">Nadace <em>v číslech</em></h2>
  <div class="kontakt-boxy mt-5 text-center">
{cisla}
  </div>
  <p class="text-center">Údaje vycházejí z databáze podpořených projektů na webu nadace.</p>
</div>
""",
        0,
        lead[:150],
    ) .replace(
        "</main>",
        f"""</main>
<section id="reference">
  <div class="container">
    <div class="content-col">
      <p class="subtitle text-center">Aktuality</p>
      <h2 class="text-center">Co je u n&aacute;s <em>nov&eacute;ho</em></h2>
      <div class="slides mt-5">
{slides}
      </div>
      <div class="text-center mt-5">
        <a class="btn btn-primary" href="novinky.html">V&scaron;echny aktuality</a>
      </div>
    </div>
  </div>
</section>""",
    )


def drobecky(depth, aktualni, mezi=None):
    up = "../" * depth
    kusy = [f'<a href="{up}index.html">Úvod</a>']
    for label, href in mezi or []:
        kusy.append(f'<a href="{up}{href}">{esc(label)}</a>')
    kusy.append(f'<span class="breadcrumb_last">{esc(aktualni)}</span>')
    sep = '<span class="breadcumb-separator">›</span>'
    return f'<div id="breadcrumbs">{sep.join(kusy)}</div>'


def subpage(page, depth, mezi=None):
    datum = (
        f'<p class="subtitle text-center">{esc(page["datum"])}</p>'
        if page.get("datum") and page["sekce"] == "novinky"
        else ""
    )
    body = f"""
{drobecky(depth, page['titul'], mezi)}
<div class="section moved">
  <p class="subtitle text-center">{esc(page['sekce_nazev'])}</p>
  <h1 class="text-center">{zeleny_zacatek(page['titul'])}</h1>
  {datum}
  <article class="mt-5">
{page['html']}
  </article>
</div>
"""
    return layout(page["titul"], body, depth, plain(page["html"], 150))


def news_index(novinky, depth=0):
    slides = "\n".join(
        f"""      <a class="slide" href="{n['out']}">
        <span class="date">{esc(n['datum'] or '')}</span>
        <h3>{esc(n['titul'])}</h3>
        <p>{esc(plain(n['html'], 150))}</p>
      </a>"""
        for n in novinky
    )
    body = f"""
{drobecky(depth, 'Aktuality')}
<div class="section moved">
  <p class="subtitle text-center">Nadace OKD</p>
  <h1 class="text-center"><em>Aktuality</em></h1>
  <div class="slides mt-5">
{slides}
  </div>
</div>
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


def zmensi(cesta, max_sirka=MAX_SIRKA):
    """Zmenší fotku na rozumnou šířku pro web; bez Pillow soubor nechá být."""
    try:
        from PIL import Image
    except ImportError:
        return
    try:
        with Image.open(cesta) as im:
            if im.width <= max_sirka:
                return
            novy = im.convert("RGB") if im.mode in ("P", "RGBA") else im
            novy = novy.resize(
                (max_sirka, round(im.height * max_sirka / im.width)), Image.LANCZOS
            )
            novy.save(cesta, quality=82, optimize=True)
    except Exception as e:  # poškozený soubor v archivu build nepoloží
        print(f"  nešlo zmenšit {os.path.basename(cesta)}: {e}")


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
        if os.path.splitext(cil)[1].lower() in (".jpg", ".jpeg"):
            zmensi(full)

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
    for p in data:
        priprav(p)
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
            if cil.endswith(".jpg"):
                zmensi(os.path.join(DIST, "img", cil))
        else:
            print(f"  chybí obrázek: {zdroj}")

    for jmeno, svg in IKONY.items():
        with open(os.path.join(DIST, "img", jmeno), "w", encoding="utf-8") as fh:
            fh.write(svg)

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
    novinky.sort(key=lambda n: datum_klic(n["datum"]), reverse=True)

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
        zapis(n["out"], subpage(n, 1, [("Aktuality", "novinky.html")]))

    # ostatní obsahové stránky
    preskoc = {"novinky", "pro-media", "sitemap"}
    for p in data:
        if p["sekce"] in preskoc or p["delka"] < 60 or p["zdroj"] == "cs.html":
            continue
        rel = p["zdroj"][len("cs/"):]
        depth = rel.count("/")
        zapis(rel, subpage(p, depth))

    zkopiruj_prilohy()

    print(f"vygenerováno stránek: {napsano}")
    print(f"statistiky: {stats['projekty']} projektů, {stats['miliony']} mil. Kč, rozsah {rozsah} let")
    print(f"novinek: {len(novinky)}")
    print(f"výstup: {DIST}")


if __name__ == "__main__":
    main()
