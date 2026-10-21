from fastapi.testclient import TestClient

import web


def test_daten_ohne_solaranalytics(tmp_path, monkeypatch):
    monkeypatch.setenv("DATEN", str(tmp_path))
    monkeypatch.delenv("SOLARANALYTICS_URL", raising=False)
    (tmp_path / "sammlung_tageswerte.csv").write_text(
        "stichtag,zieltag,vorlauf,werkzeug,kwh,unten_kwh,oben_kwh,abgerufen_utc\n"
        "2026-10-21,2026-10-22,1,forecast_solar,2.808,,,2026-10-21T18:07:08+00:00\n"
        "2026-10-21,2026-10-22,1,quartz_icon,1.951,,,2026-10-21T18:07:09+00:00\n",
        encoding="utf-8",
    )

    daten = TestClient(web.app).get("/api/daten").json()

    assert daten["abende"] == 1
    assert daten["solaranalytics"] == "nicht eingestellt"
    assert daten["tabelle"][0]["forecast_solar"] == 2.808
    assert daten["gemeinsam"]["tage"] == 0
    assert len(daten["rohdaten"]) == 2


def test_nur_ergebnisdateien_sind_herunterladbar(tmp_path, monkeypatch):
    monkeypatch.setenv("DATEN", str(tmp_path))
    (tmp_path / "sammlung_roh.jsonl").write_text('{"werkzeug": "quartz_icon"}\n', encoding="utf-8")
    (tmp_path / "lebenszeichen.txt").write_text("2026-10-22", encoding="utf-8")
    client = TestClient(web.app)

    assert client.get("/api/dateien/sammlung_roh.jsonl").text.startswith('{"werkzeug"')
    assert client.get("/api/dateien/lebenszeichen.txt").status_code == 404
    assert client.get("/api/dateien/sammlung_tageswerte.csv").status_code == 404


def test_startseite_liefert_die_oberflaeche():
    antwort = TestClient(web.app).get("/")

    assert antwort.status_code == 200
    assert "Werkzeugvergleich" in antwort.text
