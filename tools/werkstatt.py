#!/usr/bin/env python3
"""
KGS - Digital · Werkstatt

Kleiner lokaler Server. Zeigt an, was sich im Projektordner geändert hat,
verwaltet den Bestand und lädt auf Bestätigung alles zu GitHub hoch.

Läuft ausschließlich auf diesem Rechner (127.0.0.1) und benötigt
nur die Python-Standardbibliothek.

Start:  ./start.sh
"""

import http.server
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
OBERFLAECHE = Path(__file__).resolve().parent / "werkstatt.html"
INDEXER = Path(__file__).resolve().parent / "index_erstellen.py"
GITIGNORE = WURZEL / ".gitignore"

TOKEN = secrets.token_urlsafe(24)

# Dateien, die das Indizierskript selbst erzeugt
AUTOMATISCH = re.compile(r"(^|/)dateien\.json$")

# Abschnitt in der .gitignore, den die Werkstatt selbst pflegt
MARKE_START = "# --- Nur lokal, nicht auf der Schulseite (Werkstatt) ---"
MARKE_ENDE = "# --- Ende ---"

# Ordner, die keine Fachbereiche sind
NICHT_FACH = {"assets", "tools", "bilder", "img"}
NIE_LISTEN = {"index.html", "extern.html", "dateien.json"}

# Git darf nicht auf einem Terminal nach Zugangsdaten fragen - es gibt
# keins. Stattdessen erkennen wir den Fehler und zeigen in der
# Oberfläche eine Eingabemaske.
GIT_UMGEBUNG = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

AUTHFEHLER = re.compile(
    r"could not read Username|Authentication failed|terminal prompts disabled"
    r"|Permission denied|403 Forbidden|Invalid username or (token|password)",
    re.I)


# ------------------------------------------------------------------ Git

def git(*args, roh=False, eingabe=None):
    """Git im Projektordner ausführen. Gibt (code, ausgabe) zurück.

    roh=True liefert die Standardausgabe unverändert. Das ist bei
    'status --porcelain' nötig, weil dort führende Leerzeichen den
    Zustand einer Datei kennzeichnen und nicht entfernt werden dürfen.
    """
    p = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=WURZEL, capture_output=True, text=True,
        input=eingabe, env=GIT_UMGEBUNG)
    if roh:
        return p.returncode, p.stdout
    return p.returncode, (p.stdout + p.stderr).strip()


def git_vorhanden():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def remote_adresse():
    code, url = git("remote", "get-url", "origin")
    return url.strip() if code == 0 else ""


def ueber_https():
    return remote_adresse().startswith("http")


def veroeffentlichungsadresse():
    """Aus der Remote-Adresse die GitHub-Pages-Adresse ableiten."""
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", remote_adresse())
    if not m:
        return ""
    return f"https://{m.group(1).lower()}.github.io/{m.group(2)}/"


def anmeldung_pruefen():
    """Testet ohne Schreibzugriff, ob die Anmeldung bei GitHub sitzt."""
    code, ausgabe = git("ls-remote", "--heads", "origin")
    if code == 0:
        return {"angemeldet": True}
    return {"angemeldet": False,
            "grund": "anmeldung" if AUTHFEHLER.search(ausgabe) else "verbindung",
            "ausgabe": ausgabe}


def gespeicherter_benutzer():
    """Benutzernamen aus Gits Speicher lesen, ohne das Token preiszugeben."""
    m = re.match(r"https?://([^/]+)/", remote_adresse())
    if not m:
        return ""
    wirt = m.group(1).split("@")[-1]
    code, ausgabe = git("credential", "fill",
                        eingabe=f"protocol=https\nhost={wirt}\n\n")
    if code != 0:
        return ""
    for zeile in ausgabe.splitlines():
        if zeile.startswith("username="):
            return zeile.split("=", 1)[1]
    return ""


