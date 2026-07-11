# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[SemVer](https://semver.org/lang/de/).

## [Unreleased]

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

[Unreleased]: https://github.com/kaspAir/Dashboard_Projekte/compare/v0.5.0...dev
[0.5.0]: https://github.com/kaspAir/Dashboard_Projekte/releases/tag/v0.5.0
