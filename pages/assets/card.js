/* 銘柄カード(「銘柄を探す」と同じ見た目のチャート＋情報)。ツールのページとnote紹介記事検証で共通に使う。
   StockCard.open(箱, {market, code, name, sub, kv:[{l,v,cls}], src, mark:{date,label}, per, line, foot, onClose, val})
   val:false でバリュエーション欄を出さない(ETF・指数)。StockCard.mountVal(箱, 市場, コード) は単独でも使える
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

  /* ---------- バリュエーション(株価が織り込む成長率・過去5年PERの位置・PEG) ---------- */
  /* データ= /valuation_{jp,us}.json(valuation/v07_publish.py)。「割安・割高」「理論株価」は出さない */
  /* 置き場所はここ1か所。カードは無料なので公開側(/valuation_{jp,us}.json)。会員だけにするなら Worker の鍵の対象に足す */
  const VAL_URL=mk=>ROOT+'valuation_'+mk+'.json';
  const vload=mk=>load(VAL_URL(mk));
  const vp=(x,d=1)=>x==null||!isFinite(x)?'—':(x>=0?'+':'−')+Math.abs(x*100).toFixed(d)+'%';
  const vig=x=>x==null?'—':x>0.4?'40%超':x<-0.1?'−10%未満':vp(x);
  const VCLS={'期待は控えめ':'low','実績並み':'mid','期待が先行':'high'};
  function vlab(v){if(!v||v.status!=='ok'||v.ex)return null;if(v.nolabel||!v.label)return['none','判定なし'];return[VCLS[v.label]||'mid',v.label];}
  function vgap(v){return v&&v.status==='ok'&&!v.ex&&!v.nolabel&&v.g3!=null&&v.ig!=null?v.g3-v.ig:null;}
  function vstate(v,mk){
    if(!v)return mk==='jp'?'データ収集中です（日本株は毎日少しずつ決算データを集めています）':'';
    if(v.status==='collecting')return v.pending?'最新決算の反映待ちです':'データ収集中です（日本株は毎日少しずつ決算データを集めています）';
    if(v.status==='no_data')return '四半期の決算データがありません（外国企業など）';
    if(v.status==='no_price')return '株価のデータがありません';
    return null;}
  /* 成長率の比較図。左=項目名の列、中=棒、右=数字の列に分け、文字と棒が重ならないようにする */
  function vaxis(v){const W=600,NL=150,VR=82,L=NL+8,R=W-VR-8,lo=-0.10,hi=0.40,X=x=>L+(Math.max(lo,Math.min(hi,x))-lo)/(hi-lo)*(R-L);
    const rows=[['株価が織り込む成長率',v.ig,'var(--brand)',true],['実績（過去3年の年率）',v.nolabel?null:v.g3,'var(--ink)',false],['直近1年の伸び',v.g1,'var(--faint)',false]];
    let g=`<svg viewBox="0 0 ${W} 132" width="100%" role="img" aria-label="成長率の比較" style="display:block;max-width:680px">`;
    [-0.1,0,0.1,0.2,0.3,0.4].forEach(t=>{g+=`<line x1="${X(t)}" x2="${X(t)}" y1="6" y2="104" stroke="${t===0?'var(--line-strong)':'var(--line)'}" stroke-width="${t===0?1.5:1}"/>`+
      `<text x="${X(t)}" y="122" font-size="11" fill="var(--muted)" text-anchor="middle">${t===0?'0%':(t>0?'+':'−')+Math.round(Math.abs(t*100))+'%'}</text>`;});
    rows.forEach(([nm,x,c,main],i)=>{const y=22+i*32;
      g+=`<text x="0" y="${y+4}" font-size="12" fill="${main?'var(--ink)':'var(--muted)'}" ${main?'font-weight="700"':''}>${nm}</text>`;
      if(x==null){g+=`<text x="${W}" y="${y+4}" font-size="12.5" fill="var(--faint)" text-anchor="end">—</text>`;return;}
      const px=X(x),out=x>hi||x<lo;
      g+=`<line x1="${X(0)}" x2="${px}" y1="${y}" y2="${y}" stroke="${c}" stroke-width="${main?6:4}" stroke-linecap="round"/><circle cx="${px}" cy="${y}" r="${main?7:5.5}" fill="${main?c:'var(--surface)'}" stroke="${c}" stroke-width="2"/>`;
      if(out)g+=`<text x="${x>hi?R+2:L-2}" y="${y+4}" font-size="11" fill="${c}" text-anchor="${x>hi?'start':'end'}">${x>hi?'›':'‹'}</text>`;
      g+=`<text x="${W}" y="${y+4}" font-size="13" font-weight="600" fill="${c}" text-anchor="end">${main?vig(x):vp(x)}</text>`;});
    return g+'</svg>';}
  function vgauge(v){const W=560,L=18,R=W-18,lo=v.pmin,hi=v.pmax,X=x=>L+(Math.max(lo,Math.min(hi,x))-lo)/(hi-lo||1)*(R-L);
    const over=v.per>hi,under=v.per<lo,x=X(v.per),f=n=>(+n).toFixed(1);
    let g=`<svg viewBox="0 0 ${W} 76" width="100%" role="img" aria-label="過去5年PERでの位置" style="display:block;max-width:640px">`;
    g+=`<rect x="${L}" y="26" width="${R-L}" height="8" rx="4" fill="var(--line)"/><rect x="${L}" y="26" width="${Math.max(0,x-L)}" height="8" rx="4" fill="var(--brand)" opacity=".3"/>`;
    g+=`<line x1="${X(v.pmed)}" x2="${X(v.pmed)}" y1="20" y2="40" stroke="var(--muted)" stroke-width="1.5"/>`;
    g+=`<text x="${L}" y="58" font-size="11" fill="var(--muted)">最低 ${f(lo)}倍</text><text x="${R}" y="58" font-size="11" fill="var(--muted)" text-anchor="end">最高 ${f(hi)}倍</text>`;
    if(Math.abs(X(v.pmed)-L)>=70&&Math.abs(R-X(v.pmed))>=70)g+=`<text x="${X(v.pmed)}" y="58" font-size="11" fill="var(--muted)" text-anchor="middle">中央 ${f(v.pmed)}倍</text>`;
    g+=`<circle cx="${x}" cy="30" r="8" fill="var(--brand)" stroke="var(--surface)" stroke-width="2.5"/>`;
    g+=`<text x="${x}" y="13" font-size="12" font-weight="600" fill="var(--brand)" text-anchor="${x>R-80?'end':x<L+80?'start':'middle'}">今 ${f(v.per)}倍${over?'（5年の最高超）':under?'（5年の最低未満）':''}</text>`;
    return g+'</svg>';}
  function vposTxt(v){if(!v||v.pos==null||v.pmin==null)return null;return '下から'+Math.round(v.pos*100)+'%'+(v.per>v.pmax?'（5年の最高超）':v.per<v.pmin?'（5年の最低未満）':'');}
  function vmini(pos){return `<span class="vmini"><i style="left:calc(${Math.round(pos*100)}% - 1.5px)"></i></span>`;}
  function vhtml(D,mk,code){
    const v=D&&D.stocks?D.stocks[code]:null,src=mk==='jp'?'Powered by EDINET DB（決算）・Yahoo Finance（株価）':'SEC EDGAR（決算）・Yahoo Finance（株価）';
    if(!v&&mk==='us')return '';
    const head=`<div class="vh"><span class="vt">バリュエーション</span>${D&&D.asof?`<span class="vs">${esc(D.asof)}時点</span>`:''}</div>`;
    const foot=`<div class="vsrc">出所：${src}。計算結果の表示であり、売買の推奨ではありません。</div>`;
    const stt=vstate(v,mk);if(stt)return head+`<div class="vnote">${esc(stt)}</div>`+foot;
    if(v.ex)return head+`<div class="vnote">— 計算しない銘柄です：${esc(v.ex)}<br><span class="vs">純利益が実力を表していない可能性が高いため、成長率・PERの位置・PEGを空欄にしています。</span></div>`+foot;
    const lb=vlab(v),pos=vposTxt(v),r=(D.params&&D.params.disc!=null)?Math.round(D.params.disc*100)+'%':(mk==='jp'?'8%':'9%');
    const g3=v.nolabel?'—':vp(v.g3);
    const sentence=`市場は今後10年、年${vig(v.ig)}の利益成長を見込んでいます。`+(v.nolabel?'3年前が赤字か実績が無いため、実績との比較はしません。':`過去3年の実績は年${vp(v.g3)}`)+(v.g1!=null?`${v.nolabel?'直近1年の伸びは':'、直近1年は'}${vp(v.g1)}です。`:(v.nolabel?'':'です。'));
    return head+(v.pending?'<div class="vpend">最新決算の反映待ち（下の数字は前回の決算まで）</div>':'')+
      `<div class="vgrid">
        <div><small>株価が織り込む成長率</small><b class="vb">${vig(v.ig)}</b>${lb?`<span class="vpill ${lb[0]}">${lb[1]}</span>`:''}</div>
        <div><small>実績3年（直近1年）</small><b>${g3}</b><span class="vsub">（${vp(v.g1)}）</span></div>
        <div><small>過去5年PERの位置</small>${pos?`<b>${pos}</b>${vmini(v.pos)}`:'<b>—</b><span class="vsub">有効な月が24か月未満</span>'}</div>
        <div><small>PEG（実績）</small><b>${v.peg!=null?(+v.peg).toFixed(2):'—'}</b>${v.peg==null?'<span class="vsub">減益・判定なしは計算しません</span>':''}</div></div>
      <button type="button" class="vbtn" aria-expanded="false">グラフで見る ▸</button>
      <div class="vmore" hidden><p class="vsay">${esc(sentence)}</p>${vaxis(v)}
        ${v.pmin!=null?`<div class="vlbl">過去5年のPERでの位置（今のPER ${(+v.per).toFixed(1)}倍・過去${v.pn}か月）</div>${vgauge(v)}`:''}
        <p class="vs">前提：直近4四半期の純利益を起点に、10年間 年g%で伸びその後は年2%、割引率${r}で今の時価総額と等しくなるgを逆算。判定は（実績3年 − 織り込み）が+5pt超で「期待は控えめ」、±5pt以内で「実績並み」、−5pt未満で「期待が先行」。</p></div>`+foot;}
  function vtds(v,mk){const d='<span class="muted">—</span>',m=t=>`<td colspan="7" class="l muted" style="font-size:11px">${t}</td>`;
    if(!v)return m(mk==='jp'?'データ収集中':'—');
    if(v.status!=='ok')return m(v.status==='collecting'?(v.pending?'最新決算の反映待ち':'データ収集中'):v.status==='no_data'?'決算データなし':'株価データなし');
    if(v.ex)return `<td colspan="7" class="l muted" style="font-size:11px" title="${esc(v.ex)}">対象外（${esc(v.ex)}）</td>`;
    const lb=vlab(v),gp=vgap(v),pc=x=>x==null?d:vp(x);
    return `<td style="color:var(--brand);font-weight:600">${vig(v.ig)}</td><td>${v.nolabel?d:pc(v.g3)}</td><td>${pc(v.g1)}</td>
      <td>${gp==null?d:(gp>=0?'+':'−')+Math.abs(gp*100).toFixed(1)+'pt'}</td><td class="l">${lb?`<span class="vpill ${lb[0]}">${lb[1]}</span>`:d}</td>
      <td>${v.pos!=null?vmini(v.pos)+' '+Math.round(v.pos*100)+'%':d}</td><td>${v.peg!=null?(+v.peg).toFixed(2):d}</td>`;}
  function mountVal(el,mk,code){if(!el)return;el.innerHTML='';
    vload(mk).then(D=>{const h=vhtml(D,mk,code);if(!h){el.innerHTML='';return;}el.innerHTML=`<div class="sc-val">${h}</div>`;
      const b=el.querySelector('.vbtn');if(b)b.onclick=()=>{const m=el.querySelector('.vmore'),o=m.hidden;m.hidden=!o;b.setAttribute('aria-expanded',o);b.textContent=o?'グラフを閉じる ◂':'グラフで見る ▸';};});}
  const vcss=document.createElement('style');vcss.textContent=`.sc-val{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:4px 0 10px;padding:10px 0 8px}
    .sc-val .vh{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}.sc-val .vt{font-weight:700;font-size:13px;color:var(--ink)}
    .sc-val .vs{font-size:11px;color:var(--muted)}.sc-val .vgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    @media (max-width:640px){.sc-val .vgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    .sc-val .vgrid small{display:block;font-size:11px;color:var(--muted)}.sc-val .vgrid b{font:600 17px var(--f-num);margin-right:6px}.sc-val .vgrid b.vb{color:var(--brand)}
    .sc-val .vsub{font-size:11.5px;color:var(--muted);font-family:var(--f-num)}
    .vpill{display:inline-block;font-size:11px;font-weight:700;padding:1px 9px;border-radius:999px;border:1px solid var(--line-strong);color:var(--ink-2);background:var(--surface-2);line-height:1.6;white-space:nowrap;vertical-align:2px}
    .vpill.low{background:var(--brand-soft);color:var(--brand);border-color:transparent}.vpill.high{background:var(--warn-bg);color:var(--warn-ink);border-color:transparent}
    .vpill.none{color:var(--muted);background:transparent}
    .vmini{display:inline-block;width:56px;height:6px;background:var(--line);border-radius:3px;position:relative;vertical-align:middle}.vmini i{position:absolute;top:-3px;width:3px;height:12px;background:var(--brand);border-radius:1px}
    .sc-val .vbtn{margin-top:6px;border:0;background:none;color:var(--brand);font:600 12px var(--f-body);cursor:pointer;padding:2px 0}
    .sc-val .vmore{margin-top:6px}.sc-val .vsay{margin:4px 0;font-size:13px;color:var(--ink-2)}.sc-val .vlbl{font-size:11.5px;color:var(--muted);margin-top:8px}
    .sc-val .vnote{font-size:13px;color:var(--ink-2);background:var(--surface-2);border-radius:6px;padding:8px 12px}
    .sc-val .vpend{font-size:11.5px;color:var(--warn-ink);background:var(--warn-bg);border-radius:4px;padding:2px 8px;display:inline-block;margin-bottom:6px}
    .sc-val .vsrc{font-size:10.5px;color:var(--faint);margin-top:6px}`;document.head.appendChild(vcss);
  const PER=[['21','1か月'],['63','3か月'],['126','6か月'],['252','1年'],['520','2年']];
  const st={per:126,freq:'day'};
  function open(box,o){
    if(typeof box==='string')box=document.getElementById(box);if(!box)return;
    const per=o.per||st.per,src=o.src||(ROOT+(o.market==='us'?'us_ohlc/':'ohlc/')+encodeURIComponent(o.code)+'.json');
    const tok=Symbol();box._sc=tok;
    box.innerHTML=`<div class="panel sc-card" style="margin-top:14px;position:relative"><div class="shead" style="padding-right:76px"><b>${esc(o.name)}</b><span class="num muted">${esc(o.code)}</span>${o.sub?`<span class="tag">${esc(o.sub)}</span>`:''}${o.links===false?'':links(o.market,o.code)}
        <button class="btn sm ghost" data-close style="position:absolute;top:12px;right:12px">閉じる</button></div>
      ${o.kv&&o.kv.length?`<div class="kv" style="grid-template-columns:repeat(${Math.min(o.kv.length,4)},minmax(0,1fr))">${o.kv.map(k=>`<div><small>${k.l}</small><b class="${k.cls||''}">${k.v}</b></div>`).join('')}</div>`:''}
      <div class="sc-valbox"></div>
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
    if(o.val!==false&&o.code)mountVal(box.querySelector('.sc-valbox'),o.market,o.code);
    draw();
    if(o.scroll!==false)setTimeout(()=>box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'}),30);
  }
  window.StockCard={open,root:ROOT,mountVal,valData:vload,vlab,vgap,vig,vp,vposTxt,vmini,vtds};
})();