def verbindung_lesen():
    _, zweig = git("rev-parse", "--abbrev-ref", "HEAD")
    pruefung = anmeldung_pruefen()
    return {
        "repository": remote_adresse(),
        "benutzer": gespeicherter_benutzer() if ueber_https() else "",
        "zweig": zweig.strip(),
        "ueber_https": ueber_https(),
        "angemeldet": pruefung["angemeldet"],
        "grund": pruefung.get("grund", ""),
        "adresse": veroeffentlichungsadresse(),
    }


def verbindung_testen():
    """Prüft die Verbindung Schritt für Schritt und meldet klar, was fehlt."""
    schritte = []

    def merke(titel, erfolg, hinweis=""):
        schritte.append({"titel": titel, "erfolg": erfolg, "hinweis": hinweis})
        return erfolg

    adresse = remote_adresse()
    if not merke("Repository hinterlegt", bool(adresse),
                 adresse or "Es ist kein Repository eingetragen."):
        return {"erfolg": False, "schritte": schritte,
                "meldung": "Trage zuerst die Adresse des Repositories ein."}

    erreichbar = merke("GitHub erreichbar", True)

    code, ausgabe = git("ls-remote", "--heads", "origin")
    if code != 0:
        if AUTHFEHLER.search(ausgabe):
            merke("Anmeldung akzeptiert", False,
                  "GitHub weist die Zugangsdaten zurück oder es sind keine "
                  "hinterlegt.")
            return {"erfolg": False, "schritte": schritte,
                    "meldung": "Die Anmeldung fehlt oder ist ungültig. Bitte "
                               "Benutzernamen und Token eintragen.",
                    "ausgabe": ausgabe}
        schritte[-1]["erfolg"] = False
        schritte[-1]["hinweis"] = "Keine Verbindung zu GitHub."
        return {"erfolg": False, "schritte": schritte,
                "meldung": "GitHub ist nicht erreichbar. Netzwerk prüfen und "
                           "die Adresse des Repositories kontrollieren.",
                "ausgabe": ausgabe}

    merke("Anmeldung akzeptiert", True,
          gespeicherter_benutzer() or "über gespeicherte Zugangsdaten")

    zweige = [z.split("refs/heads/")[-1]
              for z in ausgabe.splitlines() if "refs/heads/" in z]
    _, zweig = git("rev-parse", "--abbrev-ref", "HEAD")
    zweig = zweig.strip()
    merke("Zweig auf GitHub vorhanden", zweig in zweige,
          f"„{zweig}“ " + ("ist angelegt." if zweig in zweige
                           else "wird beim ersten Veröffentlichen angelegt."))

    # Schreibrecht prüfen, ohne etwas zu verändern.
    # --force gehört dazu: ohne das würde GitHub einen Probe-Push auch dann
    # ablehnen, wenn nur der Stand abweicht - das hat nichts mit dem Token zu
    # tun. --dry-run sorgt dafür, dass trotzdem nichts geschrieben wird.
    code, ausgabe2 = git("push", "--dry-run", "--force", "origin",
                         f"HEAD:refs/heads/{zweig}")
    schreiben = code == 0
    hinweis = ""

    if not schreiben:
        if re.search(r"403|permission|denied|write access|read-only|"
                     r"not authorized", ausgabe2, re.I):
            hinweis = ("Das Token darf nicht schreiben. Ein classic Token "
                       "braucht die Berechtigung 'repo', ein fine-grained "
                       "Token 'Contents: Read and write' für genau dieses "
                       "Repository.")
        elif re.search(r"404|not found|repository does not exist",
                       ausgabe2, re.I):
            hinweis = ("GitHub findet dieses Repository nicht. Bitte die "
                       "Adresse prüfen - Schreibweise und Benutzername müssen "
                       "genau stimmen.")
        elif re.search(r"workflow|refusing to allow", ausgabe2, re.I):
            hinweis = ("Dem Token fehlt die Berechtigung 'workflow'. Sie wird "
                       "gebraucht, weil im Projekt eine Datei unter "
                       ".github/workflows/ liegt.")
        else:
            hinweis = "GitHub lehnt den Schreibzugriff ab, siehe unten."

    merke("Schreibrecht vorhanden", schreiben, hinweis)

    # Abweichender Stand ist kein Fehler, aber gut zu wissen.
    if zweig in zweige:
        git("fetch", "origin", zweig)
        _, anzahl = git("rev-list", "--count", f"HEAD..FETCH_HEAD")
        if anzahl.strip().isdigit() and int(anzahl.strip()) > 0:
            merke("Stand abgeglichen", True,
                  f"GitHub hat {anzahl.strip()} Änderung(en), die hier noch "
                  "fehlen. Sie werden beim Veröffentlichen automatisch "
                  "eingespielt.")

    alles = all(s["erfolg"] for s in schritte)
    return {"erfolg": alles, "schritte": schritte,
            "adresse": veroeffentlichungsadresse(),
            "meldung": "Alles bereit. Veröffentlichen wird funktionieren."
                       if alles else
                       "Die Verbindung ist noch nicht vollständig — siehe "
                       "die markierten Punkte.",
            "ausgabe": "" if schreiben else ausgabe2}


