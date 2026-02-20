import streamlit as st
import requests
import json
import re
from datetime import datetime, timezone, timedelta

# ── CONFIG ───────────────────────────────────────────────────
st.set_page_config(
    page_title="MacroSignal",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── FRED API ─────────────────────────────────────────────────
FRED_KEY = st.secrets.get("FRED_API_KEY", "")
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

@st.cache_data(ttl=3600)
def fred(series_id, limit=12):
    if not FRED_KEY:
        return None
    try:
        r = requests.get(FRED_URL, params={
            "series_id": series_id,
            "api_key": FRED_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit
        }, timeout=10)
        data = r.json().get("observations", [])
        return [float(o["value"]) for o in data if o["value"] not in (".", "")]
    except Exception:
        return None

def delta(series_id, limit=6):
    vals = fred(series_id, limit)
    if not vals or len(vals) < 2:
        return 0.0
    recente = vals[0]
    media   = sum(vals[1:]) / len(vals[1:])
    if media == 0:
        return 0.0
    return max(-1.0, min(1.0, (recente - media) / abs(media) * 10))

# ── SÉRIES FRED ───────────────────────────────────────────────
SERIES = {
    "PAYROLL": {
        "ADP PAYROLLS":        ("ADPWNUSNERSA",  1),
        "JOBLESS CLAIMS":      ("IC4WSA",        -1),
        "JOLTS VAGAS":         ("JTSJOL",         1),
        "ISM EMPLOYMENT IDX":  ("MANEMP",         1),
        "AVG WEEKLY HOURS":    ("AWHAETP",        1),
    },
    "CPI": {
        "PPI (PRODUTOR)":      ("PPIACO",         1),
        "PCE CORE":            ("PCEPILFE",       1),
        "IMPORT PRICES":       ("IR",            -1),
        "PETRÓLEO (WTI)":      ("DCOILWTICO",     1),
        "AVG HOURLY EARNINGS": ("CES0500000003",  1),
        "SHELTER / MORADIA":   ("CUSR0000SAH1",   1),
    },
    "JUROS": {
        "PCE CORE":            ("PCEPILFE",       1),
        "CPI CORE":            ("CPILFESL",       1),
        "NFP / EMPREGO":       ("PAYEMS",         1),
        "GDP":                 ("GDP",           -1),
        "FEDWATCH PROB.":      ("FEDFUNDS",       1),
    },
}

PESOS = {
    "PAYROLL": [30, 25, 20, 15, 10],
    "CPI":     [25, 25, 15, 15, 10, 10],
    "JUROS":   [30, 25, 20, 15, 10],
}

@st.cache_data(ttl=3600)
def calcular_score(tipo):
    series = SERIES.get(tipo, {})
    pesos  = PESOS.get(tipo, [])
    total_w, score = 0, 0.0
    indicadores = []
    for i, (nome, (sid, direcao)) in enumerate(series.items()):
        w   = pesos[i] if i < len(pesos) else 10
        val = delta(sid) * direcao
        score   += val * w
        total_w += w
        indicadores.append({"nome": nome, "valor": val, "peso": w})
    return round(score / total_w if total_w > 0 else 0.0, 3), indicadores

# ── CORRELAÇÕES FX ───────────────────────────────────────────
CORRELATOS = {"USD":"CAD","CAD":"USD","AUD":"NZD","NZD":"AUD","EUR":"GBP","GBP":"EUR","CHF":"JPY","JPY":"CHF"}
ORDEM_FX   = ["EUR","GBP","AUD","NZD","USD","CAD","CHF","JPY"]
TODAS_MOE  = ["USD","EUR","GBP","AUD","NZD","CAD","CHF","JPY"]

def canonico(a, b):
    return (a+b) if ORDEM_FX.index(a) < ORDEM_FX.index(b) else (b+a)

def get_portfolio(cur):
    return [canonico(cur, m) for m in TODAS_MOE if m != cur and m != CORRELATOS.get(cur)]

def veredicto(score):
    return "FORTE" if score > 0.2 else "FRACO" if score < -0.2 else "NEUTRO"

def direcao_par(par, cur, verd):
    if verd == "NEUTRO": return "NEUTRO"
    forte = verd == "FORTE"
    return ("BUY" if forte else "SELL") if par[:3] == cur else ("SELL" if forte else "BUY")

# ── SCRAPING FOREXFACTORY ─────────────────────────────────────
# Eventos que nos interessam (keywords para match)
EVENTOS_ALVO = [
    {"keywords": ["Non-Farm Employment", "NFP"],          "cur": "USD", "nome": "NFP / PAYROLL",    "tipo": "PAYROLL"},
    {"keywords": ["Core CPI", "CPI m/m", "CPI y/y"],      "cur": "USD", "nome": "CPI — EUA",        "tipo": "CPI"},
    {"keywords": ["FOMC Statement", "Federal Funds Rate"],"cur": "USD", "nome": "FOMC — JUROS EUA", "tipo": "JUROS"},
    {"keywords": ["FOMC Meeting Minutes"],                 "cur": "USD", "nome": "FOMC — MINUTES",   "tipo": "JUROS"},
    {"keywords": ["Flash CPI", "CPI Flash", "CPI Prelim"],"cur": "EUR", "nome": "CPI — ZONA EURO",  "tipo": "CPI"},
    {"keywords": ["Main Refinancing Rate", "ECB"],         "cur": "EUR", "nome": "BCE — JUROS EUR",  "tipo": "JUROS"},
    {"keywords": ["CPI y/y", "CPI m/m"],                  "cur": "GBP", "nome": "CPI — UK",         "tipo": "CPI"},
    {"keywords": ["Official Bank Rate", "BOE"],            "cur": "GBP", "nome": "BOE — JUROS GBP",  "tipo": "JUROS"},
    {"keywords": ["CPI q/q", "CPI y/y", "Trimmed Mean"],  "cur": "AUD", "nome": "CPI — AUSTRÁLIA",  "tipo": "CPI"},
    {"keywords": ["Cash Rate", "RBA Rate"],                "cur": "AUD", "nome": "RBA — JUROS AUD",  "tipo": "JUROS"},
    {"keywords": ["Policy Rate", "BOJ"],                   "cur": "JPY", "nome": "BOJ — JUROS JPY",  "tipo": "JUROS"},
    {"keywords": ["Official Cash Rate", "RBNZ"],           "cur": "NZD", "nome": "RBNZ — JUROS NZD", "tipo": "JUROS"},
    {"keywords": ["Overnight Rate", "BOC Rate"],           "cur": "CAD", "nome": "BOC — JUROS CAD",  "tipo": "JUROS"},
]

@st.cache_data(ttl=1800)  # atualiza a cada 30 minutos
def buscar_eventos_ff():
    """Busca calendário de alto impacto do ForexFactory via JSON interno."""
    agora = datetime.now(timezone.utc)
    eventos_encontrados = []

    # ForexFactory tem endpoint JSON não oficial mas estável
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.forexfactory.com/calendar",
    }

    try:
        # Busca as próximas 3 semanas
        for semana_offset in range(0, 4):
            data_ref = agora + timedelta(weeks=semana_offset)
            url = f"https://www.forexfactory.com/calendar?week={data_ref.strftime('%b%d.%Y').lower()}"
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code != 200:
                continue

            # Extrai JSON embutido na página
            match = re.search(r'window\.calendarComponentStates\s*=\s*(\[.*?\]);', r.text, re.DOTALL)
            if not match:
                # Tenta outro padrão
                match = re.search(r'"calendar":\s*(\[.*?\])\s*[,}]', r.text, re.DOTALL)

            if match:
                try:
                    data = json.loads(match.group(1))
                    for entry in data:
                        if not isinstance(entry, dict):
                            continue
                        _processar_entry(entry, agora, eventos_encontrados)
                except Exception:
                    pass

        # Se scraping falhou, usa fallback com datas aproximadas
        if not eventos_encontrados:
            return _fallback_eventos()

        # Remove duplicatas por (cur, tipo), mantém o mais próximo futuro
        vistos = {}
        for ev in sorted(eventos_encontrados, key=lambda x: x["data"]):
            chave = f"{ev['cur']}_{ev['tipo']}"
            data_ev = ev["data"]
            if chave not in vistos:
                vistos[chave] = ev
            else:
                # prefere eventos futuros sobre passados
                if data_ev > agora and vistos[chave]["data"] < agora:
                    vistos[chave] = ev

        return sorted(vistos.values(), key=lambda x: x["data"])

    except Exception:
        return _fallback_eventos()


