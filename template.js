/* テーマ別資金フロー: 画面の描画。04_build_html.py が template.html の SCRIPT の位置に埋め込む */
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const cssv=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=1)=>x==null||!isFinite(x)?'–':Number(x).toLocaleString('ja-JP',{minimumFractionDigits:d,maximumFractionDigits:d});
const sign=(x,d=1)=>x==null||!isFinite(x)?'–':(x>=0?'+':'−')+fmt(Math.abs(x),d);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const PAL=()=>[1,2,3,4,5,6,7,8].map(i=>cssv('--c'+i));
const US_ON=!!(US_DATA&&US_DATA.themes&&US_DATA.themes.length);
const SCHED={jp:'毎日 17:00 JST 更新',us:'毎日 7:00 JST 更新'};
const MKNAME={jp:'日本株',us:'米国株'};

/* ---------- 会員限定の設定(site_config.json → GATE) ---------- */
const GCFG=(GATE&&GATE.sections)||{};
function gateN(key,total){const g=GCFG[key];if(!g||g.mode==='public')return total;return Math.min(total,Math.max(0,g.n||0));}
function lockHTML(key,hidden,cols){
  const g=GCFG[key];if(!g||g.mode==='public'||hidden<=0)return '';
  const rows=Array.from({length:Math.min(hidden,5)},(_,i)=>`<tr>${Array.from({length:cols||5},(_,j)=>`<td style="padding:8px"><span style="display:inline-block;height:9px;width:${j===1?120:48}px;border-radius:4px;background:var(--line)"></span></td>`).join('')}</tr>`).join('');
  const title=(g.title||'残り{n}件は会員限定').replace('{n}',hidden.toLocaleString());
  return `<div class="locked"><div class="veil"><table class="rk"><tbody>${rows}</tbody></table></div>
    <div class="lockcard"><div><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2.2"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
    <h4>${esc(title)}</h4><p>${esc(g.text||'会員になると、すべての行と過去の履歴を毎日確認できます。')}</p>
    <div class="row"><a class="btn sm" href="join.html">ログイン</a><a class="btn ghost sm" href="join.html">会員について</a></div></div></div></div>`;
}

/* ---------- 市場(日本株/米国株)の切り替え ---------- */
let market='jp',DATA,themes,dates,N,STK,byName,latestYear,RK,MK,OHLC_DIR='ohlc/',U={turn:'億',turnLong:'億円',mcap:'億'};
const state={metric:'index',range:120,smooth:5,sort:'surge',selected:[],focus:null,
  gran:'week',hsort:'flow',hquery:'',mapTheme:null,spSort:'to',spStock:null,spPer:126,spFreq:'day',
  rkMetric:'to',rkSel:null,rkCard:null,rkSort:{k:'rank',dir:'asc'},rkRows:20,rkQuery:'',
  secPer:1,brMode:'turnover',mcCat:'all',mcPer:126,rateSub:'jp',
  scCode:null,scPer:126,scFreq:'day',vcpIdx:null,vcpQuery:'',vcpSort:{k:'prio',dir:'desc'}};
function bindMarket(mk){
  market=(mk==='us'&&US_ON)?'us':'jp'; DATA=market==='us'?US_DATA:JP_DATA;
  themes=DATA.themes; dates=DATA.dates; N=dates.length; STK=DATA.stocks;
  byName=Object.fromEntries(themes.map(t=>[t.name,t]));
  latestYear=dates[N-1].slice(0,4); RK=DATA.rankings; MK=MKT[market]||{};
  if(!DATA.__nz){DATA.__nz=1;const nz=o=>{Object.values(o||{}).forEach(x=>{if(x&&x.name)x.name=x.name.normalize('NFKC');});};nz(STK);nz(RK&&RK.stocks);}
  const u=DATA.units||{}; OHLC_DIR=u.ohlcDir||'ohlc/';
  U={turn:u.turn||'億',turnLong:u.turnLong||'億円',mcap:u.mcap||'億'};
}
function marketReset(){
  const top=flowRows().inn.map(t=>t.name).slice(0,5);
  state.selected=top; state.focus=top[0]||null; state.mapTheme=top[0]||(themes[0]&&themes[0].name)||null;
  state.rkSel=null; state.rkCard=null; state.spStock=null; state.hquery=''; state.rkQuery=''; state.scCode=null;
  state.vcpIdx=null; state.vcpQuery=''; state.vcCode=null;
  ['#hsearch','#rksearch','#vcpsearch','#sq'].forEach(s=>{const el=$(s);if(el)el.value='';});
  ['#hsearch-x','#rksearch-x','#vcpsearch-x'].forEach(s=>{const el=$(s);if(el)el.hidden=true;});
  const r=$('#sres');if(r)r.hidden=true;
}

/* ---------- 共通の小物 ---------- */
function seg(id,fn){const el=document.getElementById(id);if(!el)return;el.onclick=e=>{const b=e.target.closest('button');if(!b)return;el.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));fn(b);};}
function setSeg(id,attr,val){const el=document.getElementById(id);if(el)el.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset[attr])===String(val)));}
function movAvg(a,w){if(w<=1)return a.slice();const o=[];let s=0;for(let i=0;i<a.length;i++){s+=a[i];if(i>=w)s-=a[i-w];o[i]=s/Math.min(i+1,w);}return o;}
function sparkPath(arr,w,h,pad){const v=arr.filter(x=>x!=null);if(v.length<2)return null;const lo=Math.min(...v),hi=Math.max(...v),rg=hi-lo||1;
  const X=i=>i/(arr.length-1)*w,Y=x=>h-pad-(x-lo)/rg*(h-pad*2);let p='',st=false;
  arr.forEach((x,i)=>{if(x==null)return;p+=(st?'L':'M')+X(i).toFixed(1)+' '+Y(x).toFixed(1)+' ';st=true;});
  const li=arr.length-1;return{p,ex:X(li),ey:Y(arr[li]??v[v.length-1])};}
function spark(arr){const s=sparkPath(arr||[],64,16,1.5);if(!s)return'';const up=arr[arr.length-1]>=arr[0];
  return `<svg width="64" height="16" viewBox="0 0 64 16" style="display:block"><path d="${s.p}" fill="none" stroke="${up?'var(--up)':'var(--down)'}" stroke-width="1.4"/></svg>`;}
function niceStep(r,n){const raw=r/Math.max(1,n),p=Math.pow(10,Math.floor(Math.log10(raw))),f=raw/p;return (f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*p;}
function niceAxis(lo,hi,n){const st=niceStep(hi-lo,n||5);const a=Math.floor(lo/st)*st,b=Math.ceil(hi/st)*st,t=[];for(let v=a;v<=b+st*1e-6;v+=st)t.push(+v.toFixed(10));return{lo:a,hi:b,ticks:t,step:st};}
function fmtTurn(v,unit){if(v==null||!isFinite(v))return'–';if(unit==='億円'&&Math.abs(v)>=10000)return fmt(v/10000,1)+'兆円';return fmt(v,v>=100?0:1)+unit;}
function mdLabel(d){return d.slice(5).replace('-','/').replace(/^0/,'').replace('/0','/');}
function tvUrl(code){return 'https://jp.tradingview.com/chart/?symbol='+encodeURIComponent(market==='us'?code.replace('-','.'):'TSE:'+code);}
function stockLinks(code){return `<a class="extl" href="${tvUrl(code)}" target="_blank" rel="noopener">TradingView↗</a>`+(market==='us'
  ?`<a class="extl" href="https://finance.yahoo.com/quote/${code}" target="_blank" rel="noopener">Yahoo↗</a><a class="extl" href="https://finviz.com/quote.ashx?t=${code}" target="_blank" rel="noopener">Finviz↗</a>`
  :`<a class="extl" href="https://finance.yahoo.co.jp/quote/${code}.T" target="_blank" rel="noopener">Yahoo↗</a><a class="extl" href="https://kabutan.jp/stock/?code=${code}" target="_blank" rel="noopener">株探↗</a>`);}
function goto(id){const el=document.getElementById(id);if(el)el.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});}

/* ================= 指数の帯 ================= */
function macroLast(t){const c=MACRO.inst&&MACRO.inst[t];if(!c)return null;const a=c.close;let i=a.length-1;while(i>=0&&a[i]==null)i--;let j=i-1;while(j>=0&&a[j]==null)j--;
  if(i<1||j<0)return null;return{name:c.name,last:a[i],prev:a[j]};}
function drawStrip(){
  const items=[];
  (MK.indices||[]).forEach(x=>items.push({n:x.name,v:fmt(x.last,x.last>1000?0:2),c:x.chg_pct,u:'%'}));
  const add=(t,label,isYield)=>{const m=macroLast(t);if(!m)return;
    items.push(isYield?{n:label,v:fmt(m.last,2)+'%',c:m.last-m.prev,u:'',d:2}:{n:label,v:fmt(m.last,m.last>1000?0:2),c:(m.last/m.prev-1)*100,u:'%'});};
  if(market==='jp'){add('jp10','日本10年',true);add('^TNX','米10年',true);add('ES=F','S&P500先物');add('GC=F','金');}
  else{add('^TNX','米10年',true);add('CL=F','WTI原油');add('GC=F','金');add('BTC-USD','ビットコイン');}
  $('#strip').innerHTML=items.map(x=>`<div class="tick"><small>${esc(x.n)}</small><span class="num">${x.v}<em class="${x.c>=0?'up':'down'}">${sign(x.c,x.d||2)}${x.u}</em></span></div>`).join('');
}

/* ================= 市場概況 ================= */
function flowRows(){const T=themes.filter(t=>t.surge!=null&&(t.n||0)>=5);
  const tv=T.map(t=>t.latest_turnover_oku||0).sort((a,b)=>a-b),med=tv[Math.floor(tv.length/2)]||0;
  const big=T.filter(t=>(t.latest_turnover_oku||0)>=med);
  return{inn:[...big].sort((a,b)=>b.surge-a.surge).slice(0,5),out:[...big].sort((a,b)=>a.surge-b.surge).slice(0,3)};}
