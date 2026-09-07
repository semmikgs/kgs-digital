# KGS - Digital

Materialsammlung der Fachbereiche. Du pflegst alles lokal in einem Ordner,
die Werkstatt lädt es auf Knopfdruck zu GitHub. Von dort ist die Seite über
IServ erreichbar.

## Einmalig einrichten

1. Auf **github.com** ein leeres Repository anlegen — ohne README, ohne
   .gitignore. Die angezeigte Adresse bereithalten.
2. Diesen Ordner an einen festen Platz legen, z. B. `~/KGS-Digital`.
3. Ein Terminal im Ordner öffnen und einmalig ausführen:

   ```bash
   chmod +x start.sh einrichten.sh
   ./einrichten.sh
   ```

   Das Skript fragt Name, E-Mail und die Repository-Adresse ab.
4. `./start.sh` starten und einmal veröffentlichen.
5. Auf github.com im Repository:
   - **Settings → Pages:** Source „Deploy from a branch", Branch `main`, Ordner `/ (root)`
   - **Settings → Actions → General → Workflow permissions:** „Read and write permissions"
6. In IServ einen Menüpunkt auf die Pages-Adresse setzen.

### Anmeldung bei GitHub

Beim ersten Veröffentlichen meldet die Werkstatt „Die Anmeldung bei GitHub
fehlt". Oben auf **Verbindung** drücken und eintragen:

- **Benutzername** — dein GitHub-Benutzername
- **Token** — statt des Kontopassworts, GitHub akzeptiert kein Passwort mehr

Ein Token erstellst du unter **github.com → Settings → Developer settings →
Personal access tokens**. Ein *classic* Token braucht die Berechtigung
`repo` und gilt für alle deine Repositories. Ein *fine-grained* Token
braucht `Contents: Read and write` und muss dieses Repository ausdrücklich
einschließen.

Die Zugangsdaten landen in Gits eigenem Speicher unter `~/.git-credentials`,
lesbar nur für dich. Das liegt bewusst außerhalb des Projektordners — dort
würde es mit auf GitHub hochgeladen. Einmal eintragen genügt.

## Verbindung prüfen und ändern

Der Knopf **Verbindung** oben zeigt Repository-Adresse, Benutzernamen und
Zweig und lässt alles davon jederzeit ändern:

- **Verbindung testen** prüft in fünf Schritten, ob Veröffentlichen
  funktionieren wird: Adresse hinterlegt, GitHub erreichbar, Anmeldung
  akzeptiert, Zweig vorhanden, Schreibrecht vorhanden. Dabei wird nichts
  verändert. Nach dem Einrichten oder nach einem Token-Wechsel lohnt sich
  dieser Test.
- **Adresse des Repositories** ändern, wenn du das Repository umbenennst
  oder auf ein anderes umziehst.
- **Token** austauschen, wenn es abgelaufen ist. Das Feld leer lassen
  behält das gespeicherte Token.
- **Zugangsdaten löschen** entfernt Benutzername und Token aus dem
  Speicher, etwa bei einem Rechnerwechsel.

## Bestand ansehen und Material zurückziehen

Der Knopf **Bestand anzeigen** klappt eine Liste aller Materialien auf,
nach Fachbereichen geordnet, mit eigener Suche. Sie ist standardmäßig
eingeklappt und stört den Upload-Ablauf nicht.

Jede Zeile zeigt, ob das Material auf der Schulseite steht oder nur lokal
liegt:

- **Von der Seite nehmen** — das Material verschwindet beim nächsten
  Veröffentlichen von der Website und aus der Suche. Auf deinem Rechner
  bleibt die Datei unangetastet.
- **Freigeben** — macht das rückgängig.

Technisch trägt die Werkstatt den Pfad in einen eigenen Abschnitt der
`.gitignore` ein. Du kannst dort auch von Hand nachsehen; der Abschnitt ist
mit einem Kommentar markiert.


## Täglicher Ablauf

