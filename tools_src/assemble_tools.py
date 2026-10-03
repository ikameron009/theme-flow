"""ツール2ページ(セクター状況・業種状況)の<script>を、共通部分 tools_common.js ＋ ページ別の定義(下のSECT/THEM)から組み立てる。
   共通JSを直したら:  python tools_src/assemble_tools.py  →  python 04_build_html.py"""
import re
import os
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '..', 'pages', 'tools')
COMMON = open(os.path.join(HERE, 'tools_common.js'), encoding='utf-8').read()

SECT = r'''const FILE='sectors',MINN=0;
let SEL=null;st.allEtf=false;
/* ③ 米国は代表ETFだけを表示(「すべて」で全部)。検索・テーマを選んだ時は全部から探す */
const FILTER=x=>mk!=='us'||st.allEtf||st.q||st.pick||!x.rep||x.rep===x.key;
const twins=x=>D.rows.filter(y=>y.rep===x.key&&y.key!==x.key);
function EXTRA(){const r=$('#repRow');if(!r)return;r.hidden=mk!=='us';if(mk!=='us')return;
  const nRep=D.rows.filter(x=>!x.rep||x.rep===x.key).length;
  $('#rep').innerHTML=`<button data-v="rep" aria-pressed="${!st.allEtf}">代表ETFだけ（${nRep}本）</button><button data-v="all" aria-pressed="${st.allEtf}">すべて（${D.rows.length}本）</button>`;
  $('#rep').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.allEtf=b.dataset.v==='all';draw();};}
function FOOT(){return (mk==='us'?'<b>データ</b>：各ETFの日次終値と出来高（Yahoo Finance）。<b>代表ETF</b>＝同じテーマの中で、日々の値動きの相関（直近1年）が0.85以上のETFを1つのグループにまとめ、売買代金が一番多いものを代表として表示（「すべて」で全部表示。名前の下の「似た動き」がまとめたETF）。'
  :'<b>データ</b>：「（33業種）」は、各業種の構成銘柄（東証上場の内国普通株）を等しい重みで平均して自前で算出した指数（現在値は表示なし・チャートは終値の折れ線）。そのほかは東証上場ETFの日次終値と出来高（Yahoo Finance）。')+COMMON_FOOT+'行（ヒートマップはタイル）を押すと、下にチャート。';}
function drawTable(R){head([['key','銘柄','l'],['name','テーマ','l']]);
  $('#tbody').innerHTML=R.map(x=>{const tw=mk==='us'&&!st.allEtf&&x.rep===x.key?twins(x):[],on=SEL===x.key;
    return `<tr class="xrow ${on?'open':''}" data-k="${esc(x.key)}"><td class="l"><span class="tk">${x.etf?esc(x.key):'<span class="muted">―</span>'}</span></td><td class="l"><span class="nm2">${esc(x.name)}</span><span style="font-size:11px;color:var(--faint)">${esc(x.group)}${tw.length?` ・ 似た動き：${tw.map(t=>esc(t.key)).join('・')}`:''}${mk==='us'&&x.rep&&x.rep!==x.key?` ・ 代表：${esc(x.rep)}`:''}</span></td>${cells(x)}</tr>`
      +(on?`<tr class="cardrow"><td colspan="17">${cardSlot('card')}</td></tr>`:'');}).join('')
    ||'<tr><td colspan="17" class="l muted" style="padding:14px">該当がありません。</td></tr>';
  $$('#tbody tr.xrow').forEach(tr=>tr.onclick=()=>{SEL=SEL===tr.dataset.k?null:tr.dataset.k;drawTable(rows());});
  if(SEL)openSec('card');}
function TILE(k){SEL=k;openSec('hcard');}
function openSec(id){const x=D.rows.find(r=>r.key===SEL);if(!x)return;fitSlot(id);const tw=twins(x);
  StockCard.open(id,{market:mk,code:x.etf?x.key:'',name:x.name,sub:x.group,links:x.etf,line:!x.etf,val:false,scroll:id==='hcard',
    src:StockCard.root+(mk==='us'?'us_ohlc/':'ohlc/')+'sec_'+encodeURIComponent(x.key)+'.json',
    kv:[{l:'現在値',v:x.last==null?'–':fmt(x.last,mk==='us'?2:0)},{l:'前日比',v:sign(x.chg1),cls:(x.chg1??0)>=0?'up':'down'},{l:'今月（'+esc((D.months||[])[0]||'')+'）',v:sign(x.months[0]),cls:(x.months[0]??0)>=0?'up':'down'},
      {l:'年初来',v:sign(x.ytd),cls:(x.ytd??0)>=0?'up':'down'},{l:'52週高値から',v:sign(x.hi52),cls:(x.hi52??0)>=0?'up':'down'},{l:'資金急増率',v:sign(x.surge,0),cls:(x.surge??0)>=0?'up':'down'},{l:'RS',v:x.rs??'–'},{l:'トレンド',v:(TREND[x.trend]||TREND.flat).slice(0,2).join(' '),cls:(TREND[x.trend]||TREND.flat)[2]}],
    foot:tw.length?'似た動きのETF：'+tw.map(t=>esc(t.key)+' '+esc(t.name)).join('、'):'',
    onClose:()=>{SEL=null;if(id==='card')drawTable(rows());}});}'''

