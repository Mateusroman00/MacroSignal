import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="MacroSignal", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

# ── CHAVES ───────────────────────────────────────────────────
FRED_KEY = st.secrets.get("FRED_API_KEY", "")
FCS_KEY  = st.secrets.get("FCS_API_KEY", "")

# ── FRED API ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fred(series_id, limit=12):
    if not FRED_KEY:
        return None
    try:
        r = requests.get("https://api.stlouisfed.org/fred/series/observations", params={
            "series_id": series_id, "api_key": FRED_KEY,
            "file_type": "json", "sort_order": "desc", "limit": limit
        }, timeout=10)
        return [float(o["value"]) for o in r.json().get("observations", []) if o["value"] not in (".", "")]
    except Exception:
        return None

def delta(series_id, limit=6):
    vals = fred(series_id, limit)
    if not vals or len(vals) < 2:
        return 0.0
    recente, media = vals[0], sum(vals[1:]) / len(vals[1:])
    if media == 0:
        return 0.0
    return max(-1.0, min(1.0, (recente - media) / abs(media) * 10))

# ── SÉRIES FRED ───────────────────────────────────────────────
SERIES = {
    "PAYROLL": {"ADP PAYROLLS":("ADPWNUSNERSA",1),"JOBLESS CLAIMS":("IC4WSA",-1),"JOLTS VAGAS":("JTSJOL",1),"ISM EMPLOYMENT":("MANEMP",1),"AVG WEEKLY HOURS":("AWHAETP",1)},
    "CPI":     {"PPI (PRODUTOR)":("PPIACO",1),"PCE CORE":("PCEPILFE",1),"IMPORT PRICES":("IR",-1),"PETROLEO WTI":("DCOILWTICO",1),"AVG HOURLY EARNINGS":("CES0500000003",1),"SHELTER":("CUSR0000SAH1",1)},
    "JUROS":   {"PCE CORE":("PCEPILFE",1),"CPI CORE":("CPILFESL",1),"NFP EMPREGO":("PAYEMS",1),"GDP":("GDP",-1),"FEDFUNDS":("FEDFUNDS",1)},
}
PESOS = {"PAYROLL":[30,25,20,15,10],"CPI":[25,25,15,15,10,10],"JUROS":[30,25,20,15,10]}

@st.cache_data(ttl=3600)
def calcular_score(tipo):
    series, pesos = SERIES.get(tipo, {}), PESOS.get(tipo, [])
    total_w = score = 0.0
    inds = []
    for i, (nome, (sid, direcao)) in enumerate(series.items()):
        w = pesos[i] if i < len(pesos) else 10
        val = delta(sid) * direcao
        score += val * w
        total_w += w
        inds.append({"nome": nome, "valor": val})
    return round(score / total_w if total_w else 0.0, 3), inds

# ── FX ────────────────────────────────────────────────────────
CORRELATOS = {"USD":"CAD","CAD":"USD","AUD":"NZD","NZD":"AUD","EUR":"GBP","GBP":"EUR","CHF":"JPY","JPY":"CHF"}
ORDEM_FX   = ["EUR","GBP","AUD","NZD","USD","CAD","CHF","JPY"]
TODAS_MOE  = ["USD","EUR","GBP","AUD","NZD","CAD","CHF","JPY"]

def canonico(a, b):
    return (a+b) if ORDEM_FX.index(a) < ORDEM_FX.index(b) else (b+a)

def get_portfolio(cur):
    return [canonico(cur, m) for m in TODAS_MOE if m != cur and m != CORRELATOS.get(cur)]

def veredicto(s):
    return "FORTE" if s > 0.2 else "FRACO" if s < -0.2 else "NEUTRO"

def direcao_par(par, cur, verd):
    if verd == "NEUTRO": return "NEUTRO"
    forte = verd == "FORTE"
    return ("BUY" if forte else "SELL") if par[:3] == cur else ("SELL" if forte else "BUY")

