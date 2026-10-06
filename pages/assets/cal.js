/* 決算・経済カレンダー。ダッシュボードの「今後3日の予定」と tools/calendar.html(2週間の一覧・検索)で共通に使う。
   データ: calendar.json(15_calendar.py が定時実行で作る)
     eco: [日付(日本時間), 時刻(日本時間), 'jp'|'us', 指標名, 重要度1-3, 前回, 予想, 結果]
     jp : [日付, コード, 社名, 区分, 時価総額(億円), 業種, 印[]]
     us : [日付(米国の現地日付), 'BMO'|'AMC'|'', ティッカー, 社名, 四半期末, 時価総額(十億ドル), EPS予想, 印[]]
   EarnCal.mountBlock(箱, {root, list})  … ダッシュボード(3列×3日・各日4件＋ほか○件の展開)
   EarnCal.mountList(箱, {root})         … 一覧ページ(経済→日本→米国のタブ・14日・検索)
   日付は日本時間の今日から暦どおり(土日も表示)。 */
(function(){
  const COLS=['eco','jp','us'];
  const TITLE={eco:'経済イベント',jp:'日本株の決算',us:'米国株の決算'};
  const SUB={eco:'日米の指標・中銀',jp:'東証',us:'NYSE・Nasdaq'};
  const MK={eco:['ec','MACRO'],jp:['jp','JP'],us:['us','US']};
  const SHOW=4, PAGE=200, WD='日月火水木金土';
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const nz=s=>String(s||'').normalize('NFKC').toLowerCase();
  const CACHE={};
  const load=root=>CACHE[root]||(CACHE[root]=fetch(root+'calendar.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null));

  /* ---------- 日付 ---------- */
  const todayJST=()=>new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'});
  const addDay=(s,n)=>{const d=new Date(s+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);};
  const wd=s=>WD[new Date(s+'T00:00:00Z').getUTCDay()];
  const isWE=s=>{const w=new Date(s+'T00:00:00Z').getUTCDay();return w===0||w===6;};
  const md=s=>(+s.slice(5,7))+'/'+(+s.slice(8,10));
  const dlabel=s=>`${md(s)}(${wd(s)})`;
  const days=n=>{const t=todayJST();return Array.from({length:n},(_,i)=>addDay(t,i));};
  const rel=s=>['今日','明日','明後日'][Math.round((Date.parse(s)-Date.parse(todayJST()))/864e5)]||'';

  /* ---------- 書式 ---------- */
  const capJP=v=>v==null?'–':v>=10000?(v/10000).toFixed(v>=100000?0:1)+'兆円':Math.round(v).toLocaleString('ja-JP')+'億円';
  const capUS=v=>v==null?'–':v>=1?'$'+(v>=100?v.toFixed(0):v.toFixed(v>=10?0:1))+'B':'$'+Math.round(v*1000)+'M';
  const eps=v=>v==null?'–':(v<0?'−$'+Math.abs(v).toFixed(2):'$'+v.toFixed(2));
  const slotJ=s=>s==='BMO'?'寄り前':s==='AMC'?'引け後':'時刻未定';
  const slotJST=s=>s==='BMO'?'日本の夜':s==='AMC'?'日本の翌朝':'';
  const ccl=c=>c==='jp'?'日':'米';
  const imp=n=>`<span class="ek-imp${n>=3?' hi':''}" title="重要度${n}">${[1,2,3].map(i=>`<i class="${i<=n?'on':''}"></i>`).join('')}</span>`;
  const FL={vcp:['vcp','VCP','当サイトのスクリーニング(VCP)に該当'],note:['note','note','note で紹介済み']};
  const flags=f=>(f||[]).map(x=>FL[x]?`<span class="ek-flag ${FL[x][0]}" title="${FL[x][2]}">${FL[x][1]}</span>`:'').join('');
  const kindCls=k=>k==='本決算'?' fy':'';
  const hl=(s,q)=>{s=String(s??'');if(!q)return esc(s);const i=nz(s).indexOf(q);return i<0?esc(s):esc(s.slice(0,i))+'<mark>'+esc(s.slice(i,i+q.length))+'</mark>'+esc(s.slice(i+q.length));};

  /* ---------- 行の取り出し ---------- */
  const rowsOf=(D,col,d)=>(D[col]||[]).filter(r=>r[0]===d);
  const capOf=(col,r)=>col==='jp'?r[4]:r[5];
  const flOf=(col,r)=>col==='jp'?r[6]:r[7];
  const byCap=col=>(a,b)=>(capOf(col,b)??-1)-(capOf(col,a)??-1);
  // 各日の表示: 決算は「印あり → 時価総額の大きい順」で4件(表示は時価総額順)、経済は重要度の高い順に4件(表示は時刻順)
  function pick(col,rows){
    if(col==='eco')return [...rows].sort((a,b)=>b[4]-a[4]||a[1].localeCompare(b[1])).slice(0,SHOW).sort((a,b)=>a[1].localeCompare(b[1]));
    const f=r=>(flOf(col,r)||[]).length?1:0;
    return [...rows].sort((a,b)=>f(b)-f(a)||byCap(col)(a,b)).slice(0,SHOW).sort(byCap(col));
  }
  const ecoDone=r=>!!r[7];
  function match(col,r,q){if(!q)return true;const f=col==='eco'?[r[3]]:col==='jp'?[r[1],r[2],r[5]]:[r[2],r[3]];return f.some(x=>nz(x).includes(q));}
  function sortRows(col,rows,how){
    const r=[...rows];
    if(col==='eco')return r.sort((a,b)=>a[0].localeCompare(b[0])||a[1].localeCompare(b[1])||b[4]-a[4]);
    if(how==='code')return r.sort((a,b)=>a[0].localeCompare(b[0])||String(col==='jp'?a[1]:a[2]).localeCompare(String(col==='jp'?b[1]:b[2])));
    if(how==='time'&&col==='us'){const o={BMO:0,AMC:1,'':2};return r.sort((a,b)=>a[0].localeCompare(b[0])||o[a[1]]-o[b[1]]||byCap(col)(a,b));}
    return r.sort((a,b)=>a[0].localeCompare(b[0])||byCap(col)(a,b));
  }
  function closedNote(D,col,d){
    const h=(D.days||[]).find(x=>x.d===d)||{};
    if(col==='jp'&&h.jp_hol)return `東証休場（${esc(h.jp_hol)}）`;
    if(col==='us'&&h.us_hol)return `米国市場休場（${esc(h.us_hol)}）`;
    if(col!=='eco'&&isWE(d))return '市場休場';
    return '予定なし';
  }

  /* ---------- 表(展開・一覧で共通) ---------- */
  function table(col,rows,q,withDate,limit){
    let th,row;
    if(col==='eco'){
      th=`<tr><th class="l">時刻</th><th class="l">国</th><th class="l">重要度</th><th class="l">イベント</th><th>前回</th><th>予想</th><th>結果</th></tr>`;
      row=r=>`<tr class="nc"><td class="num">${r[1]}</td><td><span class="ek-cc ${r[2]}">${ccl(r[2])}</span></td><td>${imp(r[4])}</td><td class="wrapc">${hl(r[3],q)}</td><td class="num">${esc(r[5])||'<span class="muted">–</span>'}</td><td class="num">${esc(r[6])||'<span class="muted">–</span>'}</td><td class="num"><b>${esc(r[7])||'<span class="muted">–</span>'}</b></td></tr>`;
    }else if(col==='jp'){
      th=`<tr><th class="l">銘柄</th><th class="l">区分</th><th class="l">業種</th><th>時価総額</th><th class="l">印</th></tr>`;
      row=r=>`<tr data-mk="jp" data-code="${esc(r[1])}" data-name="${esc(r[2])}" data-sub="${esc(r[5])}"><td><b class="ek-nm">${hl(r[2],q)}</b><span class="ek-sc">${hl(r[1],q)}</span></td><td><span class="ek-kind${kindCls(r[3])}">${esc(r[3])}</span></td><td>${hl(r[5],q)}</td><td class="num">${capJP(r[4])}</td><td>${flags(r[6])}</td></tr>`;
    }else{
      th=`<tr><th class="l">タイミング</th><th class="l">銘柄</th><th class="l">四半期末</th><th>時価総額</th><th>EPS予想</th><th class="l">印</th></tr>`;
      row=r=>`<tr data-mk="us" data-code="${esc(r[2])}" data-name="${esc(r[3])}" data-sub=""><td>${slotJ(r[1])}${slotJST(r[1])?` <span class="ek-sc">(${slotJST(r[1])})</span>`:''}</td><td><b class="ek-nm">${hl(r[3],q)}</b><span class="ek-sc">${hl(r[2],q)}</span></td><td class="num">${esc(r[4])||'–'}</td><td class="num">${capUS(r[5])}</td><td class="num">${eps(r[6])}</td><td>${flags(r[7])}</td></tr>`;
    }
    const nc=(th.match(/<th/g)||[]).length;
    let body='',last=null;
    rows.slice(0,limit).forEach(r=>{
      if(withDate&&r[0]!==last){last=r[0];const rl=rel(r[0]);body+=`<tr class="ek-dsep"><td colspan="${nc}">${dlabel(r[0])}${rl?' '+rl:''}${col==='us'?' <span class="ek-sc">米国の現地日付</span>':''}</td></tr>`;}
      body+=row(r);
    });
    if(!rows.length)body=`<tr class="nc"><td colspan="${nc}" class="muted" style="text-align:center;padding:24px">該当なし</td></tr>`;
    return `<table class="rk ek-t"><thead>${th}</thead><tbody>${body}</tbody></table>`+
      (rows.length>limit?`<div class="ek-morebox"><button class="btn sm ghost" data-more>さらに表示（残り${rows.length-limit}件）</button></div>`:'');
  }
  function openCard(boxId,tr){
    if(!window.StockCard||!tr||!tr.dataset.code)return;
    const mk=tr.dataset.mk;
    StockCard.open(boxId,{market:mk,code:tr.dataset.code,name:tr.dataset.name,sub:(mk==='jp'?'日本':'米国')+(tr.dataset.sub?'/'+tr.dataset.sub:''),per:126});
    const b=document.getElementById(boxId);if(b)b.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});
  }
  const searchBox=(id,ph,v)=>`<label class="search"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="${id}" type="text" placeholder="${ph}" value="${esc(v)}" autocomplete="off"></label>`;
  function keepFocus(id,fn){const a=document.getElementById(id),p=a?a.selectionStart:0;fn();const n=document.getElementById(id);if(n){n.focus();try{n.setSelectionRange(p,p);}catch(e){}}}

  /* ================= ダッシュボードのブロック ================= */
  function mountBlock(box,opt){
    if(typeof box==='string')box=document.getElementById(box);if(!box)return;
    const root=(opt&&opt.root)||'',list=(opt&&opt.list)||'tools/calendar.html';
    const st={open:null,q:'',sort:'cap',lim:PAGE,mcol:'eco'};
    box.innerHTML='<div class="phint" style="padding:16px 0">読み込み中…</div>';
    load(root).then(D=>{
      if(!D){box.innerHTML='<div class="phint" style="padding:16px 0">予定データを読み込めませんでした。</div>';return;}
      const render=()=>{
        const ds=days(3);
        const col=c=>{
          let h=`<div class="ek-col${st.mcol===c?' show':''}"><div class="ek-chd"><span class="ek-mk ${MK[c][0]}">${MK[c][1]}</span><b>${TITLE[c]}</b><span class="meta">${SUB[c]}</span></div>`;
          ds.forEach(d=>{
            const rows=rowsOf(D,c,d),pk=pick(c,rows),rest=rows.length-pk.length,rl=rel(d);
            h+=`<div class="ek-day"><div class="ek-dlab"><span class="ek-rel${rl==='今日'?' today':''}">${rl}</span><span class="ek-dt${isWE(d)?' we':''}">${dlabel(d)}</span><span class="ek-cnt">${rows.length?rows.length+'件':''}</span></div>`;
            if(!rows.length)h+=`<div class="ek-none">${closedNote(D,c,d)}</div>`;
            pk.forEach(r=>{
              if(c==='eco')h+=`<div class="ek-row${ecoDone(r)?' done':''}"><span class="t">${r[1]}</span><span class="n">${imp(r[4])}<span class="ek-cc ${r[2]}">${ccl(r[2])}</span>${esc(r[3])}</span><span class="v">${ecoDone(r)?`結果 <b>${esc(r[7])}</b>`:(r[6]?'予想 '+esc(r[6]):'')}</span></div>`;
              else if(c==='jp')h+=`<button type="button" class="ek-row ek-stk" data-mk="jp" data-code="${esc(r[1])}" data-name="${esc(r[2])}" data-sub="${esc(r[5])}"><span class="t">${esc(r[3])}</span><span class="n">${esc(r[2])}<small>${esc(r[1])}</small>${flags(r[6])}</span><span class="v">${capJP(r[4])}</span></button>`;
              else h+=`<button type="button" class="ek-row ek-stk" data-mk="us" data-code="${esc(r[2])}" data-name="${esc(r[3])}" data-sub=""><span class="t">${slotJ(r[1])}</span><span class="n">${esc(r[3])}<small>${esc(r[2])}</small>${flags(r[7])}</span><span class="v">${capUS(r[5])}</span></button>`;
            });
            if(rest>0){const ex=!!(st.open&&st.open.col===c&&st.open.day===d);h+=`<button type="button" class="ek-more" data-col="${c}" data-day="${d}" aria-expanded="${ex}">ほか${rest}件<span class="ar">▼</span></button>`;}
            h+='</div>';
          });
          return h+'</div>';
        };
        box.innerHTML=`<div class="ek-head"><div><div class="eyebrow">Upcoming</div><h3 class="ek-h">今後3日の予定</h3></div>
            <div class="ek-hr"><span class="meta">時刻は日本時間・米国決算は現地の日付</span><a class="ek-lnk" href="${list}">決算・経済カレンダー（2週間）→</a></div></div>
          <div class="ek-tabs" role="group" aria-label="列の切り替え">${COLS.map(c=>`<button type="button" data-c="${c}" aria-pressed="${st.mcol===c}">${TITLE[c]}</button>`).join('')}</div>
          <div class="ek-grid">${COLS.map(col).join('')}</div>
          <div id="ek-drawer"></div><div id="ek-card"></div>
          <div class="ek-note">各日、印のある銘柄を先に、時価総額の大きい順に4件まで表示。銘柄を押すとチャートを表示。${flags(['vcp'])} 当サイトのスクリーニング(VCP)に該当 ・ ${flags(['note'])} noteで紹介済み。経済イベントの●は重要度（赤●●●＝相場が大きく動きやすい）。日本株の決算は発表日のみで時刻は載せていません。出所：JPX（決算発表予定日）・Nasdaq。更新 ${esc(D.updated||'')}</div>`;
        drawer();
      };
      const drawer=()=>{
        const el=box.querySelector('#ek-drawer');if(!el)return;
        if(!st.open){el.innerHTML='';return;}
        const {col,day}=st.open,all=rowsOf(D,col,day),q=nz(st.q.trim());
        const rows=sortRows(col,all.filter(r=>match(col,r,q)),st.sort);
        const srt=col==='eco'?'':`<div class="seg" data-g="sort"><button type="button" data-s="cap" aria-pressed="${st.sort==='cap'}">時価総額順</button>${col==='us'?`<button type="button" data-s="time" aria-pressed="${st.sort==='time'}">時刻順</button>`:''}<button type="button" data-s="code" aria-pressed="${st.sort==='code'}">${col==='us'?'ティッカー順':'コード順'}</button></div>`;
        el.innerHTML=`<div class="ek-drawer"><div class="ek-drhead"><h4>${dlabel(day)} ${rel(day)} ・ ${TITLE[col]} <span class="meta num">${all.length}件</span></h4>
          ${searchBox('ek-dq',col==='eco'?'指標名で絞り込み':col==='jp'?'社名・コード・業種':'社名・ティッカー',st.q)}${srt}
          <span class="phint">${q?rows.length+'件ヒット':''}</span><button type="button" class="ek-x" data-close aria-label="閉じる">✕</button></div>
          <div class="ek-tbl">${table(col,rows,q,false,st.lim)}</div>
          <div class="ek-foot"><a class="ek-lnk" href="${list}#${col}-${day}">2週間分を一覧ページで見る →</a></div></div>`;
        const inp=el.querySelector('#ek-dq');
        inp.addEventListener('input',()=>{st.q=inp.value;st.lim=PAGE;keepFocus('ek-dq',drawer);});
      };
      box.addEventListener('click',e=>{
        const t=e.target;
        const m=t.closest('.ek-more');
        if(m){const k={col:m.dataset.col,day:m.dataset.day};st.open=(st.open&&st.open.col===k.col&&st.open.day===k.day)?null:k;st.q='';st.sort='cap';st.lim=PAGE;render();
          if(st.open){const d=box.querySelector('#ek-drawer');if(d)d.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});}return;}
        if(t.closest('[data-close]')&&t.closest('.ek-drawer')){st.open=null;render();return;}
        const tb=t.closest('.ek-tabs button');if(tb){st.mcol=tb.dataset.c;render();return;}
        const sb=t.closest('[data-g="sort"] button');if(sb){st.sort=sb.dataset.s;drawer();return;}
        if(t.closest('[data-more]')){st.lim+=PAGE;drawer();return;}
        const s=t.closest('.ek-stk,.ek-t tbody tr[data-code]');if(s){openCard('ek-card',s);}
      });
      render();
    });
  }

  /* ================= 一覧ページ ================= */
  function mountList(box,opt){
    if(typeof box==='string')box=document.getElementById(box);if(!box)return;
    const root=(opt&&opt.root)||'../';
    const st={tab:'eco',day:'all',q:'',cap:'all',flag:false,lim:PAGE};
    // #jp-2026-10-07 のように開くと、そのタブ・日付を選んだ状態にする
    const m=(location.hash||'').match(/^#(eco|jp|us)(?:-(\d{4}-\d{2}-\d{2}))?$/);
    if(m){st.tab=m[1];if(m[2])st.day=m[2];}
    box.innerHTML='<div class="phint" style="padding:16px 0">読み込み中…</div>';
    load(root).then(D=>{
      if(!D){box.innerHTML='<div class="phint" style="padding:16px 0">予定データを読み込めませんでした。</div>';return;}
      const ds=days(14);
      if(st.day!=='all'&&!ds.includes(st.day))st.day='all';
      const meta=document.getElementById('cal-meta');if(meta)meta.textContent='更新 '+(D.updated||'');
      const CAPS={eco:[['all','すべて'],['2','●●以上'],['3','●●●のみ']],jp:[['all','すべて'],['300','300億円以上'],['1000','1000億円以上']],us:[['all','すべて'],['1','$1B以上'],['10','$10B以上']]};
      const render=()=>{
        const c=st.tab,src=(D[c]||[]).filter(r=>ds.includes(r[0]));
        const cnt=d=>src.filter(r=>r[0]===d).length,max=Math.max(1,...ds.map(cnt));
        const q=nz(st.q.trim());
        let rows=src.filter(r=>(st.day==='all'||r[0]===st.day)&&match(c,r,q));
        if(st.cap!=='all')rows=rows.filter(r=>c==='eco'?r[4]>=+st.cap:(capOf(c,r)??-1)>=+st.cap);
        if(st.flag&&c!=='eco')rows=rows.filter(r=>(flOf(c,r)||[]).length);
        rows=sortRows(c,rows,'cap');
        const dayBtn=d=>{const n=cnt(d),h=(D.days||[]).find(x=>x.d===d)||{},hol=c==='jp'?h.jp_hol:c==='us'?h.us_hol:'',rl=rel(d);
          return `<button type="button" class="ek-dbtn${isWE(d)?' we':''}" data-d="${d}" aria-pressed="${st.day===d}"${hol?` title="${esc(hol)}"`:''}><small>${rl||wd(d)+'曜'}</small><b class="num">${md(d)}</b><span class="ek-bar"><i style="width:${n/max*100}%"></i></span><small class="num">${hol?'休場':n+'件'}</small></button>`;};
        box.innerHTML=`<div class="ek-ltabs" role="group" aria-label="種類">${COLS.map(k=>`<button type="button" data-t="${k}" aria-pressed="${st.tab===k}">${TITLE[k]}<span class="c num">${(D[k]||[]).filter(r=>ds.includes(r[0])).length}</span></button>`).join('')}</div>
          <div class="ek-days"><button type="button" class="ek-dbtn" data-d="all" aria-pressed="${st.day==='all'}"><small>期間</small><b>2週間</b><span class="ek-bar"><i style="width:100%"></i></span><small class="num">${src.length}件</small></button>${ds.map(dayBtn).join('')}</div>
          <div class="ek-filters">${searchBox('ek-lq',c==='eco'?'指標名（例：雇用統計・CPI・日銀）':c==='jp'?'社名・コード・業種':'社名・ティッカー',st.q)}
            <div class="seg" data-g="cap">${CAPS[c].map(([k,n])=>`<button type="button" data-c="${k}" aria-pressed="${st.cap===k}">${n}</button>`).join('')}</div>
            ${c==='eco'?'':`<label class="ek-chk"><input type="checkbox" id="ek-lflag"${st.flag?' checked':''}>印のある銘柄だけ</label>`}
            <span class="phint">${rows.length}件${q?` ・「${esc(st.q.trim())}」で検索中`:''}</span></div>
          <div id="ek-lcard"></div>
          <div class="ek-tbl ek-tall">${table(c,rows,q,true,st.lim)}</div>`;
        const inp=box.querySelector('#ek-lq');
        inp.addEventListener('input',()=>{st.q=inp.value;st.lim=PAGE;keepFocus('ek-lq',render);});
        const fl=box.querySelector('#ek-lflag');if(fl)fl.addEventListener('change',()=>{st.flag=fl.checked;st.lim=PAGE;render();});
        try{history.replaceState(null,'','#'+c+(st.day!=='all'?'-'+st.day:''));}catch(e){}
      };
      box.addEventListener('click',e=>{
        const t=e.target;
        const tb=t.closest('.ek-ltabs button');if(tb){st.tab=tb.dataset.t;st.cap='all';st.lim=PAGE;render();return;}
        const db=t.closest('.ek-dbtn');if(db){st.day=db.dataset.d;st.lim=PAGE;render();return;}
        const cb=t.closest('[data-g="cap"] button');if(cb){st.cap=cb.dataset.c;st.lim=PAGE;render();return;}
        if(t.closest('[data-more]')){st.lim+=PAGE;render();return;}
        const s=t.closest('.ek-t tbody tr[data-code]');if(s)openCard('ek-lcard',s);
      });
      render();
    });
  }

  window.EarnCal={mountBlock,mountList,load};
})();
