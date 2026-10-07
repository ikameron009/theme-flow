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
  :'<b>データ</b>：「（33業種）」は、各業種の構成銘柄（東証上場の内国普通株）を等しい重みで平均して自前で算出した指数（現在値は表示なし・チャートは終値の折れ線）。そのほかは東証上場ETFの日次終値と出来高（Yahoo Finance）。')+COMMON_FOOT+CARD_FOOT+'行を押すとその行のすぐ下に、ヒートマップはタイルを押すと図の下にカード。';}
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
    m:groupM(x),
    foot:tw.length?'似た動きのETF：'+tw.map(t=>esc(t.key)+' '+esc(t.name)).join('、'):'',
    onClose:()=>{SEL=null;if(id==='card')drawTable(rows());}});}'''

THEM = r'''const FILE='themes',MINN=5;
const OPEN=new Set(),TCLOSED=new Set();let MSEL=null,VALD=null,VLOADING=null;
/* テーマごとのバリュエーション(全銘柄の決算データがそろってから計算して出す。今はデータ収集中) */
const XCOLS=[['vig','織り込み成長（中央値）',''],['vlow','期待は控えめの割合','']];
function XCELLS(x){return '<td class="muted" style="font-size:11px">データ収集中</td><td class="muted" style="font-size:11px">データ収集中</td>';}
function FOOT(){return `<b>データ</b>：${mk==='us'?'テーマ別ETF（SSGA・ARK）の構成銘柄、Yahooの業種、事業説明文のキーワードで分類した米国株':'株探のテーマ（テーマ→構成銘柄）'}ごとに、構成銘柄の日次騰落を等しい重みで平均して自前で算出（Yahoo Finance の終値）。<b>現在値</b>＝その指数（2年前＝100）。上位3つは構成5銘柄以上のテーマから選びます。`+COMMON_FOOT+CARD_FOOT+'<b>織り込み成長（中央値）・期待は控えめの割合</b>＝構成銘柄のバリュエーションの集計（全銘柄の決算データがそろってから表示します）。行を押すとテーマのカードと構成銘柄（RSは全銘柄の中での順位）。銘柄名を押すと、その銘柄の行のすぐ下にカード。構成銘柄のバリュエーションは計算結果の表示であり、売買の推奨ではありません（出所：日本株＝Powered by EDINET DB、米国株＝SEC EDGAR、株価＝Yahoo Finance）。';}
/* 構成銘柄の配列: [名前,前日比,1週,今月,年初来,52週高値から,RS,トレンド,現在値,1か月前,2か月前,3か月前,6か月前,1年前,資金急増率,直近60日] */
const MCOLS=[['銘柄','l'],['トレンド',''],['直近60日',''],['現在値',''],['RS',''],['前日比',''],['週間%',''],['__m0',''],['1か月前',''],['2か月前',''],['3か月前',''],['6か月前',''],['1年前',''],['52週高値から',''],['資金急増率%',''],
  ['織り込み成長',''],['実績（3年）',''],['直近1年',''],['差',''],['バリュエーション','l'],['PER位置（5年）',''],['PEG（実績）','']];
function stockRow(code,th){const s=D.stocks[code];if(!s)return '';const [n,c1,w1,m0,ytd,hi,rs,tr,last,r1,r2,r3,r6,r12,sg,sp]=s,t=TREND[tr===1?'up':tr===-1?'down':'flat'],on=MSEL&&MSEL.t===th&&MSEL.c===code;
  const pc=v=>`<td class="${(v??0)>=0?'up':'down'}">${sign(v)}</td>`;
  return `<tr class="${on?'on':''}"><td class="l"><button class="mnb" data-c="${esc(code)}" data-t="${esc(th)}" title="チャートを表示"><b>${esc(n)}</b> <span class="tk">${esc(code)}</span></button></td>
    <td><span class="trend ${t[2]}">${t[0]} ${t[1]}</span></td><td>${spark(sp)}</td><td>${last==null?'–':fmt(last,last>=1000?0:(mk==='us'?2:1))}</td><td>${rs??'–'}</td>
    ${[c1,w1,m0,r1,r2,r3,r6,r12,hi].map(pc).join('')}<td class="${(sg??0)>=0?'up':'down'}">${sg==null?'–':sign(sg,1)}</td>
    ${VALD?StockCard.vtds((VALD.stocks||{})[code],mk):'<td colspan="7" class="l muted" style="font-size:11px">読み込み中…</td>'}</tr>`;}
