import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="MacroSignal", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

FRED_KEY = st.secrets.get("FRED_API_KEY", "")

# ── JANELA TEMPORAL: últimos 3 anos ──────────────────────────
HOJE        = datetime.now(timezone.utc)
DATA_INICIO = (HOJE - timedelta(days=1095)).strftime("%Y-%m-%d")
DATA_FIM    = HOJE.strftime("%Y-%m-%d")

# ── FRED: observações recentes ───────────────────────────────
@st.cache_data(ttl=3600)
def fred_obs(series_id, limit=60):
    """Busca observações dos últimos 3 anos, ordem crescente."""
    if not FRED_KEY:
        return []
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id":         series_id,
                "api_key":           FRED_KEY,
                "file_type":         "json",
                "sort_order":        "desc",
                "observation_start": DATA_INICIO,
                "observation_end":   DATA_FIM,
                "limit":             limit,
            },
            timeout=10,
        )
        obs = [
            (o["date"], float(o["value"]))
            for o in r.json().get("observations", [])
            if o["value"] not in (".", "")
        ]
        obs.reverse()
        return obs
    except Exception:
        return []

# ── FRED: datas de release (calendário econômico real) ───────
@st.cache_data(ttl=3600)
def fred_release_dates(series_id):
    """
    Busca as datas REAIS de publicação (release dates) via FRED API.
    Endpoint: /fred/series/release → pega o release_id,
    depois     /fred/release/dates → retorna as datas de publicação.
    """
    if not FRED_KEY:
        return []
    try:
        # 1. Descobre o release vinculado à série
        r1 = requests.get(
            "https://api.stlouisfed.org/fred/series/release",
            params={"series_id": series_id, "api_key": FRED_KEY, "file_type": "json"},
            timeout=10,
        )
        releases = r1.json().get("releases", [])
        if not releases:
            return []
        release_id = releases[0]["id"]

        # 2. Busca as datas de release dentro da janela temporal
        r2 = requests.get(
            "https://api.stlouisfed.org/fred/release/dates",
            params={
                "release_id":    release_id,
                "api_key":       FRED_KEY,
                "file_type":     "json",
                "sort_order":    "desc",
                "realtime_start": DATA_INICIO,
                "realtime_end":   DATA_FIM,
                "include_release_dates_with_no_data": "true",
                "limit":         60,
            },
            timeout=10,
        )
        datas = [d["date"] for d in r2.json().get("release_dates", [])]
        datas.reverse()
        return datas
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

# ── CONFIGURAÇÃO DOS EVENTOS ──────────────────────────────────
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

# Séries FRED por tipo de análise
SERIES = {
    "PAYROLL":  [("PAYEMS",1),("UNRATE",-1),("JTSJOL",1),("ADPWNUSNERSA",1),("IC4WSA",-1)],
    "CPI":      [("CPIAUCSL",1),("PCEPILFE",1),("PPIACO",1),("DCOILWTICO",1),("CES0500000003",1),("CUSR0000SAH1",1)],
    "JUROS":    [("FEDFUNDS",1),("PCEPILFE",1),("CPILFESL",1),("PAYEMS",1),("GDP",-1)],
    "GDP":      [("GDP",1),("INDPRO",1),("PAYEMS",1),("RETAILSL",1),("PCEPILFE",-1)],
    "CONSUMO":  [("RETAILSL",1),("PCE",1),("UMCSENT",1),("DSPIC96",1),("TOTALSL",1)],
    "PMI":      [("INDPRO",1),("MANEMP",1),("NEWORDER",1),("AWHAETP",1),("AMTMNO",1)],
    "CONFIANCA":[("UMCSENT",1),("DSPIC96",1),("PCE",1),("PAYEMS",1),("INDPRO",1)],
    "COMERCIO": [("BOPGSTB",1),("EXP0002",1),("IMP0002",-1),("TWEXBGSMTH",1),("DCOILWTICO",-1)],
}

# Série principal por tipo → usada para buscar as release dates
SERIE_PRINCIPAL = {
    "PAYROLL":  "PAYEMS",
    "CPI":      "CPIAUCSL",
    "JUROS":    "FEDFUNDS",
    "GDP":      "GDP",
    "CONSUMO":  "RETAILSL",
    "PMI":      "INDPRO",
    "CONFIANCA":"UMCSENT",
    "COMERCIO": "BOPGSTB",
}