def repository_setzen(adresse):
    adresse = adresse.strip()
    if not re.match(r"^(https://|git@)", adresse):
        return {"erfolg": False,
                "meldung": "Die Adresse muss mit https:// beginnen "
                           "(oder mit git@ bei SSH)."}

    code, _ = git("remote", "get-url", "origin")
    if code == 0:
        code2, ausgabe = git("remote", "set-url", "origin", adresse)
    else:
        code2, ausgabe = git("remote", "add", "origin", adresse)

    if code2 != 0:
        return {"erfolg": False,
                "meldung": "Die Adresse konnte nicht gesetzt werden.",
                "ausgabe": ausgabe}
    return {"erfolg": True,
            "meldung": "Repository eingetragen. Am besten gleich die "
                       "Verbindung testen."}


def zugangsdaten_loeschen():
    m = re.match(r"https?://([^/]+)/", remote_adresse())
    wirt = m.group(1).split("@")[-1] if m else "github.com"
    git("credential", "reject", eingabe=f"protocol=https\nhost={wirt}\n\n")
    return {"erfolg": True,
            "meldung": "Gespeicherte Zugangsdaten entfernt. Beim nächsten "
                       "Veröffentlichen musst du sie neu eintragen."}


def zugangsdaten_speichern(benutzer, token):
    """Token dauerhaft in Gits eigenem Speicher ablegen (~/.git-credentials).

    Bewusst außerhalb des Projektordners - dort würde es mit hochgeladen.
    """
    if not ueber_https():
        return {"erfolg": False,
                "meldung": "Das Repository ist über SSH eingebunden. Dort werden "
                           "keine Token verwendet, sondern SSH-Schlüssel. Ein "
                           "gespeichertes Token hätte hier keine Wirkung."}

    git("config", "--global", "credential.helper", "store")

    wirt = "github.com"
    m = re.match(r"https?://([^/]+)/", remote_adresse())
    if m:
        wirt = m.group(1).split("@")[-1]

    satz = (f"protocol=https\nhost={wirt}\n"
            f"username={benutzer}\npassword={token}\n\n")
    code, ausgabe = git("credential", "approve", eingabe=satz)
    if code != 0:
        return {"erfolg": False,
                "meldung": "Die Zugangsdaten konnten nicht gespeichert werden.",
                "ausgabe": ausgabe}

    speicher = Path.home() / ".git-credentials"
    try:
        if speicher.exists():
            speicher.chmod(0o600)
    except OSError:
        pass

    pruefung = anmeldung_pruefen()
    if pruefung["angemeldet"]:
        return {"erfolg": True,
                "meldung": "Anmeldung gespeichert. Sie wird ab jetzt automatisch "
                           "verwendet und nicht wieder abgefragt."}

    return {"erfolg": False,
            "meldung": "Die Zugangsdaten wurden gespeichert, GitHub hat sie aber "
                       "abgelehnt. Bitte den Benutzernamen prüfen und ein Token "
                       "mit der Berechtigung 'repo' beziehungsweise "
                       "'Contents: Read and write' verwenden.",
            "ausgabe": pruefung.get("ausgabe", "")}


