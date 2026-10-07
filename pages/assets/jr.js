/* 監視銘柄・売買記録(本人専用)の共通部品。tools/journal.html と、銘柄カード(card.js)を使う全ページで読む(card.js のあとに置く)。
   - 銘柄カードの「監視銘柄に登録する」「保有銘柄に登録する」= window.StockCardActs(card.js の mountActs が呼ぶ)。
     本人だけに出す: /api/journal/me が通ったときだけ StockCardActs を用意する(ログイン省略中 JOURNAL_AUTH=off は誰でも通る)
   - 「新しく建てる」の入力欄(posFormHTML / bindPosForm)。売買記録ページの新規・編集と、カードからの登録で同じものを使う
   - 監視銘柄の保存 = D1 の watchlist 表(/api/journal/watch)。保有銘柄に登録したら、その銘柄は監視銘柄から外す
   - 何か変わったら document に 'jr:change' を投げる(detail: {pos: 追加した建玉} など)。売買記録ページはこれで描き直す */
(function(){
'use strict';
const ROOT=((document.currentScript&&document.currentScript.src)||'').replace(/assets\/jr\.js.*$/,'');
const TODAY=new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'});
const STRATS=['VCP','新高値ブレイク','決算ギャップ','押し目','高配当','空売り'];
const fmt=(x,d=0)=>x==null||!isFinite(x)?'–':Number(x).toLocaleString('ja-JP',{minimumFractionDigits:d,maximumFractionDigits:d});
const sgn=(x,d=1)=>x==null||!isFinite(x)?'–':(x>0?'+':x<0?'−':'±')+Math.abs(x).toFixed(d);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cls=x=>x>0?'up':x<0?'down':'';
const D=s=>new Date(s+'T00:00:00Z');
const S=d=>d.toISOString().slice(0,10);
// pub=公開用の見え方(金額を隠す)。売買記録ページが切り替える
const st={pub:false,ref:{},card:{jp:null,us:null},earn:{},fx:null,univ:[],uidx:[],watch:null,pos:null,me:null};
const yen=(x,plus=true)=>st.pub?'<span class="j-hide">非表示</span>':x==null||!isFinite(x)?'–':(plus&&x>0?'+':x<0?'−':'')+Math.abs(Math.round(x)).toLocaleString('ja-JP')+'円';
const getJSON=u=>fetch(u,{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null);
async function api(path,opt){opt=opt||{};
  const r=await fetch('/api/journal/'+path,{method:opt.method||'GET',headers:opt.body?{'content-type':'application/json'}:{},body:opt.body?JSON.stringify(opt.body):undefined,credentials:'same-origin',cache:'no-store'});
  const j=await r.json().catch(()=>({}));
  if(!r.ok){const e=new Error(j.error||(r.status===401?'ログインしてください':'保存できませんでした（通信を確認してください）'));e.status=r.status;throw e;}
  return j;}

/* ---------- 銘柄の候補・株価・ドル円・決算日(journal_ref.json / card_{jp,us}.json / calendar.json) ---------- */
const kata=s=>s.replace(/[ぁ-ゖ]/g,c=>String.fromCharCode(c.charCodeAt(0)+0x60));
const norm=s=>kata(String(s||'').normalize('NFKC').toUpperCase()).replace(/[\s・\-]/g,'');
let LP=null;
function load(){return LP||(LP=Promise.all([getJSON(ROOT+'journal_ref.json'),getJSON(ROOT+'card_jp.json'),getJSON(ROOT+'card_us.json'),getJSON(ROOT+'calendar.json')]).then(([ref,cj,cu,cal])=>{
  st.ref=ref||{};st.card={jp:cj,us:cu};st.fx=st.ref.fx?st.ref.fx.rate:null;
  st.earn={};if(cal){(cal.jp||[]).forEach(r=>{const k='jp:'+r[1];if(r[0]>=TODAY&&(!st.earn[k]||r[0]<st.earn[k]))st.earn[k]=r[0];});(cal.us||[]).forEach(r=>{const k='us:'+r[2];if(r[0]>=TODAY&&(!st.earn[k]||r[0]<st.earn[k]))st.earn[k]=r[0];});}
  st.univ=(st.ref.univ||[]).map(u=>[u[0],u[1],u[2],u[3]||'']);
  st.uidx=st.univ.map(u=>({u,code:norm(u[1]),name:norm(u[2]),yomi:norm(u[3])}));
  return st;}));}
const priceOf=(mk,code)=>{const c=st.card[mk];const row=c&&c.s&&c.s[code];return row&&row[0]!=null?row[0]:null;};
function searchUniv(q){q=norm(q);if(!q)return [];const out=[];
  st.uidx.forEach(x=>{let sc=-1;if(x.code===q)sc=0;else if(x.code.startsWith(q))sc=1;else if(x.yomi.startsWith(q)||x.name.startsWith(q))sc=2;else if(q.length>=2&&(x.name.includes(q)||x.yomi.includes(q)))sc=3;if(sc>=0)out.push([sc,x.u]);});
  return out.sort((a,b)=>a[0]-b[0]||(a[1][0]===b[1][0]?0:a[1][0]==='jp'?-1:1)).slice(0,8).map(x=>x[1]);}

/* ---------- 入力欄の部品 ---------- */
const unitOf=mk=>mk==='us'?'ドル':'円';
const fld=(id,lab,inner,cl)=>`<div class="f${cl?' '+cl:''}"><label for="${id}">${lab}</label>${inner}</div>`;
const fsel=(id,o,v)=>`<select id="${id}" name="${id}">${o.map(x=>`<option${x===v?' selected':''}>${x}</option>`).join('')}</select>`;
// 金額・株数の入力欄は3桁区切り(t='num')。入力を終えると「10,000」の形にそろえる。読むときは num()
const commas=v=>{if(v==null||v==='')return '';let s=String(v).replace(/[^\d.\-]/g,'');if(s===''||s==='-')return s;const neg=s[0]==='-';s=s.replace(/-/g,'');
  const [i,...f]=s.split('.');return (neg?'-':'')+(i||'0').replace(/^0+(?=\d)/,'').replace(/\B(?=(\d{3})+(?!\d))/g,',')+(f.length?'.'+f.join(''):'');};
const num=el=>{const s=String((el&&el.value)||'').replace(/[,\s]/g,'');return s===''?0:+s;};
const finp=(id,v,t='text',ph='')=>t==='num'?`<input id="${id}" name="${id}" type="text" inputmode="decimal" class="j-num" value="${esc(commas(v??''))}" placeholder="${ph}" autocomplete="off">`
  :`<input id="${id}" name="${id}" type="${t}" value="${esc(v??'')}" placeholder="${ph}" ${t==='number'?'step="any"':''}>`;
const unitInp=(id,v,mk)=>`<div class="j-unit">${finp(id,v,'num')}<span class="u" data-u>${unitOf(mk)}</span></div>`;
// 株数: −／＋ボタンで 米国株は1株、日本株は100株ずつ増減
const qtyStep=mk=>mk==='us'?1:100;
const qtyInp=(id,v,mk)=>`<div class="j-step" data-step="${qtyStep(mk)}"><button type="button" data-st="-1" aria-label="株数を減らす">−</button>${finp(id,v,'num')}<button type="button" data-st="1" aria-label="株数を増やす">＋</button><span class="u">株</span></div>`;
function lineFld(px,lab,v,mk){return `<div class="f full"><label for="${px}">${lab}</label><div class="j-line">${unitInp(px,v,mk)}<span class="or">または</span><div class="j-pct"><span class="sg" id="${px}-sg">−</span><input id="${px}-pct" type="number" min="0" max="100" step="1" aria-label="${lab}を％で入れる"><span class="u">%</span></div><span class="j-pl" id="${px}-pl"></span></div></div>`;}
const dueOf=d=>S(new Date(D(d).getTime()+182*864e5)); // 信用の返済期日(6か月)

// 新規と編集で同じ入力欄。p=接頭辞(n/c)、P=編集する建玉(新規はnull)、u0=新規で最初から入れておく銘柄 [市場,コード,名前](銘柄カードから開いたとき)
function posFormHTML(p,P,u0){
  const u=P?[P.mk,P.code,P.name]:(u0||null);
  const mk=u?u[0]:'jp';const f0=P?P.fills[0]:null;const pz=!P&&u0?priceOf(u0[0],u0[1]):null;
  return `<div class="j-form">
    <div class="f w2"><label for="${p}-q">銘柄</label><div class="j-ac"><input id="${p}-q" type="text" autocomplete="off" placeholder="銘柄名・コード・ティッカー（例：と、7203、PLTR）" value="${esc(u?u[2]:'')}"><ul class="j-acl" id="${p}-acl" role="listbox" hidden></ul></div>
      <div class="j-picked" id="${p}-picked"></div></div>
    ${fld(p+'-kind','現物／信用',fsel(p+'-kind',['現物','信用'],P?P.kind:'現物'))}${fld(p+'-dir','方向',fsel(p+'-dir',['ロング（買い）','ショート（売り）'],P&&P.dir==='S'?'ショート（売り）':'ロング（買い）'))}
    ${fld(p+'-acct','口座',fsel(p+'-acct',['特定','NISA','一般'],P?P.acct:'特定'))}${fld(p+'-date','購入日（約定日）',finp(p+'-date',f0?f0.d:TODAY,'date'))}
    ${fld(p+'-qty','株数',qtyInp(p+'-qty',f0?f0.q:'',mk))}${fld(p+'-px','平均取得単価',unitInp(p+'-px',f0?f0.p:(pz!=null?pz:''),mk))}
    ${fld(p+'-total','建玉の合計（自動）','<div class="auto" id="'+p+'-total"></div>','w2')}
    ${fld(p+'-due','信用の返済期日（自動）','<div class="auto" id="'+p+'-due"></div>')}
  </div>
  <fieldset class="j-fs"><legend>損切りと利確</legend><div class="j-form">
    ${lineFld(p+'-stop','損切ライン',P?P.c.stopNow:'',mk)}${lineFld(p+'-tgt','利確ライン',P?P.target:'',mk)}
  </div></fieldset>
  <fieldset class="j-fs"><legend>エントリーの記録</legend><div class="j-form">
    ${fld(p+'-tag','手法',fsel(p+'-tag',STRATS,P?P.tag:'VCP'))}
    ${fld(p+'-reason','エントリーの理由','<textarea id="'+p+'-reason" rows="3">'+esc(P?P.reason:'')+'</textarea>','w2')}
    ${fld(p+'-memo','メモ','<textarea id="'+p+'-memo" rows="3" placeholder="あとから追記できます">'+esc(P?P.memo:'')+'</textarea>','w2')}
  </div></fieldset>`;
}
// 入力欄の動き(候補一覧・単位の切替・建玉合計・損切/利確の％と損益)。戻り値=今の入力を読む関数
function bindPosForm(root,p,P,u0){
  const g=id=>root.querySelector('#'+p+'-'+id);
  let cur=P?[P.mk,P.code,P.name,'']:(u0?[u0[0],u0[1],u0[2],'']:null);
  const q=g('q'),list=g('acl');let hi=0,items=[];
  const pick=u=>{cur=u;q.value=u[2];list.hidden=true;
    if(!P){const pz=priceOf(u[0],u[1]);g('px').value=pz!=null?commas(pz):'';g('stop-pct').value=7;g('tgt-pct').value=20;LAST.stop=LAST.tgt='pct';}upd();};
  const showList=()=>{items=searchUniv(q.value);hi=0;if(!items.length){list.innerHTML='<li class="none">見つかりません</li>';list.hidden=false;return;}
    list.innerHTML=items.map((u,i)=>`<li role="option" data-i="${i}" class="${i===hi?'on':''}"><span class="j-flag ${u[0]}">${u[0]==='jp'?'JP':'US'}</span><span class="j-code">${u[1]}</span>${esc(u[2])}</li>`).join('');list.hidden=false;
    list.querySelectorAll('li[data-i]').forEach(li=>li.onmousedown=e=>{e.preventDefault();pick(items[+li.dataset.i]);});};
  q.oninput=showList;q.onfocus=()=>{q.select();};q.onblur=()=>setTimeout(()=>{list.hidden=true;},120);
  q.onkeydown=e=>{if(list.hidden||!items.length)return;if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();hi=(hi+(e.key==='ArrowDown'?1:items.length-1))%items.length;list.querySelectorAll('li').forEach((li,i)=>li.classList.toggle('on',i===hi));}
    else if(e.key==='Enter'){e.preventDefault();pick(items[hi]);}else if(e.key==='Escape')list.hidden=true;};
  const sh=()=>g('dir').value.startsWith('ロング')?1:-1;
  const fxIn=()=>(P&&P.fills[0].fx)||st.fx||0;
  // 損切・利確: ％を入れたら価格を計算、価格を入れたら％(1%刻みの近い値)を表示。最後に触った方を正とする
  const LAST={stop:P?'px':'pct',tgt:P?'px':'pct'};
  const rnd=v=>cur&&cur[0]==='us'?+v.toFixed(2):Math.round(v);
  function upd(){
    const mk=cur?cur[0]:'jp',us=mk==='us',avg=num(g('px')),qty=num(g('qty')),s=sh();
    root.querySelectorAll('[data-u]').forEach(x=>x.textContent=unitOf(mk));
    const sw=g('qty').closest('.j-step');if(sw)sw.dataset.step=qtyStep(mk);
    const ne=cur?st.earn[cur[0]+':'+cur[1]]:null;g('picked').innerHTML=cur?`<span class="j-flag ${mk}">${us?'US':'JP'}</span><span class="j-code">${cur[1]}</span>${esc(cur[2])}${ne?` ・ 次の決算 ${ne}`:''}`:'候補から銘柄を選んでください';
    g('total').innerHTML=!avg||!qty?'—':st.pub?'非表示':us?`$${fmt(avg*qty,2)} × ドル円 ${fxIn().toFixed(2)}${P?'（建てたとき）':st.ref.fx&&st.ref.fx.date?'（'+st.ref.fx.date.slice(5).replace('-','/')+'時点）':''}＝ <b>${fmt(avg*qty*fxIn())}円</b>`:`<b>${fmt(avg*qty)}円</b>`;
    const d=g('date').value;g('due').textContent=g('kind').value==='信用'&&d?dueOf(d):'—（現物）';
    [['stop',-1],['tgt',1]].forEach(([k,dirn])=>{const pin=g(k+'-pct'),inp=g(k);const sign=dirn*s;
      g(k+'-sg').textContent=sign>0?'+':'−';
      if(avg&&LAST[k]==='pct'&&pin.value!=='')inp.value=commas(rnd(avg*(1+sign*pin.value/100)));
      const v=num(inp);
      if(avg&&LAST[k]==='px'&&v)pin.value=Math.round(Math.abs(v/avg-1)*100);
      if(v&&avg){const pl=s*(v-avg)*qty;const bad=k==='stop'?pl>0:pl<0;
        g(k+'-pl').innerHTML=(k==='stop'?'損失 ':'利益 ')+(st.pub?'非表示':us?`<span class="${cls(pl)}">${pl<0?'−':'+'}$${fmt(Math.abs(pl),2)}（${yen(pl*fxIn())}）</span>`:`<span class="${cls(pl)}">${yen(pl)}</span>`)+(bad?' <span class="j-warn">向きが逆です</span>':'');}
      else g(k+'-pl').textContent='';});
  }
  ['stop','tgt'].forEach(k=>{g(k+'-pct').oninput=()=>{LAST[k]='pct';upd();};g(k).oninput=()=>{LAST[k]='px';upd();};});
  ['px','qty','dir','kind','date'].forEach(k=>g(k).addEventListener('input',()=>upd()));
  if(!P){g('stop-pct').value=7;g('tgt-pct').value=20;}
  upd();
  return ()=>({u:cur,kind:g('kind').value,dir:sh()>0?'L':'S',acct:g('acct').value,date:g('date').value,qty:num(g('qty')),px:num(g('px')),stop:num(g('stop')),tgt:num(g('tgt'))||null,
    tag:g('tag').value,reason:g('reason').value,memo:g('memo').value});
}
// 保存する項目(表示のための計算値は保存しない)
const KEYS=['mk','code','name','kind','dir','acct','tag','fills','stops','target','regime','reason','memo','exitReason','rule','done','due'];
const pack=P=>{const o={};KEYS.forEach(k=>o[k]=P[k]===undefined?null:P[k]);return o;};
// 入力欄の値から新しい建玉を作る(保存はしない)
function newPos(v){const [mk,code,name]=v.u;
  return {mk,code,name,kind:v.kind,dir:v.dir,acct:v.acct,tag:v.tag,target:v.tgt,
    fills:[{d:v.date,t:v.dir==='L'?'buy':'sell',q:v.qty,p:v.px,fx:mk==='us'?st.fx:null}],stops:[{d:v.date,v:v.stop}],
    regime:(st.ref.regime||{})[mk]||'',reason:v.reason,memo:v.memo,exitReason:null,rule:null,done:false,
    due:v.kind==='信用'?dueOf(v.date):null};}
// 新しい建玉を保存(id が付く)。監視銘柄にあれば外す
async function addPos(v){const P=newPos(v);const r=await api('positions',{method:'POST',body:pack(P)});P.id=r.position.id;
  if(st.pos)st.pos.push(P);
  const w=findWatch(P.mk,P.code);let unwatched=false;if(w){try{await watchDel(w.id);unwatched=true;}catch(e){}}
  return {P,unwatched};}

/* ---------- 監視銘柄 ---------- */
const findWatch=(mk,code)=>(st.watch||[]).find(w=>w.mk===mk&&w.code===code)||null;
const held=(mk,code)=>(st.pos||[]).some(P=>!P.done&&P.mk===mk&&P.code===code);
async function watchList(force){if(!st.watch||force){const r=await api('watch');st.watch=r.watch||[];}return st.watch;}
async function watchSet(mk,code,name,entry){const r=await api('watch',{method:'POST',body:{mk,code,name,entry}});const it=r.item;
  st.watch=st.watch||[];const i=st.watch.findIndex(w=>w.mk===mk&&w.code===code);if(i>=0)st.watch[i]=it;else st.watch.push(it);return it;}
async function watchDel(id){await api('watch/'+id,{method:'DELETE'});st.watch=(st.watch||[]).filter(w=>w.id!==id);}
const fire=detail=>document.dispatchEvent(new CustomEvent('jr:change',{detail:detail||{}}));
const pxTxt=(mk,v)=>v==null||!isFinite(v)?'–':mk==='us'?'$'+fmt(v,2):fmt(v,v>=1000?0:1)+'円';
// 現在値 − 予定株価(円・ドル)と、予定株価に対する％
function diffHTML(mk,p,e){if(p==null||!e)return '<span class="muted">–</span>';const d=p-e,pc=(p/e-1)*100,c=cls(d);
  const a=mk==='us'?(d<0?'−':'+')+'$'+fmt(Math.abs(d),2):(d<0?'−':'+')+fmt(Math.abs(d),Math.abs(d)>=100?0:1)+'円';
  return `<span class="${c}">${a}</span><span class="w-dp ${c}">${sgn(pc)}%</span>`;}

function toast(t){const d=document.createElement('div');d.className='j-toast';d.textContent=t;document.body.appendChild(d);setTimeout(()=>d.remove(),2600);}
async function busy(btn,fn){if(btn.disabled)return;btn.disabled=true;try{await fn();}catch(e){toast(e.message);}finally{btn.disabled=false;}}
// Enterキーでは保存しない(ボタンを押したときだけ)。銘柄の候補を選ぶEnterはそのまま使える
const noEnter=f=>f.addEventListener('keydown',e=>{if(e.key==='Enter'&&!/^(TEXTAREA|BUTTON)$/.test(e.target.tagName))e.preventDefault();});

/* ---------- 銘柄カードの2つのボタン(card.js が呼ぶ) ---------- */
const ACTS={
  state:o=>{const w=findWatch(o.market,o.code);return {inWatch:!!w,watch:w?w.entry:null,hold:held(o.market,o.code)};},
  watch:async(el,o,back)=>{const mk=o.market;el.innerHTML='<div class="phint">読み込み中…</div>';await load();
    const w=findWatch(mk,o.code),p=priceOf(mk,o.code);
    el.innerHTML=`<form class="j-act jr-wform" autocomplete="off"><h4>監視銘柄に登録する：${esc(o.name)}（${esc(o.code)}）</h4><div class="j-form">
      ${fld('cw-now','現在値','<div class="auto">'+pxTxt(mk,p)+'</div>')}
      ${fld('cw-entry','エントリー予定株価',unitInp('cw-entry',w&&w.entry!=null?w.entry:'',mk))}
      ${fld('cw-diff','現在値との差（自動）','<div class="auto" id="cw-diff">—</div>','w2')}</div>
      <div class="j-btnrow"><button class="btn" type="submit">${w?'エントリー予定株価を更新する':'監視銘柄に追加する'}</button><button class="btn ghost" type="button" data-back>戻る</button></div></form>`;
    const f=el.querySelector('form'),inp=f.querySelector('#cw-entry');noEnter(f);
    const upd=()=>{f.querySelector('#cw-diff').innerHTML=num(inp)>0?diffHTML(mk,p,num(inp))+'<span class="hint" style="margin-left:8px">（現在値 − 予定株価）</span>':'—';};
    inp.oninput=upd;upd();setTimeout(()=>inp.focus(),30);
    f.querySelector('[data-back]').onclick=back;
    f.onsubmit=e=>{e.preventDefault();busy(f.querySelector('button[type=submit]'),async()=>{const v=num(inp);if(!(v>0)){toast('エントリー予定株価を入れてください');inp.focus();return;}
      await watchSet(mk,o.code,o.name,v);back();toast(`${o.name}を${w?'更新':'監視銘柄に追加'}しました`);fire({watch:true});});};},
  hold:async(el,o,back)=>{el.innerHTML='<div class="phint">読み込み中…</div>';await load();
    const u0=[o.market,o.code,o.name];
    el.innerHTML=`<form class="j-act" autocomplete="off"><div class="j-ph"><h3>保有銘柄に登録する（新しく建てる）</h3><span>灰色の欄は自動で入ります。${st.fx?'米国株の円換算は ドル円 '+st.fx.toFixed(2)+(st.ref.fx&&st.ref.fx.date?'（'+st.ref.fx.date.slice(5).replace('-','/')+'時点）':''):''}</span></div>
      <div class="jr-pos"></div><div class="j-btnrow"><button class="btn" type="submit">保有中に追加する</button><button class="btn ghost" type="button" data-back>やめる</button></div>
      ${findWatch(o.market,o.code)?'<div class="hint" style="margin-top:6px">追加すると、この銘柄は監視銘柄から外れます。</div>':''}</form>`;
    const f=el.querySelector('form'),b=f.querySelector('.jr-pos');b.innerHTML=posFormHTML('c',null,u0);const read=bindPosForm(b,'c',null,u0);noEnter(f);
    f.querySelector('[data-back]').onclick=back;
    f.onsubmit=e=>{e.preventDefault();busy(f.querySelector('button[type=submit]'),async()=>{const v=read();
      if(!v.u){toast('銘柄を候補から選んでください');return;}if(!v.qty||!v.px||!v.stop){toast('株数・平均取得単価・損切ラインを入れてください');return;}
      const {P,unwatched}=await addPos(v);back();toast(`${P.name}を保有中に追加しました${unwatched?'（監視銘柄から外しました）':''}`);fire({pos:P,watch:unwatched});});};}
};

/* ---------- 共通の見た目(入力欄・ボタン・お知らせ)。売買記録ページの j- と同じ ---------- */
const css=document.createElement('style');css.textContent=`
.j-act{background:var(--surface);border:1px solid var(--brand);border-radius:12px;padding:14px;margin-top:12px}.j-act h4{margin:0 0 10px!important;font-size:14px}
.j-ph{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}.j-ph h3{margin:0;font:700 15px var(--f-display)}.j-ph span{font-size:11.5px;color:var(--faint)}
.j-form{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px 16px}.j-form .f{display:flex;flex-direction:column;gap:4px;min-width:0}.j-form .f label{font-size:12px;color:var(--muted)}
.j-form .f.w2{grid-column:span 2}@media (max-width:520px){.j-form .f.w2{grid-column:auto}}.j-form .f.full{grid-column:1/-1}
.j-form .auto{font:13px var(--f-num);color:var(--ink);background:var(--surface-2);border-radius:8px;padding:6px 8px}.j-form .hint,.j-act .hint{font-size:11px;color:var(--faint)}
.j-form input,.j-form select,.j-form textarea{font:13px var(--f-body);color:var(--ink);background:var(--surface);border:1px solid var(--line-strong);border-radius:8px;padding:5px 8px;min-width:0}
.j-fs{border:0;border-top:1px solid var(--line);padding:14px 0 4px;margin:14px 0 0}.j-fs legend{font:700 13px var(--f-body);color:var(--ink);padding-right:8px}
.j-ac{position:relative}.j-ac input{width:100%}
.j-acl{position:absolute;left:0;right:0;top:calc(100% + 2px);z-index:20;list-style:none;margin:0;padding:4px;background:var(--surface);border:1px solid var(--line-strong);border-radius:8px;box-shadow:0 8px 24px rgba(10,40,40,.14);max-height:280px;overflow:auto}
.j-acl li{padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px;display:flex;align-items:center;gap:2px}.j-acl li.on,.j-acl li:hover{background:var(--brand-soft)}.j-acl li.none{color:var(--faint);cursor:default}
.j-picked{font-size:12px;color:var(--muted);margin-top:4px}
.j-unit{display:flex;align-items:center;gap:6px}.j-unit input{flex:1;min-width:0;width:100%}.j-unit .u{font-size:12.5px;color:var(--muted);white-space:nowrap}
.j-line{display:grid;grid-template-columns:minmax(150px,200px) auto 120px minmax(0,1fr);align-items:center;gap:8px 12px}.j-line .j-unit{flex:none}
.j-pct{display:flex;align-items:center;gap:4px}.j-pct input{width:100%;min-width:0}.j-pct .sg,.j-pct .u{font:600 13px var(--f-num);color:var(--muted)}
@media (max-width:560px){.j-line{grid-template-columns:1fr auto 110px}.j-line .j-pl{grid-column:1/-1}}.j-line .or{font-size:12px;color:var(--faint)}.j-pl{font:600 13px var(--f-num)}
.j-btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.j-btnrow .btn[disabled]{opacity:.5;cursor:wait}
.j-code{font:500 11px var(--f-num);color:var(--faint);margin-right:6px}
.j-flag{display:inline-block;font:700 10px var(--f-num);border-radius:3px;padding:0 4px;margin-right:6px;color:var(--brand-ink);vertical-align:1px}.j-flag.jp{background:#B5524A}.j-flag.us{background:#4F72B0}
.j-warn{color:var(--down);font-weight:700}.j-hide{color:var(--faint)}.w-dp{display:inline-block;min-width:52px;margin-left:6px;font-weight:500;font-size:11.5px}
.j-step{display:flex;align-items:center;gap:4px}.j-step input{flex:1;min-width:0;width:100%}.j-step .u{font-size:12.5px;color:var(--muted);white-space:nowrap}
.j-step button{flex:none;width:30px;height:30px;border:1px solid var(--line-strong);background:var(--surface-2);color:var(--ink);border-radius:8px;font:600 16px/1 var(--f-num);cursor:pointer;padding:0}
.j-step button:hover{border-color:var(--brand);color:var(--brand)}input.j-num{text-align:right;font-variant-numeric:tabular-nums}
.j-toast{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 18px;border-radius:999px;font-size:13px;z-index:50}`;
document.head.appendChild(css);

// 3桁区切り: 入力を終えたらそろえる／株数の−＋(押したら input を投げて合計などを計算し直す)
document.addEventListener('focusout',e=>{const t=e.target;if(t&&t.classList&&t.classList.contains('j-num'))t.value=commas(t.value);});
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('.j-step button[data-st]');if(!b)return;e.preventDefault();
  const w=b.closest('.j-step'),inp=w.querySelector('input'),st=+w.dataset.step||1,d=+b.dataset.st;let v=num(inp);if(!isFinite(v))v=0;
  v=Math.max(0,d>0?Math.floor(v/st)*st+st:Math.ceil(v/st)*st-st);inp.value=commas(v);inp.dispatchEvent(new Event('input',{bubbles:true}));});

/* ---------- 本人のときだけボタンを出す ---------- */
let IP=null;
function init(force){if(IP&&!force)return IP;
  return IP=api('me').then(m=>{st.me=m;window.StockCardActs=ACTS;
    return Promise.all([watchList(true).catch(()=>{}),api('positions').then(r=>{st.pos=r.positions||[];}).catch(()=>{})]);}).catch(()=>{st.me=null;});}
init();

window.JR={st,TODAY,STRATS,api,load,init,priceOf,searchUniv,norm,unitOf,fld,fsel,finp,unitInp,qtyInp,commas,num,posFormHTML,bindPosForm,pack,newPos,addPos,
  findWatch,held,watchList,watchSet,watchDel,diffHTML,pxTxt,fire,toast};
})();
