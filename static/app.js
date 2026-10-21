const stil = getComputedStyle(document.documentElement);
const FARBE = {
    gruen: stil.getPropertyValue("--color-data").trim(),
    dunkel: stil.getPropertyValue("--color-heading").trim(),
    blau: stil.getPropertyValue("--color-data-2").trim(),
    grau: "#94a3b8",
    text: stil.getPropertyValue("--color-text").trim(),
};
const NAMEN = { solaranalytics: "SolarAnalytics", forecast_solar: "Forecast.Solar", quartz_icon: "Quartz", solcast: "Solcast" };
const LINIE = {
    solaranalytics: { borderColor: FARBE.dunkel, borderWidth: 2.5 },
    forecast_solar: { borderColor: FARBE.blau, borderWidth: 2 },
    quartz_icon: { borderColor: FARBE.grau, borderWidth: 2, borderDash: [6, 4] },
    solcast: { borderColor: FARBE.blau, borderWidth: 2, borderDash: [2, 3] },
};

// Angaben aus den Beschreibungen der Anbieter, für die Arbeit an den Quellen prüfen
const STECKBRIEF = [
    ["SolarAnalytics", "diese Arbeit, Open Source, läuft lokal", "Faustregel mit Nachführung, Lernverfahren zum Vergleich, Auswahl per Diebold-Mariano-Test", "ICON über Open-Meteo", "ja, Ertragsquote der letzten 14 Messtage", "Tagessumme mit Spanne, 7 Tage"],
    ["Forecast.Solar", "freie Schnittstelle ohne Konto", "Modellrechnung aus Wettervorhersage und Anlagendaten", "vom Dienst gewählt", "nein, im freien Zugang", "Stunden- und Tageswerte, heute und morgen"],
    ["Quartz", "Open Climate Fix, Open Source, Python-Paket", "Lernverfahren, auf Daten fremder Anlagen trainiert", "ICON über Open-Meteo", "nein", "15-Minuten-Leistung, daraus Tagessumme"],
    ["Solcast", "Hobby-Konto, 10 Abrufe am Tag", "Satellitendaten und Wettermodelle", "eigene Aufbereitung", "nein, im Hobby-Konto", "Tagessumme mit 10. und 90. Perzentil"],
];

Chart.defaults.font.family = stil.getPropertyValue("--font-display").trim() || "system-ui";
Chart.defaults.color = stil.getPropertyValue("--color-text-muted").trim();

const fmt = (x, n = 2) => (x === null || x === undefined || Number.isNaN(x)) ? "n. v." : Number(x).toFixed(n).replace(".", ",");
const tagKurz = (iso) => new Date(iso + "T12:00:00").toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
const zeitpunkt = (iso) => {
    if (!iso) {
        return "noch nie";
    }
    const d = new Date(iso);
    return `${d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })} ${d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}`;
};
const achsen = () => ({ ticks: { font: { size: 11 } }, grid: { color: "#e8edf3" } });

// Schreibt den Wert ans Ende jedes Balkens, Texte kommen aus options.plugins.wertBeschriftung.texte
const wertBeschriftung = {
    id: "wertBeschriftung",
    afterDatasetsDraw(diagramm, argumente, optionen) {
        const { ctx, chartArea } = diagramm;
        ctx.save();
        ctx.font = `600 12px ${Chart.defaults.font.family}`;
        ctx.fillStyle = FARBE.text;
        ctx.textBaseline = "middle";
        diagramm.getDatasetMeta(0).data.forEach((balken, i) => {
            const x = Number.isFinite(balken.x) && balken.x > chartArea.left ? balken.x : chartArea.left;
            ctx.fillText(optionen.texte[i], x + 8, balken.y);
        });
        ctx.restore();
    },
};

async function ladeJson(pfad) {
    const antwort = await fetch(pfad);
    if (!antwort.ok) {
        throw new Error(`Datenabruf fehlgeschlagen: ${pfad} ${antwort.status}`);
    }
    return antwort.json();
}