# ── CALENDÁRIO VIA FCS API ────────────────────────────────────
KEYWORDS = {
    "USD": [
        (["Non-Farm Employment","Nonfarm Payroll"], "NFP / PAYROLL",    "PAYROLL"),
        (["Core CPI","CPI m/m","CPI y/y"],          "CPI — EUA",        "CPI"),
        (["Federal Funds Rate","FOMC Statement"],    "FOMC — JUROS EUA", "JUROS"),
        (["FOMC Meeting Minutes"],                   "FOMC — MINUTES",   "JUROS"),
    ],
    "EUR": [
        (["CPI Flash","Flash CPI","CPI Prelim","CPI y/y"], "CPI — ZONA EURO",  "CPI"),
        (["Main Refinancing Rate","ECB Rate"],              "BCE — JUROS EUR",  "JUROS"),
    ],
    "GBP": [
        (["CPI y/y","CPI m/m"],        "CPI — UK",         "CPI"),
        (["Official Bank Rate","BOE"], "BOE — JUROS GBP",  "JUROS"),
    ],
    "AUD": [
        (["CPI q/q","CPI y/y","Trimmed Mean"], "CPI — AUSTRALIA",  "CPI"),
        (["Cash Rate","RBA Rate"],              "RBA — JUROS AUD",  "JUROS"),
    ],
    "JPY": [
        (["Policy Rate","BOJ Rate","Overnight Call Rate"], "BOJ — JUROS JPY",  "JUROS"),
    ],
    "NZD": [
        (["Official Cash Rate","RBNZ Rate"], "RBNZ — JUROS NZD", "JUROS"),
    ],
    "CAD": [
        (["Overnight Rate","BOC Rate"], "BOC — JUROS CAD", "JUROS"),
    ],
}

