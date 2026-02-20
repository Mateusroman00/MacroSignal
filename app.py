import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone
import time

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
    """Busca as últimas observações de uma série no FRED."""
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
        vals = [float(o["value"]) for o in data if o["value"] not in (".", "")]
        return vals  # [0] = mais recente
    except Exception:
        return None

def delta(series_id, limit=6):
    """Retorna variação recente (último vs média anterior) como score -1..1."""
    vals = fred(series_id, limit)
    if not vals or len(vals) < 2:
        return 0.0
    recente = vals[0]
    media   = sum(vals[1:]) / len(vals[1:])
    if media == 0:
        return 0.0
    raw = (recente - media) / abs(media)
    return max(-1.0, min(1.0, raw * 10))  # normaliza

# ── SÉRIES FRED POR TIPO DE EVENTO ───────────────────────────
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
    """Calcula score ponderado -1..1 para o tipo de evento."""
    series = SERIES.get(tipo, {})
    pesos  = PESOS.get(tipo, [])
    total_w = 0
    score   = 0.0
    indicadores = []

    for i, (nome, (sid, direcao)) in enumerate(series.items()):
        w   = pesos[i] if i < len(pesos) else 10
        d   = delta(sid)
        val = d * direcao  # aplica direção
        score   += val * w
        total_w += w
        indicadores.append({
            "nome": nome,
            "valor": val,
            "peso": w,
            "direcao": direcao
        })

    score_norm = score / total_w if total_w > 0 else 0.0
    return round(score_norm, 3), indicadores

# ── CORRELAÇÕES FX ───────────────────────────────────────────
CORRELATOS = {"USD":"CAD","CAD":"USD","AUD":"NZD","NZD":"AUD","EUR":"GBP","GBP":"EUR","CHF":"JPY","JPY":"CHF"}
ORDEM_FX   = ["EUR","GBP","AUD","NZD","USD","CAD","CHF","JPY"]
TODAS_MOE  = ["USD","EUR","GBP","AUD","NZD","CAD","CHF","JPY"]

def canonico(a, b):
    return (a+b) if ORDEM_FX.index(a) < ORDEM_FX.index(b) else (b+a)

def get_portfolio(cur):
    return [canonico(cur, m) for m in TODAS_MOE if m != cur and m != CORRELATOS.get(cur)]

def veredicto(score):
    if score > 0.2:  return "FORTE"
    if score < -0.2: return "FRACO"
    return "NEUTRO"

def direcao_par(par, cur, verd):
    if verd == "NEUTRO": return "NEUTRO"
    forte = verd == "FORTE"
    return ("BUY" if forte else "SELL") if par[:3] == cur else ("SELL" if forte else "BUY")

# ── EVENTOS ───────────────────────────────────────────────────
def prox_data_mes(dia, h, m):
    agora = datetime.now(timezone.utc)
    alvo  = agora.replace(day=dia, hour=h, minute=m, second=0, microsecond=0)
    if alvo <= agora:
        mes = alvo.month + 1 if alvo.month < 12 else 1
        ano = alvo.year + (1 if alvo.month == 12 else 0)
        alvo = alvo.replace(year=ano, month=mes)
    return alvo

from datetime import timedelta

def prox_sexta(h, m):
    agora = datetime.now(timezone.utc)
    alvo  = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    dias_ate_sexta = (4 - agora.weekday()) % 7
    if dias_ate_sexta == 0 and agora >= alvo:
        dias_ate_sexta = 7
    return alvo + timedelta(days=dias_ate_sexta)

