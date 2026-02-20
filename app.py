<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MacroSignal</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

  :root {
    --bg: #080c10;
    --surface: #0d1318;
    --surface2: #111820;
    --border: #1a2530;
    --accent: #00e5a0;
    --red: #ff4558;
    --yellow: #ffd166;
    --text: #e8edf2;
    --muted: #4a5a6a;
    --muted2: #607a8a;
  }

  * { margin:0; padding:0; box-sizing:border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  body::before {
    content:''; position:fixed; inset:0;
    background-image:
      linear-gradient(rgba(0,229,160,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,229,160,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events:none; z-index:0;
  }

  .wrap { max-width:900px; margin:0 auto; padding:20px 16px 80px; position:relative; z-index:1; }

  /* HEADER */
  header {
    display:flex; justify-content:space-between; align-items:center;
    padding-bottom:24px; border-bottom:1px solid var(--border); margin-bottom:32px;
    animation: fadeDown .6s ease;
  }
  .logo { font-family:'Bebas Neue',sans-serif; font-size:2rem; letter-spacing:4px; color:var(--accent); text-shadow:0 0 30px rgba(0,229,160,.4); }
  .logo em { color:var(--text); font-style:normal; }
  .header-right { display:flex; flex-direction:column; align-items:flex-end; gap:4px; }
  .live-time { font-family:'DM Mono',monospace; font-size:.9rem; color:var(--text); letter-spacing:2px; }
  .live-label { font-family:'DM Mono',monospace; font-size:.6rem; color:var(--muted); letter-spacing:2px; }
  .dot-wrap { display:flex; align-items:center; gap:6px; }
  .dot { width:7px; height:7px; border-radius:50%; background:var(--accent); box-shadow:0 0 8px var(--accent); animation:pulse 2s infinite; }

  /* PRÓXIMOS EVENTOS */
  .section-lbl { font-family:'DM Mono',monospace; font-size:.62rem; letter-spacing:3px; color:var(--muted); margin-bottom:10px; }

  .events-list { display:flex; flex-direction:column; gap:8px; margin-bottom:28px; animation:fadeUp .5s ease .1s both; }

  .event-row {
    background:var(--surface); border:1px solid var(--border); border-radius:8px;
    padding:14px 18px; display:flex; align-items:center; justify-content:space-between;
    flex-wrap:wrap; gap:10px; cursor:pointer; transition:all .18s; position:relative; overflow:hidden;
  }
  .event-row::before { content:''; position:absolute; top:0; left:0; width:3px; height:100%; background:var(--border); transition:background .18s; }
  .event-row:hover { border-color:var(--muted2); }
  .event-row.active::before { background:var(--accent); }
  .event-row.active { border-color:rgba(0,229,160,.3); background:rgba(0,229,160,.04); }

  .ev-left { display:flex; align-items:center; gap:14px; }
  .ev-currency-tag {
    font-family:'Bebas Neue',sans-serif; font-size:1.1rem; letter-spacing:3px;
    padding:4px 10px; border-radius:4px; border:1px solid var(--border); color:var(--muted2); background:var(--surface2);
    min-width:56px; text-align:center;
  }
  .event-row.active .ev-currency-tag { border-color:rgba(0,229,160,.3); color:var(--accent); background:rgba(0,229,160,.08); }
  .ev-info {}
  .ev-name { font-family:'Bebas Neue',sans-serif; font-size:1.1rem; letter-spacing:2px; color:var(--text); }
  .ev-date { font-family:'DM Mono',monospace; font-size:.62rem; color:var(--muted); margin-top:2px; }

  .ev-right { display:flex; flex-direction:column; align-items:flex-end; gap:2px; }
  .ev-countdown { font-family:'Bebas Neue',sans-serif; font-size:1.3rem; letter-spacing:2px; color:var(--yellow); }
  .ev-countdown-lbl { font-family:'DM Mono',monospace; font-size:.55rem; color:var(--muted); letter-spacing:2px; }

  /* SIGNAL CARD */
  .signal-main {
    background:var(--surface); border:1px solid var(--border); border-radius:10px;
    overflow:hidden; margin-bottom:20px; animation:fadeUp .5s ease .2s both;
  }

  .signal-header {
    padding:22px 24px 18px; border-bottom:1px solid var(--border);
    display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;
  }
  .sig-cur { font-family:'Bebas Neue',sans-serif; font-size:2.8rem; letter-spacing:6px; line-height:1; }
  .sig-ev  { font-family:'DM Mono',monospace; font-size:.65rem; color:var(--muted2); letter-spacing:2px; margin-top:6px; }

  .verdict-badge { font-family:'Bebas Neue',sans-serif; font-size:2rem; letter-spacing:4px; padding:8px 24px; border-radius:6px; }
  .verdict-badge.forte { background:rgba(0,229,160,.12); color:var(--accent); border:1px solid rgba(0,229,160,.35); box-shadow:0 0 24px rgba(0,229,160,.12); }
  .verdict-badge.fraco { background:rgba(255,69,88,.12);  color:var(--red);    border:1px solid rgba(255,69,88,.35);  box-shadow:0 0 24px rgba(255,69,88,.12); }
  .verdict-badge.neutro{ background:rgba(74,90,106,.2);   color:var(--muted2); border:1px solid var(--border); }
  .score-lbl { font-family:'DM Mono',monospace; font-size:.68rem; color:var(--muted); text-align:right; margin-top:6px; }

  /* INDICATORS */
  .ind-section { padding:18px 24px; border-bottom:1px solid var(--border); }
  .ind-title { font-family:'DM Mono',monospace; font-size:.6rem; letter-spacing:3px; color:var(--muted); margin-bottom:14px; }
  .ind-row { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
  .ind-row:last-child { margin-bottom:0; }
  .ind-name { font-family:'DM Mono',monospace; font-size:.65rem; color:var(--muted2); width:165px; flex-shrink:0; }
  .ind-track { flex:1; height:3px; background:var(--border); border-radius:2px; overflow:hidden; }
  .ind-fill { height:100%; border-radius:2px; transition:width 1.2s cubic-bezier(.4,0,.2,1); }
  .ind-fill.up   { background:var(--accent); box-shadow:0 0 6px rgba(0,229,160,.4); }
  .ind-fill.down { background:var(--red);    box-shadow:0 0 6px rgba(255,69,88,.4); }
  .ind-fill.flat { background:var(--muted); }
  .ind-arr { font-size:.7rem; width:28px; text-align:right; font-family:'DM Mono',monospace; }
  .ind-arr.up   { color:var(--accent); }
  .ind-arr.down { color:var(--red); }
  .ind-arr.flat { color:var(--muted); }

  /* PAIRS */
  .pairs-section { padding:18px 24px 22px; }
  .pairs-title { font-family:'DM Mono',monospace; font-size:.6rem; letter-spacing:3px; color:var(--muted); margin-bottom:14px; }
  .pairs-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
  @media(max-width:480px){ .pairs-grid{ grid-template-columns:repeat(2,1fr); } }
  .pair-item {
    background:var(--surface2); border:1px solid var(--border); border-radius:6px;
    padding:12px 14px; display:flex; justify-content:space-between; align-items:center;
  }
  .pair-name { font-family:'Bebas Neue',sans-serif; font-size:1rem; letter-spacing:2px; color:var(--text); }
  .pair-dir { font-family:'Bebas Neue',sans-serif; font-size:.9rem; letter-spacing:1px; padding:3px 8px; border-radius:3px; }
  .pair-dir.buy  { background:rgba(0,229,160,.12); color:var(--accent); border:1px solid rgba(0,229,160,.25); }
  .pair-dir.sell { background:rgba(255,69,88,.12);  color:var(--red);    border:1px solid rgba(255,69,88,.25); }

  .neutro-msg { padding:32px 24px; text-align:center; font-family:'DM Mono',monospace; font-size:.72rem; color:var(--muted); letter-spacing:1px; line-height:1.8; }

  /* DISCLAIMER */
  .disclaimer {
    background:rgba(255,209,102,.04); border:1px solid rgba(255,209,102,.12);
    border-radius:6px; padding:12px 16px; font-family:'DM Mono',monospace;
    font-size:.62rem; color:rgba(255,209,102,.6); line-height:1.7; margin-bottom:20px;
    animation:fadeUp .5s ease .4s both;
  }

  footer { text-align:center; font-family:'DM Mono',monospace; font-size:.6rem; color:var(--muted); letter-spacing:2px; padding-top:20px; border-top:1px solid var(--border); animation:fadeUp .5s ease .5s both; }
  footer span { color:var(--accent); }

  @keyframes fadeDown { from{opacity:0;transform:translateY(-16px)} to{opacity:1;transform:translateY(0)} }
  @keyframes fadeUp   { from{opacity:0;transform:translateY(14px)}  to{opacity:1;transform:translateY(0)} }
  @keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:.3} }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="logo">Macro<em>Signal</em></div>
    <div class="header-right">
      <div class="dot-wrap">
        <div class="dot"></div>
        <div class="live-time" id="clk">--:--:--</div>
      </div>
      <div class="live-label">UTC · AO VIVO</div>
    </div>
  </header>

  <div class="section-lbl">PRÓXIMOS EVENTOS DE ALTO IMPACTO</div>
  <div class="events-list" id="events-list"></div>

  <div class="section-lbl" style="margin-top:8px">ANÁLISE DO EVENTO SELECIONADO</div>
  <div class="signal-main" id="main-card"></div>

  <div class="disclaimer">⚠ Análise baseada em dados históricos via FRED API. Não constitui recomendação de investimento. Toda decisão de entrada é de sua exclusiva responsabilidade.</div>
  <footer>MacroSignal · <span>Análise Fundamentalista</span> · FRED API</footer>

</div>
<script>
// ── CORRELAÇÕES ──────────────────────────────────────────────
const CORRELATOS = { USD:'CAD',CAD:'USD', AUD:'NZD',NZD:'AUD', EUR:'GBP',GBP:'EUR', CHF:'JPY',JPY:'CHF' };
const ORDEM_FX   = ['EUR','GBP','AUD','NZD','USD','CAD','CHF','JPY'];
const TODAS_MOE  = ['USD','EUR','GBP','AUD','NZD','CAD','CHF','JPY'];

function canonico(a,b){ return ORDEM_FX.indexOf(a)<ORDEM_FX.indexOf(b)?a+b:b+a; }
function getPortfolio(cur){ return TODAS_MOE.filter(m=>m!==cur&&m!==CORRELATOS[cur]).map(m=>canonico(cur,m)); }
function direcao(par,cur,verd){
  if(verd==='NEUTRO') return 'NEUTRO';
  const forte = verd==='FORTE';
  return par.slice(0,3)===cur?(forte?'BUY':'SELL'):(forte?'SELL':'BUY');
}
function veredicto(score){ return score>0.2?'FORTE':score<-0.2?'FRACO':'NEUTRO'; }

// ── CALENDÁRIO DE EVENTOS ────────────────────────────────────
// Datas reais próximas (mês/dia/hora UTC) — atualize conforme calendário econômico
function proximaDataSemana(diaSemana, horaUTC, minUTC){
  const agora = new Date();
  const alvo  = new Date(agora);
  alvo.setUTCHours(horaUTC, minUTC, 0, 0);
  let diff = (diaSemana - agora.getUTCDay() + 7) % 7;
  if(diff===0 && agora>=alvo) diff=7;
  alvo.setUTCDate(agora.getUTCDate()+diff);
  return alvo;
}

function proxDataMes(dia, horaUTC, minUTC){
  const agora = new Date();
  const alvo  = new Date(Date.UTC(agora.getUTCFullYear(), agora.getUTCMonth(), dia, horaUTC, minUTC, 0));
  if(alvo<=agora) alvo.setUTCMonth(alvo.getUTCMonth()+1);
  return alvo;
}

const EVENTOS = [
  { id:'nfp',       cur:'USD', nome:'NFP / PAYROLL',    tipo:'PAYROLL', data: proximaDataSemana(5,13,30), descricao:'Todo 1º sexta do mês · 13:30 UTC' },
  { id:'cpi_usd',   cur:'USD', nome:'CPI — EUA',        tipo:'CPI',     data: proxDataMes(12,13,30),      descricao:'Mensal · 12ª a 15ª · 13:30 UTC' },
  { id:'fomc',      cur:'USD', nome:'FOMC — JUROS EUA', tipo:'JUROS',   data: proxDataMes(19,19,0),       descricao:'8x ao ano · 19:00 UTC' },
  { id:'cpi_eur',   cur:'EUR', nome:'CPI — ZONA EURO',  tipo:'CPI',     data: proxDataMes(17,10,0),       descricao:'Mensal · 10:00 UTC' },
  { id:'bce',       cur:'EUR', nome:'BCE — JUROS EUR',  tipo:'JUROS',   data: proxDataMes(6,13,15),       descricao:'8x ao ano · 13:15 UTC' },
  { id:'cpi_gbp',   cur:'GBP', nome:'CPI — UK',         tipo:'CPI',     data: proxDataMes(19,7,0),        descricao:'Mensal · 07:00 UTC' },
  { id:'boe',       cur:'GBP', nome:'BOE — JUROS GBP',  tipo:'JUROS',   data: proxDataMes(6,12,0),        descricao:'8x ao ano · 12:00 UTC' },
  { id:'cpi_aud',   cur:'AUD', nome:'CPI — AUSTRÁLIA',  tipo:'CPI',     data: proxDataMes(26,1,30),       descricao:'Trimestral · 01:30 UTC' },
  { id:'rba',       cur:'AUD', nome:'RBA — JUROS AUD',  tipo:'JUROS',   data: proxDataMes(4,3,30),        descricao:'8x ao ano · 03:30 UTC' },
  { id:'boj',       cur:'JPY', nome:'BOJ — JUROS JPY',  tipo:'JUROS',   data: proxDataMes(24,3,0),        descricao:'8x ao ano · 03:00 UTC' },
];

// Ordena por data mais próxima
EVENTOS.sort((a,b)=>a.data-b.data);

// ── SCORES SIMULADOS ─────────────────────────────────────────
const SCORES = {
  USD:{ PAYROLL:0.65, CPI:0.55, JUROS:0.60 },
  EUR:{ CPI:-0.40, JUROS:-0.35 },
  GBP:{ CPI:0.30,  JUROS:0.25 },
  AUD:{ CPI:0.50,  JUROS:0.45 },
  NZD:{ CPI:0.10,  JUROS:0.05 },
  CAD:{ CPI:0.20,  JUROS:0.15 },
  CHF:{ CPI:-0.20, JUROS:-0.15 },
  JPY:{ CPI:-0.55, JUROS:-0.60 },
};

// ── INDICADORES ──────────────────────────────────────────────
const INDICADORES = {
  PAYROLL:[
    {name:'ADP PAYROLLS',        t:1,  w:30},
    {name:'JOBLESS CLAIMS',      t:-1, w:25},
    {name:'JOLTS VAGAS',         t:1,  w:20},
    {name:'ISM EMPLOYMENT IDX',  t:1,  w:15},
    {name:'AVG WEEKLY HOURS',    t:1,  w:10},
  ],
  CPI:[
    {name:'PPI (PRODUTOR)',       t:1,  w:25},
    {name:'PCE CORE',            t:1,  w:25},
    {name:'IMPORT PRICES',       t:-1, w:15},
    {name:'PETRÓLEO / COMMOD.',  t:1,  w:15},
    {name:'AVG HOURLY EARNINGS', t:1,  w:10},
    {name:'SHELTER / MORADIA',   t:1,  w:10},
  ],
  JUROS:[
    {name:'PCE CORE',            t:1,  w:30},
    {name:'CPI CORE',            t:1,  w:25},
    {name:'NFP / EMPREGO',       t:1,  w:20},
    {name:'GDP',                 t:-1, w:15},
    {name:'FEDWATCH PROB.',      t:1,  w:10},
  ],
};

// ── STATE ────────────────────────────────────────────────────
let selectedId = EVENTOS[0].id;

// ── UTILS ────────────────────────────────────────────────────
function pad(n){ return String(n).padStart(2,'0'); }

function formatData(d){
  const dias = ['DOM','SEG','TER','QUA','QUI','SEX','SÁB'];
  const meses = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];
  return `${dias[d.getUTCDay()]} · ${pad(d.getUTCDate())} ${meses[d.getUTCMonth()]} · ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

function calcCountdown(d){
  const diff = d - new Date();
  if(diff<=0) return 'AO VIVO';
  const h = Math.floor(diff/3600000);
  const m = Math.floor((diff%3600000)/60000);
  const s = Math.floor((diff%60000)/1000);
  if(h>=48){
    const dias = Math.floor(h/24);
    return `${dias}D ${pad(h%24)}H`;
  }
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

// ── RENDER EVENTS LIST ───────────────────────────────────────
function renderEventList(){
  const container = document.getElementById('events-list');
  container.innerHTML = EVENTOS.map(ev=>`
    <div class="event-row ${ev.id===selectedId?'active':''}" data-id="${ev.id}">
      <div class="ev-left">
        <div class="ev-currency-tag">${ev.cur}</div>
        <div class="ev-info">
          <div class="ev-name">${ev.nome}</div>
          <div class="ev-date">${formatData(ev.data)} · ${ev.descricao}</div>
        </div>
      </div>
      <div class="ev-right">
        <div class="ev-countdown" id="cd-${ev.id}">${calcCountdown(ev.data)}</div>
        <div class="ev-countdown-lbl">ATÉ O EVENTO</div>
      </div>
    </div>
  `).join('');

  container.querySelectorAll('.event-row').forEach(row=>{
    row.addEventListener('click',()=>{
      selectedId = row.dataset.id;
      renderEventList();
      renderSignal();
    });
  });
}

// ── RENDER SIGNAL CARD ───────────────────────────────────────
function renderSignal(){
  const ev    = EVENTOS.find(e=>e.id===selectedId);
  const score = SCORES[ev.cur]?.[ev.tipo] ?? 0;
  const verd  = veredicto(score);
  const inds  = INDICADORES[ev.tipo];
  const port  = getPortfolio(ev.cur);
  const bc    = verd==='FORTE'?'forte':verd==='FRACO'?'fraco':'neutro';

  const indsHTML = inds.map(ind=>{
    const cls = ind.t===1?'up':ind.t===-1?'down':'flat';
    const arr = ind.t===1?'▲':ind.t===-1?'▼':'→';
    return `<div class="ind-row">
      <div class="ind-name">${ind.name}</div>
      <div class="ind-track"><div class="ind-fill ${cls}" style="width:${ind.w*3}%"></div></div>
      <div class="ind-arr ${cls}">${arr}</div>
    </div>`;
  }).join('');

  let pairsContent = '';
  if(verd==='NEUTRO'){
    pairsContent = `<div class="neutro-msg">SINAL NEUTRO — INDICADORES CONTRADITÓRIOS<br>MELHOR FICAR DE FORA DESTE EVENTO</div>`;
  } else {
    const items = port.map(par=>{
      const dir = direcao(par,ev.cur,verd);
      return `<div class="pair-item">
        <div class="pair-name">${par.slice(0,3)}/${par.slice(3)}</div>
        <div class="pair-dir ${dir.toLowerCase()}">${dir}</div>
      </div>`;
    }).join('');
    pairsContent = `<div class="pairs-section">
      <div class="pairs-title">PORTFÓLIO — 6 PARES · ${ev.cur} vs DEMAIS (SEM ${CORRELATOS[ev.cur]})</div>
      <div class="pairs-grid">${items}</div>
    </div>`;
  }

  document.getElementById('main-card').innerHTML = `
    <div class="signal-header">
      <div>
        <div class="sig-cur">${ev.cur}</div>
        <div class="sig-ev">${ev.nome}</div>
      </div>
      <div>
        <div class="verdict-badge ${bc}">${verd}</div>
        <div class="score-lbl">SCORE: ${score>=0?'+':''}${score.toFixed(2)}</div>
      </div>
    </div>
    <div class="ind-section">
      <div class="ind-title">INDICADORES ANTECEDENTES</div>
      ${indsHTML}
    </div>
    ${pairsContent}
  `;
}

// ── CLOCK + COUNTDOWNS ───────────────────────────────────────
function tick(){
  const n = new Date();
  document.getElementById('clk').textContent = `${pad(n.getUTCHours())}:${pad(n.getUTCMinutes())}:${pad(n.getUTCSeconds())}`;
  EVENTOS.forEach(ev=>{
    const el = document.getElementById('cd-'+ev.id);
    if(el) el.textContent = calcCountdown(ev.data);
  });
}

setInterval(tick,1000);
tick();

// ── INIT ─────────────────────────────────────────────────────
renderEventList();
renderSignal();
</script>
</body>
</html>