# ------------------------------------------------------------------ .gitignore

def muster_fuer(pfad):
    """Pfad so absichern, dass Sonderzeichen nicht als Platzhalter wirken."""
    return "/" + re.sub(r"([*?\[\]!#\\])", r"\\\1", pfad)


def ignorierte_lesen():
    if not GITIGNORE.exists():
        return []
    zeilen = GITIGNORE.read_text(encoding="utf-8").splitlines()
    if MARKE_START not in zeilen:
        return []
    start = zeilen.index(MARKE_START) + 1
    ende = zeilen.index(MARKE_ENDE) if MARKE_ENDE in zeilen else len(zeilen)
    return [z.strip() for z in zeilen[start:ende] if z.strip()]


def ignorierte_schreiben(muster):
    text = GITIGNORE.read_text(encoding="utf-8") if GITIGNORE.exists() else ""
    zeilen = text.splitlines()

    if MARKE_START in zeilen:
        start = zeilen.index(MARKE_START)
        ende = zeilen.index(MARKE_ENDE) + 1 if MARKE_ENDE in zeilen else len(zeilen)
        zeilen = zeilen[:start] + zeilen[ende:]

    while zeilen and not zeilen[-1].strip():
        zeilen.pop()

    if muster:
        zeilen += ["", MARKE_START] + sorted(set(muster)) + [MARKE_ENDE]

    GITIGNORE.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def ausblenden(pfad):
    """Datei von der Schulseite nehmen, lokal aber behalten."""
    ziel = (WURZEL / pfad).resolve()
    if WURZEL not in ziel.parents:
        return {"erfolg": False, "meldung": "Ungültiger Pfad."}

    ignorierte_schreiben(ignorierte_lesen() + [muster_fuer(pfad)])
    # aus der Versionsverwaltung nehmen; die Datei auf der Platte bleibt
    git("rm", "--cached", "--quiet", "--", pfad)
    return {"erfolg": True,
            "meldung": "Wird beim nächsten Veröffentlichen von der Schulseite "
                       "entfernt. Die Datei bleibt auf deinem Rechner."}


def einblenden(pfad):
    muster = muster_fuer(pfad)
    ignorierte_schreiben([m for m in ignorierte_lesen() if m != muster])
    git("add", "--", pfad)
    return {"erfolg": True,
            "meldung": "Erscheint beim nächsten Veröffentlichen wieder auf der "
                       "Schulseite."}


# ------------------------------------------------------------------ Bestand

def bestand_lesen():
    """Alle Materialien auflisten, mit ihrem Veröffentlichungszustand."""
    code, roh = git("ls-files", roh=True)
    verfolgt = set(roh.splitlines()) if code == 0 else set()
    versteckt = set(ignorierte_lesen())

    bereiche = []
    for ordner in sorted(p for p in WURZEL.iterdir()
                         if p.is_dir() and not p.name.startswith(".")
                         and p.name not in NICHT_FACH
                         and (p / "index.html").exists()):

        dateien = []
        for datei in sorted(ordner.rglob("*")):
            if not datei.is_file() or datei.name in NIE_LISTEN:
                continue
            if any(t.startswith(".") for t in datei.relative_to(WURZEL).parts):
                continue

            pfad = datei.relative_to(WURZEL).as_posix()
            relativ = datei.relative_to(ordner)
            dateien.append({
                "pfad": pfad,
                "name": datei.name,
                "kategorie": relativ.parts[0] if len(relativ.parts) > 1 else "",
                "oeffentlich": (pfad in verfolgt
                                and muster_fuer(pfad) not in versteckt),
                "geaendert": datetime.fromtimestamp(
                    datei.stat().st_mtime).strftime("%d.%m.%Y"),
            })

        bereiche.append({
            "name": ordner.name,
            "dateien": dateien,
            "oeffentlich": sum(1 for d in dateien if d["oeffentlich"]),
            "versteckt": sum(1 for d in dateien if not d["oeffentlich"]),
        })

    return {"bereiche": bereiche,
            "gesamt": sum(len(b["dateien"]) for b in bereiche)}