NOMES_IND = {
    "PAYROLL":  ["NFP EMPREGO","TAXA DESEMPREGO","JOLTS VAGAS","ADP PAYROLLS","JOBLESS CLAIMS"],
    "CPI":      ["CPI GERAL","PCE CORE","PPI PRODUTOR","PETROLEO WTI","AVG HOURLY EARNINGS","SHELTER"],
    "JUROS":    ["FED FUNDS RATE","PCE CORE","CPI CORE","NFP EMPREGO","GDP"],
    "GDP":      ["PIB REAL","PRODUCAO INDUSTRIAL","EMPREGO","VENDAS VAREJO","PCE INFLACAO"],
    "CONSUMO":  ["RETAIL SALES","GASTOS PESSOAIS","CONFIANCA CONSUMIDOR","RENDA PESSOAL","CREDITO TOTAL"],
    "PMI":      ["PRODUCAO INDUSTRIAL","EMPREGO MANUFATURA","NOVAS ORDENS","HORAS TRABALHADAS","ORDENS BENS DURAV"],
    "CONFIANCA":["SENTIMENTO CONSUMIDOR","RENDA PESSOAL","GASTOS PESSOAIS","EMPREGO","PRODUCAO INDUSTRIAL"],
    "COMERCIO": ["BALANCA COMERCIAL","EXPORTACOES","IMPORTACOES","DOLAR INDEX","PRECO PETROLEO"],
}

PESOS = {
    "PAYROLL":  [30,25,20,15,10],
    "CPI":      [25,25,15,15,10,10],
    "JUROS":    [30,25,20,15,10],
    "GDP":      [25,20,20,20,15],
    "CONSUMO":  [25,20,20,20,15],
    "PMI":      [30,25,20,15,10],
    "CONFIANCA":[30,20,20,20,10],
    "COMERCIO": [30,25,20,15,10],
}

# ── SCORE ATUAL ───────────────────────────────────────────────
@st.cache_data(ttl=3600)
def calcular_score(tipo):
    series  = SERIES.get(tipo, [])
    nomes   = NOMES_IND.get(tipo, [])
    pesos   = PESOS.get(tipo, [])
    total_w = score = 0.0
    inds = []
    ultima_data = ""
    for i, (sid, direcao) in enumerate(series):
        dados = fred_obs(sid, limit=36)
        vals  = [v for _, v in dados]
        datas = [d for d, _ in dados]
        w     = pesos[i] if i < len(pesos) else 10
        val   = delta_de_lista(vals, direcao) if len(vals) >= 2 else 0.0
        score   += val * w
        total_w += w
        data_serie = datas[-1] if datas else ""
        if data_serie > ultima_data:
            ultima_data = data_serie
        inds.append({
            "nome":        nomes[i] if i < len(nomes) else sid,
            "valor":       val,
            "ultima_data": data_serie,
            "ultimo_val":  vals[-1] if vals else None,
        })
    return round(score / total_w if total_w else 0.0, 3), inds, ultima_data

# ── HISTÓRICO ANCORADO NAS DATAS REAIS DE RELEASE ────────────
@st.cache_data(ttl=3600)
def calcular_historico_releases(tipo, n_periodos=24):
    """
    Para cada data real de RELEASE (publicação oficial),
    recalcula o score usando apenas dados disponíveis até aquela data.
    Isso ancora o gráfico no calendário econômico real.
    """
    series      = SERIES.get(tipo, [])
    pesos       = PESOS.get(tipo, [])
    serie_princ = SERIE_PRINCIPAL.get(tipo, series[0][0] if series else "")

    # Carregar todas as séries da janela temporal
    cache = {}
    for sid, _ in series:
        obs = fred_obs(sid, limit=60)
        if obs:
            cache[sid] = obs

    if not cache:
        return []

    # Buscar datas de release reais da FRED
    datas_release = fred_release_dates(serie_princ)

    # Fallback: usar datas das observações se release dates não disponível
    if not datas_release:
        sid_fb = serie_princ if serie_princ in cache else max(cache, key=lambda s: len(cache[s]))
        datas_release = [d for d, _ in cache.get(sid_fb, [])]

    # Filtrar para a janela e limitar aos últimos n_periodos
    datas_release = sorted(set(d for d in datas_release if DATA_INICIO <= d <= DATA_FIM))
    datas_release = datas_release[-n_periodos:]

    if len(datas_release) < 2:
        return []

    # Calcular score em cada data de release
    resultado = []
    for data_ref in datas_release:
        score_t = total_w = 0.0
        for i, (sid, direcao) in enumerate(series):
            w    = pesos[i] if i < len(pesos) else 10
            vals = [v for d, v in cache.get(sid, []) if d <= data_ref]
            if len(vals) < 2:
                continue
            val     = delta_de_lista(vals[-12:], direcao)
            score_t += val * w
            total_w += w
        if total_w > 0:
            resultado.append((data_ref, round(score_t / total_w, 3)))

    return resultado

