/* サイト全体の用語説明(はてなアイコン)。説明文はこのファイルの DICT にまとめる(全ページ共通)。
   ・項目名(見出し・表の列名・ラベル)の文字が TEXT の表と一致したら、自動で右に「?」を付ける(後から描かれる表にも付く)
   ・ページの見出しには「このツールの見方」を付ける(GUIDE)
   ・パソコン=マウスを近づけると表示 / スマホ=タップで表示・ほかをタップで閉じる。表の見出しの並べ替えは「?」以外を押したときだけ */
(function(){
  const P=location.pathname;
  const PAGE=/sectors/.test(P)?'sectors':/themes/.test(P)?'themes':/research/.test(P)?'research':/note/.test(P)?'note':'index';

  /* ---------- 説明文 [名前, 意味, 例・計算] ---------- */
  const DICT={
    /* 共通 */
    rs:['RS（相対的な強さ）','過去1年の値動きを、一覧の中で順位にした点数（1〜99）。99に近いほど、ほかより強く上がっています。','計算：3か月の騰落×40%＋6か月・9か月・12か月の騰落×各20%を順位づけ。例：96＝上位4%の強さ。'],
    rs_all:['RS（相対的な強さ）','過去1年の値動きを、全銘柄の中で順位にした点数（1〜99）。99に近いほど、ほかの銘柄より強く上がっています。','計算：3か月の騰落×40%＋6か月・9か月・12か月の騰落×各20%を順位づけ。'],
    hi52:['52週高値から','過去1年でいちばん高かった値段から、今どれだけ下にいるか。0%に近いほど高値の近くです。','例：−4.9%＝1年の最高値より4.9%安い。'],
    surge:['資金急増率','最近5日の売買代金の平均が、その前の20営業日の平均より何%多いか。お金が急に集まり始めたかの目安です。','例：+50%＝ふだんの1.5倍のお金が動いている。'],
    turnover:['売買代金','その日に売り買いされた金額（株価×出来高）。多いほど、たくさんのお金が動いています。','出来高（株数）より、銘柄の大きさの違いを比べやすい数字です。'],
    trend:['トレンド','株価と移動平均線（過去の終値の平均）の並びで判断します。','上昇＝株価＞50日線＞200日線／下落＝株価＜50日線＜200日線／中立＝どちらでもない。サイト全体で同じ判断です。'],
    month:['今月','今月の初めから今日までの騰落です。',''],
    ago:['期間ごとの騰落（1か月〜1年）','その時点から今日までの騰落（累積）です。月ごとの騰落ではありません。','1か月＝21営業日、2か月＝42、3か月＝63、6か月＝126、1年＝252営業日前と比べています。'],
    w1:['週間%','5営業日前からの騰落です。',''],
    spark:['直近60日','最近60営業日の値動きの小さなグラフ。緑＝期間の初めより上、赤＝下。',''],
    vol:['出来高','その日に売り買いされた株数。値段の違う銘柄どうしを比べるときは、売買代金のほうが向いています。',''],
    mcap:['時価総額','株価×発行済株式数。会社の大きさの目安です。',''],
    /* バリュエーション(銘柄カード・業種銘柄リサーチ・VCP) */
    v_head:['バリュエーション','今の株価が、どれくらいの利益の成長を前提にしているかを見る欄です。「割安・割高」や「理論株価」は出しません。','計算結果の表示であり、売買の推奨ではありません。出所：日本株＝Powered by EDINET DB、米国株＝SEC EDGAR、株価＝Yahoo Finance。'],
    v_ig:['株価が織り込む成長率','今の株価（時価総額）が「直近4四半期の純利益が、今後10年 年何%で伸びる」ことを前提にしているかを逆算した数字です。','割引率は日本株8%・米国株9%、11年目以降は年2%。−10%〜40%の外は「40%超」などと表示。'],
    v_g3:['実績3年','純利益（直近4四半期の合計）の、過去3年の年率の伸び。織り込み成長率と比べる「実績」です。','カードの（　）内は直近1年の伸び。3年前が赤字か実績が無い銘柄は表示せず、判定もしません。'],
    v_g1:['直近1年','純利益（直近4四半期の合計）の、1年前と比べた伸びです。',''],
    v_gap:['差','実績3年 − 株価が織り込む成長率。プラスが大きいほど、実績に比べて株価の前提が控えめです。',''],
    v_label:['判定','実績3年と、株価が織り込む成長率の差で3つに分けています。','期待は控えめ＝差が+5pt超／実績並み＝±5pt以内／期待が先行＝−5pt未満。「割安・割高」の意味ではありません。'],
    v_pos:['過去5年PERの位置','今のPERが、過去5年（毎月末）のPERの中で下から何%の位置か。0%に近いほど、5年の中で低いPERです。','PERが0倍以下・100倍超の月は除き、有効な月が24か月未満なら表示しません。'],
    v_peg:['PEG（実績）','PER ÷ 過去3年の純利益の年率（%）。1に近いほど、利益の伸びに対してPERが低めです。','実績ベースの数字で、noteのデータシート（予想ベース）とは別です。減益なら計算しません。'],
    v_fil:['バリュエーションで絞り込む','判定・過去5年PERの位置・株価が織り込む成長率で絞り込みます。計算できない銘柄（赤字・データ収集中など）は外れます。','日本株は決算データを毎日少しずつ集めているため、まだ一部の銘柄だけです。'],
    /* 市場概況 */
    g_market:['市場概況の見方','1. 一番上の「地合い」で、市場全体が買いやすい状況かを確認　2. 強い業種・弱い業種で、お金がどこに向かっているかを見る　3. 市場健全度カレンダーで、最近の流れが良くなっているか悪くなっているかを見る','日本株・米国株はページ上の切り替えで変わります。'],
    jiai:['地合い','市場全体が買いやすい状況かを、3つの指標で判断します。','3つのうち2つ以上が強気＝RISK-ON、0＝RISK-OFF、それ以外＝中立。'],
    m_hl:['新高値と新安値','52週高値を更新した銘柄の数が、52週安値を更新した銘柄の数より多ければ強気。','上がっている銘柄が多い市場かどうかの目安です。'],
    m_ma:['移動平均線より上の銘柄','株価が移動平均線（日本株は25日線、米国株は50日線）より上にある銘柄が半分以上なら強気。',''],
    m_ad:['値上がりと値下がり','直近10日で、値上がりした銘柄の数の合計が、値下がりした銘柄の数より多ければ強気。','例：1.22倍＝値上がりが値下がりの1.22倍。'],
    sec_strong:['強い業種・弱い業種','業種ごとの騰落の順位。日本株は東証33業種（構成銘柄を同じ重みで平均）、米国株は業種ETF（SPDRの11業種）です。','上位に来ている業種に、お金が向かっています。'],
    cal:['市場健全度カレンダー','日ごとに、新高値の銘柄と新安値の銘柄のどちらが多かったかを色で表します。','緑が続く＝上がる銘柄が多い健全な市場、赤が続く＝下がる銘柄が多い弱い市場。'],
    br_turn:['市場全体の売買代金','市場全体で1日に売り買いされた金額の推移。お金が市場に入ってきているかの目安です。','▼は売り抜け日＝主要な指数が0.2%以上下がり、売買代金が前日より多かった日。大口の売りが出た可能性があり、増えるほど警戒。'],
    dist:['売り抜け日','主要な指数が0.2%以上下がり、しかも売買代金が前日より多かった日。大口の売りが出た可能性がある日です。','直近25日で数が増えるほど、天井が近い警戒サイン。'],
    world:['世界のお金の流れ','株価指数・金利・通貨・商品などの騰落を並べて、世界のお金がどこに向かっているかを見ます。',''],
    cross:['クロスアセット・パフォーマンス','株・債券・通貨・商品など、種類の違う資産の騰落を同じ期間で比べたもの。',''],
    ratio:['資金移動の比率','2つの資産の値段の比の推移。上がっていれば、左側の資産にお金が移っています。','期間の初日を100として表示。'],
    /* テーマ別資金フロー */
    g_themes:['テーマ別資金フローの見方','1. 資金の初動ランキングで、お金が急に集まり始めたテーマを見つける　2. 資金ローテーションマップで、テーマごとの流れを日ごとに見る　3. テーマを押すと、右に構成銘柄が出る','売り買いの方向は区別せず、売買代金の大きさで見ています。'],
    inflow:['資金が流入しているテーマ','最近5日の売買代金が、その前の20日より大きく増えたテーマです。','直近5日 ÷ 前20日の平均で比べています。'],
    th_chart:['売買代金の推移','テーマごとの売買代金（またはシェア）の毎日の推移。',''],
    shoki:['資金の初動ランキング','売買代金の急増率が高い順に並べたテーマ。お金が集まり始めたばかりのテーマを見つけるためのランキングです。',''],
    rotation:['資金ローテーションマップ','テーマごとの売買代金のシェアを、日ごとに色で並べた図。色が濃くなっていくテーマにお金が移っています。','シェアはテーマの重複があるため、合計が100%を超えます。'],
    share:['シェア','そのテーマの売買代金が、市場全体の売買代金の何%を占めるか。',''],
    sharechg:['シェアの変化','直近5日平均のシェアから、20営業日前の5日平均シェアを引いたもの。',''],
    rk:['売買代金ランキング','売買代金が多い順の上位100銘柄。今の市場の主役が分かります。',''],
    rkpath:['順位の推移','売買代金の順位の、最近120日の動き。上が1位で、101位以下は圏外です。',''],
    turnmcap:['代金÷時価','売買代金を時価総額で割ったもの。会社の大きさの割に、どれだけ活発に売買されているか（回転の速さ）です。','10%以上は、過熱気味のことが多い目安。'],
    px20:['株価20日','最近20営業日の株価の動き。',''],
    /* 銘柄を探す */
    g_stocks:['銘柄を探すの見方','銘柄名かコードを入れると、ローソク足と、所属テーマ・売買代金の動きが出ます。','所属テーマを押すと、テーマ別資金フローに移ります。'],
    r20:['20日の騰落','20営業日前からの騰落です。',''],
    rkno:['売買代金の順位','その日の売買代金の、市場全体での順位です。',''],
    /* スクリーニング */
    g_screen:['スクリーニングの見方','ミネルヴィニの「トレンドテンプレート」（上昇トレンドの条件）を満たし、値動きの幅が段階的に縮んでいる（VCP）銘柄の一覧です。','上の日付バーで、過去の日の一覧も見られます。新しく載った銘柄は赤字です。'],
    vcp:['VCP','値動きの幅が段階的に小さくなっていく形（Volatility Contraction Pattern）。数字は形の質の点数（0〜100）で、空欄はVCPが崩れた銘柄です。',''],
    prio:['優先度','VCPが有効で、買い点（ピボット）まで8%以内の銘柄だけに付ける点数（0〜100）。今すぐ注目すべき順の目安です。','前日は点数がなく、今日付いた銘柄は黄色。'],
    buy:['Buy','株価が買い点（ピボット）を上に抜けた直後の銘柄に付く印です。',''],
    pivot:['ピボット','最後の値幅の縮みの高値（＝買い点）までの距離。＋はまだ下にあり、−はすでに上に抜けています。','0〜+2%は買い点のすぐ手前。'],
    streak:['継続','この一覧に何日続けて載っているか。初めて載った日が1です。',''],
    recent:['最近の掲載','直近20日のうち、一覧に載った日を色で表した帯。右端が最新日です。',''],
    listing:['上場','上場してからの年数です。',''],
    /* セクター状況 */
    g_sectors:['セクター状況の見方','1. テーマのボタンで分野を絞る　2. 表の見出しを押して並べ替える（上位3つも連動）　3. 行を押すと、すぐ下にチャートが出る','色が濃いほど大きく動いたことを表します。'],
    repetf:['代表ETF','同じテーマの中で値動きがほぼ同じETF（日々の騰落の相関が0.85以上）を1つにまとめ、売買代金が一番多いものを代表として表示します。','「すべて」で、まとめたETFも全部表示します。'],
    price_sec:['現在値','ETFの最新の値段。「（33業種）」は自前で計算した指数なので、値段は出していません。',''],
    /* 業種状況 */
    g_themetool:['業種状況の見方','1. テーマのボタンや入力欄で分野を絞る　2. 見出しを押して並べ替える　3. 行を押すと構成銘柄が開き、銘柄名を押すとチャートが出る','上位3つは、構成5銘柄以上のテーマから選んでいます。'],
    price_th:['現在値（テーマ指数）','テーマの構成銘柄を同じ重みで平均して作った指数。2年前を100とした値です。','例：166＝2年前より66%上。'],
    /* 業種銘柄リサーチ */
    g_research:['業種銘柄リサーチの見方','1. 業種・テーマ・トレンド・条件で絞り込む　2. 表・ヒートマップ・ツリーマップで見比べる　3. 銘柄名を押すとチャート、左のチェックでコピー・CSVの対象を選ぶ',''],
    f_sec:['業種','大分類と小分類の2段で選びます。日本株は大分類＝東証17業種・小分類＝東証33業種、米国株は大分類＝セクター・小分類＝業種です。','大分類だけ選ぶとその中すべて。同じ大分類の小分類も選ぶと、その小分類だけに絞ります。'],
    f_th:['テーマ','業種より細かい分野（例：パワー半導体）。大分類だけでも、小分類だけでも選べます。','業種とテーマを両方選ぶと、両方に当てはまる銘柄だけになります。'],
    f_cond:['条件を追加','数字の条件で絞り込みます。複数追加すると、すべてを満たす銘柄だけになります。','例：RS ≧ 80、52週高値から ≧ −10%。'],
    f_preset:['よく使う条件','よく使う絞り込みを1回で入れるボタン。',''],
    volx:['出来高倍率','その日の出来高が、50日平均の何倍か。2倍以上は、大きな材料が出た可能性があります。',''],
    adr:['ADR%','1日の値幅（高値÷安値−1）の20日平均。1日にどれくらい動く銘柄かの目安です。','例：5%＝1日に平均5%くらい上下する。'],
    ma50x:['50日線から','株価が50日移動平均線から何%上（または下）にあるか。大きくプラスだと、短期的に上がりすぎの目安です。',''],
    ma200x:['200日線から','株価が200日移動平均線から何%上（または下）にあるか。長い目で見た位置です。',''],
    ema21x:['21日EMAから','株価が21日の指数移動平均線（最近の値段を重く見る平均）から何%離れているか。',''],
    trend_mix:['トレンドの内訳','今の絞り込み結果の銘柄を、上昇・中立・下落に分けた数。',''],
    /* note紹介記事検証 */
    g_note:['note紹介記事検証の見方','noteで紹介した銘柄を、外れた銘柄も含めて全部記録し、その後の値動きを確かめるページです。','上の期間・売り方・比べる指数を変えると、すべての表と数字が計算し直されます。'],
    n_score:['急成長スコア','銘柄データシートの点数（100点満点）。売上・利益の伸びや加速など、急成長の度合いを点数にしたものです。','70点以上が「合格」。記事の株価基準日の時点で、今の計算方法で計算し直しています。'],
    n_must:['必須条件','急成長株として最低限満たしてほしい9つの条件のうち、いくつを満たしていたか。',''],
    n_label:['状態ラベル','記事を書いた時点で、その銘柄がどの段階にいたかの見立て（例：業績の加速待ち、押し目待ち）。',''],
    n_entry:['掲載時の株価','noteで公開した時点で確定していた最後の終値。日本株は15:30、米国株は米国時間16:00の引けで判断します。','例：日本時間の夜に公開した米国株は、前日の終値。'],
    n_ret:['騰落（掲載日から現在まで）','掲載時の株価から、最新の終値までの騰落。上で選んだ「配当込み／配当なし」で計算します。',''],
    n_ex:['指数との差','その銘柄の騰落から、同じ期間の指数の騰落を引いたもの。プラスなら指数に勝っています。','日本株はTOPIX（またはグロース250）、米国株はS&P500（またはラッセル2000）の連動ETFと比較。'],
    n_sel:['選んだ期間・売り方での成績','上で選んだ期間の終わりまで持つか、その前に売りの条件に当たればその日の終値で売った場合の損益。利益確定だけでなく、損失確定も含みます。','期間がまだたっていない銘柄は「期間前」。'],
    n_mfe:['最大上昇','掲載してから今日までで、いちばん上がったときの騰落。',''],
    n_mae:['最大下落','掲載してから今日までで、いちばん下がったときの騰落。',''],
    n_days:['経過','掲載してから何営業日たったか。',''],
    n_trend:['今のトレンド','今の株価が50日移動平均線の上か下か。',''],
    n_hz:['期間','掲載日から何営業日後で成績を見るか。1か月＝21、3か月＝63、半年＝126、1年＝252営業日。','「現在まで」は今日までの成績。'],
    n_rule:['売り方','持ち続けるか、移動平均線を割ったら売るか。「50日線割れで売る」は、掲載日の翌日以降に終値が50日線を初めて下回った日の終値で売ります。','損切りの幅は設定していません。'],
    n_bm:['比べる指数','成績を比べる相手。大型中心（TOPIX・S&P500）か、小型・新興（グロース250・ラッセル2000）かを選べます。','どちらも配当込みの連動ETFで計算。'],
    n_div:['配当','配当込み＝受け取った配当を再投資した場合の成績。配当なし＝株価の値動きだけ。比べる指数も同じ扱いにそろえます。',''],
    n_cnt:['集計した銘柄','今の条件で成績を計算できた銘柄の数。公開当日の銘柄と、まだ期間がたっていない銘柄は入りません。',''],
    n_win:['勝率','成績がプラスで終わった銘柄の割合。',''],
    n_avg:['平均リターン','各銘柄の成績の単純平均。大きく上がった1銘柄に引っ張られやすい数字です。',''],
    n_med:['中央値','成績を順に並べたときの真ん中の銘柄の値。一部の大当たりに引っ張られにくい数字です。',''],
    n_exavg:['指数との差（平均）','銘柄ごとの「指数との差」の平均。プラスなら、平均して指数に勝っています。',''],
    n_beat:['指数に勝った割合','指数との差がプラスだった銘柄の割合。',''],
    n_band:['急成長スコアの区分ごとの成績','掲載時の急成長スコアで分けた成績。点数が高いほど成績が良ければ、点数が役に立っている証拠です。','10件未満の区分は、偶然の影響が大きいため「参考値」。'],
    n_scatter:['急成長スコアとリターン','1つの点が1銘柄。右に行くほど点数が高く、上に行くほど成績が良い銘柄です。',''],
  };

  /* ---------- どの項目名に付けるか(文字が一致したら) ---------- */
  const COMMON=[
    ['RS','rs'],['52週高値','hi52'],['52週高値から','hi52'],['資金急増率%','surge'],['資金急増率','surge'],['急増率','surge'],['売買代金の急増率','surge'],
    ['トレンド','trend'],['バリュエーション','v_head'],['株価が織り込む成長率','v_ig'],['織り込み成長','v_ig'],['実績3年（直近1年）','v_g3'],['実績3年','v_g3'],
    ['直近1年','v_g1'],['差','v_gap'],['判定','v_label'],['過去5年PERの位置','v_pos'],['PER位置','v_pos'],['PEG（実績）','v_peg'],['PEG','v_peg'],['週間%','w1'],['直近60日','spark'],[/^今月（/,'month'],['1か月前','ago'],
  ];
  const BYPAGE={
    index:[['本日の地合い','jiai'],[/^本日の地合い/,'jiai'],[/^新高値が新安値を上回る/,'m_hl'],[/日線より上の銘柄が50%以上/,'m_ma'],[/^直近10日の値上がり/,'m_ad'],
      ['強い業種・弱い業種','sec_strong'],['市場健全度カレンダー','cal'],['市場全体の売買代金','br_turn'],[/^売り抜け日/,'dist'],['世界のお金の流れ','world'],
      ['クロスアセット・パフォーマンス','cross'],['資金移動の比率','ratio'],[/^クロスアセット/,'cross'],[/^売買代金の推移/,'th_chart'],[/^売買代金（/,'turnover'],[/^出来高（/,'vol'],[/^時価総額（/,'mcap'],['資金が流入しているテーマ','inflow'],['売買代金の推移','th_chart'],['資金の初動ランキング','shoki'],
      ['資金ローテーションマップ','rotation'],['売買代金ランキング','rk'],['順位の推移','rkpath'],['代金÷時価','turnmcap'],['株価20日','px20'],['売買代金','turnover'],
      ['20日の騰落','r20'],['売買代金の順位','rkno'],['時価総額','mcap'],
      ['優先度','prio'],['Buy','buy'],['VCP','vcp'],['ピボット','pivot'],['継続','streak'],['最近の掲載','recent'],['上場','listing']],
    sectors:[['ETF','repetf'],['現在値','price_sec']],
    themes:[['現在値','price_th']],
    research:[['バリュエーション','v_fil'],['RS','rs_all'],['業種','f_sec'],['テーマ','f_th'],['条件を追加','f_cond'],['よく使う条件','f_preset'],['出来高倍率','volx'],[/^ADR%/,'adr'],
      ['50日線から','ma50x'],['200日線から','ma200x'],['21日EMAから','ema21x'],['トレンドの内訳','trend_mix'],[/^売買代金（20日平均/,'turnover'],['売買代金','turnover'],['時価総額','mcap'],['1か月','ago'],['3か月','ago'],['6か月','ago']],
    note:[['急成長スコア','n_score'],['必須条件','n_must'],['状態ラベル','n_label'],['掲載時の株価','n_entry'],['騰落','n_ret'],['指数との差','n_ex'],
      ['選んだ期間・売り方','n_sel'],['最大上昇','n_mfe'],['最大下落','n_mae'],['経過','n_days'],['今のトレンド','n_trend'],
      ['期間','n_hz'],['売り方','n_rule'],['比べる指数','n_bm'],['配当','n_div'],
      ['集計した銘柄','n_cnt'],['勝率','n_win'],['平均リターン','n_avg'],['中央値','n_med'],['指数との差（平均）','n_exavg'],['指数に勝った割合','n_beat'],
      ['急成長スコアの区分ごとの成績','n_band'],['急成長スコアとリターン','n_scatter']],
  };
  /* ページの見出し → 「このツールの見方」 */
  const GUIDE={index:[['市場概況','g_market'],['テーマ別資金フロー','g_themes'],['銘柄を探す','g_stocks'],['スクリーニング','g_screen']],
    sectors:[['セクター状況','g_sectors']],themes:[['業種状況','g_themetool']],research:[['業種銘柄リサーチ','g_research']],note:[['note紹介記事検証','g_note']]};
  const RULES=[...(BYPAGE[PAGE]||[]),...COMMON];
  /* 付ける場所(見出し・列名・ラベル)。統計の小さな表(table.st)は列名が何度も出るので付けない */
  const SEL='h3,th,.ctl-label,.flabel,.meter small,.kv small,.kpi small,.v-top .meta,.legend span,.sc-val .vt,.sc-val .vgrid small';
  const SKIP='table.st,.hq,.hq-tip,button,.seg,.ms-pop';

  /* ---------- 見た目 ---------- */
  const css=`.hq{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;box-sizing:border-box;border-radius:50%;border:1px solid var(--line-strong,#c9cfcd);
      color:var(--muted,#6b7573);font:600 10px/1 var(--f-num,system-ui);margin-left:4px;cursor:help;vertical-align:1px;flex:none;user-select:none;text-transform:none;letter-spacing:0}
    .hq:hover,.hq.on,.hq:focus-visible{border-color:var(--brand,#0e6b62);color:var(--brand,#0e6b62);outline:none}
    .hq-guide{display:inline-flex;align-items:center;gap:4px;margin-left:10px;padding:2px 9px;border-radius:999px;border:1px solid var(--line-strong,#c9cfcd);
      font:500 11px var(--f-body,system-ui);color:var(--muted,#6b7573);cursor:help;vertical-align:3px;letter-spacing:0;white-space:nowrap;background:var(--surface,#fff)}
    .hq-guide:hover,.hq-guide.on,.hq-guide:focus-visible{border-color:var(--brand,#0e6b62);color:var(--brand,#0e6b62);outline:none}
    .hq-guide .hq{margin:0;width:13px;height:13px;font-size:9px;border-color:currentColor;color:inherit}
    .hq-tip{position:fixed;z-index:200;width:min(290px,calc(100vw - 24px));background:var(--surface,#fff);border:1px solid var(--line-strong,#c9cfcd);border-radius:10px;
      box-shadow:0 10px 28px rgba(10,40,40,.16);padding:10px 12px;font:400 12px/1.65 var(--f-body,system-ui);color:var(--ink,#132322);text-align:left;white-space:normal;letter-spacing:0;text-transform:none}
    .hq-tip b{display:block;font-size:13px;font-weight:700;margin-bottom:3px}
    .hq-tip .ex{margin-top:7px;padding-top:7px;border-top:1px solid var(--line,#e3e7e6);color:var(--muted,#6b7573);font-size:11.5px}
    .hq-tip.g{width:min(340px,calc(100vw - 24px))}
    .hq-tip.g .st{display:block;margin:2px 0}`;
  const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

  /* ---------- ふきだし ---------- */
  let tip=null,cur=null,pinned=false;
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  function show(el){const d=DICT[el.dataset.hk];if(!d)return;hide();cur=el;el.classList.add('on');
    tip=document.createElement('div');tip.className='hq-tip'+(el.classList.contains('hq-guide')?' g':'');tip.setAttribute('role','tooltip');
    const body=el.classList.contains('hq-guide')?d[1].split(/\s*(?=\d\.\s)/).map(x=>`<span class="st">${esc(x)}</span>`).join(''):esc(d[1]);
    tip.innerHTML=`<b>${esc(d[0])}</b>${body}${d[2]?`<div class="ex">${esc(d[2])}</div>`:''}`;document.body.appendChild(tip);
    const r=el.getBoundingClientRect(),w=tip.offsetWidth,h=tip.offsetHeight,vw=innerWidth,vh=innerHeight;
    let x=Math.min(Math.max(8,r.left-12),vw-w-8),y=r.bottom+8;if(y+h>vh-8&&r.top-h-8>8)y=r.top-h-8;
    tip.style.left=x+'px';tip.style.top=y+'px';}
  function hide(){if(tip){tip.remove();tip=null;}if(cur){cur.classList.remove('on');cur=null;}pinned=false;}
  function bind(el){el.tabIndex=0;el.setAttribute('role','button');el.setAttribute('aria-label',(DICT[el.dataset.hk]||[''])[0]+'の説明');
    el.addEventListener('mouseenter',()=>{if(!pinned)show(el);});
    el.addEventListener('mouseleave',()=>{if(!pinned)hide();});
    el.addEventListener('focus',()=>show(el));el.addEventListener('blur',()=>{if(!pinned)hide();});
    el.addEventListener('click',e=>{e.stopPropagation();e.preventDefault();if(cur===el&&pinned){hide();return;}show(el);pinned=true;});}
  document.addEventListener('click',()=>hide());
  addEventListener('scroll',()=>{if(!pinned)hide();},true);
  addEventListener('keydown',e=>{if(e.key==='Escape')hide();});

  /* ---------- 付ける ---------- */
  const norm=s=>s.replace(/[▲▼]/g,'').replace(/\s+/g,' ').trim();
  function keyFor(t){for(const [m,k] of RULES){if(typeof m==='string'?t===m:m.test(t))return k;}return null;}
  function firstText(el){for(const n of el.childNodes){if(n.nodeType===3&&n.textContent.trim())return n;if(n.nodeType===1&&!n.matches('.ar,.hq'))return null;}return null;}
  function icon(k){const s=document.createElement('span');s.className='hq';s.textContent='?';s.dataset.hk=k;bind(s);return s;}
  function scan(){
    document.querySelectorAll(SEL).forEach(el=>{if(el.dataset.hqDone===el.textContent||el.closest(SKIP))return;
      const n=firstText(el);if(!n){el.dataset.hqDone=el.textContent;return;}
      const k=keyFor(norm(n.textContent));
      if(k&&!el.querySelector(':scope > .hq')){n.after(icon(k));}
      el.dataset.hqDone=el.textContent;});
    (GUIDE[PAGE]||[]).forEach(([t,k])=>{document.querySelectorAll('h2').forEach(h=>{if(h.querySelector('.hq-guide'))return;const n=firstText(h);if(!n||norm(n.textContent)!==t)return;
      const b=document.createElement('span');b.className='hq-guide';b.dataset.hk=k;b.innerHTML='<span class="hq" aria-hidden="true">?</span>このツールの見方';bind(b);
      const tg=h.querySelector('.tagline');(tg||h.lastChild).after?(tg?tg.after(b):h.appendChild(b)):h.appendChild(b);});});
  }
  let t0=null;const later=()=>{clearTimeout(t0);t0=setTimeout(scan,60);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scan);else scan();
  new MutationObserver(m=>{if(m.some(x=>[...x.addedNodes].some(n=>n.nodeType===1&&!n.classList.contains('hq')&&!n.classList.contains('hq-tip'))))later();})
    .observe(document.body,{childList:true,subtree:true});
  window.SiteHelp={DICT,scan};
})();
