import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import sammler
from vergleich import EIGENES, WERKZEUGE, kennzahlen, lade_rueckblick, lade_sammlung, mit_daten, tabelle_fuer_morgen

log = logging.getLogger("web")

HIER = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # der Sammler läuft als Thread im selben Container, die Oberfläche liest nur seine Dateien
    if os.environ.get("SAMMLER", "an").strip().lower() in ("an", "1", "true", "ja"):
        threading.Thread(target=sammler.laufe, args=(sammler.Einstellungen.aus_umgebung(),),
                         daemon=True, name="sammler").start()
    yield


app = FastAPI(title="Werkzeugvergleich", description="Prognosen freier Werkzeuge gegen SolarAnalytics", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=HIER / "static"), name="static")


def _solaranalytics(tage: int = 150) -> tuple[list[dict] | None, str]:
    """Messwerte und eigene Prognosen vom Vorabend aus der SolarAnalytics-Instanz."""
    adresse = os.environ.get("SOLARANALYTICS_URL", "").strip().rstrip("/")
    if not adresse:
        return None, "nicht eingestellt"
    try:
        antwort = requests.get(f"{adresse}/api/analytics/verlauf", params={"tage": tage}, timeout=20)
        antwort.raise_for_status()
        return antwort.json()["tage"], "ok"
    except Exception as fehler:
        log.warning("SolarAnalytics nicht erreichbar: %r", fehler)
        return None, f"nicht erreichbar ({type(fehler).__name__})"


def _als_liste(frame: pd.DataFrame) -> list[dict]:
    return frame.reset_index().astype(object).where(frame.reset_index().notna(), None).to_dict("records")


@app.get("/")
def startseite() -> FileResponse:
    return FileResponse(HIER / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/daten")
def daten() -> dict:
    """Alles für die Oberfläche: Sammelstand, Tabelle je Zieltag, Kennzahlen, Rückblick und Rohdaten."""
    e = sammler.Einstellungen.aus_umgebung()
    sammlung = lade_sammlung(e.daten / "sammlung_tageswerte.csv")
    verlauf, status = _solaranalytics()
    tabelle = tabelle_fuer_morgen(sammlung, verlauf)
    spalten = mit_daten(tabelle)
    lebenszeichen = e.daten / "lebenszeichen.txt"

    return {
        "anlage": {"breite": e.breite, "laenge": e.laenge, "neigung": e.neigung,
                   "ausrichtung": e.ausrichtung, "kwp": e.kwp, "ab_stunde": e.ab_stunde},
        "werkzeuge": {name: name in sammler.aktive_dienste(e) for name in WERKZEUGE},
        "solaranalytics": status,
        "abende": int(sammlung["stichtag"].nunique()) if len(sammlung) else 0,
        "letzter_abruf": str(sammlung["abgerufen_utc"].max()) if len(sammlung) else None,
        "lebenszeichen": lebenszeichen.read_text(encoding="utf-8").strip() if lebenszeichen.exists() else None,
        "tabelle": _als_liste(tabelle),
        "gemeinsam": kennzahlen(tabelle, spalten),
        "einzeln": {s: kennzahlen(tabelle, [s]) for s in spalten},
        "eigenes": EIGENES,
        "rueckblick": lade_rueckblick(e.daten / "rueckblick_quartz.csv"),
        "rohdaten": _als_liste(sammlung.sort_values("abgerufen_utc", ascending=False).head(60).set_index("stichtag"))
        if len(sammlung) else [],
    }
