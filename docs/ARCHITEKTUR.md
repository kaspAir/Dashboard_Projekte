# Projekt-Dashboard – Architektur-Grundsätze

> Gemeinsame Referenz für die Architektur. Festgehalten **vor** der ersten Codezeile,
> damit alle Design-Entscheidungen an einem klaren Fundament gemessen werden können.
> Dieses Dokument wächst mit dem Projekt – Änderungen an den Grundsätzen werden hier
> bewusst nachgeführt.

## 1. Zweck & Vision

Ein Dashboard, das der Leitung (z. B. einem Amtsdirektor) den **Stand aller Projekte**
sichtbar macht – gespeist aus den bestehenden **Projektstatusreports (PSR)** der
Organisation.

Von Anfang an gross gedacht:

- **Mandantenfähig** – einsetzbar für mehrere Organisationen, mit harter Datenisolation.
- **Konfigurierbar, woher** die Informationen stammen (Quellen).
- **Konfigurierbar, was** relevant ist und **wie** es dargestellt wird
  (Inhalte, Granularität: einzelne Projekte, Projekttypen, Portfolios …).

Erster Kunde: Liechtensteinische Landesverwaltung (LLV).

## 2. Leitprinzipien

1. **Quelle und Darstellung sind strikt entkoppelt** über ein source-agnostisches,
   kanonisches Status-Modell in der Mitte. Keine Schicht ausser der Extraktion kennt
   je das konkrete PSR-Format.
2. **Konfiguration ist Daten, nicht Code.** Quell-Bindung und Darstellung werden pro
   Mandant konfiguriert, ohne Codeänderung.
3. **Provenienz statt Halluzination.** Jeder extrahierte Wert verweist auf seine
   Fundstelle in der Quelle und trägt eine Konfidenz. Bei Unsicherheit bleibt das Feld
   **leer statt geraten** – ein Dashboard, das Status erfindet, ist schlimmer als eines
   mit Lücken.
4. **Historisierung von Beginn weg.** Jeder Report wird als **Snapshot** gespeichert,
   nicht überschrieben. Das ergibt Zeitreihen und damit **Trends** – der eigentliche
   Mehrwert für die Leitung (welches Projekt kippt gerade von grün auf gelb?).
5. **Mandanten-Isolation durchgängig.** `org_id`-Scoping über alle Schichten hinweg.
6. **Statisch starten, interaktiv wachsen.** Die Daten-/API-Schicht wird so gebaut,
   dass Interaktivität später *nur* Frontend-Arbeit ist, kein Umbau darunter.

## 3. Schichtenarchitektur

Vertikaler Datenfluss, jede Schicht ein Erweiterungspunkt:

| # | Schicht | Aufgabe |
|---|---------|---------|
| 1 | **Quellen** | SharePoint/PSR, Excel, manuelle Eingabe, HERMES PIA … |
| 2 | **Connector** | `fetch(source_config) → Artefakte`. Dokument-basiert **oder** strukturiert. Pluggable. |
| 3 | **Extraktion** | Artefakt → strukturierte Felder. LLM-gestützt, **findet** relevante Inhalte, liefert **Fundstellen-Nachweis**. Pro Connector optional. |
| 4 | **Kanonisches Status-Modell** | Normalisiert, `org_id`-gescoped, **historisierte Snapshots**. Die Nabe. |
| 5 | **Aggregation** | Roll-ups: Projekt → Projekttyp → Portfolio → Amt. |
| 6 | **Präsentation** | Dashboard + API. Config-getrieben. Statisch → interaktiv. |

**Wichtig zur Extraktion (Schicht 3):** Sie ist **pro Connector optional**.
Dokument-Quellen (unbekannte docx/PDF) gehen durch die LLM-Extraktion; **strukturierte
Quellen wie HERMES PIA** liefern bereits saubere Daten und mappen fast direkt ins
kanonische Modell.

## 4. Kernartefakte der Konfiguration (pro Mandant)

- **Management-Informationsmodell** – *die* zentrale Definition: beschreibt aus
  Management-Sicht, **welche Information relevant ist** (z. B. Gesamtstatus, Budget-Ampel,
  Termin-Ampel, Top-Risiken, nächste Meilensteine). Es steuert **gleichzeitig**
  die Extraktion (*was suchen?*) **und** die Präsentation (*was zeigen?*).
  Eine Definition, zwei Zwecke.
- **Quell-Bindung** – wo die Quellen liegen, Zugang/Credentials, optionale Hinweise.

Das semantische Mapping (Informationsmodell → im PSR finden) ist bewusst **nicht
positionsbasiert** («Zelle B7»), weil das bei jedem neuen PSR-Layout bricht.

## 5. Datenmodell – Grundzüge

- **Status-Snapshot** je (Projekt, Berichtsperiode, Quelle) – historisiert, nie überschrieben.
- Jeder **Wert** trägt: Herkunft (Fundstelle), Konfidenz, ggf. leer.
- Alles **`org_id`-gescoped**; NULL-Semantik für geteilte/Referenzdaten analog bewährtem Muster.

## 6. Tech-Stack (Entscheid)

Konsistent mit den bestehenden Systemen, um Betriebs-, Deployment- und CI-Synergien zu nutzen:

- **Python** (Backend), **Gunicorn**
- **SQLite → ggf. Postgres** bei wachsendem Bedarf
- Hosting auf **Infomaniak** (managed), **Jenkins** CI/CD via SSH
- **LLM-gestützte Extraktion** (Provenienz-Pflicht, siehe Prinzip 3)
- Frontend zunächst statisch gerendert; interaktive Ausbaustufe später

## 7. Roadmap / Phasen

- **Phase 0 – Vertikaler Durchstich, ohne SharePoint.**
  Dünner, aber durchgehender Schnitt durch alle sechs Schichten mit **einfachen
  «Mickey-Mouse»-PSR** und **Excel-/Datei-Upload als erstem Connector**. Beweist
  Datenmodell + semantische Extraktion an echten Beispielen, ohne auf den
  (politisch langsamen) SharePoint-Zugang zu warten.
  Umfang: kanonisches Modell + Snapshots, erstes Management-Informationsmodell als
  Config, LLM-Extraktion mit Fundstellen, `org_id`-Scoping, statisches Dashboard mit
  Ampeln + Drill-down nach Projekttyp.
- **Phase 1 – SharePoint/Graph-Connector.** Austausch der Connector-Schicht
  (Microsoft Graph, Azure-AD-App-Registrierung, least-privilege `Sites.Selected`).
  Modell bleibt unverändert.
- **Phase 2 – Interaktives Dashboard.** Reine Frontend-Ausbaustufe.
- **Später – weitere Connectoren**, u. a. **HERMES PIA als strukturierte Quelle**.

## 8. Offene Punkte & Risiken

- **PSR-Struktur & -Inhalt** noch unbekannt → Modell tolerant designen; mit echten
  Beispielen validieren, sobald verfügbar.
- **SharePoint-Zugang (LLV):** Azure-AD-App-Registrierung im Kunden-Tenant ist eine
  organisatorisch-politische Abhängigkeit → früh anstossen, kann zum Nadelöhr werden.
- **Frontend-Technologie** für die interaktive Stufe noch offen.
- **Verhältnis zu HERMES PIA:** eigenständiges Produkt; HERMES PIA nur als andockbare
  Datenquelle, kein geteiltes Org-/Auth-Backbone (Entscheid: bewusst getrennt).
