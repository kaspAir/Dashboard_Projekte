# -*- coding: utf-8 -*-
"""Projekt-Stammdaten fuer die Zeitreihen-Simulation der PSR (fiktiv, LLV-nah).

Je Projekt werden monatliche PSR-Snapshots erzeugt (siehe generate_psr.py).
Felder:
  start (Jahr,Monat), dur = geplante Laufzeit in Monaten,
  lifecycle: active | completed | aborted,
  arch (Archetyp der Ampel-Entwicklung):
    stabil, solide, gelb_stabil, erholung, verschlechterung, volatil,
    gescheitert_frueh (ehrlich gewarnt), gescheitert_spaet (spät gewarnt),
  weak: Bereiche, die die Probleme treiben.
"""

MPF = "Ministerium für Präsidiales und Finanzen"
MIWU = "Ministerium für Inneres, Wirtschaft und Umwelt"
MGK = "Ministerium für Gesellschaft und Kultur"
MIJ = "Ministerium für Infrastruktur und Justiz"
MABS = "Ministerium für Äusseres, Bildung und Sport"


def Q(short, name, nummer, pl, ag, ve, gb, start, dur, lifecycle, arch, weak, cost, eff, ziel, risks):
    return dict(short=short, name=name, nummer=nummer, pl=pl, ag=ag, ve=ve, gb=gb,
                start=start, dur=dur, lifecycle=lifecycle, arch=arch, weak=weak,
                cost_plan=cost, eff_plan=eff, ziel=ziel, risks=risks)


