#!/usr/bin/env bash
#
# KGS - Digital · Einmalige Einrichtung
#
# Verbindet diesen Ordner mit deinem GitHub-Repository.
# Danach wird nur noch start.sh gebraucht.
#
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

echo
echo "  KGS - Digital · Einrichtung"
echo "  --------------------------------------------"
echo

for werkzeug in git python3; do
  if ! command -v "$werkzeug" >/dev/null 2>&1; then
    echo "  $werkzeug fehlt. Installieren mit:  sudo apt install $werkzeug"
    exit 1
  fi
done

# --- Name und E-Mail ---------------------------------------------------

if [ -z "$(git config --global user.name || true)" ]; then
  read -rp "  Dein Name (erscheint in der Versionsgeschichte): " name
  git config --global user.name "$name"
fi

if [ -z "$(git config --global user.email || true)" ]; then
  read -rp "  Deine E-Mail-Adresse bei GitHub: " mail
  git config --global user.email "$mail"
fi

# --- Repository --------------------------------------------------------

if [ ! -d .git ]; then
  git init -q
  git branch -M main
  echo "  Ordner als Repository angelegt."
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo
  echo "  Lege auf github.com ein leeres Repository an (ohne README),"
  echo "  und kopiere die angezeigte Adresse hierher."
  echo "  Beispiel:  https://github.com/benutzername/kgs-digital.git"
  echo
  read -rp "  Adresse des Repositories: " adresse
  git remote add origin "$adresse"
  echo "  Repository verbunden."
fi

# --- Anmeldung dauerhaft speichern -------------------------------------

if [ -z "$(git config --global credential.helper || true)" ]; then
  git config --global credential.helper "store"
  echo
  echo "  Die Anmeldung wird beim ersten Hochladen einmalig abgefragt"
  echo "  und danach gespeichert."
  echo
  echo "  Wichtig: GitHub verlangt statt des Passworts ein Token."
  echo "  Erstellen unter:  github.com  ->  Settings  ->  Developer settings"
  echo "                    ->  Personal access tokens  ->  Tokens (classic)"
  echo "  Berechtigung 'repo' auswählen, Token kopieren und beim"
  echo "  Hochladen anstelle des Passworts eingeben."
fi

# --- Erster Stand ------------------------------------------------------

python3 tools/index_erstellen.py >/dev/null 2>&1 || true
git add -A
if ! git diff --staged --quiet; then
  git commit -q -m "Portal eingerichtet"
  echo "  Erster Stand festgeschrieben."
fi

chmod +x start.sh einrichten.sh 2>/dev/null || true

echo
echo "  Fertig."
echo
echo "  Nächste Schritte:"
echo "    1. ./start.sh  starten und veröffentlichen"
echo "    2. Auf github.com unter Settings -> Pages:"
echo "         Source: Deploy from a branch, Branch: main, Ordner: / (root)"
echo "    3. Unter Settings -> Actions -> General:"
echo "         Workflow permissions auf 'Read and write' stellen"
echo
read -rp "  Mit Eingabetaste schließen … " _
