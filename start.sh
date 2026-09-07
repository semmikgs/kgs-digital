#!/usr/bin/env bash
#
# KGS - Digital · Werkstatt starten
#
# Doppelklick auf diese Datei (oder im Terminal: ./start.sh)
# Öffnet die Oberfläche im Browser.
#
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "  Python 3 fehlt. Installieren mit:"
  echo "      sudo apt install python3"
  echo
  read -rp "  Mit Eingabetaste schließen … " _
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo
  echo "  Git fehlt. Installieren mit:"
  echo "      sudo apt install git"
  echo
  read -rp "  Mit Eingabetaste schließen … " _
  exit 1
fi

python3 tools/werkstatt.py || {
  echo
  read -rp "  Es ist ein Fehler aufgetreten. Mit Eingabetaste schließen … " _
}