THEM = r'''const FILE='themes',MINN=5;
const OPEN=new Set();let MSEL=null;
function FOOT(){return `<b>データ</b>：${mk==='us'?'テーマ別ETF（SSGA・ARK）の構成銘柄、Yahooの業種、事業説明文のキーワードで分類した米国株':'株探のテーマ（テーマ→構成銘柄）'}ごとに、構成銘柄の日次騰落を等しい重みで平均して自前で算出（Yahoo Finance の終値）。<b>現在値</b>＝その指数（2年前＝100）。上位3つは構成5銘柄以上のテーマから選びます。`+COMMON_FOOT+'行を押すと構成銘柄（RSは全銘柄の中での順位）。銘柄名を押すと、その下にチャート。';}
function stockRow(code,th){const s=D.stocks[code];if(!s)return '';const [n,c1,w1,m0,ytd,hi,rs,tr]=s,t=TREND[tr===1?'up':tr===-1?'down':'flat'],on=MSEL&&MSEL.t===th&&MSEL.c===code;
  return `<tr class="${on?'on':''}"><td class="l"><button class="mnb" data-c="${esc(code)}" data-t="${esc(th)}" title="チャートを表示"><span class="tk">${esc(code)}</span> <b>${esc(n)}</b></button></td>
    ${[c1,w1,m0,ytd,hi].map(v=>`<td class="${v>=0?'up':'down'}">${sign(v)}</td>`).join('')}<td>${rs??'–'}</td><td><span class="trend ${t[2]}">${t[0]}</span></td></tr>`;}
function memberHTML(x){const M=D.months||[];
  return `<tr class="mem"><td colspan="17"><div class="memhead"><b>${esc(x.name)}</b><span class="muted">構成銘柄 ${x.members.length}（売買代金の多い順・銘柄名を押すとチャート）</span>
    <button class="btn sm ghost" data-copy="${esc(x.name)}">ティッカーをコピー</button><span class="phint" data-copied></span></div>
    <div style="overflow-x:auto"><table class="mt"><thead><tr><th class="l">銘柄</th><th>前日比</th><th>1週</th><th>今月（${esc(M[0]||'')}）</th><th>年初来</th><th>52週高値から</th><th>RS</th><th>トレンド</th></tr></thead>
    <tbody>${x.members.map(c=>stockRow(c,x.name)).join('')}</tbody></table></div>${MSEL&&MSEL.t===x.name?cardSlot('mcard'):''}</td></tr>`;}
function drawTable(R){head([['name','テーマ','l']]);
  $('#tbody').innerHTML=R.map(x=>{const open=OPEN.has(x.name);
    return `<tr class="th-row ${open?'open':''}" data-nm="${esc(x.name)}"><td class="l"><span class="nm2" style="font-weight:600">${open?'▾':'▸'} ${esc(x.name)}</span><span style="font-size:11px;color:var(--faint)">${esc(x.group)} ・ ${x.n}銘柄</span></td>${cells(x)}</tr>`+(open?memberHTML(x):'');}).join('')
    ||'<tr><td colspan="17" class="l muted" style="padding:14px">該当がありません。</td></tr>';
  $$('#tbody tr.th-row').forEach(tr=>tr.onclick=()=>{const n=tr.dataset.nm;OPEN.has(n)?OPEN.delete(n):OPEN.add(n);if(MSEL&&MSEL.t===n)MSEL=null;drawTable(rows());});
  $$('#tbody .mnb').forEach(b=>b.onclick=e=>{e.stopPropagation();const c=b.dataset.c,t=b.dataset.t;MSEL=MSEL&&MSEL.c===c&&MSEL.t===t?null:{c,t};drawTable(rows());});
  $$('#tbody [data-copy]').forEach(b=>b.onclick=e=>{e.stopPropagation();const x=D.rows.find(r=>r.name===b.dataset.copy);
    const txt=x.members.map(c=>mk==='jp'?c+'.T':c).join(',');const note=b.parentNode.querySelector('[data-copied]');
    navigator.clipboard.writeText(txt).then(()=>note.textContent='コピーしました（'+x.members.length+'銘柄）').catch(()=>{note.textContent=txt;});});
  if(MSEL&&document.getElementById('mcard'))openMember();}
function openMember(){const {c,t}=MSEL,s=D.stocks[c];if(!s)return;const [n,c1,w1,m0,ytd,hi,rs,tr]=s,T=TREND[tr===1?'up':tr===-1?'down':'flat'];fitSlot('mcard');
  const cl=v=>(v??0)>=0?'up':'down',ths=D.rows.filter(r=>r.members&&r.members.includes(c)).map(r=>r.name);
  StockCard.open('mcard',{market:mk,code:c,name:n,sub:t,
    kv:[{l:'前日比',v:sign(c1),cls:cl(c1)},{l:'1週',v:sign(w1),cls:cl(w1)},{l:'今月（'+esc((D.months||[])[0]||'')+'）',v:sign(m0),cls:cl(m0)},{l:'年初来',v:sign(ytd),cls:cl(ytd)},
      {l:'52週高値から',v:sign(hi),cls:cl(hi)},{l:'RS',v:rs??'–'},{l:'トレンド',v:T[0]+' '+T[1],cls:T[2]},{l:'所属テーマ数',v:ths.length}],
    foot:ths.length>1?'ほかの所属テーマ：'+ths.filter(x=>x!==t).map(esc).join('、'):'',
    onClose:()=>{MSEL=null;drawTable(rows());}});}'''


