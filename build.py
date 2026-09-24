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

# pořadí = důležitost programu (tak je chce mít nadace ve slideru i v gridu)
PROGRAMY = [
    {
        "nazev": "Pro region",
        "slug": "granty/grantove-programy/pro-region.html",
        "popis": "Granty pro neziskové organizace v Moravskoslezském kraji na "
        "sociální služby, kulturu, sport a životní prostředí.",
        "kratce": "Granty pro neziskové organizace v Moravskoslezském kraji.",
        "hero": "Granty pro neziskové organizace<br>v&nbsp;Moravskoslezském kraji",
        "img": "program-region.jpg",
        "ikona": "ico-region.svg",
    },
    {
        "nazev": "Srdcovka",
        "slug": "granty/grantove-programy/srdcovka.html",
        "popis": "Program pro zaměstnance dárců, kteří ve volném čase dělají něco "
        "prospěšného pro své okolí.",
        "kratce": "Program pro zaměstnance dárců, kteří pomáhají ve svém okolí.",
        "hero": "Program pro zaměstnance dárců,<br>kteří pomáhají ve svém okolí",
        "img": "program-srdcovka.jpg",
        "ikona": "ico-srdcovka.svg",
    },
    {
        "nazev": "Hornické tradice",
        "slug": "granty/grantove-programy/hornicke-tradice.html",
        "popis": "Zachování hornického historicko-kulturního dědictví a podpora "
        "klubů hornických seniorů a krojovaných horníků.",
        "kratce": "Zachování hornického dědictví regionu.",
        "img": "program-hornicke.jpg",
        "ikona": "ico-hornicke.svg",
    },
    {
        "nazev": "Spolek svatá Barbora",
        "slug": "granty/grantove-programy/spolek-svata-barbora.html",
        "popis": "Pomoc dětem a rodinám zaměstnanců, kteří zemřeli v důsledku "
        "práce v hornictví.",
        "kratce": "Pomoc dětem hornických rodin, které přišly o rodiče.",
        "img": "program-barbora.jpg",
        "ikona": "ico-barbora.svg",
    },
    {
        "nazev": "Nadace OKD obcím",
        "slug": "granty/grantove-programy/nadace-okd-obcim.html",
        "popis": "Podpora obcí zasažených důlní činností. Peníze jdou na veřejná "
        "prostranství, dětská hřiště a občanskou vybavenost.",
        "kratce": "Podpora obcí zasažených důlní činností.",
        "img": "program-obcim.jpg",
        "ikona": "ico-obcim.svg",
    },
]
# slider v hlavičce úvodní stránky ukazuje tři nejdůležitější programy
SLIDER_PROGRAMY = PROGRAMY[:3]

# stránka Spolku svatá Barbora na starém webu chybí, text je z „O nadaci“
# a z webu spolku svatabarbora.cz
BARBORA_HTML = """<h1>Spolek svatá Barbora</h1>
<p>Od založení ctí Nadace OKD ideu pomoci dětem a rodinám zaměstnanců, kteří
zemřeli v důsledku práce v hornictví. Spolek svatá Barbora umožňuje díky nadaci
a dalším dárcům dětem, které tato nešťastná událost potkala, dosáhnout vzdělání
odpovídající jejich představám, přáním a předpokladům, aby se mohly v budoucnu
zařadit do aktivního pracovního procesu.</p>
<p>Kromě podpory vzdělávání je spolek rodinám oporou i při řešení dalších
problémů a životních situací, navíc pořádá řadu oblíbených akcí a setkání.</p>
<p>Spolek vznikl 24. června 2004. Za více než 20 let činnosti pomohl více než
100 sirotkům částkou přesahující 40 milionů korun.</p>
<p><strong>Spolek svatá Barbora</strong><br>
Stonava 1077, 735 34 Stonava<br>
<a href="mailto:spolek.barbora@seznam.cz">spolek.barbora@seznam.cz</a>, +420 725 756 830</p>
<p><a class="btn btn-primary" href="https://www.svatabarbora.cz/" target="_blank" rel="noopener">Web spolku svatabarbora.cz</a></p>
"""

# stránka programu Hornické tradice na starém webu chybí, text je z „O nadaci“
HORNICKE_TRADICE_HTML = """<h1>Hornické tradice</h1>
<p>Nadace OKD neopomíjí hornické tradice. Základní myšlenkou a cílem programu
je zachování historicko-kulturního dědictví v rámci činnosti klubů hornických
seniorů a příznivců hornictví.</p>
<p><strong>Program podporuje zejména:</strong></p>
<ul>
<li>udržování hornických tradic u výročních příležitostí,</li>
<li>předávání historicko-kulturního dědictví regionu,</li>
<li>volný čas hornických seniorů a členů kroužků krojovaných horníků.</li>
</ul>
<p><a href="../../podporene-projekty.html?program=Hornick%C3%A9%20tradice">Projekty
podpořené v programu Hornické tradice</a></p>
<p>Administrátorka programu: Silvie Balčíková,
<a href="mailto:balcikova@nadaceokd.com">balcikova@nadaceokd.com</a>, +420 725 389 852</p>
"""

