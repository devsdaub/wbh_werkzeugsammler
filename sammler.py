import csv
import json
import logging
import os
import time
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from auswertung import LOKAL, forecast_solar_tage, leistung_zu_tagen, ohne_adresse, solcast_tage

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%d.%m. %H:%M")
log = logging.getLogger("sammler")

SPALTEN = ["stichtag", "zieltag", "vorlauf", "werkzeug", "kwh", "unten_kwh", "oben_kwh", "abgerufen_utc"]
VERSUCHE_JE_TAG = {"forecast_solar": 6, "solcast": 3, "quartz_icon": 6}


def _an(name: str, standard: str = "an") -> bool:
    return os.environ.get(name, standard).strip().lower() in ("an", "1", "true", "ja")


@dataclass(frozen=True)
class Einstellungen:
    breite: float
    laenge: float
    neigung: int
    ausrichtung: int
    kwp: float
    ab_stunde: int
    intervall_minuten: int
    daten: Path
    forecast_solar: bool
    quartz: bool
    solcast_schluessel: str
    solcast_anlage: str

    @property
    def solcast(self) -> bool:
        return bool(self.solcast_schluessel and self.solcast_anlage)

    @classmethod
    def aus_umgebung(cls) -> "Einstellungen":
        return cls(
            breite=float(os.environ.get("BREITE", "48.75")),
            laenge=float(os.environ.get("LAENGE", "9.17")),
            neigung=int(os.environ.get("NEIGUNG", "72")),
            # nordbasiert wie in plant.yaml, 180 ist Süden
            ausrichtung=int(os.environ.get("AUSRICHTUNG", "208")),
            kwp=float(os.environ.get("KWP", "0.9")),
            ab_stunde=int(os.environ.get("ABRUF_AB_STUNDE", "20")),
            intervall_minuten=int(os.environ.get("INTERVALL_MINUTEN", "10")),
            daten=Path(os.environ.get("DATEN", "/data")),
            forecast_solar=_an("FORECAST_SOLAR"),
            quartz=_an("QUARTZ"),
            solcast_schluessel=os.environ.get("SOLCAST_API_KEY", "").strip(),
            solcast_anlage=os.environ.get("SOLCAST_RESOURCE_ID", "").strip(),
        )


def hole_forecast_solar(e: Einstellungen, stichtag: date) -> tuple[dict, dict]:
    # Forecast.Solar zählt den Azimut von Süden aus, Westen positiv
    adresse = (f"https://api.forecast.solar/estimate/{e.breite}/{e.laenge}/"
               f"{e.neigung}/{e.ausrichtung - 180}/{e.kwp}")
    antwort = requests.get(adresse, timeout=60)
    antwort.raise_for_status()
    daten = ohne_adresse(antwort.json())
    return forecast_solar_tage(daten, stichtag), daten


def hole_solcast(e: Einstellungen, stichtag: date) -> tuple[dict, dict]:
    antwort = requests.get(
        f"https://api.solcast.com.au/rooftop_sites/{e.solcast_anlage}/forecasts",
        params={"format": "json", "hours": 72},
        headers={"Authorization": f"Bearer {e.solcast_schluessel}"},
        timeout=60,
    )
    antwort.raise_for_status()
    daten = antwort.json()
    return solcast_tage(daten["forecasts"], stichtag), daten


def hole_quartz(e: Einstellungen, stichtag: date) -> tuple[dict, dict]:
    import requests_cache

    # der Zwischenspeicher von requests-cache scheitert an den Versionen, die Quartz mitbringt
    class OhneZwischenspeicher(requests.Session):
        def __init__(self, *args, **kwargs):
            super().__init__()

    requests_cache.CachedSession = OhneZwischenspeicher
    from quartz_solar_forecast.forecast import run_forecast
    from quartz_solar_forecast.pydantic_models import PVSite

    anlage = PVSite(latitude=e.breite, longitude=e.laenge, capacity_kwp=e.kwp,
                    tilt=e.neigung, orientation=e.ausrichtung)
    jetzt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    vorhersage = run_forecast(site=anlage, ts=jetzt, nwp_source="icon")
    leistung = vorhersage["power_kw"]
    roh = {"ts_utc": jetzt.isoformat(), "kw": [round(float(w), 4) for w in leistung]}
    return leistung_zu_tagen(leistung, stichtag), roh


