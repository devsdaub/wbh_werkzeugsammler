from pathlib import Path

import pandas as pd

SPALTEN = ["stichtag", "zieltag", "vorlauf", "werkzeug", "kwh", "unten_kwh", "oben_kwh", "abgerufen_utc"]
WERKZEUGE = ["forecast_solar", "quartz_icon", "solcast"]
EIGENES = "solaranalytics"

# Spalten aus dem Rückblick vom 14.10.2026, Quartz gegen die eigenen Verfahren
RUECKBLICK = {
    "quartz_kwh": "Quartz",
    "faustregel_nachgefuehrt_vorhersage": "SolarAnalytics, Faustregel für morgen",
    "faustregel_nachgefuehrt_rueckblick": "SolarAnalytics, Faustregel im Nachhinein",
    "random_forest_nachgefuehrt_vorhersage": "SolarAnalytics, Random Forest für morgen",
}


def lade_sammlung(datei: Path) -> pd.DataFrame:
    if not datei.exists():
        return pd.DataFrame(columns=SPALTEN)
    return pd.read_csv(datei, dtype={"stichtag": str, "zieltag": str, "werkzeug": str})


def tabelle_fuer_morgen(sammlung: pd.DataFrame, verlauf: list[dict] | None) -> pd.DataFrame:
    """Je Zieltag die Prognosen vom Vorabend aller Werkzeuge neben Messung und eigener Prognose."""
    morgen = sammlung[sammlung["vorlauf"].astype(int) == 1] if len(sammlung) else sammlung
    breit = (morgen.pivot_table(index="zieltag", columns="werkzeug", values="kwh", aggfunc="last")
             if len(morgen) else pd.DataFrame(index=pd.Index([], name="zieltag")))
    breit = breit.reindex(columns=WERKZEUGE)
    eigen = pd.DataFrame(verlauf or [], columns=["datum", "ist", "p1"])
    eigen = eigen.rename(columns={"datum": "zieltag", "p1": EIGENES}).set_index("zieltag")
    tabelle = breit.join(eigen, how="left")
    return tabelle[["ist", EIGENES, *WERKZEUGE]].sort_index()


def kennzahlen(tabelle: pd.DataFrame, spalten: list[str], ist: str = "ist") -> dict:
    """MAE, Bias und nMAE je Spalte, nur auf Tagen, an denen alle Spalten und die Messung vorliegen."""
    gemeinsam = tabelle.dropna(subset=[ist, *spalten])
    if gemeinsam.empty:
        return {"tage": 0, "von": None, "bis": None, "werte": []}
    mittel = float(gemeinsam[ist].mean())
    werte = []
    for spalte in spalten:
        fehler = gemeinsam[spalte].astype(float) - gemeinsam[ist].astype(float)
        mae = float(fehler.abs().mean())
        werte.append({
            "spalte": spalte,
            "mae": round(mae, 3),
            # positiv bedeutet, das Werkzeug sagt im Mittel zu viel vorher
            "bias": round(float(fehler.mean()), 3),
            "nmae_prozent": round(100 * mae / mittel, 1) if mittel else None,
        })
    return {"tage": int(len(gemeinsam)), "von": str(gemeinsam.index.min()), "bis": str(gemeinsam.index.max()),
            "werte": sorted(werte, key=lambda w: w["mae"])}


def mit_daten(tabelle: pd.DataFrame) -> list[str]:
    return [spalte for spalte in [EIGENES, *WERKZEUGE] if tabelle[spalte].notna().any()]


def lade_rueckblick(datei: Path) -> dict | None:
    """Der einmalige Rückblick über 57 Tage, falls die Datei im Datenordner liegt."""
    if not datei.exists():
        return None
    frame = pd.read_csv(datei).set_index("date")
    spalten = [s for s in RUECKBLICK if s in frame.columns]
    ergebnis = kennzahlen(frame, spalten)
    for wert in ergebnis["werte"]:
        wert["name"] = RUECKBLICK[wert["spalte"]]
    return ergebnis