# ── PRÓXIMA RELEASE + FORECAST ───────────────────────────────
@st.cache_data(ttl=3600)
def proxima_release(series_id):
    """Busca a próxima data de release programada (futura) da FRED."""
    if not FRED_KEY:
        return None
    try:
        r1 = requests.get(
            "https://api.stlouisfed.org/fred/series/release",
            params={"series_id": series_id, "api_key": FRED_KEY, "file_type": "json"},
            timeout=10,
        )
        releases = r1.json().get("releases", [])
        if not releases:
            return None
        release_id = releases[0]["id"]
        release_nome = releases[0].get("name", "")

        # Busca datas futuras
        amanha = (HOJE + timedelta(days=1)).strftime("%Y-%m-%d")
        futuro = (HOJE + timedelta(days=90)).strftime("%Y-%m-%d")
        r2 = requests.get(
            "https://api.stlouisfed.org/fred/release/dates",
            params={
                "release_id":    release_id,
                "api_key":       FRED_KEY,
                "file_type":     "json",
                "sort_order":    "asc",
                "realtime_start": amanha,
                "realtime_end":   futuro,
                "include_release_dates_with_no_data": "true",
                "limit":         5,
            },
            timeout=10,
        )
        datas = [d["date"] for d in r2.json().get("release_dates", [])]
        if datas:
            return {"data": datas[0], "release_nome": release_nome}
        return None
    except Exception:
        return None

def calcular_forecast(historico_scores, inds):
    """
    Gera forecast estatístico baseado em:
    - Tendência linear das últimas 6 releases
    - Média ponderada dos indicadores antecedentes
    - Momentum (aceleração/desaceleração)
    Retorna dict com forecast, confiança e sinal.
    """
    if len(historico_scores) < 3:
        return None

    ultimos = [s for _, s in historico_scores[-8:]]
    n = len(ultimos)

    # Tendência linear simples
    soma_x = sum(range(n))
    soma_y = sum(ultimos)
    soma_xy = sum(i * v for i, v in enumerate(ultimos))
    soma_x2 = sum(i*i for i in range(n))
    denom = n * soma_x2 - soma_x ** 2
    if denom != 0:
        slope = (n * soma_xy - soma_x * soma_y) / denom
    else:
        slope = 0.0

    # Forecast = último valor + slope (próximo passo)
    forecast_val = round(ultimos[-1] + slope, 3)
    forecast_val = max(-1.0, min(1.0, forecast_val))

    # Momentum: diferença média das últimas 3 variações
    variacoes = [ultimos[i] - ultimos[i-1] for i in range(1, len(ultimos))]
    momentum = sum(variacoes[-3:]) / 3 if len(variacoes) >= 3 else 0.0

    # Score dos indicadores antecedentes (já calculado)
    score_atual = ultimos[-1]

    # Confiança baseada na consistência direcional
    direcoes = [1 if v > 0 else -1 for v in ultimos[-6:]]
    consistencia = abs(sum(direcoes)) / len(direcoes)  # 0 a 1

    # Sinal composto
    if forecast_val > 0.2 and momentum > 0:
        sinal = "ALTA ACELERANDO"
        cor_sinal = "#00e5a0"
        emoji = "🚀"
    elif forecast_val > 0.2 and momentum <= 0:
        sinal = "ALTA DESACELERANDO"
        cor_sinal = "#7ecfa0"
        emoji = "📈"
    elif forecast_val < -0.2 and momentum < 0:
        sinal = "QUEDA ACELERANDO"
        cor_sinal = "#ff4558"
        emoji = "📉"
    elif forecast_val < -0.2 and momentum >= 0:
        sinal = "QUEDA DESACELERANDO"
        cor_sinal = "#ff8a94"
        emoji = "⚠️"
    elif abs(forecast_val) <= 0.2 and score_atual > 0.2:
        sinal = "REVERTENDO PARA NEUTRO"
        cor_sinal = "#ffd166"
        emoji = "↩️"
    elif abs(forecast_val) <= 0.2 and score_atual < -0.2:
        sinal = "RECUPERANDO PARA NEUTRO"
        cor_sinal = "#ffd166"
        emoji = "↪️"
    else:
        sinal = "LATERAL / INDEFINIDO"
        cor_sinal = "#607a8a"
        emoji = "➡️"

    # Alinhamento score vs forecast (surpresa potencial)
    alinhado = (score_atual > 0.2 and forecast_val > 0.2) or (score_atual < -0.2 and forecast_val < -0.2)
    divergente = (score_atual > 0.2 and forecast_val < -0.1) or (score_atual < -0.2 and forecast_val > 0.1)

    if alinhado:
        alinhamento = "ALINHADO"
        cor_ali = "#00e5a0"
        desc_ali = "Score e tendência apontam mesma direção → maior confiança na entrada"
    elif divergente:
        alinhamento = "DIVERGENTE"
        cor_ali = "#ff4558"
        desc_ali = "Score e tendência divergem → cautela, aguardar confirmação no evento"
    else:
        alinhamento = "NEUTRO"
        cor_ali = "#607a8a"
        desc_ali = "Sinal misto → operar apenas com confirmação técnica"

    return {
        "forecast":     forecast_val,
        "slope":        round(slope, 4),
        "momentum":     round(momentum, 4),
        "consistencia": round(consistencia * 100),
        "sinal":        sinal,
        "cor_sinal":    cor_sinal,
        "emoji":        emoji,
        "alinhamento":  alinhamento,
        "cor_ali":      cor_ali,
        "desc_ali":     desc_ali,
    }

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

