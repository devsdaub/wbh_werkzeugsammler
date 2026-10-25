# wbh_werkzeugsammler

Sammler und Vergleichsseite für die Bachelorarbeit SolarAnalytics. Er speichert jeden
Abend ab 20 Uhr, was Forecast.Solar, Quartz Solar Forecast und Solcast für das
Balkonkraftwerk vorhersagen. Eine kleine Oberfläche stellt diese Werte der eigenen
Prognose und der Messung gegenüber.

## Auf dem NAS starten

GitHub Actions baut bei jedem Push auf main das Image
`ghcr.io/devsdaub/wbh-werkzeugsammler` mit den Tags `latest` und `sha-xxxxxxx`. Das NAS
zieht nur dieses Image, neue Stände spielt das NAS-Projekt `nas-autoupdate` selbst ein.

1. Auf dem NAS den Ordner `docker/werkzeugsammler/data` anlegen. Bisher gesammelte
   Abende und den Rückblick vorher hineinkopieren: `sammlung_tageswerte.csv` und
   `rueckblick_quartz.csv` aus `wbh_solaranalytics_extras/werkzeugtests_2026-10-14/fuer_nas`.
2. In UGOS Pro: Docker → Projekt → Erstellen, Ordner `docker/werkzeugsammler`, Inhalt
   von `docker-compose.yml` einfügen, Bereitstellen. Ist das Paket privat, braucht das
   NAS einen Token mit `read:packages`, derselbe wie für SolarAnalytics.
3. Im Protokoll des Containers steht beim Start, welche Werkzeuge aktiv sind. Ab 20 Uhr
   folgen Zeilen wie `forecast_solar gespeichert: 22.10. 2.07 kWh`.
4. Läuft der Sammler zusätzlich auf dem PC, dort anhalten, sonst wird doppelt gesammelt.

Die Oberfläche liegt unter `http://<ip-des-nas>:8011`. Messung und eigene Prognose holt
sie bei jedem Aufruf aus der SolarAnalytics-Instanz unter `SOLARANALYTICS_URL`, die Daten
der Seite gibt es auch als JSON unter `/api/daten`.

## Ergebnisdateien im Ordner `data`

- `sammlung_tageswerte.csv`: je Werkzeug, Stichtag und Zieltag eine Zeile,
  `unten_kwh` und `oben_kwh` füllt nur Solcast
- `sammlung_roh.jsonl`: vollständige Antwort jedes Abrufs, ohne die Adresse, die
  Forecast.Solar aus den Koordinaten ermittelt
- `rueckblick_quartz.csv`: optional, der einmalige Rückblick vom 14.10.2026
- `lebenszeichen.txt`: für den Healthcheck

Jedes Werkzeug wird pro Abend einmal gespeichert. Scheitert ein Abruf, folgt alle 10
Minuten ein neuer Versuch, bei Solcast höchstens drei am Tag.

## Solcast einschalten

1. Auf toolkit.solcast.com.au ein Hobbyist-Konto anlegen und eine Rooftop Site
   hinzufügen: Standort wie in der Tabelle unten, Neigung (Tilt) 72°, AC-Leistung 0,8 kW, DC-Leistung 0,9 kWp,
   Ausrichtung (Azimuth) **152**. Solcast zählt von Norden gegen den Uhrzeigersinn,
   aus 208° nach Kompass (28° westlich von Süd) wird also 180 − 28 = 152. In der
   Kartenvorschau prüfen, ob der Pfeil nach Südsüdwest zeigt.
2. Neue Konten schaltet Solcast erst nach einer Prüfung frei.
3. Unter „Your API Key“ den Schlüssel kopieren, bei der Anlage die Resource ID.
4. Beides im Projekt auf dem NAS bei `SOLCAST_API_KEY` und `SOLCAST_RESOURCE_ID`
   eintragen und neu bereitstellen. Der Schlüssel gehört nur auf das NAS.

## Einstellungen

| Variable | Standard | Bedeutung |
|---|---|---|
| `BREITE`, `LAENGE` | 48.75, 9.17 | Standort seit März 2026 |
| `NEIGUNG`, `AUSRICHTUNG` | 72, 208 | Grad, Ausrichtung nordbasiert wie in `plant.yaml` |
| `KWP` | 0.9 | Modulleistung |
| `ABRUF_AB_STUNDE` | 20 | ab wann abends gespeichert wird |
| `FORECAST_SOLAR`, `QUARTZ` | an | mit `aus` abschalten |
| `SOLCAST_API_KEY`, `SOLCAST_RESOURCE_ID` | leer | Solcast läuft nur, wenn beide gesetzt sind |
| `INTERVALL_MINUTEN` | 10 | Abstand der Prüfungen |
| `SOLARANALYTICS_URL` | leer | SolarAnalytics-Instanz für Messung und eigene Prognose |
| `SAMMLER` | an | mit `aus` nur die Oberfläche, ohne Abrufe |

## Entwicklung

```bash
pip install -r requirements-dev.txt
pytest -q
```

Die Tests laufen ohne Netz. Quartz selbst steckt nur im Image (`requirements.txt`), weil
es alte Versionen von numpy, scikit-learn und XGBoost verlangt.

Wetterdaten für Quartz: [Open-Meteo.com](https://open-meteo.com/), Lizenz
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