@st.cache_data(ttl=1800)
def buscar_eventos():
    if not FCS_KEY:
        return [], False

    agora = datetime.now(timezone.utc)
    date_from = agora.strftime("%Y-%m-%d")
    date_to   = (agora + timedelta(days=45)).strftime("%Y-%m-%d")
    moedas    = "USD,EUR,GBP,AUD,JPY,NZD,CAD"

    try:
        url = "https://api-v4.fcsapi.com/forex/economy_cal"
        r = requests.get(url, params={
            "symbol":     moedas,
            "from_date":  date_from,
            "to_date":    date_to,
            "importance": "2",       # alto impacto
            "access_key": FCS_KEY,
        }, timeout=15)

        data = r.json()
        if not data.get("status") or not data.get("response"):
            return [], False

        eventos_encontrados = {}
        for item in data["response"]:
            titulo  = item.get("title", "") or item.get("event", "")
            moeda   = item.get("currency", "").upper()
            data_s  = item.get("date", "")

            if not titulo or not moeda or not data_s:
                continue

            # Parseia data
            try:
                dt = datetime.strptime(data_s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue

            # Match com keywords
            for kws, nome, tipo in KEYWORDS.get(moeda, []):
                if any(kw.lower() in titulo.lower() for kw in kws):
                    chave = f"{moeda}_{tipo}"
                    # Mantém o próximo evento futuro; se já tem passado, substitui por futuro
                    if chave not in eventos_encontrados:
                        eventos_encontrados[chave] = {
                            "id": chave, "cur": moeda, "nome": nome, "tipo": tipo,
                            "data": dt, "desc": dt.strftime("%d %b %Y · %H:%M UTC").upper()
                        }
                    else:
                        existente = eventos_encontrados[chave]["data"]
                        # Prefere futuro sobre passado, e mais próximo no futuro
                        if dt > agora and (existente < agora or dt < existente):
                            eventos_encontrados[chave] = {
                                "id": chave, "cur": moeda, "nome": nome, "tipo": tipo,
                                "data": dt, "desc": dt.strftime("%d %b %Y · %H:%M UTC").upper()
                            }
                    break

        return sorted(eventos_encontrados.values(), key=lambda x: x["data"]), True

    except Exception:
        return [], False

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
:root{--bg:#080c10;--surface:#0d1318;--surface2:#111820;--border:#1a2530;--accent:#00e5a0;--red:#ff4558;--yellow:#ffd166;--text:#e8edf2;--muted:#4a5a6a;--muted2:#607a8a;}
.stApp{background:var(--bg)!important;}
.block-container{padding:24px 20px 60px!important;max-width:960px!important;}
.logo{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;letter-spacing:5px;color:#00e5a0;text-shadow:0 0 30px rgba(0,229,160,.4);}
.logo em{color:#e8edf2;font-style:normal;}
.slbl{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:3px;color:#4a5a6a;margin-bottom:8px;}
.evrow{background:#0d1318;border:1px solid #1a2530;border-radius:8px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;border-left:3px solid #1a2530;}
.evrow.sel{border-left-color:#00e5a0;background:rgba(0,229,160,.04);border-color:rgba(0,229,160,.3);}
.evrow.past{opacity:0.4;}
.evcur{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:3px;padding:4px 10px;border-radius:4px;border:1px solid #1a2530;color:#607a8a;background:#111820;min-width:52px;text-align:center;display:inline-block;}
.evnm{font-family:'Bebas Neue',sans-serif;font-size:1.05rem;letter-spacing:2px;color:#e8edf2;}
.evdt{font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;margin-top:2px;}
.evcd{font-family:'Bebas Neue',sans-serif;font-size:1.25rem;letter-spacing:2px;color:#ffd166;text-align:right;}
.evcdl{font-family:'DM Mono',monospace;font-size:.52rem;color:#4a5a6a;letter-spacing:2px;text-align:right;}
.badge{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:4px;padding:8px 22px;border-radius:6px;display:inline-block;}
.bf{background:rgba(0,229,160,.12);color:#00e5a0;border:1px solid rgba(0,229,160,.35);}
.bfr{background:rgba(255,69,88,.12);color:#ff4558;border:1px solid rgba(255,69,88,.35);}
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
.sbadge{font-family:'DM Mono',monospace;font-size:.55rem;padding:3px 8px;border-radius:3px;display:inline-block;margin-bottom:12px;}
.sl{background:rgba(0,229,160,.08);color:#00e5a0;border:1px solid rgba(0,229,160,.2);}
.sf{background:rgba(255,209,102,.08);color:#ffd166;border:1px solid rgba(255,209,102,.2);}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
div[data-testid="stVerticalBlock"]{gap:0!important;}
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
      <span style="font-family:'DM Mono',monospace;font-size:.85rem;color:#e8edf2;letter-spacing:2px;margin-left:6px;">{agora.strftime('%H:%M:%S')}</span><br>
      <span style="font-family:'DM Mono',monospace;font-size:.55rem;color:#4a5a6a;letter-spacing:2px;">UTC · AO VIVO</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border-color:#1a2530;margin:16px 0 24px;">', unsafe_allow_html=True)

# ── ALERTAS ───────────────────────────────────────────────────
if not FRED_KEY:
    st.warning("FRED_API_KEY nao configurada. Va em Settings > Secrets.", icon="🔑")
if not FCS_KEY:
    st.warning("FCS_API_KEY nao configurada. Cadastre em fcsapi.com e adicione em Settings > Secrets.", icon="📅")

# ── BUSCAR EVENTOS ────────────────────────────────────────────
with st.spinner("Buscando calendario economico..."):
    EVENTOS, sucesso = buscar_eventos()

if sucesso and EVENTOS:
    st.markdown('<div class="sbadge sl">FCS API - CALENDARIO AO VIVO</div>', unsafe_allow_html=True)
elif not FCS_KEY:
    st.markdown('<div class="sbadge sf">CONFIGURE FCS_API_KEY PARA CALENDARIO AO VIVO</div>', unsafe_allow_html=True)
    EVENTOS = []
else:
    st.markdown('<div class="sbadge sf">ERRO NA FCS API - TENTE NOVAMENTE</div>', unsafe_allow_html=True)
    EVENTOS = []

# ── SELEÇÃO DE EVENTO ─────────────────────────────────────────
if EVENTOS:
    if "evento_idx" not in st.session_state:
        idx = next((i for i, e in enumerate(EVENTOS) if e["data"] > agora), 0)
        st.session_state.evento_idx = idx

    st.markdown('<div class="slbl">PROXIMOS EVENTOS DE ALTO IMPACTO</div>', unsafe_allow_html=True)

    DIAS  = ["SEG","TER","QUA","QUI","SEX","SAB","DOM"]
    MESES = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]

    for i, ev in enumerate(EVENTOS):
        diff  = ev["data"] - agora
        total = int(diff.total_seconds())
        past  = total <= 0

        if past:
            cd = '<span style="font-family:Bebas Neue,sans-serif;font-size:1rem;color:#4a5a6a;">ENCERRADO</span>'
        elif total < 172800:
            h, rem = divmod(total, 3600)
            m, s   = divmod(rem, 60)
            cd = f'<div class="evcd">{h:02d}:{m:02d}:{s:02d}</div><div class="evcdl">ATE O EVENTO</div>'
        else:
            dias = total // 86400
            h    = (total % 86400) // 3600
            cd = f'<div class="evcd">{dias}D {h:02d}H</div><div class="evcdl">ATE O EVENTO</div>'

        dt   = ev["data"]
        sel  = "sel" if i == st.session_state.evento_idx else ""
        pcls = "past" if past else ""
        fmt  = f"{DIAS[dt.weekday()]} {dt.day:02d} {MESES[dt.month-1]} - {dt.hour:02d}:{dt.minute:02d} UTC"

        st.markdown(f"""
        <div class="evrow {sel} {pcls}">
          <div style="display:flex;align-items:center;gap:14px;">
            <span class="evcur">{ev['cur']}</span>
            <div>
              <div class="evnm">{ev['nome']}</div>
              <div class="evdt">{fmt}</div>
            </div>
          </div>
          <div>{cd}</div>
        </div>
        """, unsafe_allow_html=True)

    # Seletor simples para trocar evento
    st.markdown("<br>", unsafe_allow_html=True)
    opcoes = [f"{e['cur']} - {e['nome']} ({e['data'].strftime('%d/%m %H:%M')})" for e in EVENTOS]
    escolha = st.selectbox("Selecionar evento para analise:", opcoes, index=st.session_state.evento_idx)
    st.session_state.evento_idx = opcoes.index(escolha)

    ev = EVENTOS[st.session_state.evento_idx]

    # ── ANÁLISE ───────────────────────────────────────────────
    st.markdown('<hr style="border-color:#1a2530;margin:20px 0 16px;">', unsafe_allow_html=True)
    st.markdown('<div class="slbl">ANALISE DO EVENTO SELECIONADO</div>', unsafe_allow_html=True)

    with st.spinner("Buscando dados FRED..."):
        score, inds = calcular_score(ev["tipo"])

    verd = veredicto(score)
    bc   = "bf" if verd == "FORTE" else "bfr" if verd == "FRACO" else "bn"
    port = get_portfolio(ev["cur"])

    ca, cb = st.columns([1, 1])
    with ca:
        st.markdown(f"""
        <div style="padding:8px 0">
          <div style="font-family:'Bebas Neue',sans-serif;font-size:2.6rem;letter-spacing:6px;color:#e8edf2;">{ev['cur']}</div>
          <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#607a8a;letter-spacing:2px;margin-top:4px;">{ev['nome']}</div>
        </div>
        """, unsafe_allow_html=True)
    with cb:
        st.markdown(f"""
        <div style="text-align:right;padding:8px 0">
          <div class="badge {bc}">{verd}</div>
          <div class="scl">SCORE: {'+' if score >= 0 else ''}{score:.3f}</div>
          <div class="scl" style="font-size:.5rem;">{'DADOS REAIS FRED API' if FRED_KEY else 'SEM FRED API KEY'}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1a2530;margin:12px 0;">', unsafe_allow_html=True)
    st.markdown('<div class="itl">INDICADORES ANTECEDENTES</div>', unsafe_allow_html=True)

    for ind in inds:
        val = ind["valor"]
        pct = min(100, abs(val) * 100)
        cor = "#00e5a0" if val > 0.05 else "#ff4558" if val < -0.05 else "#607a8a"
        arr = "A" if val > 0.05 else "V" if val < -0.05 else "-"
        cn, cb2, ca2 = st.columns([3, 6, 1])
        with cn:
            st.markdown(f'<div class="inm" style="padding-top:4px;">{ind["nome"]}</div>', unsafe_allow_html=True)
        with cb2:
            st.markdown(f'<div style="margin-top:8px;height:3px;background:#1a2530;border-radius:2px;"><div style="width:{pct:.0f}%;height:100%;background:{cor};border-radius:2px;"></div></div>', unsafe_allow_html=True)
        with ca2:
            st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:.65rem;color:{cor};text-align:right;padding-top:2px;">{arr}</div>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1a2530;margin:16px 0;">', unsafe_allow_html=True)
    correlato = CORRELATOS.get(ev["cur"], "-")

    if verd == "NEUTRO":
        st.markdown('<div style="text-align:center;font-family:DM Mono,monospace;font-size:.7rem;color:#4a5a6a;padding:24px;background:#0d1318;border:1px solid #1a2530;border-radius:8px;line-height:1.8;">SINAL NEUTRO - INDICADORES CONTRADITORIOS<br>MELHOR AGUARDAR ESTE EVENTO</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="itl">PORTFOLIO - {ev["cur"]} vs DEMAIS (SEM {correlato})</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for j, par in enumerate(port):
            dp  = direcao_par(par, ev["cur"], verd)
            cls = "pb" if dp == "BUY" else "ps"
            with cols[j % 3]:
                st.markdown(f'<div class="pc"><span class="pn">{par[:3]}/{par[3:]}</span><span class="{cls}">{dp}</span></div>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1a2530;margin:20px 0 16px;">', unsafe_allow_html=True)
    st.markdown("""
    <div class="disc">
      Calendario via FCS API (tempo real). Scores calculados com dados historicos da FRED API.
      Nao constitui recomendacao de investimento. Toda decisao e de sua exclusiva responsabilidade.
    </div>
    <div style="text-align:center;font-family:'DM Mono',monospace;font-size:.58rem;color:#4a5a6a;letter-spacing:2px;padding:16px 0;">
      MacroSignal - <span style="color:#00e5a0;">Analise Fundamentalista</span> - FCS API + FRED API
    </div>
    """, unsafe_allow_html=True)

st.markdown('<meta http-equiv="refresh" content="1800">', unsafe_allow_html=True)
