/* 銘柄カード(「銘柄を探す」と同じ見た目のチャート＋情報)。ツールのページとnote紹介記事検証で共通に使う。
   StockCard.open(箱, {market, code, name, sub, kv:[{l,v,cls}], src, mark:{date,label}, per, line, foot, onClose})
   src を省くと 銘柄を探す と同じ ohlc/<code>.json(米国は us_ohlc/)を読む。o/h/l の無いデータは折れ線で描く。 */
(function(){
  const ROOT=(document.currentScript&&document.currentScript.src||'').replace(/assets\/card\.js.*$/,'');
  const cssv=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const fmt=(x,d)=>x==null||!isFinite(x)?'–':Number(x).toLocaleString('ja-JP',{minimumFractionDigits:d,maximumFractionDigits:d});
  const CACHE={};
  const load=url=>CACHE[url]||(CACHE[url]=fetch(url).then(r=>r.ok?r.json():null).catch(()=>null));
  function niceStep(r,n){const raw=r/Math.max(1,n),p=Math.pow(10,Math.floor(Math.log10(raw))),f=raw/p;return (f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*p;}
  function niceAxis(lo,hi,n){const st=niceStep(hi-lo,n||5);const a=Math.floor(lo/st)*st,b=Math.ceil(hi/st)*st,t=[];for(let v=a;v<=b+st*1e-6;v+=st)t.push(+v.toFixed(10));return{lo:a,hi:b,ticks:t,step:st};}
  function sma(a,w){const o=[];let s=0;for(let i=0;i<a.length;i++){s+=a[i];if(i>=w)s-=a[i-w];o.push(i>=w-1?s/w:null);}return o;}
  function weekly(oh){const R={d:[],o:[],h:[],l:[],c:[]};for(let i=0;i<oh.d.length;i+=5){const e=Math.min(i+5,oh.d.length);let hh=-1e18,ll=1e18;
    for(let j=i;j<e;j++){if(oh.h[j]>hh)hh=oh.h[j];if(oh.l[j]<ll)ll=oh.l[j];}R.d.push(oh.d[i]);R.o.push(oh.o[i]);R.h.push(hh);R.l.push(ll);R.c.push(oh.c[e-1]);}return R;}
  function chart(oh,per,freq,W,mark,line){
    if(!oh||!oh.c||!oh.c.length)return '<div class="phint" style="padding:16px 0">チャートのデータがありません。</div>';
    if(!oh.o){oh={d:oh.d,c:oh.c,o:oh.c,h:oh.c,l:oh.c};line=true;}
    const data=freq==='week'?weekly(oh):oh;let bars=Math.min(freq==='week'?Math.ceil(per/5):per,data.c.length);const s=data.c.length-bars;
    const D=data.d.slice(s),O=data.o.slice(s),Hi=data.h.slice(s),Lo=data.l.slice(s),C=data.c.slice(s);
    const m5=sma(data.c,5).slice(s),m20=sma(data.c,20).slice(s),m50=sma(data.c,50).slice(s);
    const CH=320,L=58,R=8,T=14,B=20;let lo=Infinity,hi=-Infinity;Hi.forEach(v=>{if(v>hi)hi=v});Lo.forEach(v=>{if(v<lo)lo=v});
    [m5,m20,m50].forEach(a=>a.forEach(v=>{if(v!=null){if(v>hi)hi=v;if(v<lo)lo=v;}}));const pad=(hi-lo)*0.04||1;lo-=pad;hi+=pad;
    const ax=niceAxis(lo,hi,4);lo=ax.lo;hi=ax.hi;
    const n=C.length,bw=(W-L-R)/Math.max(n,1),X=i=>L+bw*(i+0.5),Y=v=>T+(CH-T-B)*(1-(v-lo)/(hi-lo));
    const cUp=cssv('--up'),cDn=cssv('--down');let g='';
    ax.ticks.forEach(v=>{const y=Y(v);g+=`<line class="gl" x1="${L}" y1="${y.toFixed(1)}" x2="${W-R}" y2="${y.toFixed(1)}"/><text class="axl" x="${L-5}" y="${(y+3).toFixed(1)}" text-anchor="end">${fmt(v,ax.step<1?2:0)}</text>`;});
    let lm='';D.forEach((d,i)=>{const mo=d.slice(0,7);if(mo!==lm){lm=mo;g+=`<text class="axl" x="${X(i).toFixed(1)}" y="${CH-6}" text-anchor="middle">${d.slice(2,7).replace('-','/')}</text>`;}});
    if(mark&&mark.date){let mi=-1;for(let i=0;i<n;i++){if(D[i]<=mark.date)mi=i;}
      if(mi>=0){const x=X(mi);g+=`<line x1="${x.toFixed(1)}" y1="${T}" x2="${x.toFixed(1)}" y2="${CH-B}" stroke="${cssv('--warn-ink')||cssv('--brand')}" stroke-width="1.2" stroke-dasharray="4 3"/>`+
        `<text x="${(x+4).toFixed(1)}" y="${T-3}" font-size="11" font-weight="700" fill="${cssv('--warn-ink')||cssv('--brand')}">${esc(mark.label||'')}</text>`;}}
    if(line){let p='';C.forEach((v,i)=>p+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ');g+=`<path d="${p}" fill="none" stroke="${cssv('--ink-2')}" stroke-width="1.6"/>`;}
    else{const wq=Math.max(0.6,bw*0.32);
      for(let i=0;i<n;i++){const c=C[i]>=O[i]?cUp:cDn,x=X(i);g+=`<line x1="${x.toFixed(1)}" y1="${Y(Hi[i]).toFixed(1)}" x2="${x.toFixed(1)}" y2="${Y(Lo[i]).toFixed(1)}" stroke="${c}" stroke-width="1"/>`;
        const ya=Y(Math.max(O[i],C[i])),yb=Y(Math.min(O[i],C[i]));g+=`<rect x="${(x-wq).toFixed(1)}" y="${ya.toFixed(1)}" width="${(wq*2).toFixed(1)}" height="${Math.max(0.8,yb-ya).toFixed(1)}" fill="${c}"/>`;}}
    const ln=(a,col)=>{let p='',st=false;a.forEach((v,i)=>{if(v==null)return;p+=(st?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';st=true;});return p?`<path d="${p}" fill="none" stroke="${col}" stroke-width="1.3"/>`:'';};
    g+=ln(m5,cssv('--c2'))+ln(m20,cssv('--brand'))+ln(m50,cssv('--c4'));
    return `<svg viewBox="0 0 ${W} ${CH}" width="100%" style="display:block;overflow:visible">${g}</svg>`;
  }
  function links(m,code){
    const tv='https://jp.tradingview.com/chart/?symbol='+encodeURIComponent(m==='us'?code.replace('-','.'):'TSE:'+code);
    const a=(u,t)=>`<a class="extl" href="${u}" target="_blank" rel="noopener">${t}↗</a>`;
    return a(tv,'TradingView')+(m==='us'?a('https://finance.yahoo.com/quote/'+code,'Yahoo')+a('https://finviz.com/quote.ashx?t='+code,'Finviz')
      :a('https://finance.yahoo.co.jp/quote/'+code+'.T','Yahoo')+a('https://kabutan.jp/stock/?code='+code,'株探'));
  }
  const PER=[['21','1か月'],['63','3か月'],['126','6か月'],['252','1年'],['520','2年']];
  const st={per:126,freq:'day'};
  function open(box,o){
    if(typeof box==='string')box=document.getElementById(box);if(!box)return;
    const per=o.per||st.per,src=o.src||(ROOT+(o.market==='us'?'us_ohlc/':'ohlc/')+encodeURIComponent(o.code)+'.json');
    const tok=Symbol();box._sc=tok;
    box.innerHTML=`<div class="panel sc-card" style="margin-top:14px"><div class="shead"><b>${esc(o.name)}</b><span class="num muted">${esc(o.code)}</span>${o.sub?`<span class="tag">${esc(o.sub)}</span>`:''}${o.links===false?'':links(o.market,o.code)}
        <button class="btn sm ghost" data-close style="margin-left:auto">閉じる</button></div>
      ${o.kv&&o.kv.length?`<div class="kv" style="grid-template-columns:repeat(${Math.min(o.kv.length,4)},minmax(0,1fr))">${o.kv.map(k=>`<div><small>${k.l}</small><b class="${k.cls||''}">${k.v}</b></div>`).join('')}</div>`:''}
      <div class="ctlrow" style="margin:6px 0 4px"><div class="seg" data-g="per">${PER.map(p=>`<button data-v="${p[0]}" aria-pressed="${+p[0]===per}">${p[1]}</button>`).join('')}</div>
        <div class="seg" data-g="freq"><button data-v="day" aria-pressed="${st.freq==='day'}">日足</button><button data-v="week" aria-pressed="${st.freq==='week'}">週足</button></div>
        <span class="legend" style="margin:0"><span><i style="background:var(--c2)"></i>5日線</span><span><i style="background:var(--brand)"></i>20日線</span><span><i style="background:var(--c4)"></i>50日線</span>${o.mark?`<span><i style="background:var(--warn-ink,var(--brand));height:2px"></i>${esc(o.mark.label)}</span>`:''}</span></div>
      <div class="sc-chart"><div class="phint">読み込み中…</div></div>${o.foot?`<div class="phint" style="margin-top:6px">${o.foot}</div>`:''}</div>`;
    let cur={per,freq:st.freq};
    const draw=()=>load(src).then(oh=>{if(box._sc!==tok)return;const el=box.querySelector('.sc-chart');if(!el)return;
      el.innerHTML=chart(oh,cur.per,cur.freq,Math.max(320,Math.round(el.clientWidth||700)),o.mark,o.line);});
    box.querySelectorAll('.seg').forEach(sg=>sg.onclick=e=>{const b=e.target.closest('button');if(!b)return;sg.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));
      if(sg.dataset.g==='per'){cur.per=+b.dataset.v;st.per=cur.per;}else{cur.freq=b.dataset.v;st.freq=cur.freq;}draw();});
    box.querySelector('[data-close]').onclick=()=>{box._sc=null;box.innerHTML='';o.onClose&&o.onClose();};
    draw();
    if(o.scroll!==false)setTimeout(()=>box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'}),30);
  }
  window.StockCard={open,root:ROOT};
})();