# ------------------------------------------------------------------ Zustand

def aenderungen_lesen():
    code, roh = git("status", "--porcelain", "-uall", roh=True)
    if code != 0:
        return []

    zustand = {"?": "neu", "A": "neu", "M": "geändert",
               "D": "gelöscht", "R": "verschoben", "C": "kopiert"}
    liste = []

    for zeile in roh.splitlines():
        if len(zeile) < 4:
            continue
        marker = zeile[0] if zeile[0] != " " else zeile[1]
        pfad = zeile[3:].strip().strip('"')
        if " -> " in pfad:
            pfad = pfad.split(" -> ")[-1]
        liste.append({
            "pfad": pfad,
            "art": zustand.get(marker, "geändert"),
            "bereich": pfad.split("/")[0] if "/" in pfad else "Hauptordner",
            "automatisch": bool(AUTOMATISCH.search(pfad)),
        })

    liste.sort(key=lambda e: (e["automatisch"], e["bereich"], e["pfad"]))
    return liste


def zustand_ermitteln():
    if not git_vorhanden():
        return {"bereit": False,
                "meldung": "Git ist auf diesem Rechner nicht installiert. "
                           "Installieren mit: sudo apt install git"}

    if not (WURZEL / ".git").exists():
        return {"bereit": False,
                "meldung": "Dieser Ordner ist noch nicht mit GitHub verbunden. "
                           "Bitte einmalig ./einrichten.sh ausführen."}

    if not remote_adresse():
        return {"bereit": False,
                "meldung": "Es ist kein GitHub-Repository hinterlegt (origin "
                           "fehlt). Bitte ./einrichten.sh ausführen."}

    indexmeldung = ""
    try:
        p = subprocess.run([sys.executable, str(INDEXER)],
                           cwd=WURZEL, capture_output=True, text=True)
        indexmeldung = (p.stdout + p.stderr).strip()
    except OSError as f:
        indexmeldung = f"Übersicht konnte nicht erzeugt werden: {f}"

    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _, letzter = git("log", "-1", "--format=%cI|%s")

    zeit, betreff = "", ""
    if "|" in letzter:
        roh_zeit, betreff = letzter.split("|", 1)
        try:
            zeit = datetime.fromisoformat(roh_zeit).strftime("%d.%m.%Y um %H:%M")
        except ValueError:
            zeit = roh_zeit

    anmeldung = anmeldung_pruefen()

    return {
        "bereit": True,
        "branch": branch,
        "adresse": veroeffentlichungsadresse(),
        "letzte_veroeffentlichung": zeit,
        "letzter_betreff": betreff,
        "index": indexmeldung,
        "angemeldet": anmeldung["angemeldet"],
        "anmeldegrund": anmeldung.get("grund", ""),
        "ueber_https": ueber_https(),
        "aenderungen": aenderungen_lesen(),
    }


# ------------------------------------------------------------------ Upload

