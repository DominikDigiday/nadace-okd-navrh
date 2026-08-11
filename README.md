# Nadace OKD — ukázkový návrh webu

Statický návrh nového webu Nadace OKD. Obsah je převzatý z archivu stávajícího
webu nadaceokd.cz, vizuál vychází ze stylu novasichta.cz.

Náhled: https://dominikdigiday.github.io/nadace-okd-navrh/

## Co je v repozitáři

| Cesta | Obsah |
|---|---|
| `docs/` | vygenerovaný web, kořen GitHub Pages |
| `extract.py` | vytěží obsah z lokálního archivu do `content.json` |
| `build.py` | z `content.json` vygeneruje `docs/` |
| `style.css` | zdrojový styl, build ho kopíruje do `docs/css/` |
| `content.json` | vytěžený obsah, 652 stránek |

## Přegenerování

```bash
python3 build.py
git add -A && git commit -m "aktualizace návrhu" && git push
```

`extract.py` je potřeba spustit jen při novém stažení archivu — očekává ho
v `~/projects/nadaceokd-archiv`.

## Poznámky k obsahu

- Obrázky jsou zkopírované z archivu do `docs/`.
- Dokumenty (výroční zprávy a další PDF) odkazují na živý web nadaceokd.cz.
  Mají dohromady přes 500 MB naskenovaných stran, do repozitáře nepatří.
  Přepínač `DOKUMENTY_NA_ZIVY_WEB` v `build.py` to umí otočit na plně offline
  verzi.
- Sekce `pro-media` (fotogalerie se stránkováním, 609 stránek archivu) se do
  návrhu negeneruje.