def fmt_data(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return s

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&display=swap');
:root{--bg:#080c10;--surface:#0d1318;--border:#1a2530;--accent:#00e5a0;--red:#ff4558;--text:#e8edf2;--muted:#4a5a6a;--muted2:#607a8a;}
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
.ind-data{font-family:'DM Mono',monospace;font-size:.5rem;color:#2a3a4a;margin-top:2px;}
.pc{background:#111820;border:1px solid #1a2530;border-radius:6px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.pn{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:2px;color:#e8edf2;}
.pb{font-family:'Bebas Neue',sans-serif;font-size:.85rem;padding:3px 8px;border-radius:3px;background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.25);}
.ps{font-family:'Bebas Neue',sans-serif;font-size:.85rem;padding:3px 8px;border-radius:3px;background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.25);}
.disc{background:rgba(255,209,102,.04);border:1px solid rgba(255,209,102,.12);border-radius:6px;padding:12px 16px;font-family:'DM Mono',monospace;font-size:.6rem;color:rgba(255,209,102,.6);line-height:1.7;}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#00e5a0;box-shadow:0 0 8px #00e5a0;animation:pulse 2s infinite;}
.dtag{display:inline-block;font-family:'DM Mono',monospace;font-size:.52rem;color:#2a4a38;background:rgba(0,229,160,.06);border:1px solid rgba(0,229,160,.12);border-radius:3px;padding:1px 6px;margin-left:6px;}
.relbadge{font-family:'DM Mono',monospace;font-size:.5rem;color:#2a4a38;background:rgba(0,229,160,.08);border:1px solid rgba(0,229,160,.15);border-radius:3px;padding:1px 5px;}
div[data-testid="stSelectbox"] label{font-family:'DM Mono',monospace!important;font-size:.6rem!important;letter-spacing:3px!important;color:#4a5a6a!important;}
div[data-testid="stSelectbox"] > div > div{background:#0d1318!important;border-color:#1a2530!important;color:#e8edf2!important;font-family:'DM Mono',monospace!important;}
.chart-wrap{background:#0d1318;border:1px solid #1a2530;border-radius:10px;padding:16px 20px 8px;margin-bottom:8px;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('<div class="logo">Macro<em>Signal</em></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:8px;">
      <span class="live-dot"></span>
      <span style="font-family:'DM Mono',monospace;font-size:.85rem;color:#e8edf2;letter-spacing:2px;margin-left:6px;">{HOJE.strftime('%H:%M')} UTC</span><br>
      <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;">{HOJE.strftime('%d/%m/%Y')}</span>
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
with st.spinner("Buscando dados, releases e forecast da FRED API..."):
    score, inds, ultima_data_serie = calcular_score(ev_sel["tipo"])
    historico = calcular_historico_releases(ev_sel["tipo"], n_periodos=24)
    prox_rel  = proxima_release(SERIE_PRINCIPAL.get(ev_sel["tipo"], "PAYEMS"))
    forecast  = calcular_forecast(historico, inds)

verd      = veredicto(score)
badge_cls = "bf" if verd == "FORTE" else "bfr" if verd == "FRACO" else "bn"
correlato = CORRELATOS.get(moeda, "-")
port      = get_portfolio(moeda)

st.markdown('<hr style="border-color:#1a2530;margin:8px 0 16px;">', unsafe_allow_html=True)

# ── CARD PRINCIPAL ────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])
with col_left:
    data_ref    = fmt_data(ultima_data_serie) if ultima_data_serie else "—"
    serie_princ = SERIE_PRINCIPAL.get(ev_sel["tipo"], "—")
    st.markdown(f"""
    <div style="padding:8px 0">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:2.8rem;letter-spacing:6px;color:#e8edf2;line-height:1;">{moeda}</div>
      <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#607a8a;letter-spacing:2px;margin-top:6px;">{ev_sel['nome']}</div>
      <div style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;margin-top:4px;">TIPO: {ev_sel['tipo']} · REF: {serie_princ}</div>
      <div style="font-family:'DM Mono',monospace;font-size:.52rem;color:#2a5a3a;margin-top:6px;">
        <span style="color:#4a5a6a;">ULTIMO DADO:</span>
        <span class="dtag">{data_ref}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
with col_right:
    sinal_score = '+' if score >= 0 else ''
    fred_info_str = f"FRED API · {len(historico)} RELEASES" if FRED_KEY else "SEM FRED_API_KEY"

    # Monta bloco de variação separado
    bloco_var = ""
    if len(historico) >= 2:
        diff    = historico[-1][1] - historico[-2][1]
        dt_rec  = fmt_data(historico[-1][0])
        seta    = "▲" if diff > 0.001 else "▼" if diff < -0.001 else "●"
        cor_var = "#00e5a0" if diff > 0.001 else "#ff4558" if diff < -0.001 else "#607a8a"
        bloco_var = (
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.6rem;'
            f'color:{cor_var};margin-top:6px;">{seta} {diff:+.3f} vs release anterior</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;'
            f'color:#3a4a5a;margin-top:3px;">'
            f'<span class="relbadge">RELEASE: {dt_rec}</span></div>'
        )

    html_right = (
        '<div style="text-align:right;padding:8px 0">'
        f'<div class="badge {badge_cls}">{verd}</div>'
        f'<div class="scl">SCORE ATUAL: {sinal_score}{score:.3f}</div>'
        f'{bloco_var}'
        f'<div class="scl" style="font-size:.5rem;margin-top:4px;">{fred_info_str}</div>'
        '</div>'
    )
    st.markdown(html_right, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── GRÁFICO ANCORADO NAS DATAS DE RELEASE ────────────────────
if historico and len(historico) >= 2:
    datas  = [h[0] for h in historico]
    scores = [h[1] for h in historico]

    d_ini = fmt_data(datas[0])
    d_fim = fmt_data(datas[-1])

    st.markdown(f"""
    <div class="itl">
      EVOLUCAO POR RELEASE · {ev_sel['nome']}
      &nbsp;·&nbsp;
      <span style="color:#3a5a48;">{d_ini} → {d_fim}</span>
      &nbsp;·&nbsp; {len(historico)} RELEASES
    </div>
    """, unsafe_allow_html=True)

    datas_dt  = pd.to_datetime(datas)
    cor_linha = "#00e5a0" if scores[-1] >= 0 else "#ff4558"
    cor_fill  = "rgba(0,229,160,0.06)" if scores[-1] >= 0 else "rgba(255,69,88,0.06)"

    fig = go.Figure()

    # Área preenchida
    fig.add_trace(go.Scatter(
        x=datas_dt, y=scores,
        fill="tozeroy",
        fillcolor=cor_fill,
        line=dict(color=cor_linha, width=2),
        mode="lines+markers",
        marker=dict(color=cor_linha, size=5, line=dict(color="#080c10", width=1)),
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Score: %{y:+.3f}<extra></extra>",
    ))

    # Linha zero de referência
    fig.add_hline(
        y=0,
        line=dict(color="#1a2530", width=1, dash="dot"),
    )
    # Faixas de referência FORTE / FRACO
    fig.add_hrect(y0=0.2,  y1=1.0,  fillcolor="rgba(0,229,160,0.04)",  line_width=0)
    fig.add_hrect(y0=-1.0, y1=-0.2, fillcolor="rgba(255,69,88,0.04)", line_width=0)

    fig.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="#0d1318",
        plot_bgcolor="#0d1318",
        font=dict(family="DM Mono, monospace", color="#4a5a6a", size=10),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#3a4a5a", size=9),
            tickformat="%b/%y",
            linecolor="#1a2530",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#111820",
            zeroline=False,
            tickfont=dict(color="#3a4a5a", size=9),
            linecolor="#1a2530",
            tickformat="+.2f",
        ),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#111820",
            bordercolor="#1a2530",
            font=dict(color="#e8edf2", family="DM Mono, monospace", size=11),
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Últimas 6 releases como mini-cards ───────────────────
    ultimas = list(zip(datas, scores))[-6:]
    cols_r  = st.columns(len(ultimas))
    for k, (dt, sc) in enumerate(reversed(ultimas)):
        cor_sc  = "#00e5a0" if sc > 0.2 else "#ff4558" if sc < -0.2 else "#607a8a"
        vrd_m   = "FORTE" if sc > 0.2 else "FRACO" if sc < -0.2 else "NEUTRO"
        eh_atual = k == 0
        borda    = f"border-color:{'#00e5a0' if eh_atual else '#1a2530'};"
        with cols_r[k]:
            st.markdown(f"""
            <div style="background:#0d1318;border:1px solid;{borda}border-radius:6px;
                        padding:10px 8px;text-align:center;margin-top:8px;">
              <div style="font-family:'DM Mono',monospace;font-size:.46rem;color:#3a4a5a;margin-bottom:4px;">
                {fmt_data(dt)}{'<br><span style="color:#00e5a060;">● ATUAL</span>' if eh_atual else ''}
              </div>
              <div style="font-family:'Bebas Neue',sans-serif;font-size:1.1rem;
                          letter-spacing:2px;color:{cor_sc};">{sc:+.3f}</div>
              <div style="font-family:'DM Mono',monospace;font-size:.42rem;color:{cor_sc};opacity:.7;">{vrd_m}</div>
            </div>""", unsafe_allow_html=True)

    # ── Stats ────────────────────────────────────────────────
    col_a, col_b, col_c, col_d = st.columns(4)
    sc_max  = max(scores); sc_min = min(scores)
    sc_fim  = scores[-1];  var_tot = scores[-1] - scores[0]
    cor_tot = "#00e5a0" if var_tot > 0 else "#ff4558" if var_tot < 0 else "#607a8a"

    def stat_card(label, valor, cor="#607a8a"):
        return f"""
        <div style="background:#0d1318;border:1px solid #1a2530;border-radius:8px;
                    padding:12px 14px;text-align:center;margin-top:10px;">
          <div style="font-family:'DM Mono',monospace;font-size:.5rem;letter-spacing:2px;
                      color:#3a4a5a;margin-bottom:6px;">{label}</div>
          <div style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;
                      letter-spacing:3px;color:{cor};">{valor}</div>
        </div>"""

    with col_a: st.markdown(stat_card("ATUAL",      f"{sc_fim:+.3f}", cor_linha), unsafe_allow_html=True)
    with col_b: st.markdown(stat_card("MAXIMO",     f"{sc_max:+.3f}", "#00e5a0"), unsafe_allow_html=True)
    with col_c: st.markdown(stat_card("MINIMO",     f"{sc_min:+.3f}", "#ff4558"), unsafe_allow_html=True)
    with col_d: st.markdown(stat_card("VAR. TOTAL", f"{var_tot:+.3f}", cor_tot),  unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="background:#0d1318;border:1px solid #1a2530;border-radius:10px;padding:48px 24px;
    text-align:center;font-family:'DM Mono',monospace;font-size:.6rem;color:#2a3540;letter-spacing:2px;">
      SEM DADOS SUFICIENTES NA JANELA 2023–2026<br>
      <span style="font-size:.55rem;">CONFIGURE A FRED_API_KEY EM SETTINGS > SECRETS</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── INDICADORES ───────────────────────────────────────────────
st.markdown('<div class="itl">INDICADORES ANTECEDENTES · DADOS REAIS · FRED API</div>', unsafe_allow_html=True)

for ind in inds:
    val     = ind["valor"]
    pct     = min(100, abs(val) * 100)
    cor     = "#00e5a0" if val > 0.05 else "#ff4558" if val < -0.05 else "#607a8a"
    arr     = "+" if val > 0.05 else "−" if val < -0.05 else "="
    dt_ind  = fmt_data(ind.get("ultima_data","")) if ind.get("ultima_data") else "—"
    ult_val = ind.get("ultimo_val")
    val_fmt = f"{ult_val:,.2f}" if ult_val is not None else "—"

    cn, cb2, ca2 = st.columns([3, 5, 2])
    with cn:
        st.markdown(f"""
        <div style="padding-top:4px;">
          <div class="inm">{ind['nome']}</div>
          <div class="ind-data">📅 {dt_ind} &nbsp;·&nbsp; <span style="color:#3a5a48;">{val_fmt}</span></div>
        </div>""", unsafe_allow_html=True)
    with cb2:
        st.markdown(f"""
        <div style="margin-top:10px;height:3px;background:#1a2530;border-radius:2px;">
          <div style="width:{pct:.0f}%;height:100%;background:{cor};border-radius:2px;
                      box-shadow:0 0 6px {cor}66;"></div>
        </div>""", unsafe_allow_html=True)
    with ca2:
        st.markdown(f"""
        <div style="font-family:DM Mono,monospace;font-size:.7rem;color:{cor};
                    text-align:right;padding-top:4px;font-weight:bold;">{arr} {val:+.3f}</div>""",
                    unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── PRÓXIMO EVENTO + FORECAST ─────────────────────────────────
st.markdown('<div class="itl">PROXIMO EVENTO · FORECAST vs SCORE ATUAL</div>', unsafe_allow_html=True)

if forecast:
    fc = forecast
    dias_para_evento = "—"
    data_evento_fmt  = "—"
    release_nome_str = ""

    if prox_rel:
        try:
            dt_ev = datetime.strptime(prox_rel["data"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            dias_para_evento = (dt_ev - HOJE).days
            data_evento_fmt  = fmt_data(prox_rel["data"])
            release_nome_str = prox_rel.get("release_nome", "")
        except Exception:
            pass

    # Linha 1: próxima data + countdown
    if prox_rel:
        urgencia_cor = "#ff4558" if isinstance(dias_para_evento, int) and dias_para_evento <= 3 else \
                       "#ffd166" if isinstance(dias_para_evento, int) and dias_para_evento <= 7 else "#607a8a"
        countdown_html = (
            f'<div style="background:#0d1318;border:1px solid #1a2530;border-radius:8px;'
            f'padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
            f'<div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.52rem;color:#4a5a6a;letter-spacing:2px;">PROXIMA RELEASE</div>'
            f'<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1.4rem;letter-spacing:4px;color:#e8edf2;margin-top:4px;">{data_evento_fmt}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;color:#3a4a5a;margin-top:2px;">{release_nome_str}</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.52rem;color:#4a5a6a;">FALTAM</div>'
            f'<div style="font-family:\'Bebas Neue\',sans-serif;font-size:2rem;letter-spacing:4px;color:{urgencia_cor};">'
            f'{dias_para_evento if isinstance(dias_para_evento, int) else "—"}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;color:#3a4a5a;">DIAS</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(countdown_html, unsafe_allow_html=True)

    # Linha 2: 4 cards — Score Atual | Forecast | Sinal | Alinhamento
    c1f, c2f, c3f, c4f = st.columns(4)

    cor_sc_at = "#00e5a0" if score > 0.2 else "#ff4558" if score < -0.2 else "#607a8a"
    cor_fc    = "#00e5a0" if fc["forecast"] > 0.2 else "#ff4558" if fc["forecast"] < -0.2 else "#607a8a"
    vrd_fc    = "FORTE" if fc["forecast"] > 0.2 else "FRACO" if fc["forecast"] < -0.2 else "NEUTRO"

    with c1f:
        st.markdown(
            f'<div style="background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;color:#3a4a5a;letter-spacing:2px;margin-bottom:6px;">SCORE ATUAL</div>'
            f'<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1.6rem;letter-spacing:3px;color:{cor_sc_at};">{score:+.3f}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.48rem;color:{cor_sc_at};margin-top:4px;">{verd}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c2f:
        st.markdown(
            f'<div style="background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;color:#3a4a5a;letter-spacing:2px;margin-bottom:6px;">FORECAST</div>'
            f'<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1.6rem;letter-spacing:3px;color:{cor_fc};">{fc["forecast"]:+.3f}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.48rem;color:{cor_fc};margin-top:4px;">{vrd_fc}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c3f:
        st.markdown(
            f'<div style="background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;color:#3a4a5a;letter-spacing:2px;margin-bottom:6px;">TENDENCIA</div>'
            f'<div style="font-family:\'Bebas Neue\',sans-serif;font-size:.95rem;letter-spacing:2px;color:{fc["cor_sinal"]};margin-top:6px;">{fc["emoji"]} {fc["sinal"]}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.46rem;color:#3a4a5a;margin-top:6px;">MOMENTUM {fc["momentum"]:+.4f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c4f:
        st.markdown(
            f'<div style="background:#0d1318;border:1px solid {fc["cor_ali"]}44;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.5rem;color:#3a4a5a;letter-spacing:2px;margin-bottom:6px;">ALINHAMENTO</div>'
            f'<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1.1rem;letter-spacing:3px;color:{fc["cor_ali"]};margin-top:6px;">{fc["alinhamento"]}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:.44rem;color:#3a4a5a;margin-top:6px;">CONSISTENCIA {fc["consistencia"]}%</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Bloco de interpretação operacional
    st.markdown(
        f'<div style="background:rgba(0,0,0,.3);border:1px solid {fc["cor_ali"]}33;border-radius:8px;'
        f'padding:14px 18px;margin-top:10px;">'
        f'<div style="font-family:\'DM Mono\',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;margin-bottom:6px;">INTERPRETACAO OPERACIONAL</div>'
        f'<div style="font-family:\'DM Mono\',monospace;font-size:.62rem;color:{fc["cor_ali"]};line-height:1.8;">'
        f'{fc["desc_ali"]}'
        f'</div>'
        f'<div style="margin-top:10px;display:flex;gap:20px;">'
        f'<div style="font-family:\'DM Mono\',monospace;font-size:.52rem;color:#3a4a5a;">'
        f'SLOPE &nbsp;<span style="color:#607a8a;">{fc["slope"]:+.4f}</span>'
        f'</div>'
        f'<div style="font-family:\'DM Mono\',monospace;font-size:.52rem;color:#3a4a5a;">'
        f'CONSISTENCIA DIRECIONAL &nbsp;<span style="color:#607a8a;">{fc["consistencia"]}%</span>'
        f'</div>'
        f'<div style="font-family:\'DM Mono\',monospace;font-size:.52rem;color:#3a4a5a;">'
        f'RELEASES ANALISADAS &nbsp;<span style="color:#607a8a;">{len(historico)}</span>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

else:
    st.markdown(
        '<div style="background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:20px;'
        'text-align:center;font-family:\'DM Mono\',monospace;font-size:.6rem;color:#2a3540;">'
        'DADOS INSUFICIENTES PARA CALCULAR FORECAST</div>',
        unsafe_allow_html=True
    )

st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)

# ── PORTFÓLIO ─────────────────────────────────────────────────
if verd == "NEUTRO":
    st.markdown("""
    <div style="text-align:center;font-family:'DM Mono',monospace;font-size:.7rem;color:#4a5a6a;
    padding:28px;background:#0d1318;border:1px solid #1a2530;border-radius:8px;line-height:2;">
      SINAL NEUTRO · INDICADORES CONTRADITORIOS<br>
      <span style="font-size:.6rem;">AGUARDAR CONFIRMACAO NO EVENTO</span>
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
            </div>""", unsafe_allow_html=True)

# ── DISCLAIMER ────────────────────────────────────────────────
st.markdown('<hr style="border-color:#1a2530;margin:20px 0 16px;">', unsafe_allow_html=True)
st.markdown(f"""
<div class="disc">
  Dados via FRED API · Federal Reserve Bank of St. Louis.<br>
  O grafico exibe o score recalculado em cada data real de RELEASE (publicacao oficial) da serie de referencia.<br>
  As datas de release sao obtidas via /fred/release/dates, ancorando os pontos no calendario economico real.<br>
  Janela: {fmt_data(DATA_INICIO)} → {fmt_data(DATA_FIM)} · Atualizado: {HOJE.strftime('%d/%m/%Y %H:%M')} UTC.<br>
  Nao constitui recomendacao de investimento.
</div>
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;letter-spacing:2px;padding:16px 0;">
  MacroSignal · <span style="color:#00e5a0;">Analise Fundamentalista</span> · FRED API
</div>
""", unsafe_allow_html=True)
