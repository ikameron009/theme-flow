/* 銘柄カード(「銘柄を探す」と同じ見た目のチャート＋情報)。ツールのページとnote紹介記事検証で共通に使う。
   StockCard.open(箱, {market, code, name, sub, m, kv, extra, src, mark:{date,label}, per, line, foot, onClose, val})
   ★2026-10-08〜 チャートは TradingView Lightweight Charts(assets/lightweight-charts.js)。追加の指定 = lines / zones / markers / legend(チャート部の説明は chart() の上)、
   pre / post = カードの中身の先頭・末尾に入れるHTML(監視銘柄・売買記録の「ポジション」段など)、onMount(箱) = 中身を入れたあとに呼ぶ(ボタンの結び付け用)
   StockCard.below(行, {同じ指定 + group}) = 選んだ行のすぐ下に開く(全ページこちらを使う。2026-10-07〜)
   1段目「株価・勢い」= 3行(いま/過去から今日まで/勢い・規模)。個別銘柄は card_{jp,us}.json を自動で読む。テーマ・業種・ETFは m で渡す。
   kv(旧4列) は card_*.json に無い銘柄の予備。extra = ページ固有の補足(note掲載時の株価など)
   val:false でバリュエーション欄を出さない(ETF・指数)。StockCard.mountVal(箱, 市場, コード) は単独でも使える
   src を省くと 銘柄を探す と同じ ohlc/<code>.json(米国は us_ohlc/)を読む。o/h/l の無いデータは折れ線で描く。
   ★2026-10-07〜 個別銘柄のカードには共通で「監視銘柄に登録する」「保有銘柄に登録する」を付ける(acts:false で消す。ETF・指数=val:false・コード無しには出さない)。
   押すとカードの中身が入力画面に切り替わる。入力画面と保存は window.StockCardActs = {state(o), watch(箱,o,戻る), hold(箱,o,戻る)}(assets/jr.js。本人のときだけ用意される)が受け持つ */
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
  /* ---------- 株価チャート(TradingView Lightweight Charts。2026-10-08〜 旧SVGから差し替え) ----------
     部品 = assets/lightweight-charts.js(v4.2.0・Apache 2.0)。左下のTradingViewロゴは無料で使う条件の表記なので消さない。最初に描くときだけ読み込む。
     移動平均 = 5/20/50/150/200(週足のときは同じ本数の週線)。価格の目盛りは左。ドラッグで横に動かす・一度クリックするとホイールで拡大縮小(ページのスクロールを邪魔しないため)。
     追加の指定(open の o):
       lines:[{price,color:'--down'など,title,style:'dashed',width}] 横線＋左の目盛りに価格
       zones:{from:'YYYY-MM-DD',entry,stop,tgt} エントリー〜損切ライン=赤・エントリー〜利確ライン=緑の帯(from の足から右端まで)
       ★2026-10-08〜 説明の文字(凡例)を押すと表示のオン・オフ。key でまとめて切り替える:
         'ma5'〜'ma200'=移動平均 / 'zdn'=赤い帯 / 'zup'=緑の帯 / lines・markers は各自の key(同じ key の線・印・帯は一緒に消える)
         lines・markers の legend:'文字' で凡例に出す(legend:false や未指定は凡例に出さず、key だけで連動)。オフにした key はブラウザに覚える(全ページ共通 localStorage sc_hide)
       markers:[{date,above:true/false,shape:'up'|'down'|'circle',color,text}]
       mark:{date,label} 縦の点線(note掲載日など) */
  const HKEY='sc_hide';
  const hidGet=()=>{try{return new Set(JSON.parse(localStorage.getItem(HKEY)||'[]'));}catch(e){return new Set();}};
  const hidSet=h=>{try{localStorage.setItem(HKEY,JSON.stringify([...h]));}catch(e){}};
  let LWP=null;
  function lwc(){return LWP||(LWP=new Promise((ok,ng)=>{if(window.LightweightCharts)return ok(window.LightweightCharts);
    const s=document.createElement('script');s.src=ROOT+'assets/lightweight-charts.js';s.onload=()=>ok(window.LightweightCharts);s.onerror=()=>{LWP=null;ng(new Error('lwc'));};document.head.appendChild(s);}));}
  const MAS=[[5,'--c2'],[20,'--brand'],[50,'--c4'],[150,'--c3'],[200,'--c8']];
  const colv=c=>c&&c.slice(0,2)==='--'?cssv(c):c;
  const ymd=t=>typeof t==='string'?t:t.year+'-'+String(t.month).padStart(2,'0')+'-'+String(t.day).padStart(2,'0');
  function cleanOH(oh){const R={d:[],o:[],h:[],l:[],c:[]};let last='';
    for(let i=0;i<oh.d.length;i++){const c=oh.c[i];if(c==null||!isFinite(c)||!oh.d[i]||oh.d[i]<=last)continue;last=oh.d[i];
      const o=oh.o&&oh.o[i]!=null?oh.o[i]:c,h=oh.h&&oh.h[i]!=null?oh.h[i]:Math.max(o,c),l=oh.l&&oh.l[i]!=null?oh.l[i]:Math.min(o,c);
      R.d.push(oh.d[i]);R.o.push(o);R.h.push(Math.max(h,o,c));R.l.push(Math.min(l,o,c));R.c.push(c);}return R;}
  function chart(el,oh,per,freq,o){
    if(el._lc){try{el._lc.remove();}catch(e){}el._lc=null;}
    const none=()=>{el.innerHTML='<div class="phint" style="padding:16px 0">チャートのデータがありません。</div>';};
    if(!oh||!oh.c||!oh.c.length)return none();
    let line=!!o.line;if(!oh.o){oh={d:oh.d,c:oh.c};line=true;}
    const data=freq==='week'?weekly(cleanOH(oh)):cleanOH(oh),D=data.d,n=D.length;if(!n)return none();
    const LC=window.LightweightCharts;
    el.innerHTML='<div class="sc-lwc"><div class="sc-zl"></div><div class="sc-cv"></div></div>';
    const cv=el.querySelector('.sc-cv'),zl=el.querySelector('.sc-zl'),us=o.market==='us';
    const pf=v=>fmt(v,us?2:Math.abs(v)<100?1:0);
    const wheel=on=>({handleScale:{mouseWheel:on},handleScroll:{mouseWheel:on}});
    const ch=LC.createChart(cv,{autoSize:true,
      layout:{background:{type:'solid',color:'rgba(0,0,0,0)'},textColor:cssv('--faint'),fontFamily:cssv('--f-num')||'sans-serif',fontSize:11},
      grid:{vertLines:{visible:false},horzLines:{color:cssv('--line')}},
      leftPriceScale:{visible:true,borderVisible:false,scaleMargins:{top:0.06,bottom:0.05}},rightPriceScale:{visible:false},
      timeScale:{borderVisible:false,rightOffset:3,minBarSpacing:0.5,tickMarkFormatter:t=>ymd(t).slice(2,7).replace('-','/')},
      crosshair:{mode:LC.CrosshairMode.Normal},localization:{locale:'ja-JP',priceFormatter:pf,timeFormatter:t=>ymd(t).replace(/-/g,'/')},
      handleScroll:{mouseWheel:false,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false},
      handleScale:{mouseWheel:false,pinch:true,axisPressedMouseMove:{time:true,price:false},axisDoubleClickReset:true}});
    el._lc=ch;
    cv.addEventListener('click',()=>ch.applyOptions(wheel(true)));cv.addEventListener('mouseleave',()=>ch.applyOptions(wheel(false)));
    // 横線・帯の価格も縦の範囲に入れる
    const lv=[];(o.lines||[]).forEach(L=>{if(L&&isFinite(L.price))lv.push(L.price);});const z=o.zones;
    if(z)[z.entry,z.stop,z.tgt].forEach(v=>{if(v!=null&&isFinite(v))lv.push(v);});
    const asp=orig=>{const r=orig();if(r&&r.priceRange&&lv.length){r.priceRange.minValue=Math.min(r.priceRange.minValue,...lv);r.priceRange.maxValue=Math.max(r.priceRange.maxValue,...lv);}return r;};
    const fmtP={type:'custom',formatter:pf,minMove:us?0.01:0.1};
    let main;
    if(line){main=ch.addLineSeries({priceScaleId:'left',color:cssv('--ink-2'),lineWidth:2,priceLineVisible:false,priceFormat:fmtP,autoscaleInfoProvider:asp});
      main.setData(D.map((d,i)=>({time:d,value:data.c[i]})));}
    else{const up=cssv('--up'),dn=cssv('--down');main=ch.addCandlestickSeries({priceScaleId:'left',upColor:up,downColor:dn,wickUpColor:up,wickDownColor:dn,borderVisible:false,priceLineVisible:false,priceFormat:fmtP,autoscaleInfoProvider:asp});
      main.setData(D.map((d,i)=>({time:d,open:data.o[i],high:data.h[i],low:data.l[i],close:data.c[i]})));}
    const H=hidGet(),R={ma:[],pl:[],mk:[],zr:null,zg:null};
    MAS.forEach(([w,c])=>{let s=0;const a=[];for(let i=0;i<n;i++){s+=data.c[i];if(i>=w)s-=data.c[i-w];if(i>=w-1)a.push({time:D[i],value:s/w});}
        if(!a.length)return;const se=ch.addLineSeries({priceScaleId:'left',color:cssv(c),lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false,priceFormat:fmtP,autoscaleInfoProvider:asp,visible:!H.has('ma'+w)});
        se.setData(a);R.ma.push(['ma'+w,se]);});
    (o.lines||[]).forEach((L,k)=>{if(!L||!isFinite(L.price))return;const key=L.key||'l'+k,off=H.has(key);
      R.pl.push([key,L.title||'',main.createPriceLine({price:L.price,color:colv(L.color)||cssv('--ink-2'),lineWidth:L.width||1,
      lineStyle:L.style==='dashed'?LC.LineStyle.Dashed:L.style==='dotted'?LC.LineStyle.Dotted:LC.LineStyle.Solid,lineVisible:!off,axisLabelVisible:!off,title:off?'':L.title||''})]);});
    const idx=d=>{let k=-1;for(let i=0;i<n;i++){if(D[i]<=d)k=i;else break;}return k;};
    // 日足のデータより新しい日(当日の更新前など)の印は出さない
    R.mk=(o.markers||[]).map(m=>{const i=idx(m.date);if(i<0||(freq!=='week'&&m.date>D[n-1]))return null;return[m.key||'',{time:D[i],position:m.above?'aboveBar':'belowBar',color:colv(m.color)||cssv('--ink'),
      shape:m.shape==='down'?'arrowDown':m.shape==='circle'?'circle':'arrowUp',text:m.text||''}];}).filter(Boolean).sort((a,b)=>a[1].time<b[1].time?-1:a[1].time>b[1].time?1:0);
    const setMk=h=>main.setMarkers(R.mk.filter(([k])=>!k||!h.has(k)).map(x=>x[1]));if(R.mk.length)setMk(H);
    // 帯と縦線は下の層(.sc-zl)に描く。表示範囲・大きさが変わるたびに置き直す
    const zi=z&&z.from&&z.entry!=null?idx(z.from):-1,mi=o.mark&&o.mark.date?idx(o.mark.date):-1;
    if(zi>=0||mi>=0){const ts=ch.timeScale();let zr,zg,vl,vt;
      if(zi>=0){zr=document.createElement('i');zg=document.createElement('i');zr.className='dn';zg.className='up';zr.hidden=H.has('zdn');zg.hidden=H.has('zup');zl.append(zr,zg);R.zr=zr;R.zg=zg;}
      if(mi>=0){vl=document.createElement('i');vl.className='vl';vt=document.createElement('b');vt.textContent=o.mark.label||'';zl.append(vl,vt);}
      let tm=0;const paint=()=>{clearTimeout(tm);tm=setTimeout(()=>{if(el._lc!==ch)return;const off=ch.priceScale('left').width(),W=ts.width(),bs=ts.options().barSpacing||6;
        if(zi>=0){let x0=ts.logicalToCoordinate(zi);const yE=main.priceToCoordinate(z.entry);
          if(x0==null||yE==null){zr.style.width=zg.style.width='0';}
          else{x0=Math.max(0,Math.min(W,x0-bs/2));const put=(e,v)=>{const y=v!=null&&isFinite(v)?main.priceToCoordinate(v):null;if(y==null){e.style.width='0';return;}
            e.style.left=(off+x0)+'px';e.style.width=Math.max(0,W-x0)+'px';e.style.top=Math.min(y,yE)+'px';e.style.height=Math.abs(y-yE)+'px';};put(zr,z.stop);put(zg,z.tgt);}}
        if(mi>=0){const x=ts.logicalToCoordinate(mi);const ok=x!=null&&x>=0&&x<=W;vl.hidden=vt.hidden=!ok;if(ok){vl.style.left=(off+x)+'px';vt.style.left=(off+x+4)+'px';}}},16);};
      ts.subscribeVisibleLogicalRangeChange(paint);if(window.ResizeObserver)new ResizeObserver(paint).observe(cv);paint();}
    el._vis=h=>{if(el._lc!==ch)return;R.ma.forEach(([k,se])=>se.applyOptions({visible:!h.has(k)}));
      R.pl.forEach(([k,t,pl])=>{const off=h.has(k);pl.applyOptions({lineVisible:!off,axisLabelVisible:!off,title:off?'':t});});
      if(R.mk.length)setMk(h);if(R.zr)R.zr.hidden=h.has('zdn');if(R.zg)R.zg.hidden=h.has('zup');};
    // 表示範囲は幅が決まってから(autoSize の直後は幅0で、先に入れた範囲が捨てられるため)
    const bars=Math.min(freq==='week'?Math.ceil(per/5):per,n),setR=()=>{if(el._lc===ch)ch.timeScale().setVisibleLogicalRange({from:n-bars-0.5,to:n-1+3});};
    setR();setTimeout(setR,0);setTimeout(setR,120);
  }
  // 明暗の切り替えで描き直す(色はCSSの変数から取るため)
  const LIVE=new Set();
  const relive=()=>LIVE.forEach(f=>{if(!f.el.isConnected){LIVE.delete(f);return;}f();});
  try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',relive);}catch(e){}
  try{new MutationObserver(relive).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});}catch(e){}
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
  /* 表の上の注記: 決算データを集めている途中(9割未満)なら件数を出す */
  function valNote(vd,mk){if(!vd||!vd.universe)return '';const st=Object.values(vd.stocks||{}),done=st.filter(v=>v&&v.status&&v.status!=='collecting').length,n=vd.universe;
    if(done/n>=0.9)return '';const pct=Math.floor(done/n*100);
    return `<div class="vnote">バリュエーションの列（織り込み成長〜PEG）は、${mk==='jp'?'日本株':'米国株'}の決算データを毎日少しずつ集めている途中です（現在 ${done.toLocaleString()}／${n.toLocaleString()}銘柄・${pct}%）。まだの銘柄は「データ収集中」と表示されます。</div>`;}
  function vtds(v,mk){const d='<span class="muted">—</span>',m=t=>`<td colspan="7" class="l muted" style="font-size:11px">${t}</td>`;
    if(!v)return m(mk==='jp'?'データ収集中':'—');
    if(v.status!=='ok')return m(v.status==='collecting'?(v.pending?'最新決算の反映待ち':'データ収集中'):v.status==='no_data'?'決算データなし':'株価データなし');
    if(v.ex)return `<td colspan="7" class="l muted" style="font-size:11px" title="${esc(v.ex)}">対象外（${esc(v.ex)}）</td>`;
    const lb=vlab(v),gp=vgap(v),pc=x=>x==null?d:vp(x);
    return `<td style="color:var(--brand);font-weight:600">${vig(v.ig)}</td><td>${v.nolabel?d:pc(v.g3)}</td><td>${pc(v.g1)}</td>
      <td>${gp==null?d:(gp>=0?'+':'−')+Math.abs(gp*100).toFixed(1)+'pt'}</td><td class="l">${lb?`<span class="vpill ${lb[0]}">${lb[1]}</span>`:d}</td>
      <td>${v.pos!=null?vmini(v.pos)+' '+Math.round(v.pos*100)+'%':d}</td><td>${v.peg!=null?(+v.peg).toFixed(2):d}</td>`;}
  /* 銘柄詳細へのボタン(2026-10-15〜 日本株は全銘柄。行き先 tools/stock.html)。高配当データ(dividend_codes.json={コード:[判定,安心スコア]})にある銘柄は判定と点数を併記 */
  const DIV_URL=ROOT+'dividend_codes.json';
  const DLAB={'とても安心':'low','安心':'low','あと一歩':'none','不安':'high','必須条件×':'none'};
  function divhtml(C,mk,code){if(!code)return '';if(mk==='us')return `<div class="sc-div"><a class="btn sm ghost" href="${ROOT}tools/stock.html?m=us&code=${encodeURIComponent(code)}">銘柄詳細 →</a></div>`;const x=C&&C[code];
    return `<div class="sc-div"><a class="btn sm ghost" href="${ROOT}tools/stock.html?code=${encodeURIComponent(code)}">銘柄詳細 →</a>${x?`<span class="vpill ${DLAB[x[0]]||'none'}">${esc(x[0])}</span><span class="dvs">安心スコア <b>${x[1]}</b>点</span>`:''}</div>`;}
  function mountVal(el,mk,code){if(!el)return;el.innerHTML='';
    Promise.all([vload(mk),mk==='jp'?load(DIV_URL):null]).then(([D,C])=>{const h=vhtml(D,mk,code),dv=divhtml(C,mk,code);if(!h&&!dv){el.innerHTML='';return;}el.innerHTML=(h?`<div class="sc-val">${h}</div>`:'')+dv;
      const b=el.querySelector('.vbtn');if(b)b.onclick=()=>{const m=el.querySelector('.vmore'),o=m.hidden;m.hidden=!o;b.setAttribute('aria-expanded',o);b.textContent=o?'グラフを閉じる ◂':'グラフで見る ▸';};});}
  const vcss=document.createElement('style');vcss.textContent=`.sc-val{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:4px 0 10px;padding:10px 0 8px}
    .sc-val .vh{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}.sc-val .vt{font-weight:700;font-size:13px;color:var(--ink)}
    .sc-val .vs{font-size:11px;color:var(--muted)}.sc-val .vgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    @media (max-width:640px){.sc-val .vgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    .sc-val .vgrid small{display:block;font-size:11px;color:var(--muted)}.sc-val .vgrid b{font:600 17px var(--f-num);margin-right:6px}.sc-val .vgrid b.vb{color:var(--brand)}
    .sc-val .vsub{font-size:11.5px;color:var(--muted);font-family:var(--f-num)}
    .vnote{font-size:12px;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line);border-radius:6px;padding:6px 10px;margin:0 0 8px;line-height:1.6}
    .vpill{display:inline-block;font-size:11px;font-weight:700;padding:1px 9px;border-radius:999px;border:1px solid var(--line-strong);color:var(--ink-2);background:var(--surface-2);line-height:1.6;white-space:nowrap;vertical-align:2px}
    .vpill.low{background:var(--brand-soft);color:var(--brand);border-color:transparent}.vpill.high{background:var(--warn-bg);color:var(--warn-ink);border-color:transparent}
    .vpill.none{color:var(--muted);background:transparent}
    .vmini{display:inline-block;width:56px;height:6px;background:var(--line);border-radius:3px;position:relative;vertical-align:middle}.vmini i{position:absolute;top:-3px;width:3px;height:12px;background:var(--brand);border-radius:1px}
    .sc-val .vbtn{margin-top:6px;border:0;background:none;color:var(--brand);font:600 12px var(--f-body);cursor:pointer;padding:2px 0}
    .sc-val .vmore{margin-top:6px}.sc-val .vsay{margin:4px 0;font-size:13px;color:var(--ink-2)}.sc-val .vlbl{font-size:11.5px;color:var(--muted);margin-top:8px}
    .sc-val .vnote{font-size:13px;color:var(--ink-2);background:var(--surface-2);border-radius:6px;padding:8px 12px}
    .sc-val .vpend{font-size:11.5px;color:var(--warn-ink);background:var(--warn-bg);border-radius:4px;padding:2px 8px;display:inline-block;margin-bottom:6px}
    .sc-val .vsrc{font-size:10.5px;color:var(--faint);margin-top:6px}
    .sc-div{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:-2px 0 10px}.sc-div .dvs{font-size:12px;color:var(--muted)}.sc-div .dvs b{font:600 14px var(--f-num);color:var(--ink)}`;document.head.appendChild(vcss);
  /* ---------- 1段目: 株価・勢い(3行) ---------- */
  /* 個別銘柄 = /card_{jp,us}.json(13_tool_research.py。業種銘柄リサーチと同じ計算)。無料なので公開側に置く
     テーマ・業種・ETF = 呼ぶ側が o.m に同じ形で渡す(11/12 のデータ) */
  const CARD_URL=mk=>ROOT+'card_'+mk+'.json';
  const cload=mk=>load(CARD_URL(mk));
  const TRN={up:['上昇','up'],flat:['中立','flat'],down:['下落','down']};
  const pc=(x,d=1)=>x==null||!isFinite(x)?'–':(x>=0?'+':'−')+Math.abs(x).toFixed(d)+'%';
  const pcl=x=>x==null||!isFinite(x)?'muted':x>=0?'up':'down';
  const amt=(x,u)=>x==null||!isFinite(x)?'–':fmt(x,x>=100?0:x>=10?1:2)+`<span class="u">${esc(u)}</span>`;
  function stockM(D,code,mk){const a=D&&D.s&&D.s[code];if(!a)return null;const m={};D.cols.forEach((k,i)=>m[k]=a[i]);
    m.trend=m.trend===1?'up':m.trend===-1?'down':'flat';m.units=D.units;m.m0Label='今月（'+((D.months||[])[0]||'')+'）';m.pd=mk==='us'?2:(m.price>=1000?0:1);return m;}
  function kv3(m,mk){m=m||{};const u=m.units||(mk==='us'?{to:'百万ドル',mcap:'十億ドル'}:{to:'億円',mcap:'億円'}),t=TRN[m.trend];
    const c=(l,v,cls,big)=>`<div class="c"><small>${l}</small><b class="${cls||''}${big?' big':''}">${v}</b></div>`;
    const pd=m.pd!=null?m.pd:(m.price!=null&&m.price>=1000?0:mk==='us'?2:1);
    return `<div class="sc-kv3">
      <div class="kvr"><div class="rl">いま</div>${c('トレンド',t?`<span class="sc-tr ${t[1]}">${t[0]}</span>`:'–')}${c(m.priceLabel||'株価',m.price==null?'–':fmt(m.price,pd),'',true)}${c('RS',m.rs??'–','',true)}
        ${c('前日比',pc(m.chg1,2),pcl(m.chg1))}${c('週間',pc(m.w1),pcl(m.w1))}${c(m.m0Label||'今月',pc(m.m0),pcl(m.m0))}</div>
      <div class="kvr"><div class="rl">過去から<br>今日まで</div>${[['r1m','1か月前'],['r2m','2か月前'],['r3m','3か月前'],['r6m','6か月前'],['r12m','1年前']].map(([k,l])=>c(l,pc(m[k]),pcl(m[k]))).join('')}<div class="c e"></div></div>
      <div class="kvr"><div class="rl">勢い・規模</div>${c('52週高値から',pc(m.hi52),pcl(m.hi52))}${c('資金急増率',pc(m.surge,0),pcl(m.surge))}
        ${c(m.toLabel||'売買代金（20日平均）',amt(m.to20,u.to))}${c(m.mcapLabel||'時価総額',amt(m.mcap,u.mcap))}
        ${c(m.volxLabel||'出来高倍率',m.volx==null?'–':fmt(m.volx,2)+'<span class="u">倍</span>')}${c('ADR%',m.adr==null?'–':fmt(m.adr,2)+'%')}</div></div>`;}
  function kvOld(kv){return `<div class="kv" style="grid-template-columns:repeat(${Math.min(kv.length,4)},minmax(0,1fr))">${kv.map(k=>`<div><small>${k.l}</small><b class="${k.cls||''}">${k.v}</b></div>`).join('')}</div>`;}
  function mountKv(el,o){if(!el)return;
    if(o.m){el.innerHTML=kv3(o.m,o.market);return;}
    if(!o.code){el.innerHTML=o.kv&&o.kv.length?kvOld(o.kv):kv3({},o.market);return;}
    el.innerHTML=kv3({},o.market).replace(/<b class="([^"]*)">–<\/b>/g,'<b class="$1 muted">…</b>');
    cload(o.market).then(D=>{if(!el.isConnected)return;const m=stockM(D,o.code,o.market);
      el.innerHTML=m?kv3(m,o.market):(o.kv&&o.kv.length?kvOld(o.kv):kv3({},o.market)+(D?'<div class="sc-nodata">この銘柄は株価・勢いの集計対象外です（売買代金が少ない銘柄など）。</div>':''));});}
  const kcss=document.createElement('style');kcss.textContent=`.sc-kv3{border:1px solid var(--line);border-radius:8px;overflow:hidden;margin:12px 0 10px}
    .sc-kv3 .kvr{display:grid;grid-template-columns:96px repeat(6,minmax(0,1fr));border-top:1px solid var(--line)}.sc-kv3 .kvr:first-child{border-top:0}
    .sc-kv3 .rl{background:var(--surface-2);font-size:11.5px;font-weight:700;color:var(--ink-2);padding:7px 10px;display:flex;align-items:center;line-height:1.35}
    .sc-kv3 .c{padding:6px 10px;min-width:0}.sc-kv3 .c small{display:block;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .sc-kv3 .c b{font:600 16px/1.35 var(--f-num);font-variant-numeric:tabular-nums;white-space:nowrap}.sc-kv3 .c b.big{font-size:19px}
    .sc-kv3 .c b .u{font-size:11px;font-weight:500;color:var(--muted);margin-left:2px}
    .sc-tr{display:inline-block;font-size:12px;font-weight:700;padding:0 10px;border-radius:999px;line-height:1.8;vertical-align:2px}
    .sc-tr.up{background:var(--up-soft);color:var(--up)}.sc-tr.down{background:var(--down-soft);color:var(--down)}.sc-tr.flat{background:var(--surface-2);color:var(--muted)}
    @media (max-width:720px){.sc-kv3 .kvr{grid-template-columns:repeat(3,minmax(0,1fr))}.sc-kv3 .rl{grid-column:1/-1;padding:4px 10px}.sc-kv3 .c.e{display:none}}
    .sc-nodata{font-size:12px;color:var(--muted);margin:-4px 0 10px}
    .sc-extra{display:flex;flex-wrap:wrap;gap:6px 22px;align-items:baseline;margin:-2px 0 10px;font-size:12px;color:var(--muted)}.sc-extra b{font:600 14px var(--f-num);color:var(--ink);margin-left:6px}
    .sc-extra .t{font-weight:700;color:var(--ink-2)}
    tr.sc-row>td{padding:0 0 12px!important;background:var(--bg)!important;text-align:left;white-space:normal;font-family:var(--f-body);border-bottom:1px solid var(--line)}
    .sc-row .sc-slot{position:sticky;left:0;padding:0 6px;box-sizing:border-box}.sc-row .sc-slot>.panel{margin-top:6px!important}
    .sc-anchor>td{background:var(--brand-soft)!important}.sc-anchor>td:first-child{box-shadow:inset 3px 0 0 var(--brand)}`;document.head.appendChild(kcss);

  /* ---------- 監視銘柄・保有銘柄に登録するボタン(全ページ共通) ---------- */
  function mountActs(box,o){const el=box.querySelector('.sc-actbox'),A=window.StockCardActs;
    if(!el||o.acts===false||!o.code||o.val===false||!A){if(el)el.remove();return;}
    const paint=()=>{const s=(A.state&&A.state(o))||{},u=o.market==='us'?'ドル':'円';
      const pf=v=>o.market==='us'?'$'+fmt(v,2):fmt(v,v>=1000?0:1)+'円';
      el.innerHTML=`<div class="sc-acts"><button type="button" class="btn sm" data-sc-act="watch">☆ 監視銘柄に登録する</button><button type="button" class="btn sm ghost" data-sc-act="hold">＋ 保有銘柄に登録する</button>
        ${s.inWatch?`<span class="sc-ast w">監視中${s.watch!=null?'・エントリー予定 '+pf(s.watch):'・予定株価は未入力'}</span>`:''}${s.hold?'<span class="sc-ast h">保有中</span>':''}</div>`;
      el.querySelectorAll('[data-sc-act]').forEach(b=>b.onclick=()=>{const main=box.querySelector('.sc-main'),form=box.querySelector('.sc-form');
        const back=()=>{if(!box.isConnected)return;form.hidden=true;form.innerHTML='';main.hidden=false;el.hidden=false;paint();};
        main.hidden=true;el.hidden=true;form.hidden=false;A[b.dataset.scAct](form,o,back);});};
    paint();}
  const acss=document.createElement('style');acss.textContent=`.sc-acts{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
    .sc-ast{font-size:11.5px;font-weight:700;border-radius:999px;padding:2px 10px;white-space:nowrap}.sc-ast.w{background:var(--brand-soft);color:var(--brand)}.sc-ast.h{background:var(--warn-bg);color:var(--warn-ink)}
    .sc-form{margin-top:12px}
    .sc-lwc{position:relative;height:320px}.sc-lwc .sc-zl,.sc-lwc .sc-cv{position:absolute;inset:0}.sc-lwc .sc-zl{pointer-events:none;overflow:hidden}
    .sc-zl i{position:absolute;display:block;width:0}.sc-zl i.dn{background:rgba(var(--downrgb),.13)}.sc-zl i.up{background:color-mix(in srgb,var(--up) 14%,transparent)}
    .sc-zl i.vl{top:14px;bottom:24px;width:0;border-left:1.2px dashed var(--warn-ink,var(--brand))}.sc-zl b{position:absolute;top:0;font:700 11px var(--f-body);color:var(--warn-ink,var(--brand));white-space:nowrap}
    .sc-lhint{color:var(--faint)}@media (hover:none){.sc-lhint{display:none}}
    .sc-lk{display:inline-flex;align-items:center;border:0;background:none;padding:0;font:inherit;color:inherit;cursor:pointer;white-space:nowrap}
    .sc-lk:hover{color:var(--ink)}.sc-lk.off{opacity:.45;text-decoration:line-through}.sc-lm{font-size:10px;margin-right:4px}
    /* チャートの部品は中で表(table)を使う。一覧の「行にカーソルで色」の指定(table.rk tbody tr:hover td など)が中まで届かないように */
    .sc-lwc table,.sc-lwc tr,.sc-lwc td{background:transparent!important;box-shadow:none!important;outline:0!important}`;document.head.appendChild(acss);

  const PER=[['21','1か月'],['63','3か月'],['126','6か月'],['252','1年'],['520','2年']];
  const st={per:126,freq:'day'};
  function open(box,o){
    if(typeof box==='string')box=document.getElementById(box);if(!box)return;
    const per=o.per||st.per,src=o.src||(ROOT+(o.market==='us'?'us_ohlc/':'ohlc/')+encodeURIComponent(o.code)+'.json');
    const tok=Symbol();box._sc=tok;
    box.innerHTML=`<div class="panel sc-card" style="margin-top:14px;position:relative"><div class="shead" style="padding-right:76px"><b>${esc(o.name)}</b>${o.code&&o.showCode!==false?`<span class="num muted">${esc(o.code)}</span>`:''}${o.sub?`<span class="tag">${esc(o.sub)}</span>`:''}${o.links===false?'':links(o.market,o.code)}
        <button class="btn sm ghost" data-close style="position:absolute;top:12px;right:12px">閉じる</button></div>
      <div class="sc-actbox"></div><div class="sc-form" hidden></div><div class="sc-main">${o.pre||''}
      <div class="sc-kvbox"></div>
      ${o.extra&&o.extra.length?`<div class="sc-extra">${o.extraTitle?`<span class="t">${esc(o.extraTitle)}</span>`:''}${o.extra.map(k=>`<span>${k.l}<b class="${k.cls||''}">${k.v}</b></span>`).join('')}</div>`:''}
      <div class="sc-valbox"></div>
      <div class="ctlrow" style="margin:6px 0 4px"><div class="seg" data-g="per">${PER.map(p=>`<button data-v="${p[0]}" aria-pressed="${+p[0]===per}">${p[1]}</button>`).join('')}</div>
        <div class="seg" data-g="freq"><button data-v="day" aria-pressed="${st.freq==='day'}">日足</button><button data-v="week" aria-pressed="${st.freq==='week'}">週足</button></div>
        <span class="legend sc-leg" style="margin:0"></span></div>
      <div class="sc-chart"><div class="phint">読み込み中…</div></div>${o.foot?`<div class="phint" style="margin-top:6px">${o.foot}</div>`:''}${o.post||''}</div></div>`;
    let cur={per,freq:st.freq};
    // 凡例 = 押すと表示のオン・オフ(key ごと。消した key は全ページ共通で覚える)
    const sw=c=>c&&c.slice(0,2)==='--'?'var('+c+')':c;
    const leg=()=>{const u=cur.freq==='week'?'週線':'日線',el=box.querySelector('.sc-leg');if(!el)return;const H=hidGet(),it=[];
      MAS.forEach(([w,c])=>it.push(['ma'+w,`<i style="background:var(${c})"></i>${w}${u}`]));
      const z=o.zones;if(z&&z.entry!=null){if(z.stop!=null)it.push(['zdn','<i style="background:rgba(var(--downrgb),.22);box-shadow:inset 0 0 0 1px var(--down)"></i>エントリー〜損切ライン']);
        if(z.tgt!=null)it.push(['zup','<i style="background:color-mix(in srgb,var(--up) 24%,transparent);box-shadow:inset 0 0 0 1px var(--up)"></i>エントリー〜利確ライン（点線）']);}
      const seen=new Set();
      (o.markers||[]).forEach(m=>{if(!m.key||!m.legend||seen.has(m.key))return;seen.add(m.key);it.push([m.key,`<b class="sc-lm" style="color:${sw(m.color)||'var(--ink)'}">${m.shape==='down'?'▼':'▲'}</b>${esc(m.legend)}`]);});
      (o.lines||[]).forEach((L,k)=>{const key=L&&(L.key||'l'+k);if(!L||!L.legend||!isFinite(L.price)||seen.has(key))return;seen.add(key);it.push([key,`<i style="background:${sw(L.color)};height:2px"></i>${esc(L.legend)}`]);});
      el.innerHTML=it.map(([k,h])=>`<button type="button" class="sc-lk${H.has(k)?' off':''}" data-k="${k}" aria-pressed="${!H.has(k)}" title="押すと表示・非表示を切り替え">${h}</button>`).join('')+
        (o.mark?`<span><i style="background:var(--warn-ink,var(--brand));height:2px"></i>${esc(o.mark.label)}</span>`:'')+(o.legend||'')+'<span class="sc-lhint">ドラッグで移動・クリック後ホイールで拡大縮小・凡例を押すと表示を切り替え</span>';
      el.querySelectorAll('.sc-lk').forEach(b=>b.onclick=()=>{const h=hidGet(),k=b.dataset.k;h.has(k)?h.delete(k):h.add(k);hidSet(h);
        b.classList.toggle('off',h.has(k));b.setAttribute('aria-pressed',String(!h.has(k)));const c=box.querySelector('.sc-chart');if(c&&c._vis)c._vis(h);});};
    const draw=()=>{leg();return Promise.all([load(src),lwc().catch(()=>null)]).then(([oh,LC])=>{if(box._sc!==tok)return;const el=box.querySelector('.sc-chart');if(!el)return;
      if(!LC){el.innerHTML='<div class="phint" style="padding:16px 0">チャートの部品を読み込めませんでした。再読み込みしてください。</div>';return;}
      chart(el,oh,cur.per,cur.freq,o);});};
    draw.el=box;LIVE.add(draw);
    box.querySelectorAll('.seg').forEach(sg=>sg.onclick=e=>{const b=e.target.closest('button');if(!b)return;sg.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));
      if(sg.dataset.g==='per'){cur.per=+b.dataset.v;st.per=cur.per;}else{cur.freq=b.dataset.v;st.freq=cur.freq;}draw();});
    box.querySelector('[data-close]').onclick=()=>{box._sc=null;const el=box.querySelector('.sc-chart');if(el&&el._lc){try{el._lc.remove();}catch(e){}}LIVE.delete(draw);box.innerHTML='';o.onClose&&o.onClose();};
    mountActs(box,o);
    mountKv(box.querySelector('.sc-kvbox'),o);
    if(o.val!==false&&o.code)mountVal(box.querySelector('.sc-valbox'),o.market,o.code);
    draw();
    if(o.onMount)o.onMount(box);
    if(o.scroll!==false)setTimeout(()=>box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'}),30);
  }

  /* ---------- 選んだ行のすぐ下にカードを開く ---------- */
  /* StockCard.below(行, {open と同じ指定, group}) : 行が <tr> なら直後に1行足してカードを入れる(横スクロールしてもカードは見えている幅に収まる)。
     <tr> 以外なら要素の直後に入れる。group ごとにカードは1枚(別の行を押すと移る)。縦の高さ制限のある箱の中なら、開いている間だけ制限を外す */
  const SLOTS={};
  function closeBelow(grp){grp=grp||'main';const s=SLOTS[grp];if(!s)return;delete SLOTS[grp];
    s.host.remove();s.anchor.classList.remove('sc-anchor');s.lifted.forEach(([el,v])=>el.style.maxHeight=v);if(s.ro)s.ro.disconnect();if(s.onR)removeEventListener('resize',s.onR);}
  function below(anchor,o){const grp=o.group||'main';closeBelow(grp);if(!anchor)return null;
    let host,box;
    if(anchor.tagName==='TR'){const n=[...anchor.cells].reduce((a,c)=>a+(c.colSpan||1),0);
      host=document.createElement('tr');host.className='sc-row';host.innerHTML=`<td colspan="${n}"><div class="sc-slot"></div></td>`;box=host.querySelector('.sc-slot');}
    else{host=document.createElement('div');host.className='sc-slot sc-slot-b';box=host;}
    anchor.after(host);anchor.classList.add('sc-anchor');
    /* 高さ制限のある箱(一覧のスクロール枠)は、カードの高さぶんだけ広げる(一覧の見出し固定と前後の行はそのまま) */
    const lifted=[];let sx=null,vy=null;
    for(let el=host.parentElement;el&&el!==document.body;el=el.parentElement){const cs=getComputedStyle(el);
      if(!vy&&cs.maxHeight!=='none'&&/(auto|scroll)/.test(cs.overflowY)){vy=el;lifted.push([el,el.style.maxHeight,parseFloat(cs.maxHeight)||el.clientHeight]);}
      if(!sx&&/(auto|scroll)/.test(cs.overflowX)&&el.scrollWidth>el.clientWidth+1)sx=el;}
    const fit=()=>{if(sx&&host.tagName==='TR')box.style.width=Math.max(300,sx.clientWidth)+'px';
      lifted.forEach(([el,,mh])=>el.style.maxHeight=Math.ceil(mh+host.offsetHeight)+'px');};
    const s={host,anchor,lifted,ro:null,onR:null};SLOTS[grp]=s;
    const uc=o.onClose;
    open(box,Object.assign({},o,{scroll:false,onClose:()=>{closeBelow(grp);uc&&uc();}}));
    fit();[300,1200,3000].forEach(t=>setTimeout(()=>{if(SLOTS[grp]===s)fit();},t));
    if(window.ResizeObserver){s.ro=new ResizeObserver(fit);s.ro.observe(box);if(sx)s.ro.observe(sx);}else{s.onR=fit;addEventListener('resize',fit);}
    if(o.scroll!==false)setTimeout(()=>{
      if(vy){const th=vy.querySelector('thead');vy.scrollTop+=anchor.getBoundingClientRect().top-vy.getBoundingClientRect().top-(th?th.offsetHeight:0);}
      const r=anchor.getBoundingClientRect();if(r.top<56||r.top>innerHeight*0.45)
        scrollBy({top:r.top-72,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});},30);
    return box;}
  window.StockCard={open,below,closeBelow,root:ROOT,mountVal,valData:vload,cardData:cload,kv3,vlab,vgap,vig,vp,vposTxt,vmini,vtds,valNote};
})();
