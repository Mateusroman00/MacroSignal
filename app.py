import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, timezone

st.set_page_config(page_title="MacroSignal", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

FRED_KEY = st.secrets.get("FRED_API_KEY", "")

# ── FRED ─────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fred_obs(series_id, limit=20):
    if not FRED_KEY:
        return []
    try:
        r = requests.get("https://api.stlouisfed.org/fred/series/observations", params={
            "series_id": series_id, "api_key": FRED_KEY,
            "file_type": "json", "sort_order": "asc", "limit": limit
        }, timeout=10)
        return [
            (o["date"], float(o["value"]))
            for o in r.json().get("observations", [])
            if o["value"] not in (".", "")
        ]
    except Exception:
        return []

def delta_de_lista(vals, direcao=1):
    if len(vals) < 2:
        return 0.0
    recente = vals[-1]
    media   = sum(vals[:-1]) / len(vals[:-1])
    if media == 0:
        return 0.0
    return max(-1.0, min(1.0, (recente - media) / abs(media) * 10)) * direcao

EVENTOS = {
    "USD": [
        {"id":"nfp",       "nome":"NFP / NON-FARM PAYROLLS",       "tipo":"PAYROLL"},
        {"id":"cpi_usd",   "nome":"CPI - INFLACAO EUA",            "tipo":"CPI"},
        {"id":"fomc",      "nome":"FOMC - DECISAO DE JUROS",       "tipo":"JUROS"},
        {"id":"fomc_min",  "nome":"FOMC MINUTES",                  "tipo":"JUROS"},
        {"id":"pce",       "nome":"PCE - CORE PRICE INDEX",        "tipo":"CPI"},
        {"id":"gdp_usd",   "nome":"GDP - PIB EUA",                 "tipo":"GDP"},
        {"id":"retail_usd","nome":"RETAIL SALES - VENDAS VAREJO",  "tipo":"CONSUMO"},
        {"id":"ism_mfg",   "nome":"ISM MANUFACTURING PMI",         "tipo":"PMI"},
        {"id":"ism_svc",   "nome":"ISM SERVICES PMI",              "tipo":"PMI"},
        {"id":"jolts",     "nome":"JOLTS JOB OPENINGS",            "tipo":"PAYROLL"},
        {"id":"ppi_usd",   "nome":"PPI - PRODUCER PRICE INDEX",    "tipo":"CPI"},
        {"id":"unemp_usd", "nome":"UNEMPLOYMENT RATE",             "tipo":"PAYROLL"},
    ],
    "EUR": [
        {"id":"bce",       "nome":"BCE - DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_eur",   "nome":"CPI - INFLACAO ZONA EURO",      "tipo":"CPI"},
        {"id":"gdp_eur",   "nome":"GDP - PIB ZONA EURO",           "tipo":"GDP"},
        {"id":"pmi_eur",   "nome":"FLASH PMI ZONA EURO",           "tipo":"PMI"},
        {"id":"ifo",       "nome":"IFO - CLIMA NEGOCIOS ALEMANHA", "tipo":"CONFIANCA"},
        {"id":"zew",       "nome":"ZEW - SENTIMENTO ECONOMICO",    "tipo":"CONFIANCA"},
        {"id":"retail_eur","nome":"RETAIL SALES - ZONA EURO",      "tipo":"CONSUMO"},
        {"id":"unemp_eur", "nome":"UNEMPLOYMENT RATE ZONA EURO",   "tipo":"PAYROLL"},
    ],
    "GBP": [
        {"id":"boe",       "nome":"BOE - DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_gbp",   "nome":"CPI - INFLACAO UK",             "tipo":"CPI"},
        {"id":"gdp_gbp",   "nome":"GDP - PIB UK",                  "tipo":"GDP"},
        {"id":"retail_gbp","nome":"RETAIL SALES UK",               "tipo":"CONSUMO"},
        {"id":"pmi_gbp",   "nome":"FLASH PMI UK",                  "tipo":"PMI"},
        {"id":"unemp_gbp", "nome":"CLAIMANT COUNT / DESEMPREGO UK","tipo":"PAYROLL"},
        {"id":"rpi_gbp",   "nome":"RPI - RETAIL PRICE INDEX UK",   "tipo":"CPI"},
    ],
    "AUD": [
        {"id":"rba",       "nome":"RBA - DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_aud",   "nome":"CPI - INFLACAO AUSTRALIA",      "tipo":"CPI"},
        {"id":"emp_aud",   "nome":"EMPLOYMENT CHANGE AUSTRALIA",   "tipo":"PAYROLL"},
        {"id":"gdp_aud",   "nome":"GDP - PIB AUSTRALIA",           "tipo":"GDP"},
        {"id":"retail_aud","nome":"RETAIL SALES AUSTRALIA",        "tipo":"CONSUMO"},
        {"id":"trade_aud", "nome":"TRADE BALANCE AUSTRALIA",       "tipo":"COMERCIO"},
    ],
    "NZD": [
        {"id":"rbnz",      "nome":"RBNZ - DECISAO DE JUROS",       "tipo":"JUROS"},
        {"id":"cpi_nzd",   "nome":"CPI - INFLACAO NZ",             "tipo":"CPI"},
        {"id":"gdp_nzd",   "nome":"GDP - PIB NZ",                  "tipo":"GDP"},
        {"id":"emp_nzd",   "nome":"EMPLOYMENT CHANGE NZ",          "tipo":"PAYROLL"},
        {"id":"trade_nzd", "nome":"TRADE BALANCE NZ",              "tipo":"COMERCIO"},
    ],
    "CAD": [
        {"id":"boc",       "nome":"BOC - DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_cad",   "nome":"CPI - INFLACAO CANADA",         "tipo":"CPI"},
        {"id":"emp_cad",   "nome":"EMPLOYMENT CHANGE CANADA",      "tipo":"PAYROLL"},
        {"id":"gdp_cad",   "nome":"GDP - PIB CANADA",              "tipo":"GDP"},
        {"id":"retail_cad","nome":"RETAIL SALES CANADA",           "tipo":"CONSUMO"},
    ],
    "CHF": [
        {"id":"snb",       "nome":"SNB - DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_chf",   "nome":"CPI - INFLACAO SUICA",          "tipo":"CPI"},
        {"id":"gdp_chf",   "nome":"GDP - PIB SUICA",               "tipo":"GDP"},
        {"id":"emp_chf",   "nome":"UNEMPLOYMENT RATE SUICA",       "tipo":"PAYROLL"},
    ],
    "JPY": [
        {"id":"boj",       "nome":"BOJ - DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_jpy",   "nome":"CPI - INFLACAO JAPAO",          "tipo":"CPI"},
        {"id":"gdp_jpy",   "nome":"GDP - PIB JAPAO",               "tipo":"GDP"},
        {"id":"tankan",    "nome":"TANKAN SURVEY",                  "tipo":"CONFIANCA"},
        {"id":"retail_jpy","nome":"RETAIL SALES JAPAO",            "tipo":"CONSUMO"},
        {"id":"unemp_jpy", "nome":"UNEMPLOYMENT RATE JAPAO",       "tipo":"PAYROLL"},
        {"id":"trade_jpy", "nome":"TRADE BALANCE JAPAO",           "tipo":"COMERCIO"},
    ],
}

SERIES = {
    "PAYROLL":  [("ADPWNUSNERSA",1),("IC4WSA",-1),("JTSJOL",1),("MANEMP",1),("AWHAETP",1)],
    "CPI":      [("PPIACO",1),("PCEPILFE",1),("IR",-1),("DCOILWTICO",1),("CES0500000003",1),("CUSR0000SAH1",1)],
    "JUROS":    [("PCEPILFE",1),("CPILFESL",1),("PAYEMS",1),("GDP",-1),("FEDFUNDS",1)],
    "GDP":      [("INDPRO",1),("UMCSENT",1),("PAYEMS",1),("RETAILSL",1),("PCEPILFE",-1)],
    "CONSUMO":  [("UMCSENT",1),("RETAILSL",1),("DSPIC96",1),("PCE",1),("TOTALSL",1)],
    "PMI":      [("INDPRO",1),("MANEMP",1),("NEWORDER",1),("AWHAETP",1),("AMTMNO",1)],
    "CONFIANCA":[("UMCSENT",1),("INDPRO",1),("PAYEMS",1),("DSPIC96",1),("PCE",1)],
    "COMERCIO": [("BOPGSTB",1),("IMP0002",-1),("EXP0002",1),("DCOILWTICO",-1),("TWEXBGSMTH",1)],
}

NOMES_IND = {
    "PAYROLL":  ["ADP PAYROLLS","JOBLESS CLAIMS","JOLTS VAGAS","ISM EMPLOYMENT","AVG WEEKLY HOURS"],
    "CPI":      ["PPI PRODUTOR","PCE CORE","IMPORT PRICES","PETROLEO WTI","AVG HOURLY EARNINGS","SHELTER"],
    "JUROS":    ["PCE CORE","CPI CORE","NFP EMPREGO","GDP","FED FUNDS RATE"],
    "GDP":      ["PRODUCAO INDUSTRIAL","CONFIANCA CONSUMIDOR","EMPREGO","VENDAS VAREJO","PCE INFLACAO"],
    "CONSUMO":  ["CONFIANCA CONSUMIDOR","RETAIL SALES","RENDA PESSOAL","GASTOS PESSOAIS","CREDITO TOTAL"],
    "PMI":      ["PRODUCAO INDUSTRIAL","EMPREGO MANUFATURA","NOVAS ORDENS","HORAS TRABALHADAS","ORDENS BENS DURAV"],
    "CONFIANCA":["SENTIMENTO CONSUMIDOR","PRODUCAO INDUSTRIAL","EMPREGO","RENDA PESSOAL","GASTOS PESSOAIS"],
    "COMERCIO": ["BALANCA COMERCIAL","IMPORTACOES","EXPORTACOES","PRECO PETROLEO","DOLAR INDEX"],
}

PESOS = {
    "PAYROLL":  [30,25,20,15,10],
    "CPI":      [25,25,15,15,10,10],
    "JUROS":    [30,25,20,15,10],
    "GDP":      [25,20,20,20,15],
    "CONSUMO":  [25,25,20,20,10],
    "PMI":      [30,25,20,15,10],
    "CONFIANCA":[30,20,20,20,10],
    "COMERCIO": [30,20,20,20,10],
}

@st.cache_data(ttl=3600)
def calcular_score(tipo):
    series  = SERIES.get(tipo, [])
    nomes   = NOMES_IND.get(tipo, [])
    pesos   = PESOS.get(tipo, [])
    total_w = score = 0.0
    inds = []
    for i, (sid, direcao) in enumerate(series):
        dados = fred_obs(sid, limit=7)
        vals  = [v for _, v in dados]
        w     = pesos[i] if i < len(pesos) else 10
        val   = delta_de_lista(vals, direcao) if len(vals) >= 2 else 0.0
        score   += val * w
        total_w += w
        inds.append({"nome": nomes[i] if i < len(nomes) else sid, "valor": val})
    return round(score / total_w if total_w else 0.0, 3), inds

@st.cache_data(ttl=3600)
def calcular_historico_score(tipo, n_periodos=12):
    series = SERIES.get(tipo, [])
    pesos  = PESOS.get(tipo, [])

    cache_series = {}
    for sid, _ in series:
        obs = fred_obs(sid, limit=n_periodos + 8)
        if obs:
            cache_series[sid] = obs

    if not cache_series:
        return []

    sid_ref   = max(cache_series, key=lambda s: len(cache_series[s]))
    datas_ref = [d for d, _ in cache_series[sid_ref]]

    inicio = max(2, len(datas_ref) - n_periodos)
    datas_calcular = datas_ref[inicio:]

    resultado = []
    for data_atual in datas_calcular:
        score_t = 0.0
        total_w = 0.0
        for i, (sid, direcao) in enumerate(series):
            w    = pesos[i] if i < len(pesos) else 10
            obs  = cache_series.get(sid, [])
            vals = [v for d, v in obs if d <= data_atual]
            if len(vals) < 2:
                continue
            val      = delta_de_lista(vals, direcao)
            score_t  += val * w
            total_w  += w
        if total_w > 0:
            resultado.append((data_atual, round(score_t / total_w, 3)))

    return resultado

# ── FX ────────────────────────────────────────────────────────
ORDEM_FX   = {"EUR":0,"GBP":1,"AUD":2,"NZD":3,"USD":4,"CAD":5,"CHF":6,"JPY":7}
CORRELATOS = {"USD":"CAD","CAD":"USD","AUD":"NZD","NZD":"AUD","EUR":"GBP","GBP":"EUR","CHF":"JPY","JPY":"CHF"}
TODAS_MOE  = ["USD","EUR","GBP","AUD","NZD","CAD","CHF","JPY"]

def canonico(a, b):
    return (a+b) if ORDEM_FX.get(a,99) < ORDEM_FX.get(b,99) else (b+a)

def get_portfolio(cur):
    return [canonico(cur, m) for m in TODAS_MOE if m != cur and m != CORRELATOS.get(cur)]

def veredicto(s):
    return "FORTE" if s > 0.2 else "FRACO" if s < -0.2 else "NEUTRO"

def direcao_par(par, cur, verd):
    if verd == "NEUTRO": return "NEUTRO"
    forte = verd == "FORTE"
    return ("BUY" if forte else "SELL") if par[:3] == cur else ("SELL" if forte else "BUY")

# ── GRÁFICO PLOTLY ────────────────────────────────────────────
def gerar_grafico_plotly(historico):
    if not historico or len(historico) < 2:
        return None

    datas  = [h[0] for h in historico]
    scores = [h[1] for h in historico]

    # Separar para área colorida acima/abaixo do zero
    scores_pos = [s if s >= 0 else 0 for s in scores]
    scores_neg = [s if s <= 0 else 0 for s in scores]

    cor_ultima = "#00e5a0" if scores[-1] >= 0 else "#ff4558"

    fig = go.Figure()

    # Área positiva (verde)
    fig.add_trace(go.Scatter(
        x=datas, y=scores_pos,
        fill="tozeroy",
        fillcolor="rgba(0,229,160,0.12)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Área negativa (vermelha)
    fig.add_trace(go.Scatter(
        x=datas, y=scores_neg,
        fill="tozeroy",
        fillcolor="rgba(255,69,88,0.12)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Linha colorida por segmento (verde quando positivo, vermelho quando negativo)
    for i in range(len(scores) - 1):
        mid = (scores[i] + scores[i + 1]) / 2
        cor = "#00e5a0" if mid >= 0 else "#ff4558"
        fig.add_trace(go.Scatter(
            x=[datas[i], datas[i + 1]],
            y=[scores[i], scores[i + 1]],
            mode="lines",
            line=dict(color=cor, width=2.5),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Pontos em cada período
    cores_pontos = ["#00e5a0" if s >= 0 else "#ff4558" for s in scores]
    tamanhos     = [10 if i == len(scores) - 1 else 6 for i in range(len(scores))]
    fig.add_trace(go.Scatter(
        x=datas, y=scores,
        mode="markers",
        marker=dict(
            color=cores_pontos,
            size=tamanhos,
            line=dict(color="#080c10", width=1.5),
        ),
        text=[f"{s:+.3f}" for s in scores],
        hovertemplate="<b>%{x}</b><br>Score: %{text}<extra></extra>",
        showlegend=False,
    ))

    # Linha zero de referência
    fig.add_hline(
        y=0,
        line=dict(color="#2a3a4a", width=1, dash="dot"),
    )

    # Anotação do último valor destacado
    fig.add_annotation(
        x=datas[-1], y=scores[-1],
        text=f"<b>{scores[-1]:+.3f}</b>",
        showarrow=True,
        arrowhead=0,
        arrowcolor=cor_ultima,
        arrowwidth=1,
        ax=0, ay=-34,
        font=dict(color=cor_ultima, size=12, family="DM Mono, monospace"),
        bgcolor="#080c10",
        bordercolor=cor_ultima,
        borderwidth=1,
        borderpad=5,
    )

    # Variação vs anterior
    if len(scores) >= 2:
        diff     = scores[-1] - scores[-2]
        seta     = "▲" if diff > 0.001 else "▼" if diff < -0.001 else "●"
        cor_diff = "#00e5a0" if diff > 0.001 else "#ff4558" if diff < -0.001 else "#4a5a6a"
        fig.add_annotation(
            x=datas[0], y=max(scores) + (max(scores) - min(scores)) * 0.15,
            text=f"<span style='color:{cor_diff}'>{seta} {diff:+.3f} vs anterior</span>",
            showarrow=False,
            font=dict(color=cor_diff, size=10, family="DM Mono, monospace"),
            xanchor="left",
        )

    margem = max(0.12, (max(scores) - min(scores)) * 0.22)
    y_min  = min(min(scores) - margem, -0.28)
    y_max  = max(max(scores) + margem,  0.28)

    fig.update_layout(
        height=280,
        margin=dict(l=55, r=20, t=30, b=45),
        paper_bgcolor="#0d1318",
        plot_bgcolor="#0d1318",
        font=dict(family="DM Mono, monospace", color="#4a5a6a", size=10),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#3a4a5a", size=9, family="DM Mono, monospace"),
            linecolor="#1a2530",
            tickcolor="#1a2530",
            tickangle=-30,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#0f1820",
            zeroline=False,
            tickfont=dict(color="#4a5a6a", size=9, family="DM Mono, monospace"),
            linecolor="#1a2530",
            range=[y_min, y_max],
            tickformat="+.2f",
            title=dict(text="SCORE", font=dict(color="#2a3540", size=9), standoff=8),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#111820",
            bordercolor="#1a2530",
            font=dict(color="#e8edf2", size=11, family="DM Mono, monospace"),
        ),
    )

    return fig


# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
:root{--bg:#080c10;--surface:#0d1318;--surface2:#111820;--border:#1a2530;--accent:#00e5a0;--red:#ff4558;--yellow:#ffd166;--text:#e8edf2;--muted:#4a5a6a;--muted2:#607a8a;}
.stApp{background:var(--bg)!important;}
.block-container{padding:24px 20px 60px!important;max-width:980px!important;}
.logo{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;letter-spacing:5px;color:#00e5a0;text-shadow:0 0 30px rgba(0,229,160,.4);}
.logo em{color:#e8edf2;font-style:normal;}
.slbl{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:3px;color:#4a5a6a;margin-bottom:8px;}
.badge{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:4px;padding:8px 22px;border-radius:6px;display:inline-block;}
.bf{background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.35);box-shadow:0 0 24px rgba(0,229,160,.1);}
.bfr{background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.35);box-shadow:0 0 24px rgba(255,69,88,.1);}
.bn{background:rgba(74,90,106,.2);color:#607a8a;border:1px solid #1a2530;}
.scl{font-family:'DM Mono',monospace;font-size:.65rem;color:#4a5a6a;text-align:right;margin-top:6px;}
.itl{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:3px;color:#4a5a6a;margin-bottom:12px;}
.inm{font-family:'DM Mono',monospace;font-size:.62rem;color:#607a8a;}
.pc{background:#111820;border:1px solid #1a2530;border-radius:6px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.pn{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:2px;color:#e8edf2;}
.pb{font-family:'Bebas Neue',sans-serif;font-size:.85rem;padding:3px 8px;border-radius:3px;background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.25);}
.ps{font-family:'Bebas Neue',sans-serif;font-size:.85rem;padding:3px 8px;border-radius:3px;background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.25);}
.disc{background:rgba(255,209,102,.04);border:1px solid rgba(255,209,102,.12);border-radius:6px;padding:12px 16px;font-family:'DM Mono',monospace;font-size:.6rem;color:rgba(255,209,102,.6);line-height:1.7;}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#00e5a0;box-shadow:0 0 8px #00e5a0;animation:pulse 2s infinite;}
div[data-testid="stSelectbox"] label{font-family:'DM Mono',monospace!important;font-size:.6rem!important;letter-spacing:3px!important;color:#4a5a6a!important;}
div[data-testid="stSelectbox"] > div > div{background:#0d1318!important;border-color:#1a2530!important;color:#e8edf2!important;font-family:'DM Mono',monospace!important;}
div[data-testid="stPlotlyChart"]{background:#0d1318;border:1px solid #1a2530;border-radius:10px;padding:8px;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
agora = datetime.now(timezone.utc)
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('<div class="logo">Macro<em>Signal</em></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:8px;">
      <span class="live-dot"></span>
      <span style="font-family:'DM Mono',monospace;font-size:.85rem;color:#e8edf2;letter-spacing:2px;margin-left:6px;">{agora.strftime('%H:%M')} UTC</span><br>
      <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;">ULTIMA ATUALIZACAO</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0 24px;">', unsafe_allow_html=True)

if not FRED_KEY:
    st.warning("FRED_API_KEY nao configurada. Va em Settings > Secrets.", icon="🔑")

# ── SELETORES ─────────────────────────────────────────────────
st.markdown('<div class="slbl">SELECIONE O EVENTO PARA ANALISAR</div>', unsafe_allow_html=True)
col_m, col_e = st.columns([1, 2])
with col_m:
    moeda = st.selectbox("MOEDA", list(EVENTOS.keys()), label_visibility="collapsed",
                         format_func=lambda x: f"  {x}")
with col_e:
    opcoes_ev = EVENTOS[moeda]
    nomes_ev  = [e["nome"] for e in opcoes_ev]
    idx_ev    = st.selectbox("EVENTO", range(len(nomes_ev)), label_visibility="collapsed",
                             format_func=lambda i: nomes_ev[i])

ev_sel = opcoes_ev[idx_ev]

# ── CALCULAR ──────────────────────────────────────────────────
with st.spinner("Buscando dados FRED API..."):
    score, inds = calcular_score(ev_sel["tipo"])
    historico   = calcular_historico_score(ev_sel["tipo"], n_periodos=12)

verd      = veredicto(score)
badge_cls = "bf" if verd == "FORTE" else "bfr" if verd == "FRACO" else "bn"
correlato = CORRELATOS.get(moeda, "-")
port      = get_portfolio(moeda)

st.markdown('<hr style="border-color:#1a2530;margin:8px 0 16px;">', unsafe_allow_html=True)

# ── CARD PRINCIPAL ────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])
with col_left:
    st.markdown(f"""
    <div style="padding:8px 0">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:2.8rem;letter-spacing:6px;color:#e8edf2;line-height:1;">{moeda}</div>
      <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#607a8a;letter-spacing:2px;margin-top:6px;">{ev_sel['nome']}</div>
      <div style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;margin-top:4px;">TIPO: {ev_sel['tipo']}</div>
    </div>
    """, unsafe_allow_html=True)
with col_right:
    variacao_html = ""
    if len(historico) >= 2:
        diff     = historico[-1][1] - historico[-2][1]
        seta     = "▲" if diff > 0.001 else "▼" if diff < -0.001 else "●"
        cor_var  = "#00e5a0" if diff > 0.001 else "#ff4558" if diff < -0.001 else "#607a8a"
        variacao_html = f'<div style="font-family:\'DM Mono\',monospace;font-size:.6rem;color:{cor_var};margin-top:6px;">{seta} {diff:+.3f} vs periodo anterior</div>'

    st.markdown(f"""
    <div style="text-align:right;padding:8px 0">
      <div class="badge {badge_cls}">{verd}</div>
      <div class="scl">SCORE ATUAL: {'+' if score >= 0 else ''}{score:.3f}</div>
      {variacao_html}
      <div class="scl" style="font-size:.5rem;margin-top:4px;">{'FRED API · ' + str(len(historico)) + ' PERIODOS' if FRED_KEY else 'SEM FRED_API_KEY'}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── GRÁFICO DE EVOLUÇÃO ───────────────────────────────────────
st.markdown(f'<div class="itl">EVOLUCAO DA ANALISE · {ev_sel["nome"]} · ULTIMOS {len(historico)} PERIODOS</div>', unsafe_allow_html=True)

fig = gerar_grafico_plotly(historico)
if fig:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("""
    <div style="display:flex;gap:24px;padding:0 4px 16px;margin-top:-12px;">
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:14px;height:2px;background:#00e5a0;border-radius:2px;"></div>
        <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#3a4a5a;letter-spacing:1px;">ANALISE POSITIVA</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:14px;height:2px;background:#ff4558;border-radius:2px;"></div>
        <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#3a4a5a;letter-spacing:1px;">ANALISE NEGATIVA</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:14px;border-top:1px dashed #2a3a4a;"></div>
        <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#3a4a5a;letter-spacing:1px;">LINHA ZERO</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#0d1318;border:1px solid #1a2530;border-radius:10px;padding:48px 24px;text-align:center;
    font-family:'DM Mono',monospace;font-size:.6rem;color:#2a3540;letter-spacing:2px;">
      SEM DADOS HISTORICOS SUFICIENTES<br>
      <span style="font-size:.55rem;">CONFIGURE A FRED_API_KEY EM SETTINGS > SECRETS</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:4px 0 16px;">', unsafe_allow_html=True)

# ── INDICADORES ───────────────────────────────────────────────
st.markdown('<div class="itl">INDICADORES ANTECEDENTES · FRED API</div>', unsafe_allow_html=True)

for ind in inds:
    val = ind["valor"]
    pct = min(100, abs(val) * 100)
    cor = "#00e5a0" if val > 0.05 else "#ff4558" if val < -0.05 else "#607a8a"
    arr = "+" if val > 0.05 else "-" if val < -0.05 else "="
    cn, cb2, ca2 = st.columns([3, 6, 1])
    with cn:
        st.markdown(f'<div class="inm" style="padding-top:4px;">{ind["nome"]}</div>', unsafe_allow_html=True)
    with cb2:
        st.markdown(f"""
        <div style="margin-top:8px;height:3px;background:#1a2530;border-radius:2px;">
          <div style="width:{pct:.0f}%;height:100%;background:{cor};border-radius:2px;box-shadow:0 0 6px {cor}66;"></div>
        </div>
        """, unsafe_allow_html=True)
    with ca2:
        st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:.7rem;color:{cor};text-align:right;padding-top:2px;font-weight:bold;">{arr}</div>', unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── PORTFÓLIO ─────────────────────────────────────────────────
if verd == "NEUTRO":
    st.markdown("""
    <div style="text-align:center;font-family:'DM Mono',monospace;font-size:.7rem;color:#4a5a6a;
    padding:28px;background:#0d1318;border:1px solid #1a2530;border-radius:8px;line-height:2;">
      SINAL NEUTRO<br>INDICADORES CONTRADITORIOS<br>
      <span style="font-size:.6rem;">MELHOR AGUARDAR CONFIRMACAO NO EVENTO</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f'<div class="itl">PORTFOLIO · {moeda} vs DEMAIS · SEM {correlato} (CORRELACIONADO)</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for j, par in enumerate(port):
        dp  = direcao_par(par, moeda, verd)
        cls = "pb" if dp == "BUY" else "ps"
        with cols[j % 3]:
            st.markdown(f"""
            <div class="pc">
              <span class="pn">{par[:3]}/{par[3:]}</span>
              <span class="{cls}">{dp}</span>
            </div>
            """, unsafe_allow_html=True)

# ── DISCLAIMER ────────────────────────────────────────────────
st.markdown('<hr style="border-color:#1a2530;margin:20px 0 16px;">', unsafe_allow_html=True)
st.markdown("""
<div class="disc">
  O grafico mostra como o score da analise cresceu ou diminuiu a cada novo dado divulgado.
  Para cada periodo, o score e recalculado usando somente os dados disponiveis ate aquela data.
  Fonte: FRED API - Federal Reserve Bank of St. Louis. Nao constitui recomendacao de investimento.
</div>
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;letter-spacing:2px;padding:16px 0;">
  MacroSignal · <span style="color:#00e5a0;">Analise Fundamentalista</span> · FRED API
</div>
""", unsafe_allow_html=True)
