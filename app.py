import streamlit as st
import requests
from datetime import datetime, timezone

st.set_page_config(page_title="MacroSignal", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

FRED_KEY = st.secrets.get("FRED_API_KEY", "")

# ── FRED ─────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fred_obs(series_id, limit=20):
    """Retorna lista de (data, valor) ordenada do mais antigo ao mais recente."""
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
    """Calcula delta normalizado [-1, 1] a partir de uma lista de valores."""
    if len(vals) < 2:
        return 0.0
    recente = vals[-1]
    media   = sum(vals[:-1]) / len(vals[:-1])
    if media == 0:
        return 0.0
    return max(-1.0, min(1.0, (recente - media) / abs(media) * 10)) * direcao

# ── EVENTOS ───────────────────────────────────────────────────
EVENTOS = {
    "USD": [
        {"id":"nfp",       "nome":"NFP / NON-FARM PAYROLLS",       "tipo":"PAYROLL"},
        {"id":"cpi_usd",   "nome":"CPI — INFLACAO EUA",            "tipo":"CPI"},
        {"id":"fomc",      "nome":"FOMC — DECISAO DE JUROS",       "tipo":"JUROS"},
        {"id":"fomc_min",  "nome":"FOMC MINUTES",                  "tipo":"JUROS"},
        {"id":"pce",       "nome":"PCE — CORE PRICE INDEX",        "tipo":"CPI"},
        {"id":"gdp_usd",   "nome":"GDP — PIB EUA",                 "tipo":"GDP"},
        {"id":"retail_usd","nome":"RETAIL SALES — VENDAS VAREJO",  "tipo":"CONSUMO"},
        {"id":"ism_mfg",   "nome":"ISM MANUFACTURING PMI",         "tipo":"PMI"},
        {"id":"ism_svc",   "nome":"ISM SERVICES PMI",              "tipo":"PMI"},
        {"id":"jolts",     "nome":"JOLTS JOB OPENINGS",            "tipo":"PAYROLL"},
        {"id":"ppi_usd",   "nome":"PPI — PRODUCER PRICE INDEX",    "tipo":"CPI"},
        {"id":"unemp_usd", "nome":"UNEMPLOYMENT RATE",             "tipo":"PAYROLL"},
    ],
    "EUR": [
        {"id":"bce",       "nome":"BCE — DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_eur",   "nome":"CPI — INFLACAO ZONA EURO",      "tipo":"CPI"},
        {"id":"gdp_eur",   "nome":"GDP — PIB ZONA EURO",           "tipo":"GDP"},
        {"id":"pmi_eur",   "nome":"FLASH PMI ZONA EURO",           "tipo":"PMI"},
        {"id":"ifo",       "nome":"IFO — CLIMA NEGOCIOS ALEMANHA", "tipo":"CONFIANCA"},
        {"id":"zew",       "nome":"ZEW — SENTIMENTO ECONOMICO",    "tipo":"CONFIANCA"},
        {"id":"retail_eur","nome":"RETAIL SALES — ZONA EURO",      "tipo":"CONSUMO"},
        {"id":"unemp_eur", "nome":"UNEMPLOYMENT RATE ZONA EURO",   "tipo":"PAYROLL"},
    ],
    "GBP": [
        {"id":"boe",       "nome":"BOE — DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_gbp",   "nome":"CPI — INFLACAO UK",             "tipo":"CPI"},
        {"id":"gdp_gbp",   "nome":"GDP — PIB UK",                  "tipo":"GDP"},
        {"id":"retail_gbp","nome":"RETAIL SALES UK",               "tipo":"CONSUMO"},
        {"id":"pmi_gbp",   "nome":"FLASH PMI UK",                  "tipo":"PMI"},
        {"id":"unemp_gbp", "nome":"CLAIMANT COUNT / DESEMPREGO UK","tipo":"PAYROLL"},
        {"id":"rpi_gbp",   "nome":"RPI — RETAIL PRICE INDEX UK",   "tipo":"CPI"},
    ],
    "AUD": [
        {"id":"rba",       "nome":"RBA — DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_aud",   "nome":"CPI — INFLACAO AUSTRALIA",      "tipo":"CPI"},
        {"id":"emp_aud",   "nome":"EMPLOYMENT CHANGE AUSTRALIA",   "tipo":"PAYROLL"},
        {"id":"gdp_aud",   "nome":"GDP — PIB AUSTRALIA",           "tipo":"GDP"},
        {"id":"retail_aud","nome":"RETAIL SALES AUSTRALIA",        "tipo":"CONSUMO"},
        {"id":"trade_aud", "nome":"TRADE BALANCE AUSTRALIA",       "tipo":"COMERCIO"},
    ],
    "NZD": [
        {"id":"rbnz",      "nome":"RBNZ — DECISAO DE JUROS",       "tipo":"JUROS"},
        {"id":"cpi_nzd",   "nome":"CPI — INFLACAO NZ",             "tipo":"CPI"},
        {"id":"gdp_nzd",   "nome":"GDP — PIB NZ",                  "tipo":"GDP"},
        {"id":"emp_nzd",   "nome":"EMPLOYMENT CHANGE NZ",          "tipo":"PAYROLL"},
        {"id":"trade_nzd", "nome":"TRADE BALANCE NZ",              "tipo":"COMERCIO"},
    ],
    "CAD": [
        {"id":"boc",       "nome":"BOC — DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_cad",   "nome":"CPI — INFLACAO CANADA",         "tipo":"CPI"},
        {"id":"emp_cad",   "nome":"EMPLOYMENT CHANGE CANADA",      "tipo":"PAYROLL"},
        {"id":"gdp_cad",   "nome":"GDP — PIB CANADA",              "tipo":"GDP"},
        {"id":"retail_cad","nome":"RETAIL SALES CANADA",           "tipo":"CONSUMO"},
    ],
    "CHF": [
        {"id":"snb",       "nome":"SNB — DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_chf",   "nome":"CPI — INFLACAO SUICA",          "tipo":"CPI"},
        {"id":"gdp_chf",   "nome":"GDP — PIB SUICA",               "tipo":"GDP"},
        {"id":"emp_chf",   "nome":"UNEMPLOYMENT RATE SUICA",       "tipo":"PAYROLL"},
    ],
    "JPY": [
        {"id":"boj",       "nome":"BOJ — DECISAO DE JUROS",        "tipo":"JUROS"},
        {"id":"cpi_jpy",   "nome":"CPI — INFLACAO JAPAO",          "tipo":"CPI"},
        {"id":"gdp_jpy",   "nome":"GDP — PIB JAPAO",               "tipo":"GDP"},
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

# ── SCORE ATUAL ───────────────────────────────────────────────
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

# ── HISTÓRICO DO SCORE — 12 períodos reais ────────────────────
@st.cache_data(ttl=3600)
def calcular_historico_score(tipo, n_periodos=12):
    """
    Reconstrói o score ponderado para cada um dos últimos n_periodos pontos.
    Para cada data t, usa somente os dados disponíveis até t — sem ver o futuro.
    Retorna: [(data_str, score_float), ...] do mais antigo → mais recente.
    """
    series = SERIES.get(tipo, [])
    pesos  = PESOS.get(tipo, [])

    # Baixar histórico completo de cada série (mais dados = mais precisão no delta)
    cache_series = {}
    for sid, _ in series:
        obs = fred_obs(sid, limit=n_periodos + 8)
        if obs:
            cache_series[sid] = obs  # já vem ordenado do mais antigo

    if not cache_series:
        return []

    # Série de referência para definir as datas do eixo X
    sid_ref   = max(cache_series, key=lambda s: len(cache_series[s]))
    datas_ref = [d for d, _ in cache_series[sid_ref]]

    # Pegar os últimos n_periodos, mas garantir mínimo de histórico para o delta
    inicio = max(2, len(datas_ref) - n_periodos)
    datas_calcular = datas_ref[inicio:]

    resultado = []
    for data_atual in datas_calcular:
        score_t = 0.0
        total_w = 0.0

        for i, (sid, direcao) in enumerate(series):
            w    = pesos[i] if i < len(pesos) else 10
            obs  = cache_series.get(sid, [])
            # Valores disponíveis ATÉ essa data (inclusive) — simula o "mundo naquele dia"
            vals = [v for d, v in obs if d <= data_atual]

            if len(vals) < 2:
                continue

            val      = delta_de_lista(vals, direcao)
            score_t  += val * w
            total_w  += w

        if total_w > 0:
            resultado.append((data_atual, round(score_t / total_w, 3)))

    return resultado  # [(data, score), ...]

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

# ── GRÁFICO SVG ───────────────────────────────────────────────
def gerar_grafico_svg(historico, uid="c", W=860, H=240):
    """
    Gráfico de linha SVG puro mostrando a evolução do score período a período.
    - Verde quando score positivo, vermelho quando negativo
    - Linha zero como referência central
    - Ponto atual destacado com valor
    - Variação vs período anterior no canto
    """
    if not historico or len(historico) < 2:
        return ""

    datas  = [h[0] for h in historico]
    scores = [h[1] for h in historico]
    n      = len(scores)

    PL, PR, PT, PB = 54, 28, 32, 40
    WP = W - PL - PR
    HP = H - PT - PB

    raw_min = min(scores)
    raw_max = max(scores)
    margem  = max(0.1, (raw_max - raw_min) * 0.18)
    Y_MIN   = min(raw_min - margem, -0.2)
    Y_MAX   = max(raw_max + margem,  0.2)
    YR      = Y_MAX - Y_MIN

    def px(i): return PL + (i / (n - 1)) * WP
    def py(v): return PT + HP - ((v - Y_MIN) / YR) * HP

    y0  = py(0)
    pts = [(px(i), py(scores[i])) for i in range(n)]

    # ── Grid ──────────────────────────────────────────────────
    grid_svg = ""
    # Linhas de grade horizontais sutis
    for frac in [0.25, 0.5, 0.75]:
        gv  = Y_MIN + YR * frac
        gy  = py(gv)
        grid_svg += f'<line x1="{PL}" y1="{gy:.1f}" x2="{W-PR}" y2="{gy:.1f}" stroke="#0f1820" stroke-width="1"/>\n'
    # Linha zero destacada
    grid_svg += f'<line x1="{PL}" y1="{y0:.1f}" x2="{W-PR}" y2="{y0:.1f}" stroke="#2a3a4a" stroke-width="1" stroke-dasharray="5,5"/>\n'
    # Label zero
    grid_svg += f'<text x="{PL-8}" y="{y0+3:.1f}" text-anchor="end" font-family="DM Mono,monospace" font-size="9" fill="#3a4a5a">0.00</text>\n'

    # ── Áreas coloridas entre a linha e o zero ─────────────────
    areas_svg = ""
    for i in range(n - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        s1, s2 = scores[i], scores[i + 1]

        if (s1 >= 0 and s2 >= 0):
            cor = "#00e5a0"
            areas_svg += f'<polygon points="{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} {x2:.1f},{y0:.1f} {x1:.1f},{y0:.1f}" fill="{cor}" opacity="0.1"/>'
        elif (s1 < 0 and s2 < 0):
            cor = "#ff4558"
            areas_svg += f'<polygon points="{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} {x2:.1f},{y0:.1f} {x1:.1f},{y0:.1f}" fill="{cor}" opacity="0.1"/>'
        else:
            # Cruzamento do zero: interpolar o ponto de cruzamento
            t_cross = s1 / (s1 - s2)
            x_cross = x1 + t_cross * (x2 - x1)
            if s1 >= 0:
                areas_svg += f'<polygon points="{x1:.1f},{y1:.1f} {x_cross:.1f},{y0:.1f} {x1:.1f},{y0:.1f}" fill="#00e5a0" opacity="0.1"/>'
                areas_svg += f'<polygon points="{x_cross:.1f},{y0:.1f} {x2:.1f},{y2:.1f} {x2:.1f},{y0:.1f}" fill="#ff4558" opacity="0.1"/>'
            else:
                areas_svg += f'<polygon points="{x1:.1f},{y1:.1f} {x_cross:.1f},{y0:.1f} {x1:.1f},{y0:.1f}" fill="#ff4558" opacity="0.1"/>'
                areas_svg += f'<polygon points="{x_cross:.1f},{y0:.1f} {x2:.1f},{y2:.1f} {x2:.1f},{y0:.1f}" fill="#00e5a0" opacity="0.1"/>'

    # ── Segmentos coloridos da linha ───────────────────────────
    linha_svg = ""
    for i in range(n - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        s1, s2  = scores[i], scores[i + 1]
        mid     = (s1 + s2) / 2
        cor_seg = "#00e5a0" if mid >= 0 else "#ff4558"

        if (s1 >= 0) == (s2 >= 0):
            linha_svg += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{cor_seg}" stroke-width="2" stroke-linecap="round"/>\n'
        else:
            # Cruzamento: desenhar em duas cores
            t_cross = s1 / (s1 - s2)
            xc = x1 + t_cross * (x2 - x1)
            cor1 = "#00e5a0" if s1 >= 0 else "#ff4558"
            cor2 = "#ff4558" if s1 >= 0 else "#00e5a0"
            linha_svg += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{xc:.1f}" y2="{y0:.1f}" stroke="{cor1}" stroke-width="2" stroke-linecap="round"/>\n'
            linha_svg += f'<line x1="{xc:.1f}" y1="{y0:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{cor2}" stroke-width="2" stroke-linecap="round"/>\n'

    # ── Pontos em cada período ─────────────────────────────────
    pontos_svg = ""
    for i, (x, y) in enumerate(pts):
        sc  = scores[i]
        cor = "#00e5a0" if sc >= 0 else "#ff4558"
        if i == n - 1:
            # Último ponto: destacado com glow
            pontos_svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{cor}" opacity="0.08"/>\n'
            pontos_svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5"  fill="{cor}" opacity="0.3"/>\n'
            pontos_svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3"  fill="{cor}"/>\n'
        else:
            pontos_svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{cor}" opacity="0.6"/>\n'

    # ── Label do score atual ───────────────────────────────────
    lx_last, ly_last = pts[-1]
    sc_last  = scores[-1]
    cor_last = "#00e5a0" if sc_last >= 0 else "#ff4558"
    # Posicionar label acima ou abaixo conforme espaço
    label_offset = -18 if ly_last > PT + 22 else 20
    label_atual = f"""
    <rect x="{lx_last - 30:.1f}" y="{ly_last + label_offset - 12:.1f}" width="60" height="15"
          rx="3" fill="#080c10" stroke="{cor_last}" stroke-width="0.8"/>
    <text x="{lx_last:.1f}" y="{ly_last + label_offset:.1f}" text-anchor="middle"
          font-family="DM Mono,monospace" font-size="10" fill="{cor_last}" font-weight="500">{sc_last:+.3f}</text>
    """

    # ── Labels eixo X (datas) ──────────────────────────────────
    passo    = max(1, n // 7)
    labels_x = ""
    for i in range(n):
        if i % passo == 0 or i == n - 1:
            lx = px(i)
            dt = datas[i][5:]  # MM-DD
            labels_x += f'<text x="{lx:.1f}" y="{H - 10}" text-anchor="middle" font-family="DM Mono,monospace" font-size="9" fill="#3a4a5a">{dt}</text>\n'

    # ── Labels eixo Y ─────────────────────────────────────────
    labels_y = ""
    for lv in [Y_MAX * 0.7, Y_MIN * 0.7]:
        ly  = py(lv)
        cor = "#00e5a0" if lv > 0 else "#ff4558"
        labels_y += f'<text x="{PL-8}" y="{ly+3:.1f}" text-anchor="end" font-family="DM Mono,monospace" font-size="9" fill="{cor}">{lv:+.2f}</text>\n'

    # ── Variação vs anterior ───────────────────────────────────
    diff_label = ""
    if n >= 2:
        diff     = scores[-1] - scores[-2]
        seta     = "▲" if diff > 0.001 else "▼" if diff < -0.001 else "●"
        cor_diff = "#00e5a0" if diff > 0.001 else "#ff4558" if diff < -0.001 else "#4a5a6a"
        diff_label = f'<text x="{W - PR}" y="{PT - 10}" text-anchor="end" font-family="DM Mono,monospace" font-size="9" fill="{cor_diff}">{seta} {diff:+.3f} vs período anterior</text>'

    # ── Título do eixo Y ──────────────────────────────────────
    titulo_y = f'<text transform="rotate(-90)" x="{-(PT + HP/2):.1f}" y="12" text-anchor="middle" font-family="DM Mono,monospace" font-size="8" fill="#2a3540" letter-spacing="1">SCORE</text>'

    return f"""<svg width="100%" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;">
  {titulo_y}
  {grid_svg}
  {areas_svg}
  {linha_svg}
  {pontos_svg}
  {label_atual}
  {diff_label}
  {labels_x}
  {labels_y}
</svg>"""


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
.chart-box{background:#0d1318;border:1px solid #1a2530;border-radius:10px;padding:20px 24px;margin-bottom:8px;}
.chart-lbl{font-family:'DM Mono',monospace;font-size:.55rem;letter-spacing:3px;color:#3a4a5a;margin-bottom:14px;}
.chart-empty{font-family:'DM Mono',monospace;font-size:.6rem;color:#2a3540;text-align:center;padding:48px 0;letter-spacing:2px;}
div[data-testid="stSelectbox"] label{font-family:'DM Mono',monospace!important;font-size:.6rem!important;letter-spacing:3px!important;color:#4a5a6a!important;}
div[data-testid="stSelectbox"] > div > div{background:#0d1318!important;border-color:#1a2530!important;color:#e8edf2!important;font-family:'DM Mono',monospace!important;}
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
      <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;">ÚLTIMA ATUALIZAÇÃO</span>
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
        variacao_html = f'<div style="font-family:\'DM Mono\',monospace;font-size:.6rem;color:{cor_var};margin-top:6px;">{seta} {diff:+.3f} vs período anterior</div>'

    st.markdown(f"""
    <div style="text-align:right;padding:8px 0">
      <div class="badge {badge_cls}">{verd}</div>
      <div class="scl">SCORE ATUAL: {'+' if score >= 0 else ''}{score:.3f}</div>
      {variacao_html}
      <div class="scl" style="font-size:.5rem;margin-top:4px;">{'FRED API · ' + str(len(historico)) + ' PERÍODOS' if FRED_KEY else 'SEM FRED_API_KEY'}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── GRÁFICO DE EVOLUÇÃO DO SCORE ──────────────────────────────
st.markdown(f'<div class="itl">EVOLUÇÃO DA ANÁLISE · {ev_sel["nome"]} · ÚLTIMOS {len(historico)} PERÍODOS</div>', unsafe_allow_html=True)

if historico and len(historico) >= 2:
    svg = gerar_grafico_svg(historico, uid=ev_sel["id"])
    st.markdown(f'<div class="chart-box">{svg}</div>', unsafe_allow_html=True)

    # Legenda
    st.markdown("""
    <div style="display:flex;gap:24px;padding:2px 4px 16px;">
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:14px;height:2px;background:#00e5a0;border-radius:2px;"></div>
        <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#3a4a5a;letter-spacing:1px;">ANÁLISE POSITIVA</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:14px;height:2px;background:#ff4558;border-radius:2px;"></div>
        <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#3a4a5a;letter-spacing:1px;">ANÁLISE NEGATIVA</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:14px;height:0;border-top:1px dashed #2a3a4a;"></div>
        <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#3a4a5a;letter-spacing:1px;">LINHA ZERO (NEUTRO)</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="chart-box">
      <div class="chart-empty">
        SEM DADOS HISTÓRICOS SUFICIENTES<br>
        <span style="font-size:.55rem;color:#1a2530;">CONFIGURE A FRED_API_KEY EM SETTINGS → SECRETS</span>
      </div>
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
  O gráfico mostra como o score da análise cresceu ou diminuiu a cada novo dado divulgado.
  Para cada período, o score é recalculado usando somente os dados disponíveis até aquela data.
  Fonte: FRED API — Federal Reserve Bank of St. Louis. Não constitui recomendação de investimento.
</div>
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;letter-spacing:2px;padding:16px 0;">
  MacroSignal · <span style="color:#00e5a0;">Análise Fundamentalista</span> · FRED API
</div>
""", unsafe_allow_html=True)