1. Datei in den passenden Fachbereichsordner legen.
2. **Doppelklick auf `start.sh`** (beim ersten Mal fragt Ubuntu nach —
   „Ausführen" wählen). Der Browser öffnet sich.
3. Die Werkstatt zeigt alle neuen, geänderten und gelöschten Dateien.
   Über „Vorschau ansehen" lässt sich das Portal vorher lokal prüfen.
4. Notiz eintragen, auf **Jetzt veröffentlichen** drücken.

Nach ein bis zwei Minuten ist die Seite in der Schule aktuell.

Falls der Doppelklick nichts tut: in den Dateieigenschaften unter
„Zugriffsrechte" das Ausführen erlauben, oder im Terminal `./start.sh`
eingeben.

## Material hinzufügen

Datei in den Fachbereichsordner legen — mehr ist nicht nötig.

**Kategorie vergeben** (die Filter-Schaltflächen oben auf der Seite):
Datei in einen Unterordner legen, der Ordnername wird zur Kategorie.

```
mathematik/Klasse 7/bruchrechnen.html   →  Filter „Klasse 7"
mathematik/formelsammlung.pdf           →  ohne Filter
```

**Titel und Beschreibung** liest die Übersicht bei HTML-Dateien direkt aus
der Datei:

```html
<title>Brüche kürzen und erweitern</title>
<meta name="description" content="Interaktive Übung mit Rückmeldung.">
```

Fehlt beides, dient der Dateiname als Titel — deshalb lohnen sprechende
Dateinamen. Optional lässt sich die Kategorie auch in der Datei festlegen
und übersteuert dann den Unterordner:

```html
<meta name="kgs-kategorie" content="Klasse 8">
```

Unterstützt werden HTML, PDF, Word, PowerPoint, Excel, ODF, ZIP, Python,
Markdown und Bilder.

## Externe Links pflegen

In jedem Fachbereich liegt `extern.html`. Dort den markierten Block
kopieren und Adresse, Name und Beschreibung ersetzen. Die Suche findet
neue Einträge automatisch.

## Neuen Fachbereich anlegen

1. Ordner anlegen, z. B. `technik`.
2. `index.html` und `extern.html` aus einem bestehenden Fachbereich
   hineinkopieren.
3. In `index.html` unten im Block `const FACH = { … }` Titel, Symbol und
   Untertitel anpassen; in `extern.html` den Fachnamen ersetzen.
4. In der `index.html` des Hauptordners eine Zeile im Block
   `FACHBEREICHE` ergänzen.

## Aussehen ändern

Farben und Abstände stehen gesammelt oben in `assets/kgs.css` unter
`:root`. Eine Änderung dort wirkt auf allen Seiten.

## Aufbau

```
start.sh                       Werkstatt starten (Doppelklick)
einrichten.sh                  einmalige Einrichtung
index.html                     Startseite mit den Fachbereichskacheln
assets/kgs.css                 Aussehen aller Seiten
assets/kgs.js                  Suche, Filter, Auto-Übersicht
tools/werkstatt.py             lokaler Server der Werkstatt
tools/werkstatt.html           Oberfläche der Werkstatt
tools/index_erstellen.py       erzeugt die Übersichten
tools/vorlage-index.html       Vorlage für neue Fachbereiche
tools/vorlage-extern.html      Vorlage für neue Linkseiten
.github/workflows/             Sicherheitsnetz: indiziert auch bei
                               Änderungen direkt auf github.com
<fachbereich>/index.html       Übersicht des Fachbereichs
<fachbereich>/extern.html      Linksammlung des Fachbereichs
<fachbereich>/dateien.json     wird automatisch erzeugt, nicht bearbeiten
```

## Wenn etwas klemmt

**„GitHub hat die Anmeldung nicht akzeptiert"** — Token abgelaufen oder ohne
ausreichende Berechtigung. Oben auf *Verbindung* drücken, Token neu eintragen
und *Verbindung testen*. Falls das nicht hilft, im Terminal
`git push` ausführen, dann zeigt Git die genaue Ursache. Siehe oben
„Anmeldung bei GitHub".

**„Bei Überschneidungen galt deine Fassung"** — dieselbe Datei wurde hier
und auf GitHub geändert. Der Projektordner auf deinem Rechner gilt als
maßgeblich, seine Fassung wurde übernommen. Das ist im Normalbetrieb
richtig; es tritt vor allem beim ersten Veröffentlichen auf, wenn GitHub
das Repository mit einer eigenen README angelegt hat.

**Liste auf der Schulseite bleibt leer** — auf github.com unter *Actions*
prüfen, ob der Lauf durchging. Bei einem Berechtigungsfehler Punkt 5 der
Einrichtung nachholen.

**Werkstatt öffnet sich nicht** — im Terminal `./start.sh` ausführen, dort
steht die Fehlermeldung. Die Oberfläche läuft nur auf diesem Rechner und
ist von außen nicht erreichbar.

## Sicherheit

Die Werkstatt lauscht ausschließlich auf 127.0.0.1 und ist mit einem
Zufallsschlüssel geschützt, der bei jedem Start neu erzeugt wird. Es
werden keine Zugangsdaten in Dateien des Projekts abgelegt — die
Anmeldung verwaltet Git selbst.
