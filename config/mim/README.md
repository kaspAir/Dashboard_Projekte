# Management-Informationsmodell (MIM)

Das MIM ist das **zentrale Konfigurations-Artefakt** des Projekt-Dashboards. Es
beschreibt, *welche Managementinformation relevant ist* – und **eine** Definition
steuert damit gleich zwei Dinge:

- **Extraktion** – `description` und `values_ref` sagen der Extraktion, *was* sie
  im Bericht finden soll und *wie* Freitext auf kanonische Werte abzubilden ist.
- **Darstellung** – `display` und `aggregation` bestimmen, *was* das Dashboard
  zeigt, *wie* und *wie es hochrollt*.

Das MIM ist **generisch** und **nicht** an eine bestimmte Organisation gebunden.

## Geteilter Kern + Mandanten-Overlay

- **`mim.default.yaml`** – kanonischer Standard mit stabilen Feld-IDs. Über
  Mandanten hinweg vergleichbar.
- **`mim.<mandant>.yaml`** – Overlay je Mandant. `extends: default`, dann:
  - `hide:` – Felder **kürzen**
  - `override:` – **umbenennen / umsortieren / Einheit ändern** (IDs bleiben stabil)
  - `add:` – mandanteneigene Felder **erweitern**

Beispiel siehe [`mim.example-kompakt.yaml`](mim.example-kompakt.yaml) (generisch).

## Anatomie eines Feldes

| Facette | Zweck | Treibt |
|---|---|---|
| `id` | stabiler kanonischer Schlüssel | alles |
| `label` | menschliche Beschriftung | Darstellung |
| `type` | rag / metric / text / date / list / trend / percent | Modell + Darstellung |
| `description` | *was bedeutet das Feld* | **Extraktion** |
| `values_ref` | kontrolliertes Vokabular (+ Synonyme) | **Extraktion** |
| `with_explanation` | Freitext-Begründung mitextrahieren | Extraktion/Darstellung |
| `aggregation` | Roll-up-Regel (`worst_of`, `sum`, …) | Aggregation/Granularität |
| `source` | `extracted` (Default) oder `derived` | Herkunft |
| `display` | Darstellungsform + Reihenfolge | Darstellung |

## Grundsätze

- **Provenienz statt Halluzination:** Jeder extrahierte Wert trägt später
  Fundstelle + Konfidenz; bei Unsicherheit bleibt das Feld leer statt geraten.
- **Abgeleitete Felder** (`source: derived`, z. B. `trend_overall`) werden aus den
  historisierten Snapshots berechnet, nicht aus dem Bericht extrahiert.

## Lebenszyklus, Trends & Verlässlichkeit

Jedes Projekt liefert über die Zeit **monatliche Snapshots** (Ende Monat). Daraus
entstehen:

- **`trend_overall`** – Richtung des Gesamtstatus über die letzten Perioden.
- **`trend_stability`** – Volatilität: ein Projekt, das grün↔rot flackert, ist
  *schwankend* gemeldet (geringes Vertrauen); ein stetiges ist *stabil*.
- **Verlässlichkeit / Wahrheitsgehalt** – über `lifecycle_state: completed | aborted`
  lässt sich prüfen, ob die Ampeln ehrlich waren (wurde ein Projekt bis kurz vor dem
  Abbruch grün gemeldet?). Das bewertet die *Qualität der Berichterstattung* je
  Organisationseinheit – ein Führungsinstrument, keine reine Projektsicht.

Das Dashboard zeigt per `scope.default_filter` nur **aktive** Projekte; inaktive
speisen die obigen Analysen.