function memberHTML(x){const M=D.months||[];
  return `<tr class="mem"><td colspan="30"><div class="memhead"><b>${esc(x.name)}</b><span class="muted">構成銘柄 ${x.members.length}（売買代金の多い順・銘柄名を押すとその行の下にカード）</span>
    <button class="btn sm ghost" data-copy="${esc(x.name)}">ティッカーをコピー</button>${TCLOSED.has(x.name)?`<button class="btn sm ghost" data-tcard="${esc(x.name)}">テーマのカードを見る</button>`:''}<span class="phint" data-copied></span></div>
    ${TCLOSED.has(x.name)?'':cardSlot('tc_'+x.key)}
    ${VALD?StockCard.valNote(VALD,mk):''}<div class="memwrap"><table class="mt"><thead><tr>${MCOLS.map(([l,c])=>`<th class="${c}">${l==='__m0'?'今月（'+esc(M[0]||'')+'）':l}</th>`).join('')}</tr></thead>
    <tbody>${x.members.map(c=>stockRow(c,x.name)).join('')}</tbody></table></div></td></tr>`;}
function fitMem(){const w=document.querySelector('.sx-wrap');if(!w)return;$$('.memwrap').forEach(el=>el.style.width=Math.max(320,w.clientWidth-28)+'px');}
addEventListener('resize',fitMem);
function drawTable(R){head([['name','テーマ','l']]);
  if((!VALD||VALD.market!==mk)&&window.StockCard&&VLOADING!==mk){const m0=mk;VLOADING=m0;VALD=null;StockCard.valData(m0).then(v=>{VLOADING=null;if(mk!==m0)return;VALD=v||{market:m0,stocks:{}};if(OPEN.size)drawTable(rows());});}
  $('#tbody').innerHTML=R.map(x=>{const open=OPEN.has(x.name);
    return `<tr class="th-row ${open?'open':''}" data-nm="${esc(x.name)}"><td class="l"><span class="nm2" style="font-weight:600">${open?'▾':'▸'} ${esc(x.name)}</span><span style="font-size:11px;color:var(--faint)">${esc(x.group)} ・ ${x.n}銘柄</span></td>${cells(x)}</tr>`+(open?memberHTML(x):'');}).join('')
    ||'<tr><td colspan="20" class="l muted" style="padding:14px">該当がありません。</td></tr>';
  fitMem();
  $$('#tbody tr.th-row').forEach(tr=>tr.onclick=()=>{const n=tr.dataset.nm;OPEN.has(n)?OPEN.delete(n):OPEN.add(n);if(MSEL&&MSEL.t===n)MSEL=null;drawTable(rows());});
  $$('#tbody .mnb').forEach(b=>b.onclick=e=>{e.stopPropagation();const c=b.dataset.c,t=b.dataset.t;MSEL=MSEL&&MSEL.c===c&&MSEL.t===t?null:{c,t};drawTable(rows());});
  $$('#tbody [data-copy]').forEach(b=>b.onclick=e=>{e.stopPropagation();const x=D.rows.find(r=>r.name===b.dataset.copy);
    const txt=x.members.map(c=>mk==='jp'?c+'.T':c).join(',');const note=b.parentNode.querySelector('[data-copied]');
    navigator.clipboard.writeText(txt).then(()=>note.textContent='コピーしました（'+x.members.length+'銘柄）').catch(()=>{note.textContent=txt;});});
  $$('#tbody [data-tcard]').forEach(b=>b.onclick=e=>{e.stopPropagation();TCLOSED.delete(b.dataset.tcard);drawTable(rows());});
  R.filter(x=>OPEN.has(x.name)&&!TCLOSED.has(x.name)).forEach(openTheme);
  const mb=MSEL&&[...document.querySelectorAll('#tbody .mnb')].find(b=>b.dataset.c===MSEL.c&&b.dataset.t===MSEL.t);
  if(mb)openMember(mb.closest('tr'));else{MSEL=null;StockCard.closeBelow('m');}}
/* テーマ自体のカード(テーマを開くと最初から表示・閉じても「テーマのカードを見る」で戻せる) */
function openTheme(x){const id='tc_'+x.key;if(!document.getElementById(id))return;fitSlot(id);
  StockCard.open(id,{market:mk,code:'',name:x.name,sub:x.group+' ・ '+x.n+'銘柄',links:false,line:true,val:false,scroll:false,
    src:StockCard.root+(mk==='us'?'us_ohlc/':'ohlc/')+encodeURIComponent(x.key)+'.json',m:groupM(x),
    onClose:()=>{TCLOSED.add(x.name);drawTable(rows());}});}
function openMember(tr){const {c,t}=MSEL,s=D.stocks[c];if(!s)return;const n=s[0];
  const ths=D.rows.filter(r=>r.members&&r.members.includes(c)).map(r=>r.name);
  StockCard.below(tr,{group:'m',market:mk,code:c,name:n,sub:t,scroll:!MSEL.shown,
    foot:ths.length>1?'ほかの所属テーマ：'+ths.filter(x=>x!==t).map(esc).join('、'):'',
    onClose:()=>{MSEL=null;drawTable(rows());}});MSEL.shown=true;}'''


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