CARD_CSS = '''.cardslot{position:sticky;left:6px;text-align:left;white-space:normal;font-family:var(--f-body)}
.cardslot .panel{margin-top:4px}
tr.cardrow td{padding:0 0 12px;background:var(--bg)}
table.sx tr.xrow{cursor:pointer}
table.sx tr.xrow.open td{background:var(--surface-2)}
.mnb{background:none;border:0;padding:0;font:inherit;color:var(--ink);cursor:pointer;text-align:left}
.mnb b{font-weight:500;border-bottom:1px dotted var(--faint)}
.mnb:hover b{color:var(--brand);border-color:var(--brand)}
table.mt tr.on td{background:var(--surface-2)}
'''

for fn, page in (('sectors.html', SECT), ('themes.html', THEM)):
    p = BASE + '\\' + fn
    s = open(p, encoding='utf-8').read()
    # 期間ボタンの行を削除・分類→テーマ・検索に×
    s = re.sub(r'\s*<div class="ctlrow"><span class="ctl-label">期間</span><div class="seg" id="per"></div></div>', '', s)
    s = s.replace('<span class="ctl-label">分類</span>', '<span class="ctl-label">テーマ</span>')
    s = re.sub(r'(<input id="q" type="text" placeholder="[^"]*" autocomplete="off">)(</span>)', r'\1<span class="x" id="qx" hidden title="消す">✕</span>\2', s)
    if 'assets/card.js' not in s:
        s = s.replace('<script>', '<script src="../assets/card.js"></script>\n<script>', 1)
    if fn == 'sectors.html' and 'id="repRow"' not in s:
        s = s.replace('<div class="top3" id="top3"></div>', '<div class="ctlrow" id="repRow" hidden style="margin-top:10px"><span class="ctl-label">ETF</span><div class="seg" id="rep"></div><span class="phint">値動きがほぼ同じETFは、売買代金が一番多い1本（代表）にまとめて表示</span></div>\n  <div class="top3" id="top3"></div>', 1)
        s = s.replace('<div id="heat" hidden></div>', '<div id="heat" hidden></div>\n    <div id="hcard"></div>', 1)
    if '.cardslot' not in s:
        s = s.replace('</style>', CARD_CSS + '</style>', 1)
    i = s.index('<script>'); j = s.index('</script>', i) + len('</script>')
    s = s[:i] + COMMON.replace('/*__PAGE__*/', page) + s[j:]
    open(p, 'w', encoding='utf-8').write(s)
    print(fn, 'ok', 'qx' in s, 'id="per"' in s)

# 検索の入力例(上の置換で戻るので付け直す)
PH = {'sectors.html': '名前・ティッカー（例：半導体、SMH、銀行）', 'themes.html': 'テーマ名・銘柄（例：原子力、データセンター、7203）'}
for fn, ph in PH.items():
    p = os.path.join(BASE, fn); s = open(p, encoding='utf-8').read()
    s = re.sub(r'<input id="q" type="text" placeholder="[^"]*"', f'<input id="q" type="text" placeholder="{ph}"', s)
    open(p, 'w', encoding='utf-8').write(s)
