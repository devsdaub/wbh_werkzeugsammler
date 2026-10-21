from dataclasses import replace
from datetime import timedelta

import pytest

import sammler


@pytest.fixture
def einstellungen(tmp_path, monkeypatch):
    monkeypatch.setenv("DATEN", str(tmp_path))
    monkeypatch.setenv("ABRUF_AB_STUNDE", "0")
    monkeypatch.setenv("SOLCAST_API_KEY", "test")
    monkeypatch.setenv("SOLCAST_RESOURCE_ID", "test")
    return sammler.Einstellungen.aus_umgebung()


def test_solcast_nur_mit_schluessel_und_anlage(einstellungen):
    assert "solcast" in sammler.aktive_dienste(einstellungen)
    assert "solcast" not in sammler.aktive_dienste(replace(einstellungen, solcast_anlage=""))


def test_solcast_hoechstens_drei_versuche_am_tag(einstellungen, monkeypatch):
    aufrufe = []

    def scheitert(e, stichtag):
        aufrufe.append(stichtag)
        raise ConnectionError("gesperrt")

    monkeypatch.setattr(sammler, "DIENSTE", {**sammler.DIENSTE, "solcast": scheitert})
    nur_solcast = replace(einstellungen, forecast_solar=False, quartz=False)
    versuche = {}
    for _ in range(10):
        sammler.runde(nur_solcast, versuche)

    assert len(aufrufe) == 3


def test_gespeicherter_dienst_wird_nicht_erneut_abgerufen(einstellungen, monkeypatch):
    aufrufe = []

    def liefert(e, stichtag):
        aufrufe.append(stichtag)
        return {stichtag + timedelta(days=1): (2.0, None, None)}, {}

    monkeypatch.setattr(sammler, "DIENSTE", {**sammler.DIENSTE, "forecast_solar": liefert})
    nur_forecast_solar = replace(einstellungen, quartz=False, solcast_schluessel="")
    versuche = {}
    sammler.runde(nur_forecast_solar, versuche)
    sammler.runde(nur_forecast_solar, versuche)

    assert len(aufrufe) == 1
    zeilen = (einstellungen.daten / "sammlung_tageswerte.csv").read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 2
    assert zeilen[1].startswith(f"{aufrufe[0]},{aufrufe[0] + timedelta(days=1)},1,forecast_solar,2.0,,,")