def _processar_entry(entry, agora, resultado):
    """Tenta extrair evento relevante de uma entrada do calendário FF."""
    titulo = entry.get("name", "") or entry.get("title", "") or entry.get("event", "")
    moeda  = entry.get("currency", "") or entry.get("cur", "")
    impact = entry.get("impact", "") or entry.get("impactTitle", "")
    data_s = entry.get("date", "") or entry.get("dateline", "")
    hora_s = entry.get("time", "")

    if not titulo or not moeda:
        return
    if "high" not in str(impact).lower() and "3" not in str(impact):
        return  # só alto impacto

    # Tenta parsear data/hora
    data_ev = _parsear_data(data_s, hora_s)
    if not data_ev:
        return

    # Match com eventos alvo
    for alvo in EVENTOS_ALVO:
        if moeda.upper() != alvo["cur"]:
            continue
        for kw in alvo["keywords"]:
            if kw.lower() in titulo.lower():
                resultado.append({
                    "id":   f"{alvo['cur']}_{alvo['tipo']}_{data_ev.strftime('%Y%m%d')}",
                    "cur":  alvo["cur"],
                    "nome": alvo["nome"],
                    "tipo": alvo["tipo"],
                    "data": data_ev,
                    "desc": data_ev.strftime("%d %b · %H:%M UTC").upper(),
                })
                return


