import pandas as pd
import pytest

from vergleich import EIGENES, kennzahlen, lade_rueckblick, mit_daten, tabelle_fuer_morgen


def sammlung(zeilen):
    return pd.DataFrame(zeilen, columns=["stichtag", "zieltag", "vorlauf", "werkzeug", "kwh"])


def test_tabelle_nimmt_nur_die_prognose_vom_vorabend():
    frame = sammlung([
        ["2026-10-21", "2026-10-22", 1, "forecast_solar", 2.8],
        ["2026-10-21", "2026-10-23", 2, "forecast_solar", 1.0],
        ["2026-10-21", "2026-10-22", 1, "quartz_icon", 1.9],
    ])
    verlauf = [{"datum": "2026-10-22", "ist": 3.1, "p1": 3.2}]

    tabelle = tabelle_fuer_morgen(frame, verlauf)

    assert list(tabelle.index) == ["2026-10-22"]
    zeile = tabelle.loc["2026-10-22"]
    assert (zeile["forecast_solar"], zeile["quartz_icon"], zeile[EIGENES], zeile["ist"]) == (2.8, 1.9, 3.2, 3.1)
    assert pd.isna(zeile["solcast"])


def test_tabelle_ohne_solaranalytics_hat_trotzdem_alle_spalten():
    tabelle = tabelle_fuer_morgen(sammlung([["2026-10-21", "2026-10-22", 1, "quartz_icon", 1.9]]), None)

    assert list(tabelle.columns) == ["ist", EIGENES, "forecast_solar", "quartz_icon", "solcast"]
    assert mit_daten(tabelle) == ["quartz_icon"]


def test_kennzahlen_nur_auf_gemeinsamen_tagen():
    tabelle = pd.DataFrame({
        "ist": [2.0, 4.0, 3.0],
        "a": [3.0, 3.0, None],
        "b": [2.0, 5.0, 3.0],
    }, index=["2026-10-01", "2026-10-02", "2026-10-03"])

    ergebnis = kennzahlen(tabelle, ["a", "b"])

    assert ergebnis["tage"] == 2
    werte = {w["spalte"]: w for w in ergebnis["werte"]}
    assert werte["a"]["mae"] == pytest.approx(1.0)
    assert werte["a"]["bias"] == pytest.approx(0.0)
    assert werte["b"]["mae"] == pytest.approx(0.5)
    assert werte["b"]["nmae_prozent"] == pytest.approx(16.7)
    assert ergebnis["werte"][0]["spalte"] == "b"


def test_kennzahlen_ohne_messung_sind_leer():
    tabelle = pd.DataFrame({"ist": [None], "a": [1.0]}, index=["2026-10-22"])

    assert kennzahlen(tabelle, ["a"])["tage"] == 0


def test_rueckblick_fehlt_ohne_datei(tmp_path):
    assert lade_rueckblick(tmp_path / "rueckblick_quartz.csv") is None


def test_rueckblick_mit_namen(tmp_path):
    datei = tmp_path / "rueckblick_quartz.csv"
    datei.write_text("date,quartz_kwh,ist,faustregel_nachgefuehrt_vorhersage\n"
                     "2026-08-18,2.0,1.0,1.2\n2026-08-19,3.0,3.0,2.8\n", encoding="utf-8")

    ergebnis = lade_rueckblick(datei)

    assert ergebnis["tage"] == 2
    assert [w["name"] for w in ergebnis["werte"]] == ["SolarAnalytics, Faustregel für morgen", "Quartz"]
