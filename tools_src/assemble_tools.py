"""ツール2ページ(セクター状況・業種状況)の<script>を、共通部分 tools_common.js ＋ ページ別の定義(下のSECT/THEM)から組み立てる。
   共通JSを直したら:  python tools_src/assemble_tools.py  →  python 04_build_html.py"""
import re
import os
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '..', 'pages', 'tools')
COMMON = open(os.path.join(HERE, 'tools_common.js'), encoding='utf-8').read()

SECT = r'''const FILE='sectors',MINN=0;
function FOOT(){return (mk==='us'?'<b>データ</b>：各ETFの日次終値と出来高（Yahoo Finance）。'
  :'<b>データ</b>：「（33業種）」は、各業種の構成銘柄（東証上場の内国普通株）を等しい重みで平均して自前で算出した指数（現在値は表示なし）。そのほかは東証上場ETFの日次終値と出来高（Yahoo Finance）。')+COMMON_FOOT;}
function drawTable(R){head([['key','銘柄','l'],['name','テーマ','l']]);
  $('#tbody').innerHTML=R.map(x=>`<tr><td class="l"><span class="tk">${x.etf?esc(x.key):'<span class="muted">―</span>'}</span></td><td class="l"><span class="nm2">${esc(x.name)}</span><span style="font-size:11px;color:var(--faint)">${esc(x.group)}</span></td>${cells(x)}</tr>`).join('')
    ||'<tr><td colspan="17" class="l muted" style="padding:14px">該当がありません。</td></tr>';}'''

THEM = r'''const FILE='themes',MINN=5;
const OPEN=new Set();
function FOOT(){return `<b>データ</b>：${mk==='us'?'テーマ別ETF（SSGA・ARK）の構成銘柄、Yahooの業種、事業説明文のキーワードで分類した米国株':'株探のテーマ（テーマ→構成銘柄）'}ごとに、構成銘柄の日次騰落を等しい重みで平均して自前で算出（Yahoo Finance の終値）。<b>現在値</b>＝その指数（2年前＝100）。上位3つは構成5銘柄以上のテーマから選びます。`+COMMON_FOOT+'行を押すと構成銘柄（RSは全銘柄の中での順位）。';}
function stockRow(code){const s=D.stocks[code];if(!s)return '';const [n,c1,w1,m0,ytd,hi,rs,tr]=s,t=TREND[tr===1?'up':tr===-1?'down':'flat'];
  const link=mk==='us'?`https://finance.yahoo.com/quote/${code}`:`https://kabutan.jp/stock/?code=${code}`;
  return `<tr><td class="l"><a href="${link}" target="_blank" rel="noopener" style="color:var(--brand);font-weight:600">${esc(code)}</a> ${esc(n)}</td>
    ${[c1,w1,m0,ytd,hi].map(v=>`<td class="${v>=0?'up':'down'}">${sign(v)}</td>`).join('')}<td>${rs??'–'}</td><td><span class="trend ${t[2]}">${t[0]}</span></td></tr>`;}
function memberHTML(x){const M=D.months||[];
  return `<tr class="mem"><td colspan="17"><div class="memhead"><b>${esc(x.name)}</b><span class="muted">構成銘柄 ${x.members.length}（売買代金の多い順）</span>
    <button class="btn sm ghost" data-copy="${esc(x.name)}">ティッカーをコピー</button><span class="phint" data-copied></span></div>
    <div style="overflow-x:auto"><table class="mt"><thead><tr><th class="l">銘柄</th><th>前日比</th><th>1週</th><th>今月（${esc(M[0]||'')}）</th><th>年初来</th><th>52週高値から</th><th>RS</th><th>トレンド</th></tr></thead>
    <tbody>${x.members.map(stockRow).join('')}</tbody></table></div></td></tr>`;}
function drawTable(R){head([['name','テーマ','l']]);
  $('#tbody').innerHTML=R.map(x=>{const open=OPEN.has(x.name);
    return `<tr class="th-row ${open?'open':''}" data-nm="${esc(x.name)}"><td class="l"><span class="nm2" style="font-weight:600">${open?'▾':'▸'} ${esc(x.name)}</span><span style="font-size:11px;color:var(--faint)">${esc(x.group)} ・ ${x.n}銘柄</span></td>${cells(x)}</tr>`+(open?memberHTML(x):'');}).join('')
    ||'<tr><td colspan="17" class="l muted" style="padding:14px">該当がありません。</td></tr>';
  $$('#tbody tr.th-row').forEach(tr=>tr.onclick=()=>{const n=tr.dataset.nm;OPEN.has(n)?OPEN.delete(n):OPEN.add(n);drawTable(rows());});
  $$('#tbody [data-copy]').forEach(b=>b.onclick=e=>{e.stopPropagation();const x=D.rows.find(r=>r.name===b.dataset.copy);
    const txt=x.members.map(c=>mk==='jp'?c+'.T':c).join(',');const note=b.parentNode.querySelector('[data-copied]');
    navigator.clipboard.writeText(txt).then(()=>note.textContent='コピーしました（'+x.members.length+'銘柄）').catch(()=>{note.textContent=txt;});});}'''

for fn, page in (('sectors.html', SECT), ('themes.html', THEM)):
    p = BASE + '\\' + fn
    s = open(p, encoding='utf-8').read()
    # 期間ボタンの行を削除・分類→テーマ・検索に×
    s = re.sub(r'\s*<div class="ctlrow"><span class="ctl-label">期間</span><div class="seg" id="per"></div></div>', '', s)
    s = s.replace('<span class="ctl-label">分類</span>', '<span class="ctl-label">テーマ</span>')
    s = re.sub(r'(<input id="q" type="text" placeholder="[^"]*" autocomplete="off">)(</span>)', r'\1<span class="x" id="qx" hidden title="消す">✕</span>\2', s)
    i = s.index('<script>'); j = s.index('</script>') + len('</script>')
    s = s[:i] + COMMON.replace('/*__PAGE__*/', page) + s[j:]
    open(p, 'w', encoding='utf-8').write(s)
    print(fn, 'ok', 'qx' in s, 'id="per"' in s)

# 検索の入力例(上の置換で戻るので付け直す)
PH = {'sectors.html': '名前・ティッカー（例：半導体、SMH、銀行）', 'themes.html': 'テーマ名・銘柄（例：原子力、データセンター、7203）'}
for fn, ph in PH.items():
    p = os.path.join(BASE, fn); s = open(p, encoding='utf-8').read()
    s = re.sub(r'<input id="q" type="text" placeholder="[^"]*"', f'<input id="q" type="text" placeholder="{ph}"', s)
    open(p, 'w', encoding='utf-8').write(s)
