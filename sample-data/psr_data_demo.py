# -*- coding: utf-8 -*-
"""Test-Projekte für den Demo-Mandanten Stadt Musterstadt (fiktive Gemeinde)."""
from psr_data import Q

FIN = "Ressort Finanzen"
BAU = "Ressort Bau & Umwelt"
BIL = "Ressort Bildung"
SOZ = "Ressort Soziales & Gesundheit"
SIC = "Ressort Sicherheit"

PROJECTS = [
    Q("Buergerportal", "Bürgerportal Musterstadt", "M-2023-001", "P. Ackermann", "Stadtrat",
      "IT-Abteilung", FIN, (2023, 9), 32, "active", "volatil", ["termine"],
      780000, 620, ("Zugang", "Ein Login für alle städtischen Dienste"),
      ["Abhängigkeit von eID", "viele Fachverfahren anzubinden"]),

    Q("Baugenehmigung", "Digitale Baugenehmigung", "M-2024-002", "R. Hofer", "Ressortleitung Bau",
      "Bauamt", BAU, (2024, 6), 22, "active", "stabil", [],
      460000, 360, ("Effizienz", "Baugesuche medienbruchfrei bearbeiten"),
      ["Datenübernahme Altsystem", "Akzeptanz Sachbearbeitung"]),

    Q("SchulWLAN", "Schul-WLAN-Ausbau", "M-2024-003", "S. Brunner", "Ressortleitung Bildung",
      "Schulamt", BIL, (2024, 2), 15, "completed", "solide", [],
      320000, 180, ("Infrastruktur", "Flächendeckendes WLAN an allen Schulen"),
      ["Lieferzeiten Hardware", "bauliche Gegebenheiten"]),

    Q("ERechnung", "E-Rechnung Stadtkasse", "M-2024-004", "T. Widmer", "Ressortleitung Finanzen",
      "Stadtkasse", FIN, (2024, 8), 18, "active", "gelb_stabil", ["kosten"],
      240000, 190, ("Automatisierung", "Rechnungen automatisiert verarbeiten"),
      ["Erkennungsrate Sonderformate", "Lizenzkosten"]),

    Q("SozialPortal", "Sozialhilfe-Portal", "M-2024-005", "U. Graf", "Ressortleitung Soziales",
      "Sozialamt", SOZ, (2024, 10), 20, "active", "erholung", ["termine"],
      410000, 300, ("Servicequalität", "Anträge und Fallmanagement digital"),
      ["Datenschutz sensible Daten", "Fachbereich knapp verfügbar"]),

    Q("Verkehrsleit", "Verkehrsleitsystem", "M-2024-006", "V. Moser", "Ressortleitung Bau",
      "Bauamt", BAU, (2024, 1), 30, "active", "verschlechterung", ["kosten", "ergebnisse"],
      920000, 540, ("Verkehrsfluss", "Stauzeiten auf Hauptachsen senken"),
      ["Bewilligungen verzögern", "Budgetnachtrag nötig"]),

    Q("Einwohnerregister", "Einwohnerregister-Ablösung", "M-2022-007", "W. Steiner", "Stadtrat",
      "Einwohneramt", SIC, (2023, 3), 30, "aborted", "gescheitert_spaet", ["kosten", "termine"],
      1100000, 700, ("Datenqualität", "Fehlerfreie Migration der Personendaten"),
      ["Migration scheitert wiederholt", "Betrieb Altsystem verlängert"]),

    Q("Einsatzapp", "Stadtpolizei-Einsatzapp", "M-2024-008", "X. Keller", "Ressortleitung Sicherheit",
      "Stadtpolizei", SIC, (2024, 8), 22, "active", "gelb_stabil", ["projektrisiken"],
      560000, 360, ("Reaktionszeit", "Einsätze mobil koordinieren"),
      ["Funkschnittstelle", "24/7-Betriebsanforderungen"]),

    Q("Umweltsensorik", "Umwelt-Sensornetz", "M-2024-009", "Y. Lehmann", "Ressortleitung Bau",
      "Bauamt", BAU, (2024, 6), 18, "completed", "solide", [],
      240000, 160, ("Umweltschutz", "Luft- und Lärmwerte kontinuierlich messen"),
      ["Kalibrierung witterungsabhängig", "Standortzugang"]),

    Q("Ratsinfo", "Digitales Ratsinformationssystem", "M-2025-010", "Z. Frei", "Stadtschreiberei",
      "IT-Abteilung", FIN, (2025, 3), 14, "active", "stabil", [],
      180000, 150, ("Transparenz", "Sitzungen und Beschlüsse digital verfügbar"),
      ["Migration Altprotokolle", "Rechteverwaltung"]),

    Q("BiblioCloud", "Bibliotheks-Cloud", "M-2025-011", "A. Bucher", "Ressortleitung Bildung",
      "Schulamt", BIL, (2025, 4), 12, "active", "stabil", [],
      150000, 120, ("Service", "Digitale Ausleihe und Medienkatalog"),
      ["Anbindung Verbundkatalog", "Nutzerakzeptanz"]),

    Q("GesundheitTermin", "Gesundheitsamt-Terminsystem", "M-2024-012", "B. Küng", "Ressortleitung Soziales",
      "Sozialamt", SOZ, (2024, 9), 12, "completed", "stabil", [],
      160000, 140, ("Servicequalität", "Online-Termine für Beratungen"),
      ["Anbindung Praxissysteme", "geringe Nutzung anfangs"]),
]
