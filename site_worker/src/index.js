// テーマ別資金フロー: 公開サイトの入口。いまは静的ファイルをそのまま返す。
// ③C で /pro/* の会員確認(Cookie)をここに追加する。
export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  },
};
