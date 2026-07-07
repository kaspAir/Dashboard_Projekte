# -*- coding: utf-8 -*-
"""Test-Projekte für den Mandanten kaspAIr GmbH (Software-/KI-Firma)."""
from psr_data import Q

PE = "Produktentwicklung"
KP = "Kundenprojekte"
BC = "Betrieb & Cloud"

PROJECTS = [
    Q("HermesPIA", "HERMES PIA Weiterentwicklung", "K-2024-001", "A. Vogel", "Geschäftsleitung",
      "Team KI/ML", PE, (2024, 3), 30, "active", "stabil", [],
      420000, 900, ("Produkt", "PIA-Generierung für weitere Methoden/Projekttypen"),
      ["Modellkosten steigen", "Pflege der Vorlagen aufwändig"]),

    Q("ProS", "Prozess-Simulator ProS", "K-2024-002", "B. Meier", "Geschäftsleitung",
      "Team Plattform", PE, (2024, 1), 28, "active", "volatil", ["termine"],
      380000, 760, ("Produkt", "Simulation komplexer Prozessabläufe"),
      ["Performance bei grossen Modellen", "Browser-Kompatibilität"]),

    Q("Dashboard", "Projekt-Dashboard", "K-2025-003", "C. Frei", "Geschäftsleitung",
      "Team Plattform", PE, (2025, 6), 12, "active", "stabil", [],
      90000, 220, ("Produkt", "Mandantenfähiges PSR-Dashboard"),
      ["SharePoint-Zugänge je Kunde", "Skalierung über viele Mandanten"]),

    Q("BankKredit", "Bank X – Kreditentscheid-Automatisierung", "K-2024-010", "D. Suter", "Bank X",
      "Team Data", KP, (2024, 5), 20, "active", "gelb_stabil", ["kosten"],
      650000, 540, ("Kunde", "Automatisierter, nachvollziehbarer Kreditentscheid"),
      ["Regulatorische Anforderungen", "Datenqualität Altbestand"]),

    Q("CloudMigration", "Cloud-Migration Infrastruktur", "K-2024-004", "E. Kern", "Geschäftsleitung",
      "Team Cloud", BC, (2024, 2), 16, "completed", "solide", [],
      210000, 300, ("Betrieb", "Workloads in die Cloud überführen"),
      ["Ausfallfenster knapp", "Kostenkontrolle Cloud"]),

    Q("RAG", "RAG-Wissensdatenbank", "K-2024-006", "F. Baumann", "Geschäftsleitung",
      "Team KI/ML", PE, (2024, 9), 18, "active", "erholung", ["ergebnisse"],
      260000, 480, ("Produkt", "Grounding der Antworten auf freigegebenem Wissen"),
      ["Qualität der Quellen", "Embedding-Kosten"]),

    Q("SchadenKI", "Versicherung Y – Schadenfall-Triage", "K-2024-011", "G. Roth", "Versicherung Y",
      "Team KI/ML", KP, (2024, 4), 24, "active", "verschlechterung", ["kosten", "ergebnisse"],
      720000, 620, ("Kunde", "Automatische Ersteinschätzung von Schadenfällen"),
      ["Trefferquote unter Zielwert", "Aufwand Datenaufbereitung"]),

    Q("SecAudit", "Sicherheits-Audit & Härtung", "K-2025-005", "H. Weber", "Geschäftsleitung",
      "Team Cloud", BC, (2025, 1), 8, "completed", "stabil", [],
      120000, 150, ("Betrieb", "Härtung gemäss Audit-Empfehlungen"),
      ["Restrisiken Alt-Komponenten", "Zeitfenster für Umbau"]),

    Q("MobileApp", "Mobile App Relaunch", "K-2023-020", "I. Lang", "Geschäftsleitung",
      "Team Frontend", PE, (2023, 11), 22, "aborted", "gescheitert_frueh", ["termine", "ergebnisse"],
      300000, 520, ("Produkt", "Neue mobile App auf Cross-Plattform-Basis"),
      ["Framework unausgereift", "Ressourcen abgezogen"]),

    Q("DataPipeline", "Kunde Z – Datenpipeline-Automatisierung", "K-2025-012", "J. Arnold", "Kunde Z",
      "Team Data", KP, (2025, 2), 16, "active", "stabil", [],
      340000, 430, ("Kunde", "End-to-end automatisierte Datenaufbereitung"),
      ["Schnittstellen-Stabilität", "Monitoring der Pipeline"]),
]
