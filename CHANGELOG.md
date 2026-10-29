# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[SemVer](https://semver.org/lang/de/).

## [Unreleased]

## [0.7.2] – 2026-10-29

### Portfolio-Management (Slice 3): Pflege im Tool
- **KPI-Katalog-Editor** (`/portfolio/kpis`): KPIs und Gewichte je Portfolio im Tool
  anlegen, ändern und löschen (statt YAML).
- **Vorhaben-Editor** (`/portfolio/vorhaben/<ref>`): Durchführungsauftrag (Status,
  Budget-/Aufwand-Soll, Einheit/Bereich/Programm), KPI-Werte und das Muss-Tor mit
  Frist erfassen; neues Vorhaben anlegen, Vorhaben löschen, Auftrag zu einem
  berichtenden Projekt nacherfassen.
- Bearbeitung nur für Admins; gespeichert als Live-Stand je Mandant
  (`data/portfolio/<mandant>.yaml`), Seed bleibt als Vorgabe erhalten.

## [0.7.1] – 2026-10-29

### Portfolio-Management (Slice 2): konfigurierbare KPIs & Priorisierung
- **Konfigurierbarer KPI-Katalog je Portfolio**: der Kunde definiert eigene KPIs
  (Art tor/bewertung/messung, Skala, Richtung, Gewicht, Quelle manuell/PSR).
- **Berechnete Prioritätszahl (0–100)** als gewichteter, normierter Mittelwert der
  bewerteten KPIs; fehlende Werte gelten als „unbekannt" (nicht 0).
- **Muss-Tor an eine Frist gekoppelt** (z. B. Inkrafttreten eines Gesetzes): sticht
  das Scoring, Vorhaben werden nach Pflichtfrist geordnet, mit Warnung bei
  **überfälliger** oder **knapper** Frist.
- KPI-Katalog-Ansicht (Gewichte sichtbar) und Prioritäts-Aufschlüsselung je Vorhaben.

## [0.7.0] – 2026-10-29

### Portfolio-Management (Slice 1)
- Neue **Portfolio-Übersicht** (`/portfolio`): verbindet das gepflegte **Soll**
  (Durchführungsaufträge, genehmigtes Budget, Aufwand-Soll, Priorität inkl.
  Pflicht-Kennzeichen) mit dem **Ist/Prognose aus den Statusberichten**.
- **Soll-Ist-Warnungen**: Prognose über genehmigtem Budget bzw. Aufwand-Soll
  (nur für laufende Vorhaben); abgebrochene zählen nicht in die Budgetsummen.
- **Budget mehrdimensional**: Roll-up je **Bereich (Ressort)** und **Einheit
  (Amt/Abteilung)** gegen den zugeteilten **Budgetrahmen**, plus Programm-Rahmen.
- **Governance-Befunde** aus dem Join: Projekt berichtet *ohne erfassten Auftrag*;
  Vorhaben *freigegeben, aber ohne Bericht*.
- Portfolio-Soll als gepflegte Daten (`sample-data/portfolio-<mandant>.yaml`,
  Live-Override unter `data/portfolio/`), getrennt vom PSR-Ist.

## [0.6.0] – 2026-10-29

### Fachlichkeit
- **Ampel-Drilldown** auf der Projekt-Detailseite: jede der 8 Ampeln ist aufklappbar
  und zeigt ihren **eigenen Verlauf**, die **Erläuterung aus dem PSR**, die konkreten
  **Belegdaten** (Kosten/Aufwand, Meilensteine bzw. Sprints, Ziele, Risiken, Probleme
  & Massnahmen) sowie **Fundstelle + Konfidenz** – „warum ist diese Ampel gelb?".
- **Klassische und agile Projekte**: Vorgehensmodell je Projekt (nie gemischt);
  methodengerechte Belege (Meilensteine klassisch / Sprints & Inkremente agil). Die
  Management-Sicht (8 Ampeln) normalisiert beide Welten auf dieselbe Darstellung.
- **Programm → Projekt**: Programm-Status als Roll-up (worst-of seiner Projekte) auf
  dem Dashboard; Programm als Filter auf der Projektliste.

### Extraktion & Testdaten
- Extraktion erfasst zusätzlich: Erläuterungen je Ampel, Fazit, Ziele, Meilensteine
  bzw. Sprints, Probleme/Massnahmen, Risiken sowie Vorgehensmodell und Programm –
  jeweils mit Fundstelle (kein Raten: leer, wenn nicht im PSR).
- **Musterstadt-„Projektlaufwerk"** (verschachtelte Programm-/Projektordner, agile und
  klassische PSR, dazu bewusst Nicht-PSR-Dateien) belegt den rekursiven Root-Scan mit
  inhaltsbasiertem PSR-Filter: gescannt 236, als PSR erkannt 228, übersprungen 8.

## [0.5.1] – 2026-07-11

### Betrieb / Zuverlässigkeit
- **Watchdog** (`deploy/keepalive.sh` + Cron `@reboot` und alle 3 Minuten): Gunicorn
  startet nach Server-Neustart oder Prozess-Absturz automatisch neu – die Umgebungen
  bleiben online, ohne manuellen Deploy.
- `.gitattributes`: Shell-Skripte mit LF-Zeilenenden (Linux-Kompatibilität).

## [0.5.0] – 2026-07-07

Erste zusammenhängende Version – demofähig für Interessenten.

### Infrastruktur
- Vier Umgebungen (dev/test/int/prod) auf Infomaniak, CI/CD via Jenkins
  (Tests auf Python 3.9 = Serverversion), PHP-Proxy je Subdomain, Health-Check.
- Versionierung: `VERSION`-Datei, Git-Tags `vX.Y.Z`, dieses Changelog; App und
  `/healthz` zeigen Version + Commit-SHA.

### Fachlichkeit
- **Management-Informationsmodell (MIM)** als Config (geteilter Kern + Mandanten-Override).
- **Dashboard**: Ampel-KPIs, Roll-up (worst-of) je Bereich/Einheit, Trend, Stabilität,
  Wahrheitsgehalt-Analyse abgebrochener Projekte.
- **Drilldown** auf allen Ebenen inkl. Projekt-Verlauf (Statusband, Kostenentwicklung).

### Extraktion & Quellen
- **Deterministische Extraktion** docx → kanonisches Modell mit Fundstelle + Konfidenz
  (100 % gegen Ground-Truth); Upload-Connector.
- **Ordner-Connector** (rekursiv, inhaltsbasiert) und **SharePoint/OneDrive-Connector**
  (Microsoft Graph, App-only) – je Mandant konfigurierbar.

### Mandantenfähigkeit & Benutzer
- Hierarchie **Mandant → Organisation → Projekt**; Sicht je Organisation gescopt.
- **Login** (E-Mail + Passwort, gehasht), Rollen **super_admin / mandant_admin / user**,
  Benutzerverwaltung, „PSR hochladen" je Benutzer schaltbar.

### Testdaten
- Drei Mandanten mit eigenen Datensätzen: LLV (20 Projekte), kaspAIr GmbH (10),
  Stadt Musterstadt (12).

[Unreleased]: https://github.com/kaspAir/Dashboard_Projekte/compare/v0.7.2...dev
[0.7.2]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.7.2
[0.7.1]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.7.1
[0.7.0]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.7.0
[0.6.0]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.6.0
[0.5.1]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.5.1
[0.5.0]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.5.0
