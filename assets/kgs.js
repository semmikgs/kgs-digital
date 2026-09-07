/* =========================================================
   KGS - Digital – gemeinsame Logik
   Steuert Startseite, Fachbereichsseiten und Suche.
   Hier musst du im Normalfall nichts ändern.
   ========================================================= */

(function () {
  "use strict";

  /* ---------- kleine Helfer ---------- */

  const el = (tag, klasse, text) => {
    const k = document.createElement(tag);
    if (klasse) k.className = klasse;
    if (text != null) k.textContent = text;
    return k;
  };

  const entschaerfen = (s) => (s == null ? "" : String(s));

  // Umlaute und Groß-/Kleinschreibung für die Suche vereinheitlichen
  const normal = (s) =>
    entschaerfen(s)
      .toLowerCase()
      .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue")
      .replace(/ß/g, "ss");

  const datumDeutsch = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleDateString("de-DE", {
      day: "2-digit", month: "2-digit", year: "numeric"
    });
  };

  const SYMBOLE = {
    html: "🧩", pdf: "📄", docx: "📝", odt: "📝", pptx: "📊",
    xlsx: "📈", zip: "🗜️", py: "🐍", md: "📘", bild: "🖼️", datei: "📎"
  };

  /* ---------- Startseite ---------- */

  function startseiteAufbauen(liste) {
    const ziel = document.getElementById("kacheln");
    if (!ziel) return;

    liste.forEach((f) => {
      const a = el("a", "kachel");
      a.href = f.ordner + "/";
      a.appendChild(el("span", "symbol", f.symbol || "📁"));
      a.appendChild(el("h2", null, f.titel));
      a.appendChild(el("p", null, f.beschreibung || ""));
      ziel.appendChild(a);
    });
  }

  /* ---------- Fachbereichsseite ---------- */

  function fachbereichAufbauen(fach) {
    const ziel = document.getElementById("liste");
    const suche = document.getElementById("suche");
    const filterreihe = document.getElementById("filter");
    const zaehler = document.getElementById("zaehler");
    if (!ziel) return;

    let eintraege = [];
    let kategorie = "alle";
    let suchtext = "";

    function zeichnen() {
      ziel.innerHTML = "";

      const treffer = eintraege.filter((e) => {
        if (kategorie !== "alle" && e.kategorie !== kategorie) return false;
        if (!suchtext) return true;
        const heuhaufen = normal(
          [e.titel, e.beschreibung, e.datei, e.kategorie].join(" ")
        );
        // alle Suchwörter müssen vorkommen
        return normal(suchtext).split(/\s+/).every((w) => heuhaufen.includes(w));
      });

      if (zaehler) {
        zaehler.textContent =
          treffer.length === eintraege.length
            ? `${eintraege.length} ${eintraege.length === 1 ? "Eintrag" : "Einträge"}`
            : `${treffer.length} von ${eintraege.length} Einträgen`;
      }

      if (!treffer.length) {
        const h = el("div", "hinweis");
        h.innerHTML = eintraege.length
          ? "Keine Treffer. Suchbegriff ändern oder auf <strong>Alle</strong> zurücksetzen."
          : "Noch keine Dateien in diesem Fachbereich. Lade eine Datei in den Ordner hoch — sie erscheint nach dem nächsten Hochladen automatisch hier.";
        ziel.appendChild(h);
        return;
      }

      treffer.forEach((e) => {
        const a = el("a", "eintrag");
        a.href = e.pfad;
        if (e.typ !== "html") a.setAttribute("target", "_blank");

        const sym = SYMBOLE[e.typ] || SYMBOLE.datei;
        a.appendChild(el("h3", null, sym + "  " + e.titel));

        if (e.beschreibung) a.appendChild(el("p", null, e.beschreibung));
        if (e.kategorie) a.appendChild(el("span", "badge", e.kategorie));

        const teile = [e.datei];
        if (e.groesse) teile.push(e.groesse);
        if (e.geaendert) teile.push("aktualisiert " + datumDeutsch(e.geaendert));
        a.appendChild(el("div", "meta", teile.join("  ·  ")));

        ziel.appendChild(a);
      });
    }

    function filterAufbauen() {
      if (!filterreihe) return;
      const kats = [...new Set(eintraege.map((e) => e.kategorie).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, "de"));

      filterreihe.innerHTML = "";
      if (!kats.length) return;

      [["alle", "Alle"], ...kats.map((k) => [k, k])].forEach(([wert, text]) => {
        const b = el("button", "filter", text);
        b.type = "button";
        b.setAttribute("aria-pressed", wert === "alle" ? "true" : "false");
        b.addEventListener("click", () => {
          kategorie = wert;
          [...filterreihe.children].forEach((c) =>
            c.setAttribute("aria-pressed", String(c === b))
          );
          zeichnen();
        });
        filterreihe.appendChild(b);
      });
    }

    if (suche) {
      suche.addEventListener("input", () => {
        suchtext = suche.value.trim();
        zeichnen();
      });
    }

    // Auto-Index laden
    fetch("dateien.json?frisch=" + Date.now())
      .then((r) => {
        if (!r.ok) throw new Error("dateien.json fehlt");
        return r.json();
      })
      .then((daten) => {
        eintraege = (daten.eintraege || []).sort((a, b) => {
          const k = entschaerfen(a.kategorie).localeCompare(
            entschaerfen(b.kategorie), "de"
          );
          return k !== 0 ? k : a.titel.localeCompare(b.titel, "de");
        });
        filterAufbauen();
        zeichnen();
      })
      .catch(() => {
        ziel.innerHTML = "";
        const h = el("div", "hinweis");
        h.innerHTML =
          "Die Übersicht <strong>dateien.json</strong> wurde nicht gefunden. " +
          "Sie entsteht automatisch beim Hochladen auf GitHub. " +
          "Wenn du die Seiten lokal öffnest, starte stattdessen einen kleinen " +
          "Webserver oder sieh dir die Seiten direkt auf GitHub Pages an.";
        ziel.appendChild(h);
        if (zaehler) zaehler.textContent = "";
      });
  }

  /* ---------- Suche auf der Seite „Externe Werkzeuge" ---------- */

  function externeSucheAufbauen() {
    const suche = document.getElementById("suche");
    const ziel = document.getElementById("liste");
    if (!suche || !ziel) return;

    const karten = [...ziel.querySelectorAll(".eintrag")];
    const leer = el("div", "hinweis", "Keine Treffer.");
    leer.hidden = true;
    ziel.appendChild(leer);

    suche.addEventListener("input", () => {
      const woerter = normal(suche.value.trim()).split(/\s+/).filter(Boolean);
      let sichtbar = 0;

      karten.forEach((k) => {
        const treffer =
          !woerter.length ||
          woerter.every((w) => normal(k.textContent).includes(w));
        k.hidden = !treffer;
        if (treffer) sichtbar++;
      });

      leer.hidden = sichtbar > 0;
    });
  }

  /* ---------- Start ---------- */

  document.addEventListener("DOMContentLoaded", () => {
    if (typeof FACHBEREICHE !== "undefined") startseiteAufbauen(FACHBEREICHE);
    if (typeof FACH !== "undefined") fachbereichAufbauen(FACH);
    if (document.body.dataset.seite === "extern") externeSucheAufbauen();
  });
})();
