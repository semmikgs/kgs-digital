#!/usr/bin/env python3
"""
Erzeugt in jedem Fachbereichsordner eine dateien.json.

Ein Fachbereich ist jeder Ordner der obersten Ebene, der eine index.html
enthält (ausgenommen assets, tools und alles mit Punkt am Anfang).

Titel und Beschreibung werden bei HTML-Dateien aus <title> und
<meta name="description"> gelesen. Fehlt das, dient der Dateiname als Titel.

Die Kategorie (= Filter-Chip) ergibt sich aus dem Unterordner,
in dem die Datei liegt. Beispiel:

    mathematik/Klasse 7/bruchrechnen.html  ->  Chip "Klasse 7"
    mathematik/uebersicht.pdf              ->  kein Chip

Aufruf:  python3 tools/index_erstellen.py
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

# Ordner, die keine Fachbereiche sind
NICHT_FACH = {"assets", "tools", "bilder", "img"}

# Dateien, die nie aufgelistet werden
IGNORIEREN = {"index.html", "extern.html", "dateien.json", "README.md",
              "readme.md", "LICENSE", ".nojekyll", "CNAME"}

# erlaubte Endungen -> Typ für das Symbol in der Liste
TYPEN = {
    ".html": "html", ".htm": "html",
    ".pdf": "pdf",
    ".docx": "docx", ".doc": "docx", ".odt": "odt", ".rtf": "odt",
    ".pptx": "pptx", ".ppt": "pptx", ".odp": "pptx",
    ".xlsx": "xlsx", ".xls": "xlsx", ".ods": "xlsx", ".csv": "xlsx",
    ".zip": "zip",
    ".py": "py", ".ino": "py",
    ".md": "md",
    ".png": "bild", ".jpg": "bild", ".jpeg": "bild",
    ".gif": "bild", ".svg": "bild", ".webp": "bild",
}


def lies_kopf(datei: Path) -> dict:
    """Titel, Beschreibung und optionale Kategorie aus einer HTML-Datei holen."""
    try:
        text = datei.read_text(encoding="utf-8", errors="ignore")[:20000]
    except OSError:
        return {}

    ergebnis = {}

    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if m:
        titel = re.sub(r"\s+", " ", m.group(1)).strip()
        # ein evtl. angehängtes " · KGS - Digital" entfernen
        titel = re.split(r"\s+[·|–-]\s+KGS", titel)[0].strip()
        if titel:
            ergebnis["titel"] = titel

    for name, schluessel in (("description", "beschreibung"),
                             ("kgs-kategorie", "kategorie")):
        m = re.search(
            r"<meta[^>]*name\s*=\s*[\"']" + name + r"[\"'][^>]*>", text, re.I)
        if m:
            inhalt = re.search(
                r"content\s*=\s*[\"'](.*?)[\"']", m.group(0), re.I | re.S)
            if inhalt:
                wert = re.sub(r"\s+", " ", inhalt.group(1)).strip()
                if wert:
                    ergebnis[schluessel] = wert

    return ergebnis


def lesbarer_name(datei: Path) -> str:
    """Aus 'bruchrechnen_klasse7.html' wird 'Bruchrechnen klasse7'."""
    roh = datei.stem.replace("_", " ").replace("-", " ")
    roh = re.sub(r"\s+", " ", roh).strip()
    return roh[:1].upper() + roh[1:] if roh else datei.name


def groesse_lesbar(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.0f} KB"
    return f"{bytes_ / (1024 * 1024):.1f} MB".replace(".", ",")


def ignorierte_ermitteln(kandidaten):
    """Von Git ignorierte Dateien herausfiltern.

    Wichtig: Materialien, die über die Werkstatt von der Schulseite
    genommen wurden, liegen lokal weiter im Ordner. Ohne diesen Filter
    stünden sie im veröffentlichten Index und würden dort zu toten
    Links führen.
    """
    if not kandidaten:
        return set()
    try:
        p = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=WURZEL, capture_output=True, text=True,
            input="\n".join(str(k.relative_to(WURZEL).as_posix())
                            for k in kandidaten))
    except OSError:
        return set()          # kein Git vorhanden – dann gibt es auch nichts
    if p.returncode not in (0, 1):
        return set()          # 1 heißt schlicht: nichts wird ignoriert
    return {z.strip() for z in p.stdout.splitlines() if z.strip()}


def fachbereich_indizieren(ordner: Path, ignoriert: set) -> int:
    eintraege = []

    for datei in sorted(ordner.rglob("*")):
        if not datei.is_file():
            continue
        if datei.name in IGNORIEREN or datei.name.startswith("."):
            continue
        if any(teil.startswith(".") for teil in datei.relative_to(ordner).parts):
            continue
        if datei.relative_to(WURZEL).as_posix() in ignoriert:
            continue

        typ = TYPEN.get(datei.suffix.lower())
        if typ is None:
            continue

        relativ = datei.relative_to(ordner)
        kategorie = relativ.parts[0] if len(relativ.parts) > 1 else ""

        eintrag = {
            "pfad": relativ.as_posix(),
            "datei": datei.name,
            "typ": typ,
            "titel": lesbarer_name(datei),
            "beschreibung": "",
            "kategorie": kategorie,
            "groesse": groesse_lesbar(datei.stat().st_size),
            "geaendert": datetime.fromtimestamp(
                datei.stat().st_mtime, timezone.utc).date().isoformat(),
        }

        if typ == "html":
            eintrag.update({k: v for k, v in lies_kopf(datei).items() if v})

        eintraege.append(eintrag)

    ziel = ordner / "dateien.json"

    # Nur schreiben, wenn sich wirklich etwas geändert hat. Sonst würde
    # die Datei bei jedem Lauf als "geändert" gelten und die Liste der
    # Änderungen wäre nie leer.
    if ziel.exists():
        try:
            alt = json.loads(ziel.read_text(encoding="utf-8"))
            if alt.get("eintraege") == eintraege:
                return len(eintraege)
        except (OSError, json.JSONDecodeError):
            pass

    ziel.write_text(
        json.dumps(
            {"fachbereich": ordner.name,
             "aktualisiert": datetime.now(timezone.utc).date().isoformat(),
             "eintraege": eintraege},
            ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    return len(eintraege)


def main() -> int:
    fachbereiche = sorted(
        p for p in WURZEL.iterdir()
        if p.is_dir()
        and not p.name.startswith(".")
        and p.name not in NICHT_FACH
        and (p / "index.html").exists()
    )

    if not fachbereiche:
        print("Kein Fachbereich gefunden.")
        return 1

    alle = [d for ordner in fachbereiche
            for d in ordner.rglob("*") if d.is_file()]
    ignoriert = ignorierte_ermitteln(alle)

    gesamt = 0
    for ordner in fachbereiche:
        anzahl = fachbereich_indizieren(ordner, ignoriert)
        gesamt += anzahl
        print(f"{ordner.name:<14} {anzahl:>3} Einträge")

    if ignoriert:
        print(f"\n{len(ignoriert)} Datei(en) nur lokal – nicht im Index.")

    print(f"\n{gesamt} Einträge in {len(fachbereiche)} Fachbereichen indiziert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
