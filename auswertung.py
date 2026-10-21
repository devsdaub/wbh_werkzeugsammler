from datetime import date
from zoneinfo import ZoneInfo

import pandas as pd

LOKAL = ZoneInfo("Europe/Berlin")
MIN_STUNDEN = 23


def forecast_solar_tage(antwort: dict, stichtag: date) -> dict[date, tuple[float, None, None]]:
    """Tagessummen aus der Antwort von Forecast.Solar, nur Tage nach dem Stichtag."""
    tage = antwort["result"]["watt_hours_day"]
    return {
        date.fromisoformat(tag): (wh / 1000, None, None)
        for tag, wh in tage.items()
        if date.fromisoformat(tag) > stichtag
    }


def ohne_adresse(antwort: dict) -> dict:
    # Forecast.Solar meldet eine aus den Koordinaten ermittelte Adresse zurück, die wird nicht gespeichert
    antwort.get("message", {}).get("info", {}).pop("place", None)
    return antwort


def solcast_tage(perioden: list[dict], stichtag: date) -> dict[date, tuple[float, float, float]]:
    """Tagessummen aus den 30-Minuten-Werten von Solcast, mit 10. und 90. Perzentil."""
    summen: dict[date, list[float]] = {}
    for periode in perioden:
        ende = pd.Timestamp(periode["period_end"]).tz_convert("UTC")
        stunden = pd.Timedelta(periode.get("period", "PT30M")).total_seconds() / 3600
        # die Mitte der Periode entscheidet über den Tag, nicht ihr Ende kurz nach Mitternacht
        mitte = (ende - pd.Timedelta(hours=stunden / 2)).tz_convert(LOKAL).date()
        werte = summen.setdefault(mitte, [0.0, 0.0, 0.0, 0.0])
        werte[0] += periode["pv_estimate"] * stunden
        werte[1] += periode.get("pv_estimate10", periode["pv_estimate"]) * stunden
        werte[2] += periode.get("pv_estimate90", periode["pv_estimate"]) * stunden
        werte[3] += stunden
    return {
        tag: (werte[0], werte[1], werte[2])
        for tag, werte in summen.items()
        if tag > stichtag and werte[3] >= MIN_STUNDEN
    }


def leistung_zu_tagen(leistung_kw: pd.Series, stichtag: date) -> dict[date, tuple[float, None, None]]:
    """Tagessummen aus einer Leistungsreihe mit UTC-Zeitstempeln, etwa aus Quartz."""
    zeit = pd.to_datetime(leistung_kw.index)
    reihe = pd.Series(leistung_kw.to_numpy(dtype=float),
                      index=zeit.tz_localize("UTC") if zeit.tz is None else zeit.tz_convert("UTC"))
    schritt = (reihe.index[1] - reihe.index[0]).total_seconds() / 3600
    lokal = reihe.tz_convert(LOKAL)
    tage = {}
    for tag, werte in lokal.groupby(lokal.index.date):
        if tag > stichtag and len(werte) * schritt >= MIN_STUNDEN:
            tage[tag] = (float(werte.sum() * schritt), None, None)
    return tage