DIENSTE = {"forecast_solar": hole_forecast_solar, "solcast": hole_solcast, "quartz_icon": hole_quartz}


def aktive_dienste(e: Einstellungen) -> list[str]:
    aktiv = {"forecast_solar": e.forecast_solar, "solcast": e.solcast, "quartz_icon": e.quartz}
    return [name for name, an in aktiv.items() if an]


def schon_gesammelt(e: Einstellungen, stichtag: date, werkzeug: str) -> bool:
    datei = e.daten / "sammlung_tageswerte.csv"
    if not datei.exists():
        return False
    with datei.open(encoding="utf-8") as f:
        return any(z["stichtag"] == str(stichtag) and z["werkzeug"] == werkzeug for z in csv.DictReader(f))


def speichere(e: Einstellungen, stichtag: date, werkzeug: str, tage: dict, roh: dict) -> None:
    datei = e.daten / "sammlung_tageswerte.csv"
    neu = not datei.exists()
    abgerufen = datetime.now(timezone.utc).isoformat()
    with datei.open("a", newline="", encoding="utf-8") as f:
        schreiber = csv.writer(f)
        if neu:
            schreiber.writerow(SPALTEN)
        for zieltag, (kwh, unten, oben) in sorted(tage.items()):
            schreiber.writerow([stichtag, zieltag, (zieltag - stichtag).days, werkzeug, round(kwh, 3),
                                "" if unten is None else round(unten, 3),
                                "" if oben is None else round(oben, 3), abgerufen])
    with (e.daten / "sammlung_roh.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"stichtag": str(stichtag), "werkzeug": werkzeug, "abgerufen_utc": abgerufen, **roh}) + "\n")


def lebenszeichen(e: Einstellungen) -> None:
    (e.daten / "lebenszeichen.txt").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def runde(e: Einstellungen, versuche: dict) -> None:
    jetzt = datetime.now(LOKAL)
    if jetzt.hour < e.ab_stunde:
        return
    stichtag = jetzt.date()
    for werkzeug in aktive_dienste(e):
        schluessel = (stichtag, werkzeug)
        if schon_gesammelt(e, stichtag, werkzeug) or versuche.get(schluessel, 0) >= VERSUCHE_JE_TAG[werkzeug]:
            continue
        versuche[schluessel] = versuche.get(schluessel, 0) + 1
        try:
            tage, roh = DIENSTE[werkzeug](e, stichtag)
            if not tage:
                raise ValueError("keine vollständigen Tage in der Antwort")
            speichere(e, stichtag, werkzeug, tage, roh)
            werte = ", ".join(f"{t:%d.%m.} {w[0]:.2f} kWh" for t, w in sorted(tage.items()))
            log.info("%s gespeichert: %s", werkzeug, werte)
        except Exception as fehler:
            log.warning("%s Versuch %s fehlgeschlagen: %s", werkzeug, versuche[schluessel], repr(fehler)[:300])


def main() -> None:
    e = Einstellungen.aus_umgebung()
    e.daten.mkdir(parents=True, exist_ok=True)
    log.info("Sammler gestartet: %s, Abruf ab %s Uhr, Anlage %s°/%s°, %s kWp",
             ", ".join(aktive_dienste(e)) or "kein Dienst aktiv", e.ab_stunde, e.neigung, e.ausrichtung, e.kwp)
    if not e.solcast:
        log.info("Solcast aus: SOLCAST_API_KEY und SOLCAST_RESOURCE_ID setzen, um es einzuschalten")
    versuche: dict = {}
    while True:
        try:
            runde(e, versuche)
        except Exception:
            log.exception("Runde fehlgeschlagen")
        lebenszeichen(e)
        time.sleep(e.intervall_minuten * 60)


if __name__ == "__main__":
    main()