def hochladen(nachricht):
    protokoll = []

    def schritt(titel, *args, darf_scheitern=False):
        code, ausgabe = git(*args)
        protokoll.append({"titel": titel,
                          "erfolg": code == 0 or darf_scheitern,
                          "ausgabe": ausgabe})
        return code == 0, ausgabe

    def abbruch(meldung, **extra):
        return {"erfolg": False, "protokoll": protokoll,
                "meldung": meldung, **extra}

    p = subprocess.run([sys.executable, str(INDEXER)],
                       cwd=WURZEL, capture_output=True, text=True)
    protokoll.append({"titel": "Übersicht erzeugt",
                      "erfolg": p.returncode == 0,
                      "ausgabe": (p.stdout + p.stderr).strip()})

    # Erst festschreiben, dann abgleichen: so ist der Arbeitsordner sauber,
    # wenn die fremden Änderungen eingespielt werden.
    ok, _ = schritt("Änderungen vorgemerkt", "add", "-A")
    if not ok:
        return abbruch("Die Änderungen konnten nicht vorgemerkt werden.")

    code, _ = git("diff", "--staged", "--quiet")
    if code == 0:
        protokoll.append({"titel": "Nichts festzuschreiben", "erfolg": True,
                          "ausgabe": "Es gab keine neuen Änderungen."})
    else:
        ok, _ = schritt("Änderungen festgeschrieben", "commit", "-m", nachricht)
        if not ok:
            return abbruch("Die Änderungen konnten nicht festgeschrieben werden.")

    _, zweig = git("rev-parse", "--abbrev-ref", "HEAD")
    zweig = zweig.strip()

    ok, ausgabe = schritt("Stand von GitHub geholt", "fetch", "origin")
    if not ok:
        if AUTHFEHLER.search(ausgabe):
            return abbruch("GitHub hat die Anmeldung nicht akzeptiert. Bitte "
                           "unter „Verbindung“ Benutzernamen und Token prüfen.",
                           anmeldung_noetig=True)
        return abbruch("GitHub ist nicht erreichbar. Einzelheiten stehen im "
                       "Protokoll.")

    # Nur abgleichen, wenn es den Zweig bei GitHub überhaupt schon gibt.
    vorhanden, _ = git("rev-parse", "--verify", "--quiet", f"origin/{zweig}")
    if vorhanden == 0:
        ok, ausgabe = schritt("Abgleich geprüft – es gab Überschneidungen",
                              "rebase", "--autostash", f"origin/{zweig}")
        if not ok:
            # Dieselbe Datei wurde hier und auf GitHub verändert. Der
            # Projektordner auf diesem Rechner gilt als maßgeblich, deshalb
            # bekommt seine Fassung den Vorrang. Der Schritt sagt das offen.
            git("rebase", "--abort")
            ok, ausgabe = schritt(
                "Abgeglichen – bei Überschneidungen galt deine Fassung",
                "rebase", "--autostash", "-X", "theirs", f"origin/{zweig}")
            if not ok:
                git("rebase", "--abort")
                return abbruch(
                    "Der Stand auf GitHub und dein Stand hier lassen sich nicht "
                    "zusammenführen. Nichts ging verloren und nichts wurde "
                    "hochgeladen — bitte melde dich, bevor du weitermachst.")

    # Zwei unabhängige Fragen: Gibt es den Zweig bei GitHub schon (dann muss
    # abgeglichen werden), und ist er hier damit verknüpft (sonst braucht der
    # Push das Ziel ausdrücklich).
    verknuepft, _ = git("rev-parse", "--abbrev-ref",
                        "--symbolic-full-name", "@{u}")
    if verknuepft == 0:
        ok, ausgabe = schritt("Zu GitHub hochgeladen", "push")
    else:
        ok, ausgabe = schritt("Zu GitHub hochgeladen und verknüpft",
                              "push", "--set-upstream", "origin", zweig)
    if not ok:
        if AUTHFEHLER.search(ausgabe):
            return abbruch("GitHub hat die Anmeldung nicht akzeptiert. Bitte "
                           "unter „Verbindung“ Benutzernamen und Token prüfen.",
                           anmeldung_noetig=True)
        if re.search(r"non-fast-forward|rejected|fetch first", ausgabe, re.I):
            return abbruch("GitHub hat neuere Änderungen, die hier noch fehlen. "
                           "Bitte einfach noch einmal auf „Jetzt veröffentlichen“ "
                           "drücken — der Abgleich läuft dann erneut.")
        return abbruch("Das Hochladen ist fehlgeschlagen. Einzelheiten stehen "
                       "im Protokoll.")

    return {"erfolg": True, "protokoll": protokoll,
            "meldung": "Veröffentlicht. GitHub braucht meist ein bis zwei "
                       "Minuten, bis die Seite aktualisiert ist.",
            "adresse": veroeffentlichungsadresse()}