function kennzahl(wert, label) {
    return `<div class="stat"><span class="stat-value">${wert}</span><span class="stat-label">${label}</span></div>`;
}

function kacheln(D) {
    const aktiv = Object.values(D.werkzeuge).filter(Boolean).length;
    const solcast = D.werkzeuge.solcast ? "" : ", Solcast wartet auf Freischaltung";
    return `<section class="stats">
        ${kennzahl(D.abende, "Abende gesammelt")}
        ${kennzahl(D.gemeinsam.tage, "Tage mit Messung zum Vergleich")}
        ${kennzahl(zeitpunkt(D.letzter_abruf), "letzter Abruf")}
        ${kennzahl(`${aktiv} von 3`, `Werkzeuge aktiv${solcast}`)}
    </section>`;
}

function verlaufKarte() {
    return `<section class="card">
        <div class="card-kopf"><h2>Prognose für morgen gegen Messung</h2>
            <span class="legende" id="verlauf-status"></span></div>
        <div class="chart-box"><canvas id="chart-verlauf"></canvas></div>
    </section>`;
}

function zeichneVerlauf(D) {
    const t = D.tabelle;
    const spalten = [D.eigenes, "forecast_solar", "quartz_icon", "solcast"].filter((s) => t.some((z) => z[s] !== null));
    document.getElementById("verlauf-status").textContent = `SolarAnalytics: ${D.solaranalytics}`;
    new Chart(document.getElementById("chart-verlauf"), {
        data: {
            labels: t.map((z) => tagKurz(z.zieltag)),
            datasets: [
                ...spalten.map((s) => ({ type: "line", label: NAMEN[s], data: t.map((z) => z[s]), ...LINIE[s], backgroundColor: LINIE[s].borderColor, pointRadius: t.length > 40 ? 0 : 3, tension: 0.15, spanGaps: true, order: 1 })),
                { type: "bar", label: "Gemessen", data: t.map((z) => z.ist), backgroundColor: FARBE.gruen, borderRadius: 2, order: 2 },
            ],
        },
        options: {
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { boxWidth: 12 } },
                tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.parsed.y)} kWh` } },
            },
            scales: { x: { ...achsen(), grid: { display: false } }, y: { ...achsen(), beginAtZero: true, title: { display: true, text: "kWh je Tag" } } },
        },
    });
}

function balkenKarte(id, titel, legende) {
    return `<section class="card">
        <div class="card-kopf"><h2>${titel}</h2><span class="legende">${legende}</span></div>
        <div class="chart-box-klein"><canvas id="${id}"></canvas></div>
    </section>`;
}

function zeichneBalken(id, werte, name, istEigenes) {
    const max = Math.max(...werte.map((w) => w.mae), 0.1);
    new Chart(document.getElementById(id), {
        type: "bar",
        data: { labels: werte.map(name), datasets: [{ data: werte.map((w) => w.mae), backgroundColor: werte.map((w) => istEigenes(w) ? FARBE.dunkel : FARBE.blau), borderRadius: 3, barPercentage: 0.7 }] },
        options: {
            indexAxis: "y",
            maintainAspectRatio: false,
            layout: { padding: { right: 16 } },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (c) => `im Mittel ${fmt(werte[c.dataIndex].mae)} kWh daneben, Bias ${fmt(werte[c.dataIndex].bias)} kWh` } },
                wertBeschriftung: { texte: werte.map((w) => `± ${fmt(w.mae)} kWh · ${fmt(w.nmae_prozent, 0)} % eines Tages`) },
            },
            scales: {
                x: { ...achsen(), beginAtZero: true, max: Math.ceil(max * 1.6 * 10) / 10, title: { display: true, text: "mittlere Abweichung, kWh" } },
                y: { ...achsen(), grid: { display: false }, ticks: { autoSkip: false, color: FARBE.text, font: { size: 12 } } },
            },
        },
        plugins: [wertBeschriftung],
    });
}

function steckbrief() {
    const zeilen = STECKBRIEF.map((z) => `<tr>${z.map((zelle, i) => i === 0 ? `<td><strong style="color:var(--color-heading)">${zelle}</strong></td>` : `<td>${zelle}</td>`).join("")}</tr>`).join("");
    return `<section class="card">
        <div class="card-kopf"><h2>Die Werkzeuge im Überblick</h2><span class="legende">Angaben der Anbieter, Stand 21.10.2026</span></div>
        <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Werkzeug</th><th>Anbieter und Zugang</th><th>Verfahren</th><th>Wetterdaten</th><th>Eigene Messwerte</th><th>Ausgabe</th></tr></thead>
            <tbody>${zeilen}</tbody>
        </table></div>
    </section>`;
}

function rohdaten(D) {
    const zeilen = D.rohdaten.map((z) => `<tr><td>${tagKurz(z.stichtag)}</td><td>${tagKurz(z.zieltag)}</td><td class="num">${z.vorlauf}</td><td>${NAMEN[z.werkzeug] || z.werkzeug}</td><td class="num">${fmt(z.kwh)}</td><td class="num">${z.unten_kwh === null ? "" : `${fmt(z.unten_kwh)} bis ${fmt(z.oben_kwh)}`}</td><td>${zeitpunkt(z.abgerufen_utc)}</td></tr>`).join("");
    return `<section class="card">
        <div class="card-kopf"><h2>Gesammelte Werte</h2><span class="legende">die letzten ${D.rohdaten.length} Einträge, abgerufen ab ${D.anlage.ab_stunde} Uhr</span></div>
        <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Stichtag</th><th>Zieltag</th><th class="num">Vorlauf</th><th>Werkzeug</th><th class="num">kWh</th><th class="num">Spanne</th><th>abgerufen</th></tr></thead>
            <tbody>${zeilen || '<tr><td colspan="7">Noch nichts gesammelt.</td></tr>'}</tbody>
        </table></div>
    </section>`;
}

async function init() {
    const ziel = document.getElementById("inhalt");
    let D;
    try {
        D = await ladeJson("/api/daten");
    } catch (fehler) {
        console.error(fehler);
        ziel.innerHTML = '<section class="card"><p class="empty">Daten nicht erreichbar.</p></section>';
        return;
    }
    const a = D.anlage;
    document.getElementById("anlage").textContent = `${fmt(a.breite)}°N ${fmt(a.laenge)}°E · ${a.neigung}° Neigung · ${fmt(a.kwp, 1)} kWp`;

    const g = D.gemeinsam;
    const vergleich = g.tage
        ? balkenKarte("chart-mae", "So weit liegen die Werkzeuge bei der Prognose für morgen im Mittel daneben", `${g.tage} gemeinsame Tage, ${tagKurz(g.von)} bis ${tagKurz(g.bis)}`)
        : '<section class="card"><div class="card-kopf"><h2>So weit liegen die Werkzeuge bei der Prognose für morgen im Mittel daneben</h2></div><p class="empty">Noch kein gemeinsamer Tag mit Messung. Die Messung zu einer gesammelten Prognose kommt am Folgetag.</p></section>';
    const r = D.rueckblick;
    const rueckblick = r && r.tage
        ? balkenKarte("chart-rueckblick", "Rückblick: Quartz gegen SolarAnalytics", `${r.tage} Tage, ${tagKurz(r.von)} bis ${tagKurz(r.bis)}, Quartz mit Wetter nahe am Nachhinein`)
        : "";

    ziel.innerHTML = kacheln(D) + verlaufKarte() + vergleich + rueckblick + steckbrief() + rohdaten(D);

    if (D.tabelle.length) {
        zeichneVerlauf(D);
    }
    if (g.tage) {
        zeichneBalken("chart-mae", g.werte, (w) => NAMEN[w.spalte] || w.spalte, (w) => w.spalte === D.eigenes);
    }
    if (rueckblick) {
        zeichneBalken("chart-rueckblick", r.werte, (w) => w.name, (w) => w.spalte !== "quartz_kwh");
    }
}

init();
