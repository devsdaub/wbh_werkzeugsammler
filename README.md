# wbh-prognosevergleich

Kleiner Sammler für die Bachelorarbeit SolarAnalytics. Er speichert jeden Abend ab 20 Uhr, was drei
frei zugängliche Werkzeuge für das Balkonkraftwerk in Stuttgart vorhersagen:

| Werkzeug | Zugang | Was gespeichert wird |
|---|---|---|
| Forecast.Solar | ohne Konto, ohne Schlüssel | Tagessumme für morgen |
| Quartz Solar Forecast (Open Climate Fix) | Python-Paket, Wetter ICON über Open-Meteo | Tagessumme für morgen aus 15-Minuten-Leistung |
| Solcast | kostenloses Hobbyist-Konto, eigener Schlüssel | Tagessummen für morgen und übermorgen mit 10. und 90. Perzentil |

Die Werte landen später neben den eigenen Prognosen im Vergleich (Kapitel 7, Stand der Technik).
Der Rechner muss dafür nicht laufen, der Container läuft auf dem NAS.

## Ergebnisdateien im Ordner `data`

- `sammlung_tageswerte.csv` mit den Spalten `stichtag, zieltag, vorlauf, werkzeug, kwh, unten_kwh, oben_kwh, abgerufen_utc`.
  `vorlauf` 1 heißt Prognose für den nächsten Tag. `unten_kwh` und `oben_kwh` füllt nur Solcast.
- `sammlung_roh.jsonl` mit der vollständigen Antwort jedes Abrufs. Die Adresse, die Forecast.Solar aus den Koordinaten
  ermittelt und mitschickt, wird vorher entfernt.
- `lebenszeichen.txt` für den Healthcheck des Containers.

Jedes Werkzeug wird pro Abend genau einmal gespeichert. Scheitert ein Abruf, folgt alle 10 Minuten ein neuer Versuch,
bei Solcast höchstens drei am Tag (das Hobbyist-Konto erlaubt 10 Abrufe am Tag).

## Auf das NAS bringen

1. Repository auf GitHub anlegen (Name `wbh-prognosevergleich`) und pushen. Die Action baut das Image und legt es
   als `ghcr.io/devsdaub/wbh-prognosevergleich:latest` ab.
2. Ein neues Paket in der GitHub Container Registry ist zunächst privat. Entweder unter GitHub → Packages →
   wbh-prognosevergleich → Package settings auf **Public** stellen (das Image enthält keine Schlüssel), oder auf dem
   NAS einmal `docker login ghcr.io` mit einem Token mit dem Recht `read:packages`.
3. In UGOS Pro: Docker → Projekt → Erstellen, Inhalt von `docker-compose.yml` einfügen, Bereitstellen.
4. Im Protokoll des Containers steht beim Start, welche Werkzeuge aktiv sind. Ab 20 Uhr folgen Zeilen wie
   `forecast_solar gespeichert: 22.10. 2.07 kWh`.

## Solcast einschalten

1. Auf toolkit.solcast.com.au ein Hobbyist-Konto anlegen und eine Rooftop Site hinzufügen:
   - Standort wie unten, Neigung (Tilt) 72°
   - Ausrichtung (Azimuth) **152**. Solcast zählt von Norden gegen den Uhrzeigersinn, Westen ist +90 und Süden 180.
     Die 208° nach Kompass (28° westlich von Süd) werden dort also zu 180 − 28 = 152. In der Kartenvorschau prüfen,
     ob der Pfeil nach Südsüdwest zeigt.
   - AC-Leistung 0,8 kW (Wechselrichter), DC-Leistung 0,9 kWp (Module)
2. Unter „Your API Key“ den Schlüssel kopieren, bei der Anlage die Resource ID.
3. Beides im Projekt auf dem NAS bei `SOLCAST_API_KEY` und `SOLCAST_RESOURCE_ID` eintragen und neu bereitstellen.
   Der Schlüssel gehört nur auf das NAS, nicht in dieses Repository.

## Einstellungen

| Variable | Standard | Bedeutung |
|---|---|---|
| `BREITE`, `LAENGE` | 48.75, 9.17 | Standort seit März 2026 |
| `NEIGUNG` | 72 | Neigung der Module in Grad |
| `AUSRICHTUNG` | 208 | nordbasiert wie in `plant.yaml`, für Forecast.Solar wird daraus 28 |
| `KWP` | 0.9 | Modulleistung |
| `ABRUF_AB_STUNDE` | 20 | ab wann abends gespeichert wird, gleiche Zeit wie das eigene Prognosearchiv |
| `FORECAST_SOLAR`, `QUARTZ` | an | mit `aus` abschalten |
| `SOLCAST_API_KEY`, `SOLCAST_RESOURCE_ID` | leer | Solcast läuft nur, wenn beide gesetzt sind |
| `INTERVALL_MINUTEN` | 10 | Abstand der Prüfungen |

## Entwicklung

```bash
pip install -r requirements-dev.txt
pytest -q
```

Die Tests prüfen die Umrechnung der drei Antwortformate in Tagessummen und die Abrufsteuerung, ohne Netz.
Quartz selbst steckt nur im Image (`requirements.txt`), weil es alte Versionen von numpy, scikit-learn und XGBoost
verlangt. Im Image wird der Zwischenspeicher von requests-cache durch eine normale Session ersetzt, sonst bricht
Quartz an einem Versionskonflikt ab.