EMAIL = "nadaceokd@gmail.com"
IKONA_ADRESA = (
    '<svg class="kontakt-ikona" viewBox="0 0 24 24" width="26" height="26" fill="none" '
    'stroke="#96bf0d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/>'
    '<circle cx="12" cy="10" r="2.6"/></svg>'
)
IKONA_EMAIL = (
    '<svg class="kontakt-ikona" viewBox="0 0 24 24" width="26" height="26" fill="none" '
    'stroke="#96bf0d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/>'
    '<path d="m3.5 6.5 8.5 7 8.5-7"/></svg>'
)
SOCIALNI_SITE = [
    ("Facebook", "https://www.facebook.com/NadaceOKD"),
    ("Instagram", "https://www.instagram.com/nadaceokd/"),
    ("X", "https://x.com/Nadace_OKD"),
    ("YouTube", "https://www.youtube.com/@NadaceOKD"),
]
# ikony jsou ze Simple Icons (assets/social), jednotně černé


def socialni_ikony():
    """Odkazy na sociální sítě jako standardní loga (inline SVG v barvě značky)."""
    kusy = []
    for nazev, url in SOCIALNI_SITE:
        with open(os.path.join(HERE, "assets", "social", f"{nazev.lower()}.svg"), encoding="utf-8") as fh:
            svg = fh.read().replace(
                "<svg ", f'<svg width="32" height="32" fill="#000000" aria-hidden="true" ', 1
            )
        svg = re.sub(r"<title>.*?</title>", "", svg)
        kusy.append(
            f'<a class="social-icon" href="{url}" target="_blank" rel="noopener" '
            f'aria-label="{esc(nazev)}" title="{esc(nazev)}">{svg}</a>'
        )
    return "".join(kusy)

# čísla schválená nadací (nadace vznikla v roce 2008)
STATISTIKY = [
    ("3 649", "podpořených projektů"),
    ("456+", "milionů korun rozděleno"),
    ("18", "let pomáháme regionu (od roku 2008)"),
]

# ruční náhledová fotka aktuality (slug -> cesta v archivu); bez záznamu se
# použije první obrázek z textu aktuality
NAHLEDY = {}

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
    "ico-hornicke.svg": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none' "
        "stroke='#96bf0d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M12 54 44 22'/><path d='M36 12l18 18' stroke-width='7'/>"
        "<path d='M52 54 20 22'/><path d='M8 26C14 16 20 12 28 10' stroke-width='5'/></svg>"
    ),
    "ico-barbora.svg": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none' "
        "stroke='#96bf0d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M6 30 32 10l26 20'/><path d='M12 26v28h40V26'/>"
        "<path d='M32 48s-10-6-10-13a5 5 0 0 1 10-2 5 5 0 0 1 10 2c0 7-10 13-10 13z'/></svg>"
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
    "program-hornicke.jpg": "files/IMG-8364.jpg",
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


def layout(title, body, depth=0, popis="", hero=False):
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
        <p>{p.get('hero') or esc(p['kratce'])}</p>
      </a>"""
        for p in SLIDER_PROGRAMY
    )

    slidy = "\n".join(
        f'        <div class="carousel-item{" active" if i == 0 else ""}">'
        f'<img src="{up}img/{jm}" alt="Nadace OKD"></div>'
        for i, jm in enumerate(HERO)
    )

    hlavicka = f"""<!doctype html>
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
        <a id="logo" href="{up}index.html"><img src="{up}img/logo.svg" alt="Nadace OKD"></a>
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
"""

    hero_html = f"""
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
""" if hero else ""

    granty_menu = "\n".join(
        f'          <li><a href="{up}{p["slug"]}">{esc(p["nazev"])}</a></li>'
        for p in PROGRAMY
    )
    socialni = socialni_ikony()

    return hlavicka + hero_html + f"""
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
      <a href="{up}index.html" id="footer-logo"><img src="{up}img/logo.svg" alt="Nadace OKD" height="80"></a>
    </div>
    <div class="footer-kontakty pb-5 mb-5">
      <p>{IKONA_ADRESA}Karola &Sacute;liwky 149/17, 733 01 Karvin&aacute; &ndash; Fry&scaron;t&aacute;t</p>
      <p>{IKONA_EMAIL}<a href="mailto:{EMAIL}">{EMAIL}</a></p>
    </div>
    <div class="footer-social pb-5 mb-5">
{socialni}
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
{granty_menu}
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


def formatuj_datum(datum):
    """„4.12.2025“ na „04. 12. 2025“, jak datum ukazuje web OKD."""
    r, m, d = datum_klic(datum)
    return f"{d:02d}. {m:02d}. {r}" if r else (datum or "")


DATUM_NA_ZACATKU = re.compile(r"^\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*")
IMG_SRC = re.compile(r'<img[^>]+src="((?:\.\./)*)([^"]+)"', re.I)


def nahled(n):
    """Náhledová fotka aktuality: ruční výběr z NAHLEDY, jinak první obrázek z textu."""
    if n["slug"] in NAHLEDY:
        return NAHLEDY[n["slug"]]
    m = IMG_SRC.search(n["html"])
    return m.group(2) if m else None