def _parsear_data(data_s, hora_s):
    """Parseia data e hora do ForexFactory (ET) para UTC."""
    try:
        # Tenta timestamp Unix primeiro
        ts = int(data_s)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt
    except Exception:
        pass

    try:
        # Tenta formatos de string
        for fmt in ["%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(str(data_s), fmt)
                # ForexFactory usa ET (UTC-5 no inverno, UTC-4 no verão)
                if hora_s:
                    for hfmt in ["%I:%M%p", "%I:%M %p", "%H:%M"]:
                        try:
                            ht = datetime.strptime(str(hora_s).strip().upper(), hfmt)
                            dt = dt.replace(hour=ht.hour, minute=ht.minute)
                            break
                        except Exception:
                            pass
                # Converte ET → UTC (assume UTC-5)
                return dt.replace(tzinfo=timezone.utc) + timedelta(hours=5)
            except Exception:
                continue
    except Exception:
        pass
    return None


def _fallback_eventos():
    """Eventos com datas aproximadas caso o scraping falhe."""
    agora = datetime.now(timezone.utc)

    def prox_sexta_1(h, m):
        d = agora.replace(hour=h, minute=m, second=0, microsecond=0)
        dias = (4 - agora.weekday()) % 7
        if dias == 0 and agora >= d:
            dias = 7
        return d + timedelta(days=dias)

    def prox_dia_mes(dia, h, m):
        d = agora.replace(day=dia, hour=h, minute=m, second=0, microsecond=0)
        if d <= agora:
            mes = d.month + 1 if d.month < 12 else 1
            ano = d.year + (1 if d.month == 12 else 0)
            d = d.replace(year=ano, month=mes)
        return d

    return sorted([
        {"id":"nfp",     "cur":"USD","nome":"NFP / PAYROLL",    "tipo":"PAYROLL","data":prox_sexta_1(13,30), "desc":"1ª SEXTA DO MÊS · 13:30 UTC ⚠ APROX"},
        {"id":"cpi_usd", "cur":"USD","nome":"CPI — EUA",        "tipo":"CPI",    "data":prox_dia_mes(13,13,30), "desc":"~DIA 13 · 13:30 UTC ⚠ APROX"},
        {"id":"fomc",    "cur":"USD","nome":"FOMC — JUROS EUA", "tipo":"JUROS",  "data":prox_dia_mes(18,19,0),  "desc":"~DIA 18 · 19:00 UTC ⚠ APROX"},
        {"id":"cpi_eur", "cur":"EUR","nome":"CPI — ZONA EURO",  "tipo":"CPI",    "data":prox_dia_mes(17,10,0),  "desc":"~DIA 17 · 10:00 UTC ⚠ APROX"},
        {"id":"bce",     "cur":"EUR","nome":"BCE — JUROS EUR",  "tipo":"JUROS",  "data":prox_dia_mes(6,13,15),  "desc":"~DIA 6 · 13:15 UTC ⚠ APROX"},
        {"id":"cpi_gbp", "cur":"GBP","nome":"CPI — UK",         "tipo":"CPI",    "data":prox_dia_mes(19,7,0),   "desc":"~DIA 19 · 07:00 UTC ⚠ APROX"},
        {"id":"boe",     "cur":"GBP","nome":"BOE — JUROS GBP",  "tipo":"JUROS",  "data":prox_dia_mes(5,12,0),   "desc":"~DIA 5 · 12:00 UTC ⚠ APROX"},
        {"id":"cpi_aud", "cur":"AUD","nome":"CPI — AUSTRÁLIA",  "tipo":"CPI",    "data":prox_dia_mes(25,0,30),  "desc":"~DIA 25 · 00:30 UTC ⚠ APROX"},
        {"id":"rba",     "cur":"AUD","nome":"RBA — JUROS AUD",  "tipo":"JUROS",  "data":prox_dia_mes(3,3,30),   "desc":"~DIA 3 · 03:30 UTC ⚠ APROX"},
        {"id":"boj",     "cur":"JPY","nome":"BOJ — JUROS JPY",  "tipo":"JUROS",  "data":prox_dia_mes(24,3,0),   "desc":"~DIA 24 · 03:00 UTC ⚠ APROX"},
    ], key=lambda x: x["data"])

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
:root{--bg:#080c10;--surface:#0d1318;--surface2:#111820;--border:#1a2530;--accent:#00e5a0;--red:#ff4558;--yellow:#ffd166;--text:#e8edf2;--muted:#4a5a6a;--muted2:#607a8a;}
*{box-sizing:border-box;}
.stApp{background:var(--bg)!important;}
.block-container{padding:24px 20px 60px!important;max-width:960px!important;}
h1,h2,h3{color:var(--text)!important;}
.logo{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;letter-spacing:5px;color:#00e5a0;text-shadow:0 0 30px rgba(0,229,160,.4);}
.logo em{color:#e8edf2;font-style:normal;}
.section-lbl{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:3px;color:#4a5a6a;margin-bottom:8px;}
.ev-row{background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;border-left:3px solid #1a2530;}
.ev-row.sel{border-left-color:#00e5a0;background:rgba(0,229,160,.04);border-color:rgba(0,229,160,.3);}
.ev-row.past{opacity:0.45;}
.ev-cur{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:3px;padding:4px 10px;border-radius:4px;border:1px solid #1a2530;color:#607a8a;background:#111820;min-width:52px;text-align:center;display:inline-block;}
.ev-name{font-family:'Bebas Neue',sans-serif;font-size:1.05rem;letter-spacing:2px;color:#e8edf2;}
.ev-date{font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;margin-top:2px;}
.ev-cd{font-family:'Bebas Neue',sans-serif;font-size:1.25rem;letter-spacing:2px;color:#ffd166;text-align:right;}
.ev-cdlbl{font-family:'DM Mono',monospace;font-size:.52rem;color:#4a5a6a;letter-spacing:2px;text-align:right;}
.ev-past-lbl{font-family:'Bebas Neue',sans-serif;font-size:1rem;color:#4a5a6a;text-align:right;}
.badge{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:4px;padding:8px 22px;border-radius:6px;display:inline-block;}
.badge-forte{background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.35);box-shadow:0 0 24px rgba(0,229,160,.12);}
.badge-fraco{background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.35);box-shadow:0 0 24px rgba(255,69,88,.12);}
.badge-neutro{background:rgba(74,90,106,.2);color:#607a8a;border:1px solid #1a2530;}
.score-lbl{font-family:'DM Mono',monospace;font-size:.65rem;color:#4a5a6a;text-align:right;margin-top:6px;}
.ind-title{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:3px;color:#4a5a6a;margin-bottom:12px;}
.ind-name{font-family:'DM Mono',monospace;font-size:.62rem;color:#607a8a;}
.pair-card{background:#111820;border:1px solid #1a2530;border-radius:6px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;}
.pair-name{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:2px;color:#e8edf2;}
.pair-buy{font-family:'Bebas Neue',sans-serif;font-size:.85rem;padding:3px 8px;border-radius:3px;background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.25);}
.pair-sell{font-family:'Bebas Neue',sans-serif;font-size:.85rem;padding:3px 8px;border-radius:3px;background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.25);}
.disclaimer{background:rgba(255,209,102,.04);border:1px solid rgba(255,209,102,.12);border-radius:6px;padding:12px 16px;font-family:'DM Mono',monospace;font-size:.6rem;color:rgba(255,209,102,.6);line-height:1.7;}
.source-badge{font-family:'DM Mono',monospace;font-size:.55rem;padding:3px 8px;border-radius:3px;display:inline-block;margin-bottom:12px;}
.source-live{background:rgba(0,229,160,.08);color:#00e5a0;border:1px solid rgba(0,229,160,.2);}
.source-fallback{background:rgba(255,209,102,.08);color:#ffd166;border:1px solid rgba(255,209,102,.2);}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#00e5a0;box-shadow:0 0 8px #00e5a0;animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
div[data-testid="stVerticalBlock"]{gap:0!important;}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
agora = datetime.now(timezone.utc)
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="logo">Macro<em>Signal</em></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:8px;">
      <span class="live-dot"></span>
      <span style="font-family:'DM Mono',monospace;font-size:.85rem;color:#e8edf2;letter-spacing:2px;margin-left:6px;">
        {agora.strftime('%H:%M:%S')}
      </span><br>
      <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;">UTC · AO VIVO</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0 24px;">', unsafe_allow_html=True)

if not FRED_KEY:
    st.warning("⚠️ **FRED_API_KEY não configurada.** Vá em Settings → Secrets no Streamlit Cloud.", icon="🔑")

# ── BUSCAR EVENTOS ────────────────────────────────────────────
with st.spinner("🔄 Buscando calendário econômico..."):
    EVENTOS = buscar_eventos_ff()

# Detecta se veio do scraping real ou fallback
usando_fallback = any("⚠ APROX" in ev["desc"] for ev in EVENTOS)
badge_src = "source-fallback" if usando_fallback else "source-live"
txt_src   = "⚠ DATAS APROXIMADAS — SCRAPING INDISPONÍVEL" if usando_fallback else "✓ FOREXFACTORY · CALENDÁRIO AO VIVO"
st.markdown(f'<div class="source-badge {badge_src}">{txt_src}</div>', unsafe_allow_html=True)

# ── SELECIONAR EVENTO ─────────────────────────────────────────
if "evento_idx" not in st.session_state:
    # Seleciona automaticamente o próximo evento futuro
    idx_futuro = next((i for i, ev in enumerate(EVENTOS) if ev["data"] > agora), 0)
    st.session_state.evento_idx = idx_futuro

st.markdown('<div class="section-lbl">PRÓXIMOS EVENTOS DE ALTO IMPACTO</div>', unsafe_allow_html=True)

DIAS  = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
MESES = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]

for i, ev in enumerate(EVENTOS):
    diff  = ev["data"] - agora
    total = int(diff.total_seconds())
    past  = total <= 0

    if past:
        cd_html = f'<div class="ev-past-lbl">ENCERRADO</div>'
    elif total < 86400 * 2:
        h, rem = divmod(total, 3600)
        m, s   = divmod(rem, 60)
        cd_html = f'<div class="ev-cd">{h:02d}:{m:02d}:{s:02d}</div><div class="ev-cdlbl">ATÉ O EVENTO</div>'
    else:
        dias = total // 86400
        h    = (total % 86400) // 3600
        cd_html = f'<div class="ev-cd">{dias}D {h:02d}H</div><div class="ev-cdlbl">ATÉ O EVENTO</div>'

    dt  = ev["data"]
    sel = "sel" if i == st.session_state.evento_idx else ""
    past_cls = "past" if past else ""
    fmt = f"{DIAS[dt.weekday()]} · {dt.day:02d} {MESES[dt.month-1]} · {dt.hour:02d}:{dt.minute:02d} UTC"

    clicked = st.button(f"ev_{i}", key=f"btn_{i}", use_container_width=True, label_visibility="collapsed")
    st.markdown(f"""
    <div class="ev-row {sel} {past_cls}">
      <div style="display:flex;align-items:center;gap:14px;">
        <span class="ev-cur">{ev['cur']}</span>
        <div>
          <div class="ev-name">{ev['nome']}</div>
          <div class="ev-date">{fmt} · {ev['desc']}</div>
        </div>
      </div>
      <div>{cd_html}</div>
    </div>
    """, unsafe_allow_html=True)

    if clicked:
        st.session_state.evento_idx = i
        st.rerun()

# ── ANÁLISE DO EVENTO SELECIONADO ─────