function drawFlowLists(){
  const {inn,out}=flowRows(),max=Math.max(...inn.map(t=>Math.abs(t.surge)),...out.map(t=>Math.abs(t.surge)),1);
  const li=(t,i)=>`<li data-nm="${esc(t.name)}"><span class="rk">${i+1}</span><span class="nm">${esc(t.name)}<span class="cat">${esc(t.cat||'')} ・ ${t.n}銘柄</span></span>
    <span class="hbar1"><i style="width:${(Math.abs(t.surge)/max*100).toFixed(0)}%;${t.surge<0?'background:var(--down)':''}"></i></span>
    <span class="pct num ${t.surge>=0?'up':'down'}">${sign(t.surge)}%</span></li>`;
  $('#inflow').innerHTML=inn.map(li).join('');$('#outflow').innerHTML=out.map(li).join('');
  $$('#inflow li,#outflow li').forEach(el=>el.onclick=()=>{focusTheme(el.dataset.nm,true);goto('themes');});
}
function lastN(a,n){return (a||[]).slice(-n);}
function drawVerdict(){
  const el=$('#verdict'),v=MK.verdict;
  if(!v){el.innerHTML='<div class="meta">地合いのデータを準備中です（次回の更新から表示されます）。</div>';return;}
  const B=MK.breadth,nh=lastN(B.nh,1)[0],nl=lastN(B.nl,1)[0],ab=lastN(B.above,1)[0];
  const a10=lastN(B.adv,10).reduce((x,y)=>x+y,0),d10=lastN(B.dec,10).reduce((x,y)=>x+y,0);
  const cls=v.label==='RISK-ON'?'on':v.label==='RISK-OFF'?'off':'mid';
  const bars={hl:nh+nl?nh/(nh+nl)*100:50,ma:ab||0,ad:a10+d10?a10/(a10+d10)*100:50};
  const meters=v.items.map(it=>`<div class="meter"><small>${esc(it.label)}</small><div class="val num">${esc(it.value)}</div>
    <span class="ok ${it.ok?'up':'down'}">${it.ok?'✓ 強気':'✗ 弱気'}</span><div class="bar2"><i style="width:${Math.max(2,Math.min(100,bars[it.key]||0)).toFixed(0)}%"></i></div></div>`).join('');
  // サマリー(データから自動で文章化)
  const {inn,out}=flowRows(),top=rkTop(),r1=top&&top[0]?RK.stocks[top[0]]:null;
  const tt=B.turnover||[],lastT=tt[tt.length-1],avg20=tt.slice(-21,-1).reduce((x,y)=>x+y,0)/Math.max(1,tt.slice(-21,-1).length);
  const tpct=avg20?(lastT/avg20-1)*100:null;
  const p1=`<b>${inn.slice(0,2).map(t=>esc(t.name)).join('・')}に資金が集まっています。</b>`+(r1?`売買代金の首位は${esc(r1.name)}（${fmtTurn(r1.to,U.turnLong)}）。`:'');
  const p2=`市場全体の売買代金は${fmtTurn(lastT,MK.turn_unit)}で、20日平均を${tpct==null?'–':fmt(Math.abs(tpct),1)}%${tpct>=0?'上回りました':'下回りました'}。新高値${nh}・新安値${nl}、${MK.ma}日線より上の銘柄は${fmt(ab,1)}%。`+
    (out.length?`流出が目立つのは${out.slice(0,2).map(t=>esc(t.name)).join('・')}。`:'');
  el.innerHTML=`<div class="v-top"><div><div class="meta">本日の地合い（${mdLabel(MK.updated)}）</div><div class="v-label ${cls}">${v.label}</div>
      <div class="v-sub">3つの指標のうち ${v.score} つが強気</div></div>
      <span class="pill">${v.prev_label===v.label?'前日から変化なし':'前日は '+esc(v.prev_label)}</span></div>
    <div class="meter-row">${meters}</div>
    <div class="summary"><div class="meta">マーケットサマリー</div><p>${p1}</p><p>${p2}</p></div>`;
}
function drawIndexCards(){
  const box=$('#icards'),L=(MK.indices||[]).slice(0,4);
  if(!L.length){box.innerHTML='';box.hidden=true;return;}box.hidden=false;
  box.innerHTML=L.map((x,i)=>{const up=(x.chg_pct||0)>=0,s=sparkPath(lastN(x.closes,60),200,44,4),id='gd'+i;
    const stale=x.date&&MK.updated&&x.date<MK.updated?`<span title="この指数は${x.date}が最新です">${mdLabel(x.date)}時点</span>`:'';
    return `<div class="panel icard"><div class="nm"><span>${esc(x.name)}</span>${stale}</div><div class="px num">${fmt(x.last,x.last>1000?0:2)}</div>
      <div class="ch num ${up?'up':'down'}">${sign(x.chg,x.last>1000?0:2)}（${sign(x.chg_pct,2)}%）</div>
      ${s?`<svg viewBox="0 0 200 44" preserveAspectRatio="none"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${cssv(up?'--up':'--down')}" stop-opacity=".18"/><stop offset="1" stop-color="${cssv(up?'--up':'--down')}" stop-opacity="0"/></linearGradient></defs>
      <path d="${s.p} L200 44 L0 44 Z" fill="url(#${id})"/><path d="${s.p}" fill="none" stroke="${up?'var(--up)':'var(--down)'}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`:''}</div>`;}).join('');
}
function drawSectors(){
  const S=(MK.sectors||[]).filter(x=>x['r'+state.secPer]!=null);
  $('#sec-sub').textContent=market==='jp'?'東証33業種・等加重':'S&P500 業種ETF';
  const box=$('#sectors');if(!S.length){box.innerHTML='<div class="meta">データを準備中です。</div>';return;}
  const k='r'+state.secPer,rows=[...S].sort((a,b)=>b[k]-a[k]),max=Math.max(...rows.map(x=>Math.abs(x[k])),0.5);
  const show=rows.length>12?[...rows.slice(0,6),null,...rows.slice(-6)]:rows;
  box.innerHTML=show.map(x=>{if(!x)return '<div class="sgap"></div>';const v=x[k],w=Math.abs(v)/max*50;
    return `<div class="srow"><span class="nm" title="${esc(x.name)}${x.n?'（'+x.n+'銘柄）':''}">${esc(x.name)}</span><span class="track"><i style="${v>=0?`left:50%;width:${w}%;background:var(--up)`:`right:50%;width:${w}%;background:var(--down)`}"></i></span><span class="v num ${v>=0?'up':'down'}">${sign(v,2)}%</span></div>`;}).join('');
}
function drawCalendar(){
  const C=MK.calendar||[],box=$('#cal');
  if(!C.length){box.innerHTML='<div class="meta">データを準備中です。</div>';return;}
  let h=['月','火','水','木','金'].map(w=>`<div class="dow">${w}</div>`).join(''),col=0;
  C.forEach((c,i)=>{const wd=new Date(c.date+'T00:00:00').getDay();
    if(i===0||wd<=col){if(i>0)h+='<div></div>'.repeat(Math.max(0,5-col));h+='<div></div>'.repeat(wd-1);}
    else h+='<div></div>'.repeat(Math.max(0,wd-col-1));
    col=wd;
    const st={2:['var(--up)','var(--surface)'],1:['var(--up-soft)','var(--up)'],0:['var(--line)','var(--muted)'],'-1':['var(--down-soft)','var(--down)'],'-2':['var(--down)','var(--surface)']}[c.lv];
    h+=`<div class="d${i===C.length-1?' today':''}" style="background:${st[0]};color:${st[1]}" title="${c.date}  新高値${c.nh} / 新安値${c.nl}  値上がり${c.adv} / 値下がり${c.dec}"><b>${mdLabel(c.date)}</b><span class="num">${c.nh}/${c.nl}</span></div>`;});
  box.innerHTML=h;
}
/* 売買代金・新高値新安値などの日次グラフ(棒/線) */
function drawBreadth(){
  const B=MK.breadth,svg=$('#brchart');if(!B){svg.innerHTML='';$('#br-desc').textContent='データを準備中です。';return;}
  $('#brm-above').textContent=MK.ma+'日線より上';
  const n=Math.min(80,B.dates.length),s=B.dates.length-n,D=B.dates.slice(s);
  const W=900,H=240,L=52,R=14,T=12,Bm=26,bw=(W-L-R)/n,X=i=>L+bw*(i+.5);
  const mode=state.brMode,up=cssv('--up'),dn=cssv('--down'),br=cssv('--brand');let g='',lo,hi,tipRows;
  const yax=(lo,hi,fmtf)=>{const st=niceStep(hi-lo,4);lo=Math.floor(lo/st)*st;hi=Math.ceil(hi/st)*st;const Y=v=>T+(H-T-Bm)*(1-(v-lo)/(hi-lo));let o='';
    for(let v=lo;v<=hi+st*1e-6;v+=st)o+=`<line class="gl" x1="${L}" x2="${W-R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="axl" x="${L-6}" y="${(Y(v)+4).toFixed(1)}" text-anchor="end">${fmtf(v)}</text>`;return[Y,o];};
  let lm='';D.forEach((d,i)=>{const mo=d.slice(0,7);if(mo!==lm){lm=mo;g+=`<text class="axl" x="${X(i).toFixed(1)}" y="${H-7}" text-anchor="middle">${d.slice(2,7).replace('-','/')}</text>`;}});
  if(mode==='turnover'){
    const v=B.turnover.slice(s),ma=movAvg(B.turnover,20).slice(s);hi=Math.max(...v,...ma)*1.05;lo=0;
    const[Y,ax]=yax(lo,hi,x=>MK.turn_unit==='億円'?(x===0?'0':fmt(x/10000,x%10000?1:0)+'兆'):fmt(x,0));g=ax+g;
    const dd=new Set((MK.dist&&MK.dist.dates)||[]);
    v.forEach((x,i)=>{g+=`<rect x="${(X(i)-bw*.35).toFixed(1)}" y="${Y(x).toFixed(1)}" width="${(bw*.7).toFixed(1)}" height="${(Y(0)-Y(x)).toFixed(1)}" rx="1" fill="${br}" fill-opacity="${i===n-1?.95:.38}"/>`;
      if(dd.has(D[i]))g+=`<path d="M${X(i).toFixed(1)} ${(Y(0)+2).toFixed(1)} l-4 -7 h8 z" fill="${dn}"/>`;});
    let p='';ma.forEach((x,i)=>p+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(x).toFixed(1)+' ');g+=`<path d="${p}" fill="none" stroke="${cssv('--ink-2')}" stroke-width="1.4" stroke-dasharray="4 3"/>`;
    tipRows=i=>[[`売買代金`,fmtTurn(v[i],MK.turn_unit)],['20日平均',fmtTurn(ma[i],MK.turn_unit)]].concat(dd.has(D[i])?[['','売り抜け日']]:[]);
    const dc=MK.dist;$('#br-title').textContent='市場全体の売買代金';
    $('#br-desc').innerHTML=`全${(MK.universe||0).toLocaleString()}銘柄の売買代金の合計。点線は20日平均。<b class="down">▼</b>は売り抜け日（${dc?esc(dc.index):'指数'}が0.2%以上下げ、売買代金が前日より増えた日）`+(dc?`で、直近${dc.window}営業日に <b>${dc.count}日</b>。`:'。');
  }else if(mode==='hl'||mode==='ad'){
    const a=(mode==='hl'?B.nh:B.adv).slice(s),b=(mode==='hl'?B.nl:B.dec).slice(s),m=Math.max(...a,...b)*1.1||1;
    const[Y,ax]=yax(-m,m,x=>fmt(Math.abs(x),0));g=ax+g;
    a.forEach((x,i)=>{g+=`<rect x="${(X(i)-bw*.35).toFixed(1)}" y="${Y(x).toFixed(1)}" width="${(bw*.7).toFixed(1)}" height="${(Y(0)-Y(x)).toFixed(1)}" fill="${up}" fill-opacity="${i===n-1?1:.55}"/>`;
      g+=`<rect x="${(X(i)-bw*.35).toFixed(1)}" y="${Y(0).toFixed(1)}" width="${(bw*.7).toFixed(1)}" height="${(Y(-b[i])-Y(0)).toFixed(1)}" fill="${dn}" fill-opacity="${i===n-1?1:.55}"/>`;});
    g+=`<line x1="${L}" x2="${W-R}" y1="${Y(0)}" y2="${Y(0)}" stroke="${cssv('--line-strong')}"/>`;
    const la=mode==='hl'?['新高値','新安値']:['値上がり','値下がり'];
    tipRows=i=>[[la[0],a[i]],[la[1],b[i]]];
    $('#br-title').textContent=mode==='hl'?'52週 新高値・新安値の銘柄数':'値上がり・値下がりの銘柄数';
    $('#br-desc').textContent=mode==='hl'?'終値が過去250営業日の最高値を更新した銘柄数（上）と、最安値を更新した銘柄数（下）。':'その日に値上がりした銘柄数（上）と値下がりした銘柄数（下）。';
  }else{
    const v=B.above.slice(s);const[Y,ax]=yax(0,100,x=>x.toFixed(0)+'%');g=ax+g;
    g+=`<line x1="${L}" x2="${W-R}" y1="${Y(50)}" y2="${Y(50)}" stroke="${cssv('--line-strong')}" stroke-dasharray="4 3"/>`;
    let p='';v.forEach((x,i)=>p+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(x).toFixed(1)+' ');
    g+=`<path d="${p} L${X(n-1).toFixed(1)} ${Y(0)} L${X(0).toFixed(1)} ${Y(0)} Z" fill="${br}" fill-opacity=".08"/><path d="${p}" fill="none" stroke="${br}" stroke-width="2.2"/><circle cx="${X(n-1).toFixed(1)}" cy="${Y(v[n-1]).toFixed(1)}" r="3.5" fill="${br}"/>`;
    tipRows=i=>[[`${MK.ma}日線より上`,fmt(v[i],1)+'%']];
    $('#br-title').textContent=`${MK.ma}日移動平均線より上にある銘柄の割合`;
    $('#br-desc').textContent=`株価が${MK.ma}日移動平均線より上にある銘柄の割合。50%が強弱の分かれ目です。`;
  }
  g+=`<line class="cross" id="brx" y1="${T}" y2="${H-Bm}" style="opacity:0"/>`;
  svg.innerHTML=g;
  svg.onmousemove=ev=>{const r=svg.getBoundingClientRect(),px=(ev.clientX-r.left)/r.width*W;if(px<L||px>W-R)return;
    const i=Math.max(0,Math.min(n-1,Math.floor((px-L)/bw))),tip=$('#brtip'),cx=$('#brx');cx.setAttribute('x1',X(i));cx.setAttribute('x2',X(i));cx.style.opacity=1;
    tip.innerHTML=`<div class="td">${D[i]}</div>`+tipRows(i).map(([a,b])=>`<div class="row"><span class="l">${a}</span><span class="val">${b}</span></div>`).join('');
    tip.style.opacity=1;const xpx=X(i)/W*r.width;tip.style.left=Math.min(r.width-tip.offsetWidth-4,Math.max(4,xpx+12))+'px';tip.style.top='6px';};
  svg.onmouseleave=()=>{$('#brtip').style.opacity=0;const cx=$('#brx');if(cx)cx.style.opacity=0;};
}
function drawOverview(){
  $('#mk-meta').textContent=MK.updated?`${MKNAME[market]} ・ ${MK.updated}の大引け後 ・ ${(MK.universe||0).toLocaleString()}銘柄`:'';
  drawVerdict();drawFlowLists();drawIndexCards();drawSectors();drawCalendar();drawBreadth();
}

/* ================= 世界のお金の流れ ================= */
const MI=MACRO.inst||{},MDATES=MACRO.dates||[],MN=MDATES.length;
const CATLABEL=Object.fromEntries((MACRO.cats||[]).map(c=>[c.key,c.label]));
const RGROUPS=MACRO.rateGroups||{us:[],jp:[],world:[]};
const RSUBLABEL={us:'米国金利',jp:'日本金利',world:'主要先進国の10年金利'};
let worldDrawn=false;
function mslice(){const p=Math.min(state.mcPer,MN);return[MN-p,MN];}
function rebase(a){const b=a.find(v=>v!=null)||1;return a.map(v=>v==null?null:v/b*100);}
function avgSeries(ts,s,e){const L=e-s,out=new Array(L).fill(0),cnt=new Array(L).fill(0);
  ts.forEach(t=>{const c=MI[t];if(!c)return;rebase(c.close.slice(s,e)).forEach((v,i)=>{if(v!=null){out[i]+=v;cnt[i]++;}});});
  return out.map((v,i)=>cnt[i]?v/cnt[i]:null);}
function lineChart(svgId,tipId,series,xs,opt){
  const CW=720,CH=opt.h||340,ML=opt.ml||46,MR=14,MT=14,MB=28;
  let lo=Infinity,hi=-Infinity;series.forEach(sr=>sr.vals.forEach(v=>{if(v==null)return;if(v<lo)lo=v;if(v>hi)hi=v;}));
  if(!isFinite(lo)){lo=0;hi=1;}if(opt.base100){lo=Math.min(lo,100);hi=Math.max(hi,100);}
  const pad=(hi-lo)*0.04||1;lo-=pad;hi+=pad;const ax=niceAxis(lo,hi,5);lo=ax.lo;hi=ax.hi;const dd=ax.step<1?(ax.step<0.1?2:1):0;
  const n=xs.length,X=i=>ML+(CW-ML-MR)*(n<=1?0:i/(n-1)),Y=v=>MT+(CH-MT-MB)*(1-(v-lo)/(hi-lo));
  let g='';
  ax.ticks.forEach(v=>{const y=Y(v);g+=`<line class="gl" x1="${ML}" y1="${y.toFixed(1)}" x2="${CW-MR}" y2="${y.toFixed(1)}"/><text class="axl" x="${ML-6}" y="${(y+3.5).toFixed(1)}" text-anchor="end">${fmt(v,dd)}</text>`;});
  if(opt.base100){const y=Y(100);g+=`<line x1="${ML}" y1="${y.toFixed(1)}" x2="${CW-MR}" y2="${y.toFixed(1)}" stroke="${cssv('--line-strong')}" stroke-dasharray="4 3"/>`;}
  let lm='';xs.forEach((d,i)=>{const mo=d.slice(0,7);if(mo!==lm){lm=mo;g+=`<text class="axl" x="${X(i).toFixed(1)}" y="${CH-8}" text-anchor="middle">${d.slice(2,7).replace('-','/')}</text>`;}});
  series.forEach(sr=>{let p='',st=false;sr.vals.forEach((v,i)=>{if(v==null)return;p+=(st?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';st=true;});
    g+=`<path class="ln" d="${p}" stroke="${sr.color}" stroke-width="${sr.w||1.8}"/>`;
    for(let i=sr.vals.length-1;i>=0;i--){if(sr.vals[i]!=null){g+=`<circle cx="${X(i).toFixed(1)}" cy="${Y(sr.vals[i]).toFixed(1)}" r="3" fill="${sr.color}"/>`;break;}}});
  g+=`<g class="cg" style="opacity:0"><line class="cross cx" y1="${MT}" y2="${CH-MB}"/></g>`;
  const svg=document.getElementById(svgId);svg.innerHTML=g;
  svg.onmousemove=ev=>{const r=svg.getBoundingClientRect(),px=(ev.clientX-r.left)/r.width*CW,tip=document.getElementById(tipId);
    const cg=svg.querySelector('.cg'),cx=svg.querySelector('.cx');if(px<ML||px>CW-MR){tip.style.opacity=0;cg.style.opacity=0;return;}
    let i=Math.round((px-ML)/(CW-ML-MR)*(n-1));i=Math.max(0,Math.min(n-1,i));cg.style.opacity=1;cx.setAttribute('x1',X(i));cx.setAttribute('x2',X(i));
    const rows=series.map(sr=>({name:sr.name,color:sr.color,v:sr.vals[i]})).filter(x=>x.v!=null).sort((a,b)=>b.v-a.v);
    tip.innerHTML=`<div class="td">${xs[i]}</div>`+rows.map(rw=>`<div class="row"><span class="l"><span class="sw" style="background:${rw.color}"></span><span class="nm2">${esc(rw.name)}</span></span><span class="val">${rw.v.toFixed(opt.tipdec??1)}${opt.unit||''}</span></div>`).join('');
    tip.style.opacity=1;const xpx=X(i)/CW*r.width;tip.style.left=Math.min(r.width-tip.offsetWidth-4,Math.max(4,xpx+12))+'px';tip.style.top='8px';};
  svg.onmouseleave=()=>{document.getElementById(tipId).style.opacity=0;const cg=svg.querySelector('.cg');if(cg)cg.style.opacity=0;};
}
function legendHTML(id,series){document.getElementById(id).innerHTML=series.map(s=>`<span class="chip on" style="cursor:default"><i class="sw" style="background:${s.color}"></i>${esc(s.name)}</span>`).join('');}
function drawMacro(){
  if(!(MACRO.cats||[]).length){$('#mclegend').innerHTML='<span class="phint">データ取得に失敗したため休止中です（次回の更新で戻ります）。</span>';$('#mcchart').innerHTML='';return;}
  const cols=PAL(),[s,e]=mslice(),xs=MDATES.slice(s,e),cat=state.mcCat;
  const perLbl={21:'1か月',63:'3か月',126:'6か月',252:'1年',520:'2年'}[state.mcPer]||'';
  let series=[],opt={base100:true,tipdec:1};
  $('#ratesub-row').hidden=(cat!=='Rates');
  $('#mc-title').textContent=cat==='all'?'クロスアセット・パフォーマンス（分類ごとの平均）':(cat==='Rates'?'金利：'+RSUBLABEL[state.rateSub]:'クロスアセット：'+CATLABEL[cat]);
  $('#mc-hint').textContent=perLbl+' ・ 初日＝100';
  if(cat==='all'){MACRO.cats.forEach((c,i)=>series.push({name:c.key==='Rates'?'金利（債券価格）':c.label,color:cols[i%8],vals:avgSeries(c.key==='Rates'?MACRO.ratesPx:c.members,s,e)}));}
  else if(cat==='Rates'){opt={base100:false,unit:'%',tipdec:2,dec:2};$('#mc-hint').textContent=perLbl+' ・ 利回り（%）';
    const mem=(RGROUPS[state.rateSub]||[]).filter(t=>MI[t]);
    if(!mem.length){$('#mclegend').innerHTML='<span class="phint">データがありません。</span>';$('#mcchart').innerHTML='';return;}
    mem.forEach((t,i)=>series.push({name:MI[t].name,color:cols[i%8],vals:MI[t].close.slice(s,e)}));}
  else MACRO.cats.find(c=>c.key===cat).members.forEach((t,i)=>series.push({name:MI[t].name,color:cols[i%8],vals:rebase(MI[t].close.slice(s,e))}));
  legendHTML('mclegend',series);lineChart('mcchart','mctip',series,xs,opt);
}
function drawRatios(){
  if(!(MACRO.ratios||[]).length){$('#rtlegend').innerHTML='';$('#rtchart').innerHTML='';$('#rtdesc').innerHTML='';return;}
  const cols=PAL(),[s,e]=mslice(),xs=MDATES.slice(s,e);
  const series=MACRO.ratios.map((r,i)=>({name:r.label,color:cols[i%8],vals:rebase(r.series.slice(s,e))}));
  legendHTML('rtlegend',series);lineChart('rtchart','rttip',series,xs,{base100:true,tipdec:1,h:300});
  $('#rtdesc').innerHTML=MACRO.ratios.map((r,i)=>`<div><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${cols[i%8]};margin-right:6px"></span><b style="color:var(--ink)">${esc(r.label)}</b>：${esc(r.desc)}</div>`).join('');
}
function drawWorld(){$('#w-period').textContent=(MACRO.start&&MACRO.updated)?`${MACRO.updated}まで（欧米市場は前営業日）`:'';drawMacro();drawRatios();worldDrawn=true;}

/* ================= テーマ別資金フロー ================= */
const METRIC={
  index:{src:'turnover_oku',rebased:true,title:'売買代金の推移（指数）',desc:'各テーマの売買代金を「期間の初日＝100」にそろえた推移。規模の違うテーマどうしを伸び方で比べられます。'},
  oku:{src:'turnover_oku',rebased:false,title:'売買代金の推移（実額）',desc:'テーマの構成銘柄の売買代金の合計。実際に動いている資金の大きさです。'},
  share:{src:'share',rebased:false,title:'売買代金シェアの推移',desc:'全銘柄の売買代金に占める割合。資金の配分がどう移っているか（ローテーション）を見ます。'},
  ret:{src:'ret_index',rebased:true,title:'株価の推移（等加重）',desc:'構成銘柄の株価を等しい重みで平均した指数（初日＝100）。売買代金とは別に、株価が上がっているかを見ます。'},
};
function metUnit(){return state.metric==='share'?'%':(state.metric==='oku'?U.turnLong:'');}
function rangeIdx(){if(state.range==='ytd'){let s=dates.findIndex(d=>d>=latestYear+'-01-01');if(s<0)s=0;return[s,N];}const r=Math.min(+state.range,N);return[N-r,N];}
function seriesData(t){const m=METRIC[state.metric];let a=movAvg(t[m.src],state.smooth);const[s,e]=rangeIdx();a=a.slice(s,e);if(m.rebased){const b=a[0]||1;a=a.map(v=>v/b*100);}return a;}
const CW=760,CH=360,ML=50,MR=150,MT=14,MB=28;
function drawChart(){
  const m=METRIC[state.metric];
  $('#chart-title').textContent=m.title;$('#chart-desc').textContent=m.desc;
  $('#chart-hint').textContent=(state.range==='ytd'?'年初来':state.range+'日')+' ・ '+state.smooth+'日平均';
  const okb=document.querySelector('#metric button[data-m="oku"]');if(okb)okb.textContent='実額（'+U.turnLong+'）';
  if(!state.focus||!state.selected.includes(state.focus))state.focus=state.selected[state.selected.length-1]||null;
  const[s,e]=rangeIdx(),xs=dates.slice(s,e),br=cssv('--brand'),gl=cssv('--grey-line');
  const series=state.selected.map(n=>byName[n]).filter(Boolean).map(t=>({name:t.name,focus:t.name===state.focus,vals:seriesData(t)}));
  series.sort((a,b)=>a.focus-b.focus);
  let lo=Infinity,hi=-Infinity;series.forEach(sr=>sr.vals.forEach(v=>{if(v<lo)lo=v;if(v>hi)hi=v;}));
  if(!isFinite(lo)){lo=0;hi=1;}if(m.rebased){lo=Math.min(lo,100);hi=Math.max(hi,100);}
  const pad=(hi-lo)*0.04||1;lo-=pad;hi+=pad;if(metUnit()==='%'||!m.rebased)lo=Math.max(0,lo);
  const ax=niceAxis(lo,hi,5);lo=ax.lo;hi=ax.hi;const dd=ax.step<1?(ax.step<0.1?2:1):0;
  const n=xs.length,X=i=>ML+(CW-ML-MR)*(n<=1?0:i/(n-1)),Y=v=>MT+(CH-MT-MB)*(1-(v-lo)/(hi-lo));
  let g='';
  ax.ticks.forEach(v=>{const y=Y(v);g+=`<line class="gl" x1="${ML}" y1="${y.toFixed(1)}" x2="${CW-MR}" y2="${y.toFixed(1)}"/><text class="axl" x="${ML-6}" y="${(y+3.5).toFixed(1)}" text-anchor="end">${fmt(v,dd)}</text>`;});
  if(m.rebased){const y=Y(100);g+=`<line x1="${ML}" y1="${y.toFixed(1)}" x2="${CW-MR}" y2="${y.toFixed(1)}" stroke="${cssv('--line-strong')}" stroke-dasharray="4 3"/>`;}
  let lm='';xs.forEach((d,i)=>{const mo=d.slice(0,7);if(mo!==lm){lm=mo;g+=`<text class="axl" x="${X(i).toFixed(1)}" y="${CH-8}" text-anchor="middle">${d.slice(2,7).replace('-','/')}</text>`;}});
  // 右端ラベル(重なりを避けて縦にずらす)
  const labs=series.map(sr=>({sr,y:Y(sr.vals[sr.vals.length-1])})).sort((a,b)=>a.y-b.y);
  for(let i=1;i<labs.length;i++)if(labs[i].y-labs[i-1].y<14)labs[i].y=labs[i-1].y+14;
  series.forEach(sr=>{let p='';sr.vals.forEach((v,i)=>{p+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';});
    const li=sr.vals.length-1,c=sr.focus?br:gl;
    if(sr.focus)g+=`<path d="${p} L${X(li).toFixed(1)} ${Y(lo).toFixed(1)} L${X(0).toFixed(1)} ${Y(lo).toFixed(1)} Z" fill="${br}" fill-opacity=".07"/>`;
    g+=`<path class="ln" d="${p}" stroke="${c}" stroke-width="${sr.focus?2.6:1.4}"/><circle cx="${X(li).toFixed(1)}" cy="${Y(sr.vals[li]).toFixed(1)}" r="${sr.focus?4:2.6}" fill="${c}"/>`;});
  labs.forEach(({sr,y})=>{const v=sr.vals[sr.vals.length-1];
    g+=`<text x="${CW-MR+8}" y="${(y+4).toFixed(1)}" font-size="${sr.focus?12:11}" font-weight="${sr.focus?700:400}" fill="${sr.focus?br:cssv('--faint')}" style="cursor:pointer" data-nm="${esc(sr.name)}">${esc(sr.name.length>9?sr.name.slice(0,9)+'…':sr.name)} ${m.rebased?Math.round(v):fmt(v,metUnit()==='%'?2:0)}</text>`;});
  g+=`<g id="cg" style="opacity:0"><line class="cross" id="cx" y1="${MT}" y2="${CH-MB}"/></g>`;
  const svg=$('#chart');svg.innerHTML=g;svg.__ctx={series,xs,X,n};
  svg.querySelectorAll('text[data-nm]').forEach(t=>t.onclick=()=>{state.focus=t.dataset.nm;drawChart();drawRank();});
  drawLegend();
}
function drawLegend(){
  $('#legend').innerHTML=state.selected.map(nm=>`<span class="chip ${nm===state.focus?'on':''}" data-nm="${esc(nm)}"><i class="sw"></i>${esc(nm)}<span class="x" data-x="1" title="外す">✕</span></span>`).join('')||'<span class="phint">右のランキングからテーマを選んでください</span>';
  $$('#legend .chip').forEach(ch=>ch.onclick=e=>{const nm=ch.dataset.nm;if(e.target.dataset.x){removeTheme(nm);return;}state.focus=nm;drawChart();drawRank();});
}
function bindTip(){const svg=$('#chart'),tip=$('#tip');
  svg.addEventListener('mousemove',ev=>{const ctx=svg.__ctx;if(!ctx)return;const r=svg.getBoundingClientRect(),px=(ev.clientX-r.left)/r.width*CW;
    const cg=svg.querySelector('#cg'),cx=svg.querySelector('#cx');if(px<ML||px>CW-MR){tip.style.opacity=0;if(cg)cg.style.opacity=0;return;}
    let i=Math.round((px-ML)/(CW-ML-MR)*(ctx.n-1));i=Math.max(0,Math.min(ctx.n-1,i));const xp=ctx.X(i);cg.style.opacity=1;cx.setAttribute('x1',xp);cx.setAttribute('x2',xp);
    const m=METRIC[state.metric],rows=ctx.series.map(sr=>({name:sr.name,f:sr.focus,v:sr.vals[i]})).sort((a,b)=>b.v-a.v);
    tip.innerHTML=`<div class="td">${ctx.xs[i]}</div>`+rows.map(rw=>`<div class="row"><span class="l"><span class="sw" style="background:${rw.f?'var(--brand)':'var(--grey-line)'}"></span><span class="nm2" style="${rw.f?'font-weight:700':''}">${esc(rw.name)}</span></span><span class="val">${m.rebased?fmt(rw.v,1):fmt(rw.v,metUnit()==='%'?2:0)}${metUnit()==='%'?'%':''}</span></div>`).join('');
    tip.style.opacity=1;const xpx=xp/CW*r.width;tip.style.left=Math.min(r.width-tip.offsetWidth-4,Math.max(4,xpx+12))+'px';tip.style.top='8px';});
  svg.addEventListener('mouseleave',()=>{tip.style.opacity=0;const cg=svg.querySelector('#cg');if(cg)cg.style.opacity=0;});}
function focusTheme(nm,mapToo){if(!byName[nm])return;if(!state.selected.includes(nm)){state.selected.push(nm);if(state.selected.length>8)state.selected.shift();}
  state.focus=nm;if(mapToo){state.mapTheme=nm;drawHeat();drawStock();}drawChart();drawRank();}
function removeTheme(nm){state.selected=state.selected.filter(x=>x!==nm);if(state.focus===nm)state.focus=state.selected[state.selected.length-1]||null;drawChart();drawRank();}
function drawRank(){const key=state.sort;
  $('#th-metric').textContent=key==='surge'?'急増率':'シェア変化';
  $('#rank-desc').textContent=key==='surge'?'売買代金の「直近5日平均 ÷ その前20日平均 −1」。資金が集まり始めたテーマが上に来ます。':'売買代金シェアが20営業日前から何ポイント動いたか。プラスは流入、マイナスは流出。';
  const all=[...themes].filter(t=>t[key]!=null).sort((a,b)=>b[key]-a[key]);
  const nv=gateN('themeRank',all.length),rows=all.slice(0,nv),maxAbs=Math.max(...all.map(t=>Math.abs(t[key])),1);
  $('#rk-body').innerHTML=rows.map(t=>{const on=state.selected.includes(t.name),f=t.name===state.focus,val=t[key],w=Math.abs(val)/maxAbs*24;
    const bar=val>=0?`<i style="left:50%;width:${w}px;background:var(--brand)"></i>`:`<i style="right:50%;width:${w}px;background:var(--down)"></i>`;
    return `<tr class="${f?'on':''}" data-nm="${esc(t.name)}"><td><div class="nm"><span class="sw ${on?'on':''}" style="${on&&!f?'background:var(--grey-line)':''}"></span><span class="t" title="${esc(t.name)}（${esc(t.cat)}・${t.n}銘柄）">${esc(t.name)}</span></div></td>
      <td class="num ${val>=0?'up':'down'}">${sign(val)}${key==='surge'?'%':'pt'}</td><td><div class="sbar"><div class="mid"></div>${bar}</div></td>
      <td class="num ${t.ret_20d>=0?'up':'down'}">${sign(t.ret_20d)}%</td></tr>`;}).join('');
  $$('#rk-body tr').forEach(tr=>tr.onclick=()=>{const nm=tr.dataset.nm;if(state.selected.includes(nm)&&state.focus===nm)removeTheme(nm);else focusTheme(nm,false);});
  $('#rk-lock').innerHTML=lockHTML('themeRank',all.length-nv,4);
}
/* ローテーションマップ */
function zscore(a){const n=a.length;if(!n)return[];const mu=a.reduce((x,y)=>x+y,0)/n;let v=0;for(const x of a)v+=(x-mu)*(x-mu);const sd=Math.sqrt(v/n);return sd<1e-9?a.map(()=>0):a.map(x=>(x-mu)/sd);}
function bucket5(a){const o=[];for(let i=0;i<a.length;i+=5){const s=a.slice(i,i+5);o.push(s.reduce((x,y)=>x+y,0)/s.length);}return o;}
function mapSeries(t){if(state.gran==='day'){const z=zscore(t.share);return{z:z.slice(-50),labels:dates.slice(-50)};}
  const z=zscore(bucket5(t.share)),wl=[];for(let i=0;i<dates.length;i+=5)wl.push(dates[i]);return{z:z.slice(-50),labels:wl.slice(-50)};}
function drawHeat(){
  const pr=cssv('--brandrgb'),nr=cssv('--downrgb');
  const col=z=>{const a=Math.min(1,Math.abs(z)/2)*0.88+0.06;return z>=0?`rgba(${pr},${a.toFixed(2)})`:`rgba(${nr},${a.toFixed(2)})`;};
  let rows=themes.map(t=>({t,ms:mapSeries(t)}));rows.forEach(r=>r.lastZ=r.ms.z.length?r.ms.z[r.ms.z.length-1]:0);
  if(state.hsort==='flow')rows.sort((a,b)=>b.lastZ-a.lastZ);
  else if(state.hsort==='name')rows.sort((a,b)=>a.t.name.localeCompare(b.t.name,'ja'));
  else{const ord=DATA.categories||[];rows.sort((a,b)=>(ord.indexOf(a.t.cat)-ord.indexOf(b.t.cat))||((b.t.surge??-999)-(a.t.surge??-999)));}
  const total=rows.length;
  if(state.hquery){const q=state.hquery.toLowerCase();rows=rows.filter(r=>r.t.name.toLowerCase().includes(q)||(r.t.cat||'').toLowerCase().includes(q));}
  const nv=gateN('heatmap',rows.length),hidden=rows.length-nv;rows=rows.slice(0,nv);
  $('#hsearch-hint').textContent=state.hquery?`${rows.length+hidden} / ${total} テーマ`:`全 ${total} テーマ`;
  $('#hscale').innerHTML=[-2,-1.2,-.5,0,.5,1.2,2].map(z=>`<i style="background:${col(z)}"></i>`).join('');
  $('#hm-lock').innerHTML=lockHTML('heatmap',hidden,6);
  const svg=$('#heat');
  if(!rows.length){svg.setAttribute('viewBox','0 0 260 40');svg.setAttribute('width',260);svg.setAttribute('height',40);svg.innerHTML=`<text x="8" y="24" font-size="12" fill="${cssv('--faint')}">該当するテーマがありません</text>`;return;}
  const nc=Math.max(...rows.map(r=>r.ms.z.length),1),cell=11,rh=17,lblW=132,topH=20,W=lblW+nc*cell+8,H=topH+rows.length*rh+6,labels=rows[0].ms.labels;
  let g='';labels.forEach((d,j)=>{if(j%(state.gran==='day'?10:6)===0)g+=`<text class="axl" x="${lblW+j*cell+cell/2}" y="${topH-6}" text-anchor="middle" font-size="9">${d.slice(2,7).replace('-','/')}</text>`;});
  rows.forEach((r,ri)=>{const y=topH+ri*rh,sel=r.t.name===state.mapTheme;
    g+=`<text x="${lblW-6}" y="${y+rh/2+3.5}" text-anchor="end" font-size="11" fill="${sel?cssv('--brand'):cssv('--ink-2')}" font-weight="${sel?700:400}">${esc(r.t.name)}</text>`;
    r.ms.z.forEach((z,j)=>{g+=`<rect class="hcell" data-nm="${esc(r.t.name)}" x="${lblW+j*cell}" y="${y}" width="${cell-1.5}" height="${rh-2}" rx="2" fill="${col(z)}"><title>${esc(r.t.name)} ${r.ms.labels[j]}: z=${z.toFixed(2)}</title></rect>`;});
    g+=`<rect class="rowhit" data-nm="${esc(r.t.name)}" x="0" y="${y}" width="${W}" height="${rh-1}"></rect>`;});
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);svg.setAttribute('height',H);svg.innerHTML=g;
  svg.querySelectorAll('.rowhit,.hcell').forEach(el=>el.addEventListener('click',()=>{state.mapTheme=el.dataset.nm;state.spStock=null;drawHeat();drawStock();}));
  syncPanelHeight();
}
/* ローソク足(銘柄ごとのOHLCを表示時に読み込み) */
const OHLC_CACHE={};
function loadOHLC(code){const key=OHLC_DIR+code;if(!(key in OHLC_CACHE))OHLC_CACHE[key]=fetch(OHLC_DIR+encodeURIComponent(code)+'.json').then(r=>r.ok?r.json():null).catch(()=>null);return OHLC_CACHE[key];}
function _sma(a,w){const o=[];let s=0;for(let i=0;i<a.length;i++){s+=a[i];if(i>=w)s-=a[i-w];o.push(i>=w-1?s/w:null);}return o;}
function _aggW(oh){const R={d:[],o:[],h:[],l:[],c:[]};for(let i=0;i<oh.d.length;i+=5){const e=Math.min(i+5,oh.d.length);let hh=-1e18,ll=1e18;for(let j=i;j<e;j++){if(oh.h[j]>hh)hh=oh.h[j];if(oh.l[j]<ll)ll=oh.l[j];}R.d.push(oh.d[i]);R.o.push(oh.o[i]);R.h.push(hh);R.l.push(ll);R.c.push(oh.c[e-1]);}return R;}
function candleSVG(oh,per,freq,H,WW){
  if(!oh)return '<div class="phint" style="padding:16px 0">この銘柄のチャートは未収録です。</div>';
  const data=freq==='week'?_aggW(oh):oh;let bars=freq==='week'?Math.ceil(per/5):per;bars=Math.min(bars,data.c.length);const s=data.c.length-bars;
  const D=data.d.slice(s),O=data.o.slice(s),Hi=data.h.slice(s),Lo=data.l.slice(s),C=data.c.slice(s);
  const m5=_sma(data.c,5).slice(s),m20=_sma(data.c,20).slice(s),m50=_sma(data.c,50).slice(s);
  const W=WW||700,CH=H||280,L=56,R=8,T=8,B=20;let lo=Infinity,hi=-Infinity;Hi.forEach(v=>{if(v>hi)hi=v});Lo.forEach(v=>{if(v<lo)lo=v});
  [m5,m20,m50].forEach(a=>a.forEach(v=>{if(v!=null){if(v>hi)hi=v;if(v<lo)lo=v;}}));if(!isFinite(lo)){lo=0;hi=1;}const pad=(hi-lo)*0.04||1;lo-=pad;hi+=pad;
  const ax=niceAxis(lo,hi,4);lo=ax.lo;hi=ax.hi;
  const n=C.length,bw=(W-L-R)/Math.max(n,1),X=i=>L+bw*(i+0.5),Y=v=>T+(CH-T-B)*(1-(v-lo)/(hi-lo));
  const cUp=cssv('--up'),cDn=cssv('--down');let g='';
  ax.ticks.forEach(v=>{const y=Y(v);g+=`<line class="gl" x1="${L}" y1="${y.toFixed(1)}" x2="${W-R}" y2="${y.toFixed(1)}"/><text class="axl" x="${L-5}" y="${(y+3).toFixed(1)}" text-anchor="end">${fmt(v,ax.step<1?2:0)}</text>`;});
  let lm='';D.forEach((d,i)=>{const mo=d.slice(0,7);if(mo!==lm){lm=mo;g+=`<text class="axl" x="${X(i).toFixed(1)}" y="${CH-6}" text-anchor="middle">${d.slice(2,7).replace('-','/')}</text>`;}});
  const wq=Math.max(0.6,bw*0.32);
  for(let i=0;i<n;i++){const c=C[i]>=O[i]?cUp:cDn,x=X(i);g+=`<line x1="${x.toFixed(1)}" y1="${Y(Hi[i]).toFixed(1)}" x2="${x.toFixed(1)}" y2="${Y(Lo[i]).toFixed(1)}" stroke="${c}" stroke-width="1"/>`;
    const ya=Y(Math.max(O[i],C[i])),yb=Y(Math.min(O[i],C[i]));g+=`<rect x="${(x-wq).toFixed(1)}" y="${ya.toFixed(1)}" width="${(wq*2).toFixed(1)}" height="${Math.max(0.8,yb-ya).toFixed(1)}" fill="${c}"/>`;}
  const ln=(a,col)=>{let p='',st=false;a.forEach((v,i)=>{if(v==null)return;p+=(st?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';st=true;});return p?`<path d="${p}" fill="none" stroke="${col}" stroke-width="1.3"/>`:'';};
  g+=ln(m5,cssv('--c2'))+ln(m20,cssv('--brand'))+ln(m50,cssv('--c4'));
  return `<svg viewBox="0 0 ${W} ${CH}" width="100%" style="overflow:visible">${g}</svg>`;
}
function candleCtl(idp,per,freq){const P=[['21','1か月'],['63','3か月'],['126','6か月'],['252','1年'],['520','2年']];
  return `<div class="ctlrow" style="margin:6px 0 4px"><div class="seg" id="${idp}per">${P.map(p=>`<button data-p="${p[0]}" aria-pressed="${+p[0]===per}">${p[1]}</button>`).join('')}</div>
    <div class="seg" id="${idp}freq"><button data-f="day" aria-pressed="${freq==='day'}">日足</button><button data-f="week" aria-pressed="${freq==='week'}">週足</button></div>
    <span class="legend" style="margin:0"><span><i style="background:var(--c2)"></i>5日線</span><span><i style="background:var(--brand)"></i>20日線</span><span><i style="background:var(--c4)"></i>50日線</span></span></div>`;}
function mountCandle(boxId,idp,code,getPer,setPer,getFreq,setFreq,H,isCur,WW){
  const box=document.getElementById(boxId);if(!box)return;const render=()=>{box.innerHTML='<div class="phint">読み込み中…</div>';
    loadOHLC(code).then(oh=>{if(isCur&&!isCur())return;box.innerHTML=candleSVG(oh,getPer(),getFreq(),H,WW);});};
  seg(idp+'per',b=>{setPer(+b.dataset.p);render();});seg(idp+'freq',b=>{setFreq(b.dataset.f);render();});render();}
/* 構成銘柄パネル */
function drawStock(){
  const el=$('#stockpanel'),th=state.mapTheme?byName[state.mapTheme]:null;
  if(!th){el.innerHTML='<div class="sp-sub">左のマップでテーマを押すと、構成銘柄がここに表示されます。</div>';return;}
  let rows=(th.members||[]).map(c=>({code:c,...STK[c]})).filter(x=>x.name);
  if(state.spStock&&!rows.some(r=>r.code===state.spStock))state.spStock=null;
  const k=state.spSort;rows.sort((a,b)=>((b[k]??-1e9)-(a[k]??-1e9)));
  const nv=gateN('members',rows.length),hidden=rows.length-nv;rows=rows.slice(0,nv);
  const th2=(id,lbl)=>`<th data-k="${id}" style="${k===id?'color:var(--ink)':''}">${lbl}</th>`;
  el.innerHTML=`<div class="sp-h">${esc(th.name)}<span class="c">${esc(th.cat)}・${th.n}銘柄</span></div>
    <div class="sp-sub">売買代金の上位（見出しで並べ替え・行を押すとローソク足）</div>
    <div class="sp-list"><table class="sp"><thead><tr><th class="l">銘柄</th>${th2('to','代金')}${th2('surge','急増')}${th2('ret20','20日')}<th>推移</th></tr></thead>
    <tbody>${rows.map(s=>`<tr data-code="${esc(s.code)}" class="${s.code===state.spStock?'on':''}"><td><div class="snm" title="${esc(s.name)}">${esc(s.name)}</div><span class="sc">${esc(s.code)}</span></td>
      <td class="num">${fmt(s.to,1)}</td><td class="num ${(s.surge??0)>=0?'up':'down'}">${sign(s.surge,0)}%</td><td class="num ${(s.ret20??0)>=0?'up':'down'}">${sign(s.ret20)}%</td><td>${spark(s.spark)}</td></tr>`).join('')}</tbody></table>${lockHTML('members',hidden,4)}</div>
    <div class="sp-h" style="font-size:13px;margin-top:10px">${state.spStock?esc(STK[state.spStock]?.name||state.spStock)+stockLinks(state.spStock):'<span class="phint">銘柄を押すとローソク足を表示</span>'}</div>
    ${state.spStock?candleCtl('sp',state.spPer,state.spFreq):''}<div id="spcandle"></div>`;
  el.querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{state.spSort=h.dataset.k;drawStock();});
  el.querySelectorAll('tbody tr').forEach(tr=>tr.onclick=()=>{state.spStock=tr.dataset.code;drawStock();});
  if(state.spStock){const cur=state.spStock;mountCandle('spcandle','sp',cur,()=>state.spPer,v=>state.spPer=v,()=>state.spFreq,v=>state.spFreq=v,300,()=>state.spStock===cur);}
  syncPanelHeight();
}
function syncPanelHeight(){const hm=document.querySelector('.hm-scroll'),sp=$('#stockpanel');if(!hm||!sp)return;
  if(window.innerWidth<=980){sp.style.height='';return;}const h=hm.getBoundingClientRect().height;if(h>200)sp.style.height=Math.max(h,520)+'px';}
/* Top100 */
function rkTop(){return RK?(state.rkMetric==='to'?RK.top_to:RK.top_vol):[];}
function rkSeries(code){const s=RK.stocks[code];return state.rkMetric==='to'?s.rt:s.rv;}
function rkDelta(code){const s=RK.stocks[code];return state.rkMetric==='to'?s.d_to:s.d_vol;}
function rankMini(arr){const w=64,h=16,cl=v=>Math.min(105,v);let p='';arr.forEach((r,i)=>{const x=arr.length<2?0:i/(arr.length-1)*w,y=(cl(r)-1)/104*(h-3)+1.5;p+=(i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1)+' ';});
  return`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="display:block;margin:0 auto"><path d="${p}" fill="none" stroke="var(--brand)" stroke-width="1.3" opacity="0.85"/></svg>`;}
function rkChip(d){if(d==null)return'<span class="muted">NEW</span>';if(d>0)return`<span class="up">▲${d}</span>`;if(d<0)return`<span class="down">▼${-d}</span>`;return'<span class="muted">―</span>';}
function drawRkList(){
  const top=rkTop(),mrank=new Map(top.map((c,i)=>[c,i+1])),{k,dir}=state.rkSort,sgn=dir==='asc'?1:-1;
  const gv=c=>{const s=RK.stocks[c];if(k==='to')return s.to;if(k==='vol')return s.vol??-1;if(k==='mcap')return s.mcap??-1;if(k==='ratio')return s.ratio??-1;return mrank.get(c);};
  const nv=gateN('top100',top.length),open=new Set(top.slice(0,nv));
  let rows=[...top].filter(c=>open.has(c)).sort((a,b)=>(gv(a)-gv(b))*sgn);
  if(state.rkQuery){const q=state.rkQuery.toLowerCase();rows=rows.filter(c=>(RK.stocks[c].name||'').toLowerCase().includes(q)||c.toLowerCase().includes(q));}
  $('#rksearch-hint').textContent=state.rkQuery?`${rows.length}件`:'';
  $$('#rktbl .ar').forEach(a=>a.textContent=a.dataset.a===k?(dir==='asc'?'▲':'▼'):'');
  const H={to:`売買代金（${U.turn}）`,vol:market==='us'?'出来高（百万株）':'出来高（万株）',mcap:`時価総額（${U.mcap}）`,ratio:'代金÷時価'};
  $$('#rktbl thead th.srt').forEach(th=>{const kk=th.dataset.k;if(H[kk])th.innerHTML=H[kk]+`<span class="ar" data-a="${kk}">${kk===k?(dir==='asc'?'▲':'▼'):''}</span>`;});
  $('#rktbody').innerHTML=rows.length?rows.map(code=>{const s=RK.stocks[code],on=code===state.rkSel;
    return `<tr class="${on?'on':''}" data-code="${esc(code)}"><td class="num" style="text-align:left;font-weight:600;${on?'color:var(--brand)':''}">${mrank.get(code)}</td>
      <td><span class="nm"><span class="t" title="${esc(s.name)}">${esc(s.name)}</span><span class="cat num">${esc(code)}</span></span></td>
      <td class="num">${fmt(s.to,s.to>=100?0:1)}</td><td class="num">${s.vol==null?'–':(market==='us'?fmt(s.vol/1e6,1):fmt(s.vol/1e4,0))}</td><td class="num">${s.mcap!=null?fmt(s.mcap,s.mcap>=100?0:1):'–'}</td>
      <td class="num">${s.ratio==null?'–':(s.ratio>=10?`<span class="ratio-hi">${s.ratio.toFixed(2)}%</span>`:s.ratio.toFixed(2)+'%')}</td>
      <td class="num">${rkChip(rkDelta(code))}</td><td>${rankMini(rkSeries(code))}</td></tr>`;}).join('')
    :'<tr><td colspan="8" style="padding:12px;color:var(--faint)">該当する銘柄がありません。</td></tr>';
  $$('#rktbody tr[data-code]').forEach(tr=>tr.onclick=()=>selectRk(tr.dataset.code,true));
  openRkCard(false);
  $('#rkl-lock').innerHTML=lockHTML('top100',top.length-nv,7);
}
function drawRkBump(){
  const days=RK.days,n=days.length,top=rkTop();if(!top.length)return;
  const W=760,H=300,L=34,R=150,T=14,B=22,MAXR=105,X=i=>L+(n<=1?0:i/(n-1))*(W-L-R),Y=r=>T+(Math.min(MAXR,r)-1)/(MAXR-1)*(H-T-B);
  const gl=cssv('--grey-line'),ink=cssv('--ink-2'),br=cssv('--brand');let g='';
  [1,20,40,60,80,100].forEach(r=>{g+=`<line class="gl" x1="${L}" y1="${Y(r).toFixed(1)}" x2="${W-R}" y2="${Y(r).toFixed(1)}"/><text class="axl" x="${L-6}" y="${(Y(r)+3).toFixed(1)}" text-anchor="end">${r}</text>`;});
  let lm='';days.forEach((d,i)=>{const mo=d.slice(0,7);if(mo!==lm){lm=mo;g+=`<text class="axl" x="${X(i).toFixed(1)}" y="${H-7}" text-anchor="middle">${d.slice(2,7).replace('-','/')}</text>`;}});
  const path=code=>{let p='';rkSeries(code).forEach((r,i)=>p+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(r).toFixed(1)+' ');return p;};
  top.slice(0,state.rkRows).forEach(code=>{if(code===state.rkSel)return;const p=path(code),s=RK.stocks[code],lr=rkSeries(code)[n-1];
    g+=`<path class="rkbg" data-code="${esc(code)}" d="${p}" fill="none" stroke="${gl}" stroke-width="1.1" opacity="0.55"/>`;
    g+=`<path class="rkhit" data-code="${esc(code)}" d="${p}" fill="none" stroke="transparent" stroke-width="7" style="cursor:pointer"><title>${esc(s.name)} (${esc(code)}) ${lr>100?'圏外':lr+'位'}</title></path>`;});
  const sel=state.rkSel||top[0],s=RK.stocks[sel],lr=rkSeries(sel)[n-1];
  g+=`<path d="${path(sel)}" fill="none" stroke="${br}" stroke-width="2.6" stroke-linejoin="round"/><circle cx="${X(n-1).toFixed(1)}" cy="${Y(lr).toFixed(1)}" r="3.6" fill="${br}"/>`;
  g+=`<text x="${(X(n-1)+8).toFixed(1)}" y="${(Y(lr)+4).toFixed(1)}" font-size="12" font-weight="700" fill="${br}">${esc(s.name.length>10?s.name.slice(0,10)+'…':s.name)} ${lr>100?'圏外':lr+'位'}</text>`;
  const svg=$('#rkbump');svg.innerHTML=g;
  svg.querySelectorAll('.rkhit').forEach(el=>{const c=el.dataset.code,v=()=>svg.querySelector(`.rkbg[data-code="${c}"]`);
    el.addEventListener('mouseenter',()=>{const x=v();if(x){x.setAttribute('stroke',ink);x.setAttribute('opacity','1');x.setAttribute('stroke-width','1.9');}});
    el.addEventListener('mouseleave',()=>{const x=v();if(x){x.setAttribute('stroke',gl);x.setAttribute('opacity','0.55');x.setAttribute('stroke-width','1.1');}});
    el.addEventListener('click',()=>selectRk(c));});
  $('#rkselname').textContent=' ― '+s.name;
}
/* 銘柄カード: 押した行のすぐ下(同じ行をもう一度押すと閉じる)。順位の推移の線を押しても開く */
function openRkCard(scroll){const tr=state.rkCard&&[...document.querySelectorAll('#rktbody tr[data-code]')].find(t=>t.dataset.code===state.rkCard);
  if(!tr){StockCard.closeBelow('rk');return;}
  const box=StockCard.below(tr,cardOpts(state.rkCard,{group:'rk',scroll,onClose:()=>{state.rkCard=null;}}));bindChips(box);}
function selectRk(code,toggle){state.rkSel=code;state.rkCard=toggle&&state.rkCard===code?null:code;
  if(state.rkCard&&state.rkQuery&&!(RK.stocks[code].name||'').toLowerCase().includes(state.rkQuery.toLowerCase())&&!code.toLowerCase().includes(state.rkQuery.toLowerCase())){state.rkQuery='';const q=$('#rksearch');if(q)q.value='';}
  drawRkList();openRkCard(true);drawRkBump();}
function drawRk(){if(!RK||!rkTop().length)return;if(!state.rkSel)state.rkSel=rkTop()[0];drawRkList();drawRkBump();}
function drawThemes(){
  $('#th-meta').textContent=`${MKNAME[market]} ・ ${DATA.n_themes}テーマ・${DATA.n_stocks.toLocaleString()}銘柄 ・ ${DATA.updated}まで`;
  $('#rk-sub').textContent=market==='us'?'米国上場の普通株・上位100':'東証上場の全銘柄・上位100';
  $('#th-foot').innerHTML=`<b>データ</b>：${market==='us'?'テーマ別ETF（SSGA・ARK）の構成銘柄':'株探のテーマ（テーマ→銘柄）'} × Yahoo Finance（日次の終値・出来高）。売買代金＝終値×出来高で近似。売り買いの方向は区別しません。<br>
    <b>急増率</b>＝直近5日平均の売買代金 ÷ その前20営業日の平均 −1。<b>シェアの変化</b>＝直近5日平均のシェア − 20営業日前の5日平均シェア。シェアはテーマの重複があるため合計が100%を超えます。`;
  drawChart();drawRank();drawHeat();drawStock();drawRk();
}

/* ================= 銘柄を探す ================= */
const _nz=s=>String(s||'').normalize('NFKC').toLowerCase();
let UIDX=null;
function univIndex(){const L=UNIV[market]||[];const m=new Map(L.map(x=>[x[0],x]));
  Object.entries(STK||{}).forEach(([c,s])=>{if(!m.has(c))m.set(c,[c,s.name,'']);});
  Object.entries((RK&&RK.stocks)||{}).forEach(([c,s])=>{if(!m.has(c))m.set(c,[c,s.name,'']);});
  return [...m.values()].map(x=>({code:x[0],name:x[1],sec:x[2]||'',k:_nz(x[0]+' '+x[1])}));}
function searchStocks(q){q=_nz(q).trim();if(!q)return[];UIDX=UIDX||univIndex();const c=_nz(q);
  return UIDX.map(x=>{const code=_nz(x.code),nm=_nz(x.name);let s=-1;
    if(code===c)s=0;else if(code.startsWith(c))s=1;else if(nm.startsWith(c))s=2;else if(nm.includes(c))s=3;else if(x.k.includes(c))s=4;return{x,s};})
    .filter(o=>o.s>=0).sort((a,b)=>a.s-b.s||a.x.code.localeCompare(b.x.code)).slice(0,30).map(o=>o.x);}
function themesOf(code){return themes.filter(t=>(t.members||[]).includes(code));}
function showStock(code){state.scCode=code;$('#sres').hidden=true;drawStockCard();}
function drawStockCard(){const box=$('#scard');if(!box)return;if(!state.scCode){box.innerHTML='';return;}
  StockCard.open(box,cardOpts(state.scCode,{scroll:false,onClose:()=>{state.scCode=null;}}));bindChips(box);}
/* 銘柄カード(assets/card.js・サイト共通)に渡す指定。所属テーマのボタンはカードの下に */
function cardOpts(code,extra){UIDX=UIDX||univIndex();const u=UIDX.find(x=>x.code===code)||{code,name:code,sec:''},ths=themesOf(code);
  return Object.assign({market,code,name:u.name,sub:u.sec||'',per:126,
    foot:ths.length?`<div class="meta" style="margin:4px 0 6px">所属テーマ（押すとテーマ別資金フローへ）</div><div class="chips">${ths.map(t=>`<button class="chip" data-nm="${esc(t.name)}">${esc(t.name)} <span class="${(t.surge??0)>=0?'up':'down'}">${sign(t.surge,0)}%</span></button>`).join('')}</div>`:''},extra);}
function bindChips(box){if(box)box.querySelectorAll('.chips .chip[data-nm]').forEach(b=>b.onclick=()=>{focusTheme(b.dataset.nm,true);goto('themes');});}
function renderResults(q){const box=$('#sres'),R=searchStocks(q);
  if(!q.trim()){box.hidden=true;return;}box.hidden=false;
  box.innerHTML=R.length?R.map((x,i)=>`<button data-code="${esc(x.code)}" class="${i===0?'kb':''}"><span>${esc(x.name)}</span><small>${esc(x.code)}${x.sec?' ・ '+esc(x.sec):''}</small></button>`).join(''):'<div class="phint" style="padding:10px 14px">該当する銘柄がありません。</div>';
  box.querySelectorAll('button').forEach(b=>b.onclick=()=>showStock(b.dataset.code));}
function drawStockSearch(){
  UIDX=null;$('#st-meta').textContent=`${MKNAME[market]} ・ ${((UNIV[market]||[]).length||0).toLocaleString()}銘柄から検索`;
  $('#sq').placeholder=market==='us'?'例：NVDA、Micron、Palantir':'例：6857、アドバンテスト、キオクシア';
  const pop=rkTop().slice(0,6);
  $('#spop').innerHTML=pop.length?'<span class="meta" style="align-self:center">売買代金の上位：</span>'+pop.map(c=>`<button class="chip" data-code="${esc(c)}">${esc(RK.stocks[c].name)} <span class="num muted">${esc(c)}</span></button>`).join(''):'';
  $$('#spop .chip').forEach(b=>b.onclick=()=>showStock(b.dataset.code));
  drawStockCard();
}

/* ================= スクリーニング(VCP) ================= */
// VCP_VAR: 'vcp'=VCP（従来） / 'vcp2'=VCP2（翌営業日の注文条件つき）。同じ表を vcp_{mk}.json / vcp2_{mk}.json で描き分ける
const VCP_DATA={};let VCP_VAR='vcp';
const vcpKey=mk=>VCP_VAR+'_'+mk;
function loadVcp(mkt){const key=vcpKey(mkt);if(VCP_DATA[key]!=null)return Promise.resolve(VCP_DATA[key]);
  return fetch(key+'.json?cb='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():{sessions:[]}).catch(()=>({sessions:[]})).then(j=>{VCP_DATA[key]=j;return j;});}
function vcpCols(){return [['prio','優先度','r'],['name','銘柄','l'],['sector','セクター','l'],['mcap','時価総額','r'],['listing','上場','r'],['buy','Buy','c'],['vcp','VCP','r'],['dist','ピボット','r'],...(VCP_VAR==='vcp2'?[['order','注文（翌営業日）','l']]:[]),['rs','RS','r'],['streak','継続','r'],['tl','最近の掲載','c'],['val','バリュエーション','c']];}
// 注文列(VCP2のみ): スクリーナー(vcp_check.make_order)が出す {ok,trig,lim,stop,risk,why}。値段は配当調整前の実際の株価
const VCP_ORDER_TIP='引けの時点でピボット待ちのVCPだけ。買い＝ピボットを上に抜けたら逆指値で買う（ピボット+3%を超えて始まったら買わない）。損切り＝最後の締まりの安値を下回ったら逆指値で売る。ピボットから損切りまで10%を超える形と、直前の出来高が多い形は見送り。';
function vcpOrderCell(o,mk){
  const P=v=>mk==='us'?'$'+Number(v).toFixed(2):Number(v).toLocaleString('ja-JP')+'円';
  const rv=Number(o.risk),rk=rv>10&&rv<10.05?rv.toFixed(2):rv.toFixed(1);   // 10%をわずかに超えた見送りが「10.0%」に見えないように
  const tip=`逆指値で${P(o.trig)}以上になったら、${P(o.lim)}までの指値で買い（${P(o.lim)}より上で始まったら買わない）。損切りは、逆指値で${P(o.stop)}以下になったら売り（ピボットから−${rk}%）。`;
  if(!o.ok)return `<span class="vord muted" title="${esc('見送り（'+o.why+'）。参考までに条件は：'+tip)}">見送り<small>${esc(o.why)}${String(o.why).includes('10%')?`（−${rk}%）`:''}</small></span>`;
  return `<span class="vord" title="${esc(tip)}"><b class="up">買</b> ${P(o.trig)}以上で逆指値（${P(o.lim)}まで）<small><b class="down">損切</b> ${P(o.stop)}以下で逆指値（−${rk}%）</small></span>`;}
function numOf(v){if(v==null||v==='')return null;if(typeof v==='number')return v;const n=parseFloat(String(v).replace(/[^0-9.]/g,''));return isFinite(n)?n:null;}
function vcpTL(sess,idx,code){const s=Math.max(0,idx-19);let g='<span class="vtl">';for(let i=s;i<=idx;i++){const on=sess[i].rows.some(r=>r.code===code);g+=`<i style="background:${on?'var(--brand)':'var(--surface-2)'}"></i>`;}return g+'</span>';}
const VALD={};
function drawVcp(){
  if(!(market in VALD)&&window.StockCard){const m=market;VALD[m]=null;StockCard.valData(m).then(j=>{VALD[m]=j||{stocks:{}};if(market===m)drawVcp();});}
  const mk=market,D=VCP_DATA[vcpKey(mk)],head=$('#vcp-head'),body=$('#vcp-body'),slider=$('#vcp-day'),sess=(D&&D.sessions)?D.sessions:[];
  const v2=VCP_VAR==='vcp2';
  $('#vcp-sched').textContent=SCHED[mk];$('#vcp-title').textContent=v2?'VCP2 ・ 翌営業日の注文つき':'VCP ・ トレンドテンプレート';$('#vcp2-foot').hidden=!v2;
  $('#vcp-lead').textContent=(mk==='us'?'上昇トレンドの条件（トレンドテンプレート）を満たし、値動きの幅が段階的に縮んでいる米国株。業績の成長条件つき。':'上昇トレンドの条件（トレンドテンプレート）を満たし、値動きの幅が段階的に縮んでいる日本株。増収15%以上・増益15%以上の条件つき。')+(v2?'VCPに、翌営業日の逆指値注文（買い・損切り・見送り）を加えたものです。':'');
  $('#sc-meta').textContent=D&&D.updated?`${MKNAME[mk]} ・ ${D.updated}まで`:'';
  if(!sess.length){head.innerHTML='';body.innerHTML='<tr><td style="padding:16px;color:var(--faint)">データを準備中です。</td></tr>';['#vs-n','#vs-new','#vs-gone'].forEach(s=>$(s).textContent='–');
    $('#vcp-daylabel').textContent='–';slider.max=0;$('#vcp-prev').disabled=true;$('#vcp-next').disabled=true;$('#vcp-lock').innerHTML='';return;}
  if(state.vcpIdx==null||state.vcpIdx>sess.length-1)state.vcpIdx=sess.length-1;
  slider.max=sess.length-1;slider.value=state.vcpIdx;
  const L=sess[sess.length-1],LP=sess.length>1?sess[sess.length-2]:null,lc=new Set(L.rows.map(r=>r.code)),lpc=new Set(LP?LP.rows.map(r=>r.code):[]);
  $('#vs-n').textContent=L.rows.length;$('#vs-new').textContent=LP?L.rows.filter(r=>!lpc.has(r.code)).length:'–';$('#vs-gone').textContent=LP?LP.rows.filter(r=>!lc.has(r.code)).length:'–';
  const idx=state.vcpIdx,cur=sess[idx],prev=idx>0?sess[idx-1]:null,prevCodes=new Set(prev?prev.rows.map(r=>r.code):[]),curCodes=new Set(cur.rows.map(r=>r.code)),prevMap=new Map(prev?prev.rows.map(r=>[r.code,r]):[]);
  $('#vcp-daylabel').textContent=cur.date;$('#vcp-prev').disabled=idx<=0;$('#vcp-next').disabled=idx>=sess.length-1;
  let rows=cur.rows.map((r,i)=>{const pr=prevMap.get(r.code);return Object.assign({},r,{_ord:i,_new:!!prev&&!prevCodes.has(r.code),_gone:false,_newprio:!!prev&&r.prio!=null&&!(pr&&pr.prio!=null)});});
  if(prev)prev.rows.filter(r=>!curCodes.has(r.code)).forEach(r=>rows.push(Object.assign({},r,{_gone:true,vcp:null,dist:null,prio:null,buy:false})));
  const q=_nz(state.vcpQuery);if(q)rows=rows.filter(r=>_nz(r.name).includes(q)||_nz(r.code).includes(q));
  // 優先度の並び=スクリーナーの並び(_ord)そのもの。Buy(VCP/FB)→買い場近辺→監視。FBのみBuyは優先度の数字が空欄でも最上段
  const{k,dir}=state.vcpSort,sgn=dir==='asc'?1:-1,gv=r=>{if(k==='prio')return r._ord==null?-1e9:-r._ord;if(k==='name'||k==='sector')return r[k==='name'?'code':'sector']||'';const v=(k==='mcap'||k==='listing')?(String(r[k]||'').includes('以上')?99:numOf(r[k])):r[k];return v==null?-1e9:v;};
  rows.sort((a,b)=>{if(a._gone!==b._gone)return a._gone?1:-1;const x=gv(a),y=gv(b);return(x<y?-1:x>y?1:0)*sgn;});
  const nv=gateN('vcp',rows.length),hidden=rows.length-nv;rows=rows.slice(0,nv);
  const cols=vcpCols();
  head.innerHTML=cols.map(c=>c[0]==='order'?`<th class="l" title="${esc(VCP_ORDER_TIP)}">${c[1]}</th>`:c[0]==='tl'||c[0]==='val'?`<th style="text-align:center">${c[1]}</th>`:`<th class="${c[2]==='l'?'l':''} srt" data-k="${c[0]}">${c[1]}<span class="ar">${c[0]===k?(dir==='asc'?'▲':'▼'):''}</span></th>`).join('');
  const cell=(r,c)=>{
    if(c==='prio'){if(r._gone||r.prio==null)return'<span class="muted">–</span>';return`<span style="font-weight:600;${r._newprio?'background:var(--warn-bg);color:var(--warn-ink);padding:1px 7px;border-radius:5px':''}">${r.prio}</span>`;}
    if(c==='buy'){if(!r.buy||r._gone)return'';
      // buy_type: VCP=段階的な収縮からの上抜け / FB=レンジ(ボックス)からの上抜け。古い履歴は buy_type なし=VCP
      if(r.buy_type==='FB')return'<span title="レンジブレイク：一定の値幅で持ち合ったあと、出来高を伴って上限を上に抜けた"><span class="up" style="font-weight:700;font-size:11px">BUY</span><span style="display:block;font-size:9.5px;font-weight:700;line-height:1.1;color:var(--brand)">レンジ</span></span>';
      return'<span class="up" style="font-weight:700;font-size:11px" title="VCPブレイク：値動きの幅が段階的に縮んだあと、買い点を上に抜けた">BUY</span>';}
    if(c==='name')return`<span class="nm"><span class="t" title="${esc(r.name)}" style="${r._new?'color:var(--down)':''}">${esc(r.name)}</span><span class="cat num">${esc(r.code)}</span>${r._new?'<span class="vtag down">●新規</span>':''}${r._gone?'<span class="vtag muted">消失</span>':''}</span>`;
    if(c==='vcp')return r.vcp!=null?`<b>${r.vcp}</b>`:'<span class="muted">–</span>';
    if(c==='dist')return r.dist!=null?`<span class="${r.dist>=0&&r.dist<=2?'up':''}">${r.dist>=0?'+':''}${r.dist.toFixed(1)}%</span>`:'<span class="muted">–</span>';
    if(c==='order')return(r._gone||!r.order)?'<span class="muted">–</span>':vcpOrderCell(r.order,mk);
    if(c==='rs')return r.rs??'';if(c==='mcap')return r.mcap?(typeof r.mcap==='number'?'$'+r.mcap+'B':esc(r.mcap)):'<span class="muted">–</span>';
    if(c==='sector')return `<span class="cat" style="font-size:11.5px">${esc(r.sector||'')}</span>`;
    if(c==='listing')return r.listing?(/[A-Za-z年]/.test(String(r.listing))?esc(String(r.listing).replace(/^(\d+)M$/,'$1か月')):esc(r.listing)+'年'):'<span class="muted">–</span>';
    if(c==='streak')return r._gone?'':r.streak;if(c==='tl')return vcpTL(sess,idx,r.code);
    if(c==='val'){const V=VALD[mk];if(!V)return '<span class="muted">…</span>';const v=V.stocks&&V.stocks[r.code],lb=window.StockCard&&StockCard.vlab(v);
      if(lb)return `<span class="vpill ${lb[0]}">${lb[1]}</span>`;const t=!v?(mk==='jp'?'収集中':'—'):v.ex?'対象外':v.status==='no_data'?'データなし':'—';return `<span class="muted" style="font-size:11px" title="${esc(v&&v.ex||'')}">${t}</span>`;}
    return'';};
  body.innerHTML=rows.map(r=>`<tr class="${r._gone?'gone':''}" data-code="${esc(r.code)}" style="cursor:pointer">`+cols.map(c=>`<td ${c[0]==='tl'?'style="text-align:center"':(c[2]==='l'?'':'class="num"')}>${cell(r,c[0])}</td>`).join('')+'</tr>').join('');
  body.querySelectorAll('tr[data-code]').forEach(tr=>tr.onclick=()=>{const c=tr.dataset.code;state.vcCode=state.vcCode===c?null:c;openVcCard(true);});
  $('#vcp-lock').innerHTML=lockHTML('vcp',hidden,8);
  openVcCard(false);
}
/* 銘柄カード: 押した行のすぐ下(同じ行をもう一度押すと閉じる) */
function openVcCard(scroll){const tr=state.vcCode&&[...document.querySelectorAll('#vcp-body tr[data-code]')].find(t=>t.dataset.code===state.vcCode);
  if(!tr){StockCard.closeBelow('vc');return;}
  const box=StockCard.below(tr,cardOpts(state.vcCode,{group:'vc',scroll,onClose:()=>{state.vcCode=null;}}));bindChips(box);}
function drawScreening(){const mk=market;loadVcp(mk).then(()=>{if(market===mk&&sn.tab!=='sns')drawVcp();});if(sn.tab==='sns')drawSns();}

/* ================= スクリーニング: SNS話題銘柄(日本株のみ・sns_jp.json) ================= */
const SN_T=['news','earn','anal','chart','div'];
const SN_TJ={news:'なぜ動いた？',earn:'決算の中身',anal:'今後どうなる？',chart:'どこで買う・売る？',div:'配当・優待・長期'};
const SN_TJME={news:'ニュース解説',earn:'決算解説',anal:'銘柄分析',chart:'チャート・売買',div:'配当・長期'};
const SN_SC={att:'var(--sn-att)',sup:'var(--sn-sup)',gap:'var(--sn-gap)'};
const SN_KW={news:['なぜ','理由','急騰','暴落','急落','下落','上昇','ストップ高','ストップ安','ニュース','tob','買収','提携','発表','爆上げ','材料','速報','破産'],
  earn:['決算','上方修正','下方修正','業績','増益','減益','増収','四半期','通期','赤字','黒字'],
  anal:['今後','将来性','買い時','分析','割安','見通し','成長','評価','注目','期待','予想','どうなる','買うべき','やばい'],
  chart:['チャート','テクニカル','目標株価','押し目','空売り','信用','デイトレ','掲示板','売り時'],
  div:['配当','優待','増配','減配','nisa','利回り','高配当','長期','権利','自社株買い','分割']};
const snStore={get(k){try{return localStorage.getItem(k);}catch(e){return null;}},set(k,v){try{localStorage.setItem(k,v);}catch(e){}}};
let SNS=null,snLoading=false;
const sn={tab:snStore.get('sc_tab')||'vcp',sort:snStore.get('sns_sort')||'att',idx:null,q:'',tf:'all',open:null};
/* 本人(動画を作る人)だけ: 足りない動画の型・既存動画の型との比較・動画の切り口 */
const snMe=()=>!!(window.JR&&JR.st&&JR.st.me);
const snTL=()=>snMe()?SN_TJME:SN_TJ;
const snFmtV=v=>v>=10000?(v/10000).toFixed(v>=100000?0:1)+'万':String(v||0);
const snLv=v=>v>=70?['h','高']:v>=40?['m','中']:['l','低'];
function loadSns(){if(SNS||snLoading)return;snLoading=true;
  fetch('sns_jp.json?cb='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():{sessions:[]}).catch(()=>({sessions:[]})).then(j=>{SNS=j;snLoading=false;drawSns();});
  if(window.JR&&JR.init)Promise.resolve(JR.init()).then(()=>{if(SNS)drawSns();}).catch(()=>{});}
function setScTab(t){sn.tab=t;snStore.set('sc_tab',t);
  $$('.sn-sub button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===t));
  $('#vcp-pane').hidden=t==='sns';$('#sns-pane').hidden=t!=='sns';
  if(t==='sns'){loadSns();drawSns();return;}
  if(VCP_VAR!==t){VCP_VAR=t;state.vcpIdx=null;state.vcCode=null;}
  const mk=market;drawVcp();loadVcp(mk).then(()=>{if(market===mk&&VCP_VAR===t)drawVcp();});}
function snRsn(s){const c=/ストップ|急騰|急落/.test(s)?'hot':/決算/.test(s)?'earn':'';return `<span class="sn-rsn ${c}">${esc(s)}</span>`;}
function snTbar(need){return `<span class="sn-tbar">${SN_T.map((t,i)=>`<i style="width:${need[i]||0}%;background:var(--sn-${t})" title="${SN_TJ[t]} ${need[i]||0}%"></i>`).join('')}</span>`;}
function snCell(k,v,sub){const[c,l]=snLv(v);
  return `<td class="${sn.sort===k?'sn-on':''} ${k==='sup'?'sn-hide':''}"><div class="sn-sc" style="--sc:${SN_SC[k]}"><span class="sn-lv ${c}">${l}</span><span class="sn-bar"><i style="width:${v}%"></i></span><span class="n">${v}</span></div>${sub?`<span class="sn-cs" style="text-align:right">${sub}</span>`:''}</td>`;}
function snStreak(sess,idx,code){let n=0;for(let i=idx;i>=0;i--){if(sess[i].rows.some(r=>r.code===code))n++;else break;}return n;}
function drawSns(){
  if(sn.tab!=='sns')return;
  const us=market!=='jp';$('#sn-usnote').hidden=!us;$('#sn-main').hidden=us;
  const sess=(SNS&&SNS.sessions)||[];
  $('#sc-meta').textContent=SNS&&SNS.updated?`日本株 ・ ${SNS.updated}更新`:'';
  if(us)return;
  const me=snMe(),TL=snTL(),body=$('#sn-body');
  $('#sn-thtype').textContent=me?'足りない動画の型':'みんなが知りたいこと';$('#sn-tflabel').textContent=$('#sn-thtype').textContent;
  $('#sn-tf').innerHTML=[['all','すべて'],...SN_T.map(t=>[t,TL[t]])].map(([k,l])=>`<button type="button" aria-pressed="${k===sn.tf}" data-k="${k}">${l}</button>`).join('');
  $('#sn-legend').innerHTML='知りたいことの割合：'+SN_T.map(t=>`<span><i style="background:var(--sn-${t})"></i>${TL[t]}</span>`).join('');
  $$('#sn-sort button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===sn.sort));
  $$('#sntbl th.sn-th').forEach(th=>th.classList.toggle('on',th.dataset.k===sn.sort));
  if(!sess.length){body.innerHTML=`<tr><td colspan="8" style="padding:16px;color:var(--faint)">${SNS?'データを準備中です（毎日17時台に更新）。':'読み込み中…'}</td></tr>`;
    ['#sn-n','#sn-new','#sn-open'].forEach(s=>$(s).textContent='–');$('#sn-daylabel').textContent='–';$('#sn-lock').innerHTML='';return;}
  if(sn.idx==null||sn.idx>sess.length-1)sn.idx=sess.length-1;
  const sl=$('#sn-day');sl.max=sess.length-1;sl.value=sn.idx;
  const idx=sn.idx,cur=sess[idx],prev=idx>0?sess[idx-1]:null,pc=new Set(prev?prev.rows.map(r=>r.code):[]),latest=idx===sess.length-1;
  $('#sn-daylabel').textContent=cur.date;$('#sn-prev').disabled=idx<=0;$('#sn-next').disabled=idx>=sess.length-1;
  const L=sess[sess.length-1],LP=sess.length>1?sess[sess.length-2]:null,lpc=new Set(LP?LP.rows.map(r=>r.code):[]);
  $('#sn-n').textContent=L.rows.length;$('#sn-new').textContent=LP?L.rows.filter(r=>!lpc.has(r.code)).length:'–';$('#sn-open').textContent=L.rows.filter(r=>r.gap>=70).length;
  const k=sn.sort,typeOf=r=>me?r.best:r.want;
  let all=cur.rows.map(r=>Object.assign({},r,{_new:!!prev&&!pc.has(r.code)})).sort((a,b)=>b[k]-a[k]||b.att-a.att);
  all.forEach((r,i)=>r._rank=i+1);
  const q=_nz(sn.q);let rows=all.filter(r=>(sn.tf==='all'||typeOf(r)===sn.tf)&&(!q||_nz(r.name).includes(q)||_nz(r.code).includes(q)));
  const nv=me?rows.length:gateN('sns',rows.length),hidden=rows.length-nv;rows=rows.slice(0,nv);
  body.innerHTML=rows.map(r=>{const t=typeOf(r),st=snStreak(sess,idx,r.code),dt=latest&&SNS.detail?SNS.detail[r.code]:null;
    const attSub=`候補${r.sug}件${r.tr!=null?` ・ 検索×${(+r.tr).toFixed(1)}`:''}`;
    const supSub=r.solo==null?'':(r.solo+r.multi)?`専用${r.solo}本・まとめ${r.multi}本`:'動画なし';
    const gapSub=dt&&dt.bonus?'<span class="down">伸びている動画あり</span>':'';
    const tg=dt&&me?` <span class="sn-cs" style="display:inline">空き+${dt.tgap[SN_T.indexOf(t)]}pt</span>`:'';
    return `<tr data-code="${esc(r.code)}" class="${r._new?'new':''} ${sn.open===r.code?'on':''}" style="cursor:pointer">
      <td class="num" style="text-align:right;color:var(--faint)">${r._rank}</td>
      <td class="nm"><b>${esc(r.name)}</b><small>${esc(r.code)}</small><span class="sn-cs">${esc(r.sector||'')}</span></td>
      <td>${(r.reasons||[]).map(snRsn).join('')}</td>
      <td><span class="sn-tl" style="--tc:var(--sn-${t})">${TL[t]}</span>${tg}<div style="margin-top:4px">${snTbar(r.need)}</div></td>
      ${snCell('att',r.att,attSub)}${snCell('sup',r.sup,supSub)}${snCell('gap',r.gap,gapSub)}
      <td class="num sn-hide" style="text-align:right">${r._new||!prev?'<b class="down">新規</b>':st+'日'}</td></tr>${sn.open===r.code?snDetail(r,dt,me):''}`;}).join('')
    ||'<tr><td colspan="8" class="muted" style="text-align:center;padding:24px">該当なし</td></tr>';
  body.querySelectorAll('tr[data-code]').forEach(tr=>tr.onclick=()=>{sn.open=sn.open===tr.dataset.code?null:tr.dataset.code;drawSns();});
  $('#sn-lock').innerHTML=me?'':lockHTML('sns',hidden,7);
}
function snDetail(r,dt,me){
  const TL=snTL(),need=r.need;
  const three=`<div class="sn-three">
    <div style="--sc:var(--sn-att)"><small>注目度</small><b>${r.att}</b><em>${dt?`予測候補 ${dt.parts.sug}/40 ・ 検索の伸び ${dt.parts.tr==null?'取得なし':dt.parts.tr+'/30'} ・ 株価の動き ${dt.parts.move}/30`:`予測候補 ${r.sug}件`}</em></div>
    <div style="--sc:var(--sn-sup)"><small>解説動画の多さ</small><b>${r.sup}</b><em>${r.solo!=null?`直近7日 専用${r.solo}本・まとめ${r.multi}本`:''}${dt?` ・ 合計${snFmtV(dt.views_sum)}回`:''}</em></div>
    <div style="--sc:var(--sn-gap)"><small>穴場度</small><b>${r.gap}</b><em>${dt&&dt.bonus?`伸びている専用動画で +${dt.bonus}点`:'注目度と（100 − 解説の多さ）の両方で決まる'}</em></div></div>`;
  if(!dt)return `<tr class="sn-detail"><td colspan="8">${three}<div class="sn-cs">動画の一覧と検索されている言葉は、最新日だけ表示します。</div></td></tr>`;
  const base=(dt.q||'').toLowerCase(),kindOf=w=>SN_T.find(t=>SN_KW[t].some(x=>w.includes(x)));
  const words=(dt.words||[]).map(w=>{const k=kindOf(w.replace(base,''));return `<span class="${k?'k':''}" style="${k?`--tc:var(--sn-${k})`:''}">${esc(w)}</span>`;}).join('')||'<span class="muted">株の話の予測候補なし</span>';
  const cmp=SN_T.map((t,i)=>`<span>${TL[t]}</span><span class="bars" style="--tc:var(--sn-${t})"><i style="width:${need[i]}%"></i>${me?`<i class="have" style="width:${dt.have[i]}%"></i>`:''}</span>
    <span class="g ${me&&dt.tgap[i]>0?'up':'muted'}">${me?(dt.tgap[i]>0?'+':'')+dt.tgap[i]:need[i]+'%'}</span>`).join('');
  const vids=(dt.top||[]).map((v,i)=>`<li class="${i===0&&!v.multi?'first':''}"><span class="t">${v.multi?'<span class="sn-rsn">まとめ</span>':'<span class="sn-rsn earn">専用</span>'}<a class="sn-vl" href="https://www.youtube.com/watch?v=${encodeURIComponent(v.id)}" target="_blank" rel="noopener">${esc(v.title)} ↗</a></span><span class="num">${snFmtV(v.views)}回</span>
    <span class="m">${i===0&&!v.multi?'<b style="color:var(--brand)">まず見るならこの動画</b> ・ ':''}${esc(v.ch)} ・ 登録者 ${snFmtV(v.subs)} ・ 再生÷登録者 <span class="${v.ratio>=1?'hot':''}">${(+v.ratio).toFixed(2)}倍</span></span></li>`).join('')||'<li class="muted">直近7日の解説動画はまだありません（穴場）</li>';
  const pct=x=>x==null?'–':`<span class="${x>=0?'up':'down'}">${(x*100).toFixed(1)}%</span>`;
  const idea={news:`「${dt.q}は${/ストップ高|急騰/.test(r.reasons.join(''))?'なぜ急騰した':/ストップ安|急落/.test(r.reasons.join(''))?'なぜ急落した':'なぜ動いた'}のか」— 材料と、続くかどうかを解説`,
    earn:`「${dt.q} 決算の中身」— 何が良くて何が悪かったかを数字で`,anal:`「${dt.q}の今後」— 事業の稼ぎ方と成長が続く条件（銘柄分析の型）`,
    chart:`「${dt.q} どこで買う・どこで逃げる」— 出来高とチャートの節目`,div:`「${dt.q} 配当・優待・株式分割」— 長期で持つ価値があるか`}[r.best];
  return `<tr class="sn-detail"><td colspan="8">
    <div class="sn-kpi"><span>終値<b>${Number(dt.close).toLocaleString()}</b>円</span><span>前日比<b>${pct(dt.r1)}</b></span><span>5日<b>${pct(dt.r5)}</b></span><span>売買代金<b>${dt.to}</b>億円</span><span>出来高<b>${dt.vr}</b>倍（20日中央値比）</span>${dt.earn?`<span>決算<b>${dt.earn.slice(5).replace('-','/')}</b> ${esc(dt.earn_kind||'')}</span>`:''}<a class="sn-vl" href="tools/stock.html?code=${encodeURIComponent(r.code)}" style="color:var(--brand)">銘柄詳細 ↗</a></div>
    ${three}
    <div class="sn-dgrid">
      <div class="sn-dbox"><h4>${me?'見たい型と、出ている動画の型':'みんなが知りたいこと'} <small>${me?'濃い＝見たい割合／薄い＝既存動画の割合／右＝空き（pt）':'予測候補の言葉と話題の理由から'}</small></h4>
        <div class="sn-cmp">${cmp}</div>
        <h4 style="margin-top:14px">YouTubeで検索されている言葉 <small>色つき＝知りたいことの手がかり</small></h4><div class="sn-words">${words}</div>
        ${me?`<div class="sn-idea"><b>動画の切り口（本人だけに表示）：</b>${esc(idea)}</div>`:''}</div>
      <div class="sn-dbox"><h4>なぜ話題かを確かめる動画 <small>直近7日 ・ 専用を先に再生の多い順 ・ <a class="sn-vl" href="https://www.youtube.com/results?search_query=${encodeURIComponent(dt.q+' 株')}&sp=EgIIAw%253D%253D" target="_blank" rel="noopener">YouTubeで今週の動画を全部見る ↗</a></small></h4>
        <ul class="sn-vids">${vids}</ul></div>
    </div></td></tr>`;
}
$$('.sn-sub button').forEach(b=>b.onclick=()=>setScTab(b.dataset.t));
$('#sn-sort').onclick=e=>{const b=e.target.closest('button');if(!b)return;sn.sort=b.dataset.k;snStore.set('sns_sort',sn.sort);drawSns();};
$$('#sntbl th.sn-th').forEach(th=>th.onclick=()=>{sn.sort=th.dataset.k;snStore.set('sns_sort',sn.sort);drawSns();});
$('#sn-tf').onclick=e=>{const b=e.target.closest('button');if(!b)return;sn.tf=b.dataset.k;drawSns();};
$('#sn-prev').onclick=()=>{if(sn.idx>0){sn.idx--;sn.open=null;drawSns();}};
$('#sn-next').onclick=()=>{const s=(SNS&&SNS.sessions)||[];if(sn.idx<s.length-1){sn.idx++;sn.open=null;drawSns();}};
$('#sn-day').addEventListener('input',e=>{sn.idx=+e.target.value;sn.open=null;drawSns();});


/* ================= 全体 ================= */
function renderAll(){
  $$('#mseg button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===market));
  $('#u-date').textContent=DATA.updated;$('#u-sched').textContent=SCHED[market];
  drawStrip();drawOverview();if(!worldDrawn)drawWorld();drawThemes();drawStockSearch();drawScreening();
}
function setMarket(mk){if(mk==='us'&&!US_ON)mk='jp';try{localStorage.setItem('tf_market',mk);}catch(e){}
  bindMarket(mk);marketReset();renderAll();}

/* 操作のつなぎ込み */
seg('mseg',b=>setMarket(b.dataset.m));
seg('secper',b=>{state.secPer=+b.dataset.p;drawSectors();});
seg('brm',b=>{state.brMode=b.dataset.b;drawBreadth();});
seg('mccat',b=>{state.mcCat=b.dataset.c;drawMacro();});
seg('mcper',b=>{state.mcPer=+b.dataset.p;drawMacro();drawRatios();});
seg('ratesub',b=>{state.rateSub=b.dataset.r;drawMacro();});
seg('metric',b=>{state.metric=b.dataset.m;drawChart();});
seg('range',b=>{state.range=b.dataset.r==='ytd'?'ytd':+b.dataset.r;drawChart();});
seg('smooth',b=>{state.smooth=+b.dataset.w;drawChart();});
seg('sortby',b=>{state.sort=b.dataset.s;drawRank();});
seg('gran',b=>{state.gran=b.dataset.g;drawHeat();});
seg('hsort',b=>{state.hsort=b.dataset.h;drawHeat();});
seg('rkmetric',b=>{state.rkMetric=b.dataset.m;state.rkSel=null;drawRk();});
seg('rkrows',b=>{state.rkRows=+b.dataset.n;drawRkBump();});
$('#rktbl').querySelector('thead').addEventListener('click',e=>{const th=e.target.closest('th.srt');if(!th)return;const k=th.dataset.k;
  if(state.rkSort.k===k)state.rkSort.dir=state.rkSort.dir==='asc'?'desc':'asc';else state.rkSort={k,dir:k==='rank'?'asc':'desc'};drawRkList();});
function wireSearch(inputId,clearId,fn){const el=$('#'+inputId),x=$('#'+clearId);if(!el)return;
  el.addEventListener('input',()=>{const v=el.value.trim();if(x)x.hidden=!v;fn(v);});
  if(x)x.addEventListener('click',()=>{el.value='';x.hidden=true;fn('');el.focus();});}
wireSearch('hsearch','hsearch-x',v=>{state.hquery=v;drawHeat();});
wireSearch('rksearch','rksearch-x',v=>{state.rkQuery=v;drawRkList();});
wireSearch('vcpsearch','vcpsearch-x',v=>{state.vcpQuery=v;drawVcp();});
wireSearch('snsearch','snsearch-x',v=>{sn.q=v;drawSns();});
$('#vcp-prev').onclick=()=>{if(state.vcpIdx>0){state.vcpIdx--;drawVcp();}};
$('#vcp-next').onclick=()=>{const D=VCP_DATA[vcpKey(market)];if(D&&D.sessions&&state.vcpIdx<D.sessions.length-1){state.vcpIdx++;drawVcp();}};
$('#vcp-day').addEventListener('input',e=>{state.vcpIdx=+e.target.value;drawVcp();});
$('#vcptbl').addEventListener('click',e=>{const th=e.target.closest('th.srt');if(!th)return;const k=th.dataset.k;
  if(state.vcpSort.k===k)state.vcpSort.dir=state.vcpSort.dir==='asc'?'desc':'asc';else state.vcpSort={k,dir:k==='name'?'asc':'desc'};drawVcp();});
/* 銘柄検索(本文の検索窓とヘッダーの検索窓) */
$('#sq').addEventListener('input',e=>renderResults(e.target.value));
$('#sq').addEventListener('keydown',e=>{if(e.key==='Enter'){const b=$('#sres button');if(b)showStock(b.dataset.code);}if(e.key==='Escape')$('#sres').hidden=true;});
$('#hq').addEventListener('keydown',e=>{if(e.key!=='Enter')return;const q=e.target.value.trim();if(!q)return;
  const th=themes.find(t=>_nz(t.name)===_nz(q))||(!searchStocks(q).length&&themes.find(t=>_nz(t.name).includes(_nz(q))));
  if(th){focusTheme(th.name,true);goto('themes');return;}
  $('#sq').value=q;renderResults(q);const R=searchStocks(q);if(R.length===1)showStock(R[0].code);goto('stocks');});

/* ジャンプリンクの現在位置 */
const navLinks=$$('nav.jump a[href^="#"]');/* ページ移動のリンクは除外 */
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)navLinks.forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+e.target.id));}),{rootMargin:'-35% 0px -60% 0px'});
$$('section.sec').forEach(s=>io.observe(s));

/* 配色の切り替え(ライト/ダーク)で描き直す */
function redrawAll(){drawStrip();drawIndexCards();drawBreadth();drawMacro();drawRatios();drawChart();drawRank();drawHeat();drawStock();drawRkBump();drawStockCard();if(RK&&rkTop().length)drawRkList();if(VCP_DATA[vcpKey(market)])drawVcp();if(sn.tab==='sns')drawSns();}
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change',redrawAll);
new MutationObserver(redrawAll).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
window.addEventListener('resize',()=>syncPanelHeight());

/* 起動 */
if(!US_ON){const ub=$('#mseg button[data-m="us"]');if(ub)ub.hidden=true;}
let initMk='jp';try{const p=new URLSearchParams(location.search).get('m');initMk=p||localStorage.getItem('tf_market')||'jp';}catch(e){}
bindMarket(initMk);marketReset();bindTip();renderAll();
setScTab(['sns','vcp2'].includes(sn.tab)?sn.tab:'vcp');

/* 手動更新ボタン & 新しい公開の自動検知 */
$('#upd-btn').addEventListener('click',()=>{const h=$('#upd-hint');h.hidden=false;h.textContent='GitHubのページで「Run workflow」を押してください。完了（約5〜10分後）を自動で検知して、再読み込みボタンを出します。';});
$('#upd-reload').addEventListener('click',()=>location.reload());
async function checkUpdate(){try{const r=await fetch('version.json?cb='+Date.now(),{cache:'no-store'});if(!r.ok)return;const v=await r.json();if(v.built&&BUILT&&v.built!==BUILT)$('#upd-banner').hidden=false;}catch(e){}}
setInterval(checkUpdate,60000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkUpdate();});