def karta_novinky(n, up=""):
    """Šedý čtverec aktuality podle tiskových zpráv na okd.cz."""
    foto = nahled(n)
    obr = (
        f'<img src="{up}{esc(foto)}" alt="" loading="lazy">'
        if foto
        else f'<img class="placeholder" src="{up}img/logo.svg" alt="">'
    )
    perex = plain(DATUM_NA_ZACATKU.sub("", plain(n["html"])), 170)
    return f"""      <article class="news-card">
        <a class="news-thumb" href="{up}{n['out']}" tabindex="-1">{obr}</a>
        <p class="news-date">{esc(formatuj_datum(n['datum']))}</p>
        <h3><a href="{up}{n['out']}">{esc(n['titul'])}</a></h3>
        <p class="news-perex">{esc(perex)}</p>
        <a class="news-more" href="{up}{n['out']}">Zjistit více</a>
      </article>"""


def homepage(pages, novinky):
    o_nadaci = pages.get("cs/nadace-okd/o-nadaci.html")
    # první skutečný odstavec „O nadaci“ celý (dřív se useknul na 260 znacích)
    odstavce = [plain(x) for x in re.findall(r"<p>(.*?)</p>", o_nadaci["html"], re.S)] if o_nadaci else []
    lead = next((o for o in odstavce if len(o) > 100), "")

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
          <p class="large-number">{esc(hodnota)}</p>
          <p>{esc(popisek)}</p>
        </div>"""
        for hodnota, popisek in STATISTIKY
    )

    karty = "\n".join(karta_novinky(n) for n in novinky[:6])

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
  <div class="boxes boxes-5 mt-5">
{programy}
  </div>
  <div class="text-center mt-5">
    <a class="btn btn-primary" href="granty/jak-pozadat-o-grant.html">Jak po&zcaron;&aacute;dat o grant</a>
  </div>
</div>

<div class="section moved">
  <p class="subtitle text-center">V &ccaron;&iacute;slech</p>
  <h2 class="text-center">Nadace <em>v číslech</em></h2>
  <div class="cisla mt-5 text-center">
{cisla}
  </div>
</div>
""",
        0,
        plain(lead, 150),
        hero=True,
    ).replace(
        "</main>",
        f"""</main>
<section id="reference">
  <div class="container">
    <div class="content-col">
      <p class="subtitle text-center">Aktuality</p>
      <h2 class="text-center">Co je u n&aacute;s <em>nov&eacute;ho</em></h2>
      <div class="news-grid mt-5">
{karty}
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


UVODNI_OBRAZEK = re.compile(
    r"^\s*<p>\s*(?:<strong>)?\s*(<img[^>]+>)\s*(?:</strong>)?\s*</p>(.*)$", re.S
)


def obrazek_vedle_textu(fragment):
    """Stránka začínající samostatným obrázkem (tužka u Pro region, logo Srdcovky)
    dostane obrázek vlevo a text vpravo v poměru 30 / 70."""
    m = UVODNI_OBRAZEK.match(fragment)
    if not m:
        return fragment
    return (
        f'<div class="media-split"><div class="media-img">{m.group(1)}</div>'
        f'<div class="media-text">{m.group(2)}</div></div>'
    )


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
{obrazek_vedle_textu(page['html'])}
  </article>
</div>
"""
    return layout(page["titul"], body, depth, plain(page["html"], 150))


NOVINEK_NA_STRANKU = 24


def news_index(novinky, depth=0):
    karty = "\n".join(
        karta_novinky(n).replace('class="news-card"', 'class="news-card skryta"', 1)
        if i >= NOVINEK_NA_STRANKU else karta_novinky(n)
        for i, n in enumerate(novinky)
    )
    body = f"""
{drobecky(depth, 'Aktuality')}
<div class="section moved">
  <p class="subtitle text-center">Nadace OKD</p>
  <h1 class="text-center"><em>Aktuality</em></h1>
  <div class="news-grid mt-5" id="novinky">
{karty}
  </div>
  <div class="text-center mt-5"><button class="btn btn-primary" id="dalsi-novinky" type="button">Zobrazit další aktuality</button></div>
</div>
<script>
(function () {{
  var btn = document.getElementById('dalsi-novinky');
  var zbyva = function () {{ return document.querySelectorAll('#novinky .news-card.skryta'); }};
  btn.addEventListener('click', function () {{
    Array.prototype.slice.call(zbyva(), 0, {NOVINEK_NA_STRANKU}).forEach(function (k) {{ k.classList.remove('skryta'); }});
    if (!zbyva().length) btn.style.display = 'none';
  }});
  if (!zbyva().length) btn.style.display = 'none';
}})();
</script>
"""
    return layout("Aktuality", body, depth)


TYM = [
    {
        "jmeno": "Monika Němcová",
        "funkce": "ředitelka",
        "programy": "administrátorka programů Pro region, Nadace OKD obcím",
        "email": "nemcova@nadaceokd.com",
        "telefon": "+420 607 042 769",
    },
    {
        "jmeno": "Silvie Balčíková",
        "funkce": "projektová manažerka",
        "programy": "administrátorka programů Srdcovka, Pro region, Hornické tradice, "
        "Operativní fond, Krizový fond",
        "email": "balcikova@nadaceokd.com",
        "telefon": "+420 725 389 852",
    },
]


# rozcestník sekce Ke stažení (na starém webu vnořený seznam na každé stránce)
KE_STAZENI = [
    ("Pro žadatele", [
        ("Pro region", "ke-stazeni/pro-zadatele.html"),
        ("Srdcovka", "ke-stazeni/pro-zadatele/srdcovka.html"),
    ]),
    ("Pro příjemce", [
        ("Pro region", "ke-stazeni/pro-prijemce.html"),
        ("Srdcovka", "ke-stazeni/pro-prijemce/srdcovka.html"),
    ]),
    ("Logo", [
        ("Logo a pravidla pro práci s logem", "ke-stazeni/logo-a-manual-pro-praci-s-logem.html"),
    ]),
]


def prvni_ul(fragment):
    """Rozsah prvního <ul> včetně vnořených seznamů."""
    start = fragment.find("<ul")
    if start < 0:
        return None
    hloubka, i = 0, start
    for m in re.finditer(r"<(/?)ul\b[^>]*>", fragment[start:]):
        hloubka += -1 if m.group(1) else 1
        if hloubka == 0:
            return start, start + m.end()
    return None


def rozcestnik_ke_stazeni(page):
    """Nahradí vnořený seznam odkazů šedými políčky podle okd.cz."""
    rozsah = prvni_ul(page["html"])
    if not rozsah:
        return
    aktualni = page["zdroj"][len("cs/"):]
    up = "../" * aktualni.count("/")
    skupiny = "".join(
        f'<div class="tile-group"><h3>{esc(nadpis)}</h3><div class="link-tiles">'
        + "".join(
            f'<a class="link-tile{" active" if href == aktualni else ""}" '
            f'href="{up}{href}">{esc(label)}</a>'
            for label, href in odkazy
        )
        + "</div></div>"
        for nadpis, odkazy in KE_STAZENI
    )
    a, b = rozsah
    page["html"] = (
        page["html"][:a] + f'<div class="tile-groups">{skupiny}</div>' + page["html"][b:]
    )

    # tabulka souborů (Název / Publikováno / Stáhnout) -> šedá políčka
    def soubory(m):
        policka = []
        for tr in TR_RE.findall(m.group(0)):
            odkaz = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', tr, re.S)
            bunky = TD_RE.findall(tr)
            if not odkaz or len(bunky) < 2:
                continue
            nazev = re.sub(r"\.(pdf|zip|docx?|xlsx?)$", "", plain(odkaz.group(2)), flags=re.I)
            policka.append(
                f'<a class="link-tile file-tile" href="{odkaz.group(1)}">'
                f'<span>{esc(nazev)}</span>'
                f'<small>Publikováno {esc(plain(bunky[1]))} · Stáhnout</small></a>'
            )
        return f'<div class="link-tiles">{"".join(policka)}</div>' if policka else m.group(0)

    page["html"] = re.sub(r"<table>.*?</table>", soubory, page["html"], flags=re.S)


def kontakty():
    """Kontakty ve stylu okd.cz: údaje + mapa, pod tím šedé karty lidí."""
    socialni = socialni_ikony()
    karty = "\n".join(
        f"""    <div class="person-card">
      <p class="person-role">{esc(t['funkce'])}</p>
      <h3>{esc(t['jmeno'])}</h3>
      <p class="person-programs">{esc(t['programy'])}</p>
      <p>E-mail: <a href="mailto:{t['email']}">{t['email']}</a><br>
      Telefon: {esc(t['telefon'])}</p>
    </div>"""
        for t in TYM
    )
    body = f"""
{drobecky(0, 'Kontakty')}
<div class="section moved">
  <h1 class="text-center"><em>Kontakty</em></h1>
  <div class="kontakt-info mt-5">
    <div>
      <h4>Nadace OKD</h4>
      <p>Karola Śliwky 149/17, 733 01 Karviná – Fryštát</p>
      <p><strong>IČO:</strong> 27832813<br>
      <strong>Datová schránka:</strong> sbs7qgj<br>
      <strong>E-mail:</strong> <a href="mailto:{EMAIL}">{EMAIL}</a></p>
      <h4>Provozní doba</h4>
      <p>pondělí až pátek 8:00–15:00</p>
      <p><em>Z důvodu návštěv projektů nás nemusíte v kanceláři zastihnout,
      proto doporučujeme se předem telefonicky či e-mailem objednat.</em></p>
      <h4>Sledujte nás</h4>
      <p class="social-links">{socialni}</p>
    </div>
    <iframe class="kontakt-mapa" title="Mapa" loading="lazy"
      src="https://maps.google.com/maps?q=Karola%20%C5%A0liwky%20149%2F17%2C%20Karvin%C3%A1&z=15&output=embed"></iframe>
  </div>
</div>

<div class="section moved">
  <h2 class="text-center">Náš <em>tým</em></h2>
  <div class="person-grid mt-5">
{karty}
  </div>
</div>
"""
    return layout("Kontakty", body, 0, "Kontakty Nadace OKD")


TR_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
PRAVNI_FORMA = re.compile(r"\s+((?:[^\W\d_]{1,3}\.\s*)+[\"“”]?)$")
KRAJ_RE = re.compile(r"<h2>(.*?)</h2>(.*?)(?=<h2>|$)", re.S)


def podporene_projekty(page):
    """Databáze podpořených projektů s filtrem místo mapy a tabulek po krajích."""
    src = page["html"]
    radky = []
    for m in KRAJ_RE.finditer(src):
        kraj = plain(m.group(1))
        for tr in TR_RE.findall(m.group(2)):
            td = [plain(t) for t in TD_RE.findall(tr)]
            if len(td) == 6:
                program, org, projekt, rok, castka, mesto = td
                # právní formu („z. s.“, „o. p. s.“) přilepit k názvu, ať nepřetéká sama na řádek
                org = PRAVNI_FORMA.sub(
                    lambda m: "\u00a0" + re.sub(r"\s+", "\u00a0", m.group(1).strip()), org
                )
                radky.append([
                    program, org, projekt, int(rok) if rok.isdigit() else 0,
                    int(re.sub(r"\D", "", castka) or 0), mesto, kraj,
                ])
    radky.sort(key=lambda r: (-r[3], r[1]))

    uvod = "\n".join(re.findall(r"<p>.*?</p>", src.split("<p>Celkem", 1)[0], re.S))
    konec = src.rsplit("</table>", 1)[-1]
    pdf = re.search(r"<ul>.*?</ul>", konec, re.S)
    pdf = pdf.group(0) if pdf else ""

    def moznosti(idx, razeni=None):
        hodnoty = sorted({r[idx] for r in radky if r[idx]}, key=razeni)
        return "".join(f'<option value="{esc(str(v))}">{esc(str(v))}</option>' for v in hodnoty)

    data = json.dumps(radky, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = f"""
{drobecky(0, 'Podpořené projekty')}
<div class="section moved">
  <p class="subtitle text-center">Nadace OKD</p>
  <h1 class="text-center"><em>Podpořené</em> projekty</h1>
  <article class="mt-5">
{uvod}
  </article>
  <form class="filtr" id="filtr" onsubmit="return false">
    <label>Program<select name="program"><option value="">Všechny programy</option>{moznosti(0)}</select></label>
    <label>Rok<select name="rok"><option value="">Všechny roky</option>{moznosti(3, lambda v: -v)}</select></label>
    <label>Kraj<select name="kraj"><option value="">Všechny kraje</option>{moznosti(6)}</select></label>
    <label>Město<select name="mesto"><option value="">Všechna města</option>{moznosti(5)}</select></label>
    <label class="filtr-hledat">Hledat<input type="search" name="q" placeholder="Organizace nebo název projektu"></label>
    <button type="reset" class="btn btn-light">Zrušit filtr</button>
  </form>
  <p class="filtr-souhrn" id="souhrn"></p>
  <div class="tabulka-wrap">
    <table class="projekty">
      <thead><tr><th>Program</th><th>Organizace</th><th>Projekt</th><th>Rok</th><th class="num">Částka</th><th>Město</th></tr></thead>
      <tbody id="projekty"></tbody>
    </table>
  </div>
  <div class="text-center mt-5"><button class="btn btn-primary" id="dalsi" type="button">Zobrazit další</button></div>
  <h2 class="mt-5">Seznamy podpořených projektů podle let</h2>
  <article>
{pdf}
  </article>
</div>
<script>
(function () {{
  var D = {data};
  var f = document.getElementById('filtr'), tb = document.getElementById('projekty');
  var souhrn = document.getElementById('souhrn'), dalsi = document.getElementById('dalsi');
  var STRANKA = 50, limit = STRANKA, vysledek = [];
  var kc = function (n) {{ return n.toLocaleString('cs-CZ') + ' Kč'; }};
  var e = function (s) {{ return String(s).replace(/[&<>"]/g, function (c) {{ return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]; }}); }};
  var bezDiak = function (s) {{ return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }};
  function vykresli() {{
    tb.innerHTML = vysledek.slice(0, limit).map(function (r) {{
      return '<tr><td>' + e(r[0]) + '</td><td>' + e(r[1]) + '</td><td>' + e(r[2]) + '</td><td>' + (r[3] || '') +
        '</td><td class="num">' + kc(r[4]) + '</td><td>' + e(r[5]) + '</td></tr>';
    }}).join('');
    dalsi.style.display = vysledek.length > limit ? '' : 'none';
  }}
  function filtruj() {{
    var p = f.program.value, rok = f.rok.value, kraj = f.kraj.value, m = f.mesto.value, q = bezDiak(f.q.value.trim());
    vysledek = D.filter(function (r) {{
      return (!p || r[0] === p) && (!rok || String(r[3]) === rok) && (!kraj || r[6] === kraj) &&
        (!m || r[5] === m) && (!q || bezDiak(r[1] + ' ' + r[2]).indexOf(q) > -1);
    }});
    var suma = vysledek.reduce(function (s, r) {{ return s + r[4]; }}, 0);
    souhrn.innerHTML = 'Nalezeno <strong>' + vysledek.length.toLocaleString('cs-CZ') + '</strong> projektů v celkové částce <strong>' + kc(suma) + '</strong>';
    limit = STRANKA;
    vykresli();
  }}
  var url = new URLSearchParams(location.search);
  ['program', 'rok', 'kraj', 'mesto', 'q'].forEach(function (k) {{ if (url.get(k)) f[k].value = url.get(k); }});
  f.addEventListener('input', filtruj);
  f.addEventListener('change', filtruj);
  f.addEventListener('reset', function () {{ setTimeout(filtruj, 0); }});
  dalsi.addEventListener('click', function () {{ limit += STRANKA; vykresli(); }});
  filtruj();
}})();
</script>
"""
    return layout("Podpořené projekty", body, 0, "Databáze projektů podpořených Nadací OKD")


# ---------------------------------------------------------------- úpravy stránek


def ikonove_karty(polozky, up=""):
    """Karty s piktogramem jako boxy „Pomáháme tam, kde se těžilo uhlí“.
    polozky: (href, ikona, nazev, text, odkaz_text)"""
    karty = "".join(
        f'<a class="icon-card" href="{href}"{' target="_blank" rel="noopener"' if href.endswith(".pdf") else ""}>'
        f'<img src="{up}img/{ikona}" alt="">'
        f"<h3>{esc(nazev)}</h3><p>{esc(text)}</p>"
        f'<span class="icon-card-more">{esc(odkaz)}</span></a>'
        for href, ikona, nazev, text, odkaz in polozky
    )
    return f'<div class="icon-cards">{karty}</div>'


def uprav_granty(page):
    """Menší úvodní věta a všechny programy jako karty s piktogramy."""
    page["html"] = page["html"].replace(
        "<h2>Nadace OKD realizuje grantové programy:</h2>",
        '<p class="large-text text-center">Nadace OKD realizuje grantové programy:</p>',
    )
    karty = ikonove_karty(
        [(p["slug"], p["ikona"], p["nazev"], p["kratce"], "Zjistit více") for p in PROGRAMY]
    )
    page["html"] = re.sub(r"<ul>.*?</ul>", karty, page["html"], count=1, flags=re.S)


def uprav_jak_pozadat(page):
    """Tabulka s výzvami -> karty s piktogramy programů."""
    def karty(m):
        polozky = []
        for href, text in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(0), re.S):
            nazev = plain(text)
            program = next((p for p in PROGRAMY if p["nazev"] == nazev), None)
            rok = re.search(r"20\d\d", href.rsplit("/", 1)[-1])  # rok z názvu souboru, ne ze složky
            polozky.append((
                href, program["ikona"] if program else "ico-region.svg", nazev,
                f"Výzva programu pro rok {rok.group(0)}" if rok else "Výzva programu",
                "Stáhnout výzvu (PDF)",
            ))
        return ikonove_karty(polozky, "../") if polozky else m.group(0)

    page["html"] = re.sub(
        r"(?<=Výzvy jednotlivých grantových programů:</strong></p>)\s*<table>.*?</table>",
        karty, page["html"], count=1, flags=re.S,
    )


def uprav_rady(page):
    """Správní a dozorčí rada jako karty podle okd.cz/o-nas/organy-spolecnosti."""
    src = page["html"]
    konec = src.rsplit("</table>", 1)
    skupiny, osoba = [], None
    for kus in re.split(r"(<h3>.*?</h3>|<img[^>]+>)", konec[0], flags=re.S):
        if kus.startswith("<h3>"):
            skupiny.append((plain(kus), []))
        elif kus.startswith("<img"):
            osoba = kus
        elif osoba and skupiny:
            jmeno = re.search(r"<strong>(.*?)</strong>", kus, re.S)
            if not jmeno:
                continue
            funkce = plain(kus).replace(plain(jmeno.group(1)), "", 1).strip()
            foto = re.search(r'src="([^"]+)"', osoba).group(1)
            skupiny[-1][1].append((plain(jmeno.group(1)), funkce[:1].lower() + funkce[1:], foto))
            osoba = None
    html_ = ""
    for nazev, lide in skupiny:
        karty = "".join(
            f'<div class="organ-item"><figure><img src="{foto}" alt="{esc(jm)}"></figure>'
            f'<p class="organ-pozice"><em>{esc(fce)}</em></p><h3>{esc(jm)}</h3></div>'
            for jm, fce, foto in lide
        )
        html_ += f'<h2 class="text-center">{esc(nazev)}</h2><div class="organ-grid">{karty}</div>'
    page["html"] = html_ + (konec[1] if len(konec) > 1 else "")


# výroční zpráva 2020 na starém webu omylem odkazovala na PDF za rok 2021
VZ_OPRAVY = {"2020": "../../files/2021/Vyrocni-zprava-2020-final-s-podpisem_1.pdf"}


def uprav_vyrocni_zpravy(page):
    """Výroční zprávy jako karty podle okd.cz/o-nas/vyrocni-zpravy, vždy s titulní
    stranou (assets/vz, vyrenderovaná z první strany PDF)."""
    karty = []
    for td in TD_RE.findall(page["html"]):
        rok = re.search(r"Výroční zpráva\s*(\d{4})", plain(td))
        pdf = re.search(r'href="([^"]+\.pdf)"', td)
        if not (rok and pdf):
            continue
        r = rok.group(1)
        href = VZ_OPRAVY.get(r, pdf.group(1))
        obal = f"../img/vz/vz-{r}.jpg"
        karty.append(
            f'<div class="organ-item organ-item--hover vz-item">'
            f'<figure><img src="{obal}" alt="Titulní strana výroční zprávy {r}" loading="lazy"></figure>'
            f"<h3>Výroční zpráva {r}</h3>"
            f'<p class="organ-more">Zjistit více</p>'
            f'<a class="absolute-anchor" href="{href}" target="_blank" rel="noopener" '
            f'aria-label="Výroční zpráva {r} (PDF)"></a></div>'
        )
    page["html"] = f'<div class="organ-grid vz-grid">{"".join(karty)}</div>'


LOGA = {
    "zrizovatel": [("OKD, a.s.", "https://www.okd.cz/", "../../files/images_raw/logo_okd_2008_on.gif")],
    "darci": [
        ("Green Gas DPB, a.s.", "https://www.dpb.cz/", "../../files/images_raw/greengas.gif"),
        ("Prisko a.s.", "https://www.prisko.cz/", "../../files/Prisko-167x40.jpg"),
    ],
    # Česká spořitelna a Cyber Fox na přání nadace vypadly
    "partneri": [
        ("Horník", "https://www.okd.cz/tiskove-zpravy-a-aktuality/hornik/",
         "../../files/09ho19-WEB-1-page-0001-228x40.jpg"),
        ("Statutární město Karviná", "https://www.karvina.cz/",
         "../../files/2018/partneri-a-darci/1175-115x80_1.jpg"),
        ("Nadace Partnerství", "https://www.nadacepartnerstvi.cz/",
         "../../files/images_raw/partneri_logo_partnerstvi_on_2.gif"),
    ],
}


def uprav_zrizovatele(page):
    """Loga jako odkazy, bez loga OKD v textu a bez ČS a Cyber Foxu."""
    h = re.sub(r'^\s*<a href="http://www.okd.cz/"><img[^>]+></a>', "", page["html"])
    text = h.split("<h2><strong>ZŘIZOVATEL", 1)[0]
    partneri_text = re.search(r"<p>V jednotě je síla.*?</p>", h, re.S)

    def loga(klic):
        return '<div class="logo-grid">' + "".join(
            f'<a class="logo-tile" href="{url}" target="_blank" rel="noopener" title="{esc(n)}">'
            f'<img src="{src}" alt="{esc(n)}"></a>'
            for n, url, src in LOGA[klic]
        ) + "</div>"

    page["html"] = (
        f"<p>{text.strip()}</p>"
        f"<h2>Zřizovatel</h2>{loga('zrizovatel')}"
        f"<h2>Dárci</h2>{loga('darci')}"
        f"<h2>Partneři</h2>{partneri_text.group(0) if partneri_text else ''}{loga('partneri')}"
    )


def uprav_stranky(pages):
    for p in pages.values():
        # osobní adresy pracovníků přešly z .cz na .com; aktuality zůstávají
        # v původním znění (článek o nefunkčních e-mailech by jinak ztratil smysl)
        if p["sekce"] != "novinky":
            p["html"] = re.sub(r"\b([\w.-]+)@nadaceokd\.cz\b", r"\1@nadaceokd.com", p["html"])
    for zdroj in ("cs/nadace-okd.html", "cs/nadace-okd/o-nadaci.html"):
        # nadpis „Nadace OKD“ byl v textu podruhé jako samostatný odstavec
        if zdroj in pages:
            pages[zdroj]["html"] = re.sub(r"^\s*<p>Nadace OKD</p>", "", pages[zdroj]["html"])
    statut = pages.get("cs/nadace-okd/statut-nadace.html")
    if statut:
        statut["html"] = re.sub(r"<img[^>]*homepage\.gif[^>]*>", "", statut["html"])
    for zdroj, fce in (
        ("cs/granty.html", uprav_granty),
        ("cs/granty/jak-pozadat-o-grant.html", uprav_jak_pozadat),
        ("cs/nadace-okd/spravni-a-dozorci-rada-nadace.html", uprav_rady),
        ("cs/nadace-okd/vyrocni-zpravy.html", uprav_vyrocni_zpravy),
        ("cs/nadace-okd/zrizovatele-darci-a-partneri.html", uprav_zrizovatele),
    ):
        if zdroj in pages:
            fce(pages[zdroj])


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
            png = cesta.lower().endswith(".png")
            novy = im if png else (im.convert("RGB") if im.mode in ("P", "RGBA") else im)
            novy = novy.resize(
                (max_sirka, round(im.height * max_sirka / im.width)), Image.LANCZOS
            )
            if png:
                novy.save(cesta, optimize=True)
            else:
                novy.save(cesta, quality=80, optimize=True)
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
        if os.path.splitext(cil)[1].lower() in (".jpg", ".jpeg", ".png"):
            # fotky z aktualit (lightbox) stačí menší, jinak by web měl stovky MB
            zmensi(full, 1400)

    velikost = sum(os.path.getsize(os.path.join(DIST, c)) for c in prenesene)
    print(f"obrázků přeneseno: {len(prenesene)} ({velikost / 1_048_576:.1f} MB)")
    print(f"dokumentů odkázaných na živý web: {na_zivy}")
    print(f"stránek s přepsanými odkazy: {upravene}")
    if chybejici:
        print(f"chybí v archivu: {sum(chybejici.values())} odkazů")
        for cesta, poc in chybejici.most_common(10):
            print(f"  {poc}× {cesta}")


def orez_obrazky_vedle_textu():
    """Obrázky ve sloupci vedle textu mají v archivu velké bílé okraje (logo
    Srdcovky), které by dělaly prázdné místo. Ořízne je na obsah."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return
    img_re = re.compile(r'<div class="media-img"><img[^>]+src="([^"]+)"')
    for koren, _, soubory in os.walk(DIST):
        for jmeno in soubory:
            if not jmeno.endswith(".html"):
                continue
            with open(os.path.join(koren, jmeno), encoding="utf-8") as fh:
                m = img_re.search(fh.read())
            if not m or m.group(1).startswith("http"):
                continue
            cesta = os.path.normpath(os.path.join(koren, unquote(m.group(1))))
            if not os.path.isfile(cesta) or cesta.lower().endswith(".gif"):
                continue
            with Image.open(cesta) as im:
                rgb = im.convert("RGB")
                bila = Image.new("RGB", rgb.size, (255, 255, 255))
                maska = ImageChops.difference(rgb, bila).point(lambda p: 255 if p > 18 else 0)
                box = maska.getbbox()
                if not box or box == (0, 0) + rgb.size:
                    continue
                okraj = 8
                box = (max(box[0] - okraj, 0), max(box[1] - okraj, 0),
                       min(box[2] + okraj, rgb.size[0]), min(box[3] + okraj, rgb.size[1]))
                im.crop(box).save(cesta, quality=90)


# ---------------------------------------------------------------- build


def main():
    with open(os.path.join(HERE, "content.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    for p in data:
        priprav(p)
    pages = {p["zdroj"]: p for p in data}
    uprav_stranky(pages)

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

    shutil.copy(os.path.join(HERE, "assets", "logo.svg"), os.path.join(DIST, "img", "logo.svg"))
    shutil.copy(os.path.join(HERE, "assets", "program-barbora.jpg"), os.path.join(DIST, "img", "program-barbora.jpg"))
    shutil.copytree(os.path.join(HERE, "assets", "vz"), os.path.join(DIST, "img", "vz"))

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
        # starý obecný e-mail už nadace nepoužívá
        text = text.replace("info@nadaceokd.cz", EMAIL)
        # překlep v odkazu na živém webu (aktualita „Máme nové emaily!“)
        text = text.replace("mailto:balcikova@nadace.com", "mailto:balcikova@nadaceokd.com")
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        napsano += 1

    zapis("index.html", homepage(pages, novinky))
    zapis("novinky.html", news_index(novinky))
    for n in novinky:
        zapis(n["out"], subpage(n, 1, [("Aktuality", "novinky.html")]))
    zapis("kontakty.html", kontakty())
    zapis("podporene-projekty.html", podporene_projekty(pages["cs/podporene-projekty.html"]))

    ht = priprav({
        "zdroj": "cs/granty/grantove-programy/hornicke-tradice.html",
        "sekce": "granty", "nadpis": "Granty", "html": HORNICKE_TRADICE_HTML,
    })
    zapis("granty/grantove-programy/hornicke-tradice.html", subpage(ht, 2))

    sb = priprav({
        "zdroj": "cs/granty/grantove-programy/spolek-svata-barbora.html",
        "sekce": "granty", "nadpis": "Granty", "html": BARBORA_HTML,
    })
    zapis("granty/grantove-programy/spolek-svata-barbora.html", subpage(sb, 2))

    # ostatní obsahové stránky
    preskoc = {"novinky", "pro-media", "sitemap"}
    vlastni = {"cs.html", "cs/kontakty.html", "cs/podporene-projekty.html"}
    for p in data:
        if p["sekce"] in preskoc or p["delka"] < 60 or p["zdroj"] in vlastni:
            continue
        rel = p["zdroj"][len("cs/"):]
        depth = rel.count("/")
        if p["sekce"] == "ke-stazeni":
            rozcestnik_ke_stazeni(p)
        zapis(rel, subpage(p, depth))

    zkopiruj_prilohy()
    orez_obrazky_vedle_textu()

    print(f"vygenerováno stránek: {napsano}")
    print(f"novinek: {len(novinky)}")
    print(f"výstup: {DIST}")


if __name__ == "__main__":
    main()
