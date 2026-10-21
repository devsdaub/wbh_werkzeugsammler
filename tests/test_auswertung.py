from datetime import date

import pandas as pd
import pytest

from auswertung import forecast_solar_tage, leistung_zu_tagen, ohne_adresse, solcast_tage


def test_forecast_solar_nur_tage_nach_dem_stichtag():
    antwort = {"result": {"watt_hours_day": {"2026-10-21": 1800, "2026-10-22": 2162}}}

    tage = forecast_solar_tage(antwort, date(2026, 10, 21))

    assert tage == {date(2026, 10, 22): (2.162, None, None)}


def test_adresse_wird_nicht_gespeichert():
    antwort = {"message": {"info": {"place": "Musterstraße 1", "latitude": 48.75}}}

    assert "place" not in ohne_adresse(antwort)["message"]["info"]


def solcast_perioden(tag: str, kw: float) -> list[dict]:
    enden = pd.date_range(f"{tag} 00:30", periods=48, freq="30min", tz="Europe/Berlin").tz_convert("UTC")
    return [{"period_end": e.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"), "period": "PT30M",
             "pv_estimate": kw, "pv_estimate10": kw / 2, "pv_estimate90": kw * 2} for e in enden]


def test_solcast_summiert_halbe_stunden_zum_lokalen_tag():
    tage = solcast_tage(solcast_perioden("2026-10-22", 0.1), date(2026, 10, 21))

    kwh, unten, oben = tage[date(2026, 10, 22)]
    assert kwh == pytest.approx(2.4)
    assert unten == pytest.approx(1.2)
    assert oben == pytest.approx(4.8)


def test_solcast_angebrochene_tage_fallen_weg():
    perioden = solcast_perioden("2026-10-22", 0.1)[:20]

    assert solcast_tage(perioden, date(2026, 10, 21)) == {}


def test_quartz_viertelstunden_ergeben_tagessummen():
    zeit = pd.date_range("2026-10-21 18:00", periods=192, freq="15min")
    leistung = pd.Series(0.2, index=zeit)

    tage = leistung_zu_tagen(leistung, date(2026, 10, 21))

    assert list(tage) == [date(2026, 10, 22)]
    assert tage[date(2026, 10, 22)][0] == pytest.approx(4.8)
