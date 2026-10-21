# wbh_werkzeugsammler

Sammler und Vergleichsseite für die Bachelorarbeit SolarAnalytics. Er speichert jeden Abend ab 20 Uhr, was drei
frei zugängliche Werkzeuge für das Balkonkraftwerk in Stuttgart vorhersagen, und stellt sie auf einer kleinen
Oberfläche der eigenen Prognose und der Messung gegenüber:

| Werkzeug | Zugang | Was gespeichert wird |
|---|---|---|
| Forecast.Solar | ohne Konto, ohne Schlüssel | Tagessumme für morgen |
| Quartz Solar Forecast (Open Climate Fix) | Python-Paket, Wetter ICON über Open-Meteo | Tagessumme für morgen aus 15-Minuten-Leistung |
| Solcast | kostenloses Hobbyist-Konto, eigener Schlüssel | Tagessummen für morgen und übermorgen mit 10. und 90. Perzentil |

Die Werte dienen dem Vergleich mit dem Stand der Technik in der Arbeit (Kapitel 3 und 7). Der Container läuft auf
dem NAS, der Rechner muss dafür nicht an sein.

## Oberfläche

Unter `http://<ip-des-nas>:8011`, im selben Stil wie SolarAnalytics:

- Kacheln mit gesammelten Abenden, Tagen mit Messung, letztem Abruf und aktiven Werkzeugen
- Prognose für morgen je Werkzeug neben der SolarAnalytics-Prognose und der Messung, Tag für Tag
- „So weit liegen die Werkzeuge im Mittel daneben“: MAE, Bias und Anteil am Tagesertrag, nur auf Tagen, an denen
  alle Werkzeuge und die Messung vorliegen
- Rückblick Quartz gegen SolarAnalytics über 57 Tage vom 14.10.2026, falls `rueckblick_quartz.csv` im Datenordner liegt
- die Werkzeuge im Überblick als Steckbrief zur Abgrenzung
- die zuletzt gesammelten Rohwerte

Messwerte und eigene Prognosen kennt der Sammler nicht selbst. Er holt sie bei jedem Aufruf der Seite aus der
SolarAnalytics-Instanz (`SOLARANALYTICS_URL`, Endpunkt `/api/analytics/verlauf`). Ohne diese Adresse zeigt die Seite
nur die Werkzeuge. Die Daten der Seite gibt es auch als JSON unter `/api/daten`.

## Ergebnisdateien im Ordner `data`

- `sammlung_tageswerte.csv` mit den Spalten `stichtag, zieltag, vorlauf, werkzeug, kwh, unten_kwh, oben_kwh, abgerufen_utc`.
  `vorlauf` 1 heißt Prognose für den nächsten Tag. `unten_kwh` und `oben_kwh` füllt nur Solcast.
- `sammlung_roh.jsonl` mit der vollständigen Antwort jedes Abrufs. Die Adresse, die Forecast.Solar aus den Koordinaten
  ermittelt und mitschickt, wird vorher entfernt.
- `rueckblick_quartz.csv`, optional, der einmalige Rückblick vom 14.10.2026.
- `lebenszeichen.txt` für den Healthcheck des Containers.

Jedes Werkzeug wird pro Abend genau einmal gespeichert. Scheitert ein Abruf, folgt alle 10 Minuten ein neuer Versuch,
bei Solcast höchstens drei am Tag (das Hobbyist-Konto erlaubt 10 Abrufe am Tag).

## Auf das NAS bringen

1. Jeder Push auf `main` startet die Action unter `.github/workflows/docker-publish.yml`. Sie testet, baut das Image und
   legt es als `ghcr.io/devsdaub/wbh-werkzeugsammler:latest` ab, dazu ein Tag `sha-xxxxxxx` je Commit.
2. Auf dem NAS den Ordner `docker/werkzeugsammler/data` anlegen. Die bisher auf dem PC gesammelten Abende und den
   Rückblick vorher hineinkopieren: `sammlung_tageswerte.csv` und `rueckblick_quartz.csv` aus
   `wbh_solaranalytics_extras/werkzeugtests_2026-10-14/fuer_nas`.
3. In UGOS Pro: Docker → Projekt → Erstellen, Ordner `docker/werkzeugsammler`, Inhalt von `docker-compose.yml`
   einfügen, Bereitstellen. Ist das Paket privat, braucht das NAS den Registry-Zugang mit einem Token mit
   `read:packages`, derselbe wie für SolarAnalytics.
4. Im Protokoll des Containers steht beim Start, welche Werkzeuge aktiv sind. Ab 20 Uhr folgen Zeilen wie
   `forecast_solar gespeichert: 22.10. 2.07 kWh`.
5. Sobald das NAS sammelt, den alten Container `werkzeugsammler` auf dem PC anhalten, sonst wird doppelt gesammelt.

## Solcast einschalten

1. Auf toolkit.solcast.com.au ein Hobbyist-Konto anlegen und eine Rooftop Site hinzufügen:
   - Standort wie unten, Neigung (Tilt) 72°
   - Ausrichtung (Azimuth) **152**. Solcast zählt von Norden gegen den Uhrzeigersinn, Westen ist +90 und Süden 180.
     Die 208° nach Kompass (28° westlich von Süd) werden dort also zu 180 − 28 = 152. In der Kartenvorschau prüfen,
     ob der Pfeil nach Südsüdwest zeigt.
   - AC-Leistung 0,8 kW (Wechselrichter), DC-Leistung 0,9 kWp (Module)
2. Neue Hobby-Konten schaltet Solcast erst nach einer Prüfung frei („Your account requires verification by our team“).
3. Unter „Your API Key“ den Schlüssel kopieren, bei der Anlage die Resource ID.
4. Beides im Projekt auf dem NAS bei `SOLCAST_API_KEY` und `SOLCAST_RESOURCE_ID` eintragen und neu bereitstellen.
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
| `SOLARANALYTICS_URL` | leer | Adresse der SolarAnalytics-Instanz für Messung und eigene Prognose |
| `SAMMLER` | an | mit `aus` nur die Oberfläche, ohne Abrufe |

## Entwicklung

```bash
pip install -r requirements-dev.txt
pytest -q
```

Die Tests prüfen die Umrechnung der drei Antwortformate in Tagessummen, die Abrufsteuerung, die Vergleichstabelle
mit den Kennzahlen und die Oberfläche, alles ohne Netz. Quartz selbst steckt nur im Image (`requirements.txt`),
weil es alte Versionen von numpy, scikit-learn und XGBoost verlangt. Im Image wird der Zwischenspeicher von
requests-cache durch eine normale Session ersetzt, sonst bricht Quartz an einem Versionskonflikt ab.