# ------------------------------------------------------------------ Server

class Werkstatt(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WURZEL), **kw)

    def log_message(self, *a):
        pass

    def antwort_json(self, daten, status=200):
        roh = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(roh)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(roh)

    def token_gueltig(self):
        frage = urllib.parse.urlparse(self.path).query
        gegeben = urllib.parse.parse_qs(frage).get("t", [""])[0]
        return secrets.compare_digest(gegeben, TOKEN)

    def rumpf(self):
        laenge = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(laenge) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        weg = urllib.parse.urlparse(self.path).path

        if weg in ("/", "/werkstatt"):
            seite = OBERFLAECHE.read_text(encoding="utf-8")
            roh = seite.replace("__TOKEN__", TOKEN).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(roh)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(roh)
            return

        if weg.startswith("/api/"):
            if not self.token_gueltig():
                return self.antwort_json({"fehler": "Zugriff verweigert"}, 403)

            if weg == "/api/zustand":
                return self.antwort_json(zustand_ermitteln())
            if weg == "/api/bestand":
                return self.antwort_json(bestand_lesen())
            if weg == "/api/verbindung":
                return self.antwort_json(verbindung_lesen())
            if weg == "/api/test":
                return self.antwort_json(verbindung_testen())
            if weg == "/api/beenden":
                self.antwort_json({"erfolg": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            return self.antwort_json({"fehler": "Unbekannt"}, 404)

        return super().do_GET()

    def do_POST(self):
        weg = urllib.parse.urlparse(self.path).path
        if not self.token_gueltig():
            return self.antwort_json({"fehler": "Zugriff verweigert"}, 403)

        daten = self.rumpf()

        try:
            if weg == "/api/hochladen":
                nachricht = (daten.get("nachricht") or "").strip()
                return self.antwort_json(
                    hochladen(nachricht or "Material aktualisiert"))

            if weg == "/api/zugangsdaten":
                if daten.get("loeschen"):
                    return self.antwort_json(zugangsdaten_loeschen())
                benutzer = (daten.get("benutzer") or "").strip()
                token = (daten.get("token") or "").strip()
                if not benutzer or not token:
                    return self.antwort_json(
                        {"erfolg": False,
                         "meldung": "Benutzername und Token werden beide "
                                    "benötigt."})
                return self.antwort_json(zugangsdaten_speichern(benutzer, token))

            if weg == "/api/repository":
                return self.antwort_json(
                    repository_setzen(daten.get("adresse") or ""))

            if weg == "/api/sichtbarkeit":
                pfad = (daten.get("pfad") or "").strip()
                if not pfad:
                    return self.antwort_json(
                        {"erfolg": False, "meldung": "Kein Pfad angegeben."})
                return self.antwort_json(
                    einblenden(pfad) if daten.get("oeffentlich")
                    else ausblenden(pfad))

        except Exception as f:  # noqa: BLE001
            return self.antwort_json(
                {"erfolg": False, "meldung": f"Unerwarteter Fehler: {f}"})

        return self.antwort_json({"fehler": "Unbekannt"}, 404)


def freier_port(start=8765):
    for port in range(start, start + 40):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("Kein freier Port gefunden.")


def main():
    if not OBERFLAECHE.exists():
        raise SystemExit(f"Oberfläche fehlt: {OBERFLAECHE}")

    port = freier_port()
    adresse = f"http://127.0.0.1:{port}/?t={TOKEN}"
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Werkstatt)

    print("\n  KGS - Digital · Werkstatt")
    print("  " + "-" * 44)
    print(f"  Projektordner : {WURZEL}")
    print(f"  Oberfläche    : {adresse}")
    print("\n  Das Fenster offen lassen, solange du arbeitest.")
    print("  Beenden mit Strg+C oder über die Schaltfläche in der Seite.\n")

    threading.Timer(0.6, lambda: webbrowser.open(adresse)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("  Werkstatt beendet.\n")


if __name__ == "__main__":
    main()