EVENTOS = sorted([
    {"id":"nfp",     "cur":"USD","nome":"NFP / PAYROLL",   "tipo":"PAYROLL","data":prox_sexta(13,30),         "desc":"1º sexta do mês · 13:30 UTC"},
    {"id":"cpi_usd", "cur":"USD","nome":"CPI — EUA",       "tipo":"CPI",    "data":prox_data_mes(12,13,30),   "desc":"Mensal · 13:30 UTC"},
    {"id":"fomc",    "cur":"USD","nome":"FOMC — JUROS EUA","tipo":"JUROS",  "data":prox_data_mes(19,19,0),    "desc":"8x ao ano · 19:00 UTC"},
    {"id":"cpi_eur", "cur":"EUR","nome":"CPI — ZONA EURO", "tipo":"CPI",    "data":prox_data_mes(17,10,0),    "desc":"Mensal · 10:00 UTC"},
    {"id":"bce",     "cur":"EUR","nome":"BCE — JUROS EUR", "tipo":"JUROS",  "data":prox_data_mes(6,13,15),    "desc":"8x ao ano · 13:15 UTC"},
    {"id":"cpi_gbp", "cur":"GBP","nome":"CPI — UK",        "tipo":"CPI",    "data":prox_data_mes(19,7,0),     "desc":"Mensal · 07:00 UTC"},
    {"id":"boe",     "cur":"GBP","nome":"BOE — JUROS GBP", "tipo":"JUROS",  "data":prox_data_mes(6,12,0),     "desc":"8x ao ano · 12:00 UTC"},
    {"id":"cpi_aud", "cur":"AUD","nome":"CPI — AUSTRÁLIA", "tipo":"CPI",    "data":prox_data_mes(26,1,30),    "desc":"Trimestral · 01:30 UTC"},
    {"id":"rba",     "cur":"AUD","nome":"RBA — JUROS AUD", "tipo":"JUROS",  "data":prox_data_mes(4,3,30),     "desc":"8x ao ano · 03:30 UTC"},
    {"id":"boj",     "cur":"JPY","nome":"BOJ — JUROS JPY", "tipo":"JUROS",  "data":prox_data_mes(24,3,0),     "desc":"8x ao ano · 03:00 UTC"},
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
.ev-row{background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;cursor:pointer;border-left:3px solid #1a2530;}
.ev-row.sel{border-left-color:#00e5a0;background:rgba(0,229,160,.04);border-color:rgba(0,229,160,.3);}
.ev-cur{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:3px;padding:4px 10px;border-radius:4px;border:1px solid #1a2530;color:#607a8a;background:#111820;min-width:52px;text-align:center;display:inline-block;}
.ev-name{font-family:'Bebas Neue',sans-serif;font-size:1.05rem;letter-spacing:2px;color:#e8edf2;}
.ev-date{font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;margin-top:2px;}
.ev-cd{font-family:'Bebas Neue',sans-serif;font-size:1.25rem;letter-spacing:2px;color:#ffd166;text-align:right;}
.ev-cdlbl{font-family:'DM Mono',monospace;font-size:.52rem;color:#4a5a6a;letter-spacing:2px;text-align:right;}
.card{background:#0d1318;border:1px solid #1a2530;border-radius:10px;padding:24px;margin-bottom:16px;}
.sig-cur{font-family:'Bebas Neue',sans-serif;font-size:2.6rem;letter-spacing:6px;line-height:1;color:#e8edf2;}
.sig-ev{font-family:'DM Mono',monospace;font-size:.6rem;color:#607a8a;letter-spacing:2px;margin-top:4px;}
.badge{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:4px;padding:8px 22px;border-radius:6px;display:inline-block;}
.badge-forte{background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.35);box-shadow:0 0 24px rgba(0,229,160,.12);}
.badge-fraco{background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.35);box-shadow:0 0 24px rgba(255,69,88,.12);}
.badge-neutro{background:rgba(74,90,106,.2);color:#607a8a;border:1px solid #1a2530;}
.score-lbl{font-family:'DM Mono',monospace;font-size:.65rem;color:#4a5a6a;text-align:right;margin-top:6px;}
.ind-title{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:3px;color:#4a5a6a;margin-bottom:12px;}
.ind-name{font-family:'DM Mono',monospace;font-size:.62rem;color:#607a8a;}
.pair-card{background:#111820;border:1px solid #1a2530;border-radius:6px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;}
.pair-name{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:2px;color:#e8edf2;}
.pair-buy{font-family:'Bebas Neue',sans-serif;font-size:.85rem;letter-spacing:1px;padding:3px 8px;border-radius:3px;background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.25);}
.pair-sell{font-family:'Bebas Neue',sans-serif;font-size:.85rem;letter-spacing:1px;padding:3px 8px;border-radius:3px;background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.25);}
.disclaimer{background:rgba(255,209,102,.04);border:1px solid rgba(255,209,102,.12);border-radius:6px;padding:12px 16px;font-family:'DM Mono',monospace;font-size:.6rem;color:rgba(255,209,102,.6);line-height:1.7;}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#00e5a0;box-shadow:0 0 8px #00e5a0;animation:pulse 2s infinite;}
.stButton>button{display:none!important;}
hr{border-color:#1a2530!important;}
div[data-testid="stVerticalBlock"]{gap:0!important;}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
agora_utc = datetime.now(timezone.utc)
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="logo">Macro<em>Signal</em></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:8px;">
      <span class="live-dot"></span>
      <span style="font-family:'DM Mono',monospace;font-size:.85rem;color:#e8edf2;letter-spacing:2px;margin-left:6px;">
        {agora_utc.strftime('%H:%M:%S')}
      </span><br>
      <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;">UTC · AO VIVO</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="margin:16px 0 24px;">', unsafe_allow_html=True)

# ── ALERTA SE SEM API KEY ─────────────────────────────────────
if not FRED_KEY:
    st.warning("⚠️ **FRED_API_KEY não configurada.** Vá em Settings → Secrets no Streamlit Cloud e adicione sua chave. Registre-se grátis em [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)", icon="🔑")

# ── SELECIONAR EVENTO ─────────────────────────────────────────
if "evento_idx" not in st.session_state:
    st.session_state.evento_idx = 0

st.markdown('<div class="section-lbl">PRÓXIMOS EVENTOS DE ALTO IMPACTO</div>', unsafe_allow_html=True)

DIAS  = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
MESES = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]

for i, ev in enumerate(EVENTOS):
    diff  = ev["data"] - agora_utc
    total = int(diff.total_seconds())
    if total <= 0:
        cd = "AO VIVO"
    elif total < 86400 * 2:
        h, rem = divmod(total, 3600)
        m, s   = divmod(rem, 60)
        cd = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        dias = total // 86400
        h    = (total % 86400) // 3600
        cd   = f"{dias}D {h:02d}H"

    dt  = ev["data"]
    sel = "sel" if i == st.session_state.evento_idx else ""
    fmt = f"{DIAS[dt.weekday()]} · {dt.day:02d} {MESES[dt.month-1]} · {dt.hour:02d}:{dt.minute:02d} UTC"

    clicked = st.button(f"__EV_{i}__", key=f"btn_{i}", use_container_width=True)

    st.markdown(f"""
    <div class="ev-row {sel}" id="ev_{i}" onclick="window.location.href='?ev={i}'">
      <div style="display:flex;align-items:center;gap:14px;">
        <span class="ev-cur">{ev['cur']}</span>
        <div>
          <div class="ev-name">{ev['nome']}</div>
          <div class="ev-date">{fmt} · {ev['desc']}</div>
        </div>
      </div>
      <div>
        <div class="ev-cd">{cd}</div>
        <div class="ev-cdlbl">ATÉ O EVENTO</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if clicked:
        st.session_state.evento_idx = i
        st.rerun()

# ── ANÁLISE DO EVENTO SELECIONADO ────────────────────────────
ev = EVENTOS[st.session_state.evento_idx]

st.markdown('<hr style="margin:20px 0 16px;">', unsafe_allow_html=True)
st.markdown('<div class="section-lbl">ANÁLISE DO EVENTO SELECIONADO</div>', unsafe_allow_html=True)

with st.spinner("Buscando dados na FRED API..."):
    score, indicadores = calcular_score(ev["tipo"])

verd  = veredicto(score)
bc    = f"badge-{verd.lower()}"
port  = get_portfolio(ev["cur"])

# Header do card
col_a, col_b = st.columns([1, 1])
with col_a:
    st.markdown(f"""
    <div style="padding:8px 0">
      <div class="sig-cur">{ev['cur']}</div>
      <div class="sig-ev">{ev['nome']}</div>
    </div>
    """, unsafe_allow_html=True)
with col_b:
    st.markdown(f"""
    <div style="text-align:right;padding:8px 0">
      <div class="badge {bc}">{verd}</div>
      <div class="score-lbl">SCORE: {'+' if score>=0 else ''}{score:.3f}</div>
      <div class="score-lbl" style="margin-top:4px;font-size:.52rem;">{'⚡ DADOS REAIS · FRED API' if FRED_KEY else '⚠ SEM API KEY — SCORE ZERADO'}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="margin:12px 0;">', unsafe_allow_html=True)

# Indicadores
st.markdown('<div class="ind-title">INDICADORES ANTECEDENTES — DADOS REAIS FRED</div>', unsafe_allow_html=True)

for ind in indicadores:
    val   = ind["valor"]
    pct   = min(100, abs(val) * 100)
    cor   = "#00e5a0" if val > 0.05 else "#ff4558" if val < -0.05 else "#607a8a"
    arr   = "▲" if val > 0.05 else "▼" if val < -0.05 else "→"
    cls   = "up" if val > 0.05 else "down" if val < -0.05 else "flat"

    col_n, col_b2, col_a2 = st.columns([3, 6, 1])
    with col_n:
        st.markdown(f'<div class="ind-name" style="padding-top:4px;">{ind["nome"]}</div>', unsafe_allow_html=True)
    with col_b2:
        st.markdown(f"""
        <div style="margin-top:8px;height:3px;background:#1a2530;border-radius:2px;">
          <div style="width:{pct:.0f}%;height:100%;background:{cor};border-radius:2px;box-shadow:0 0 6px {cor}44;"></div>
        </div>
        """, unsafe_allow_html=True)
    with col_a2:
        st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:.65rem;color:{cor};text-align:right;padding-top:2px;">{arr}</div>', unsafe_allow_html=True)

st.markdown('<hr style="margin:16px 0;">', unsafe_allow_html=True)

# Pares
correlato = CORRELATOS.get(ev["cur"], "—")
if verd == "NEUTRO":
    st.markdown(f"""
    <div style="text-align:center;font-family:'DM Mono',monospace;font-size:.7rem;color:#4a5a6a;letter-spacing:1px;padding:24px;background:#0d1318;border:1px solid #1a2530;border-radius:8px;line-height:1.8;">
      SINAL NEUTRO — INDICADORES CONTRADITÓRIOS<br>MELHOR AGUARDAR ESTE EVENTO
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f'<div class="ind-title">PORTFÓLIO — {ev["cur"]} vs DEMAIS (EXCLUINDO {correlato})</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for j, par in enumerate(port):
        dir_par = direcao_par(par, ev["cur"], verd)
        cls_dir = "pair-buy" if dir_par == "BUY" else "pair-sell"
        with cols[j % 3]:
            st.markdown(f"""
            <div class="pair-card" style="margin-bottom:8px;">
              <span class="pair-name">{par[:3]}/{par[3:]}</span>
              <span class="{cls_dir}">{dir_par}</span>
            </div>
            """, unsafe_allow_html=True)

# Disclaimer + footer
st.markdown('<hr style="margin:20px 0 16px;">', unsafe_allow_html=True)
st.markdown("""
<div class="disclaimer">
  ⚠ Análise baseada em dados históricos via FRED API (Federal Reserve Bank of St. Louis).
  Scores calculados comparando a leitura mais recente de cada indicador com a média dos períodos anteriores.
  Não constitui recomendação de investimento. Toda decisão de entrada é de sua exclusiva responsabilidade.
</div>
""", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;letter-spacing:2px;padding:16px 0;">
  MacroSignal · <span style="color:#00e5a0;">Análise Fundamentalista</span> · FRED API · Federal Reserve Bank of St. Louis
</div>
""", unsafe_allow_html=True)

# Auto-refresh a cada 60s
time.sleep(0)
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)