PROJECTS = [
    Q("Baubewilligung", "Digitale Baubewilligung", "P-2024-018", "M. Frick", "R. Büchel",
      "Amt für Bau und Infrastruktur", MIJ, (2024, 6), 22, "active", "stabil", ["termine"],
      480000, 360, ("Effizienz", "Durchlaufzeit Baugesuch von 40 auf 20 Tage"),
      ["Verzögerte Datenübernahme aus Altsystem", "Akzeptanz bei Sachbearbeitenden"]),

    Q("ESteuer", "E-Steuererklärung 2.0", "P-2023-047", "S. Kaufmann", "D. Oehri",
      "Steuerverwaltung", MPF, (2024, 2), 30, "active", "volatil", ["kosten"],
      650000, 420, ("Servicequalität", "80% der Steuererklärungen digital eingereicht"),
      ["Lizenzkosten steigen", "Schnittstelle zu Bundessystem instabil"]),

    Q("EPatientenakte", "Elektronische Patientenakte", "P-2023-012", "B. Marxer", "C. Hasler",
      "Amt für Gesundheit", MGK, (2023, 5), 30, "aborted", "gescheitert_frueh", ["termine", "personalaufwand"],
      1200000, 900, ("Interoperabilität", "Anbindung an nationale eHealth-Plattform"),
      ["Datenschutzauflagen erzwingen Redesign", "Ressourcenengpass hält an"]),

    Q("Netzwerk", "Netzwerk-Modernisierung LLV", "P-2023-033", "T. Nigg", "P. Real",
      "Amt für Informatik", MPF, (2023, 8), 23, "completed", "solide", [],
      820000, 300, ("Verfügbarkeit", "Netzverfügbarkeit auf 99.9% erhöhen"),
      ["Ausfallfenster für Migration knapp", "Altgeräte-Abkündigung"]),

    Q("Grundbuch", "Digitales Grundbuch", "P-2024-031", "A. Vogt", "M. Beck",
      "Grundbuch- und Öffentlichkeitsregisteramt", MIJ, (2024, 9), 20, "active", "erholung", ["termine"],
      540000, 410, ("Rechtssicherheit", "Medienbruchfreie Eintragungen"),
      ["Gesetzliche Grundlage ändert sich", "Zulieferungen Rechtsdienst verspätet"]),

    Q("SchulCloud", "Schul-Cloud Liechtenstein", "P-2024-021", "L. Ospelt", "K. Gassner",
      "Schulamt", MABS, (2024, 4), 26, "active", "stabil", [],
      380000, 280, ("Nutzung", "Alle Sekundarschulen angebunden"),
      ["Datenschutz Schülerdaten", "Support-Aufwand höher als geplant"]),

    Q("Auslaenderregister", "Ausländerregister-Ablösung", "P-2023-054", "R. Kind", "S. Quaderer",
      "Ausländer- und Passamt", MIWU, (2023, 9), 26, "aborted", "gescheitert_frueh", ["termine", "ergebnisse"],
      950000, 700, ("Datenqualität", "Fehlerfreie Migration Personendaten"),
      ["Produktivmigration scheitert erneut", "Betrieb Altsystem länger nötig"]),

    Q("Umweltmonitoring", "Umwelt-Monitoring-Plattform", "P-2024-009", "N. Büchel", "F. Batliner",
      "Amt für Umwelt", MIWU, (2024, 10), 18, "active", "solide", ["projektrisiken"],
      300000, 240, ("Transparenz", "Echtzeitdaten öffentlich verfügbar"),
      ["Lieferverzug Sensoren", "Kalibrierung witterungsabhängig"]),

    Q("Einsatzleit", "Polizei-Einsatzleitsystem", "P-2023-020", "D. Hoop", "W. Seger",
      "Landespolizei", MIJ, (2023, 12), 30, "active", "volatil", ["termine"],
      1100000, 620, ("Reaktionszeit", "Alarmierungszeit unter 60 Sekunden"),
      ["Funkschnittstelle inkompatibel", "24/7-Betriebsanforderungen unklar"]),

    Q("Sozialhilfe", "Sozialhilfe-Fallmanagement", "P-2025-014", "E. Wolff", "G. Marock",
      "Amt für Soziale Dienste", MGK, (2025, 1), 16, "active", "stabil", [],
      420000, 300, ("Effizienz", "Fallbearbeitungszeit -25%"),
      ["Datenschutz sensible Sozialdaten", "Fachbereich knapp verfügbar"]),

    Q("OpenData", "Statistikportal Open Data", "P-2025-027", "H. Meier", "I. Frommelt",
      "Amt für Statistik", MPF, (2025, 2), 12, "completed", "solide", [],
      210000, 150, ("Offenheit", "100 Datensätze als Open Data"),
      ["Nachfrage bindet Ressourcen", "Datenfreigaben verzögert"]),

    Q("Buergerkonto", "E-Government-Portal Bürgerkonto", "P-2023-005", "P. Ritter", "V. Gstöhl",
      "Amt für Informatik", MPF, (2023, 7), 34, "active", "volatil", ["termine", "projektrisiken"],
      1800000, 1200, ("Zugang", "Ein Login für alle Behördendienste"),
      ["eID nicht rechtzeitig verfügbar", "Fachverfahren liefern Schnittstellen spät"]),

    Q("Rechnung", "Digitale Rechnungsverarbeitung", "P-2024-030", "C. Sele", "D. Oehri",
      "Steuerverwaltung", MPF, (2024, 9), 15, "completed", "stabil", [],
      260000, 190, ("Automatisierung", "70% der Rechnungen dunkelverarbeitet"),
      ["Erkennungsrate bei Sonderformaten niedrig", "Change bei Fachbereich"]),

    Q("Terminplattform", "Gesundheits-Terminplattform", "P-2025-036", "M. Ender", "C. Hasler",
      "Amt für Gesundheit", MGK, (2025, 4), 14, "active", "stabil", [],
      180000, 150, ("Servicequalität", "Online-Terminbuchung für Impfungen"),
      ["Anbindung Praxissysteme heterogen", "geringe Nutzung anfangs"]),

    Q("Verkehr", "Verkehrsmanagement-System", "P-2024-042", "R. Kaiser", "M. Beck",
      "Amt für Bau und Infrastruktur", MIJ, (2024, 3), 28, "active", "gelb_stabil", ["termine"],
      920000, 540, ("Verkehrsfluss", "Stauzeiten Hauptachsen -15%"),
      ["Bewilligungen verzögern Ausbau", "Sensorik-Lieferung knapp"]),

    Q("eAkte", "Justiz-Aktenverwaltung eAkte", "P-2024-001", "S. Wanger", "T. Ritter",
      "Amt für Justiz", MIJ, (2024, 1), 30, "active", "verschlechterung", ["kosten", "ergebnisse"],
      1400000, 950, ("Effizienz", "Aktenzugriff medienbruchfrei"),
      ["Budgetnachtrag wird nicht bewilligt", "Suchperformance ungenügend"]),

    Q("Berufsbildung", "Lernplattform Berufsbildung", "P-2025-040", "A. Nescher", "K. Gassner",
      "Schulamt", MABS, (2025, 3), 16, "active", "stabil", [],
      320000, 230, ("Lernqualität", "Digitale Lerninhalte für 10 Berufe"),
      ["Betriebe liefern Inhalte spät", "didaktische Abstimmung aufwändig"]),

    Q("Wasserqualitaet", "Wasserqualitäts-Sensorik", "P-2024-033", "F. Kindle", "F. Batliner",
      "Amt für Umwelt", MIWU, (2024, 6), 18, "completed", "solide", [],
      240000, 160, ("Umweltschutz", "Kontinuierliche Überwachung 12 Messstellen"),
      ["Kalibrierung witterungsabhängig", "Standortzugang saisonal"]),

    Q("Warnsystem", "Katastrophen-Warnsystem", "P-2024-058", "M. Gstöhl", "W. Seger",
      "Landespolizei", MIJ, (2024, 8), 22, "active", "gelb_stabil", ["projektrisiken"],
      560000, 360, ("Sicherheit", "Bevölkerungswarnung in unter 5 Minuten"),
      ["Cell-Broadcast nicht flächendeckend", "Abhängigkeit Mobilfunkbetreiber"]),

    Q("HRSystem", "HR-System Landesverwaltung", "P-2023-049", "B. Ospelt", "P. Real",
      "Amt für Informatik", MPF, (2023, 1), 32, "aborted", "gescheitert_spaet", ["kosten", "termine"],
      2200000, 1400, ("Effizienz", "Durchgängige HR-Prozesse für 1'200 Mitarbeitende"),
      ["Weitere Budgetüberschreitung", "Go-Live-Termin erneut gefährdet"]),
]
