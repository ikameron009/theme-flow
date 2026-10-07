// テーマ別資金フロー: 公開サイトの入口。静的ファイルはそのまま返す。
// /api/journal/* = 本人専用の売買記録(保存先 D1: trade-journal)。パスワードは Worker の秘密の値 JOURNAL_PASSWORD
//   (登録: cd site_worker && npx wrangler@4 secret put JOURNAL_PASSWORD)。ログインすると署名つき Cookie を30日渡す。
// ③C で /pro/* の会員確認(Cookie)もここに追加する。

const COOKIE = "jr_s";
const DAYS = 30;
const enc = new TextEncoder();

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
// 長さの違いも時間差も出さない比較
function same(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function cookieOf(req, name) {
  const m = (req.headers.get("Cookie") || "").match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return m ? m[1] : null;
}
async function signedIn(req, env) {
  if (!env.JOURNAL_PASSWORD) return false;
  const v = cookieOf(req, COOKIE);
  if (!v) return false;
  const [exp, sig] = v.split(".");
  if (!exp || !sig || Number(exp) < Date.now() / 1000) return false;
  return same(sig, await hmac(env.JOURNAL_PASSWORD, "jr1." + exp));
}
const json = (obj, status = 200, headers = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers } });

function rowOut(r) {
  return { id: r.id, done: !!r.done, created_at: r.created_at, updated_at: r.updated_at, ...JSON.parse(r.data) };
}
// 1件の記録(建玉)として保存してよい形か。中身はページ側の項目をそのまま JSON で持つ
function clean(body) {
  if (!body || typeof body !== "object") return null;
  const { id, created_at, updated_at, ...data } = body;
  if (!data.code || !Array.isArray(data.fills) || !data.fills.length) return null;
  const s = JSON.stringify(data);
  return s.length > 100000 ? null : { data: s, done: data.done ? 1 : 0 };
}

async function journal(req, env, path) {
  const method = req.method;
  if (path === "/api/journal/login" && method === "POST") {
    if (!env.JOURNAL_PASSWORD) return json({ error: "パスワードがまだ登録されていません" }, 503);
    let pw = "";
    try { pw = String((await req.json()).password || ""); } catch (e) {}
    const ok = same(await hmac(env.JOURNAL_PASSWORD, "pw:" + pw), await hmac(env.JOURNAL_PASSWORD, "pw:" + env.JOURNAL_PASSWORD));
    if (!ok) {
      await new Promise((r) => setTimeout(r, 1200)); // 総当たりを遅らせる
      return json({ error: "パスワードが違います" }, 401);
    }
    const exp = Math.floor(Date.now() / 1000) + DAYS * 86400;
    const v = exp + "." + (await hmac(env.JOURNAL_PASSWORD, "jr1." + exp));
    return json({ ok: true }, 200, { "set-cookie": `${COOKIE}=${v}; Path=/; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Strict` });
  }
  if (path === "/api/journal/logout" && method === "POST")
    return json({ ok: true }, 200, { "set-cookie": `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict` });

  if (!(await signedIn(req, env))) return json({ error: "ログインしてください" }, 401);
  // 書き込みは同じサイトからだけ(他サイトからの送信を断る)
  if (method !== "GET") {
    const origin = req.headers.get("Origin");
    if (origin && origin !== new URL(req.url).origin) return json({ error: "forbidden" }, 403);
  }
  const db = env.JOURNAL_DB;
  if (path === "/api/journal/me") return json({ ok: true });
  if (path === "/api/journal/positions" && method === "GET") {
    const { results } = await db.prepare("SELECT * FROM positions ORDER BY id").all();
    return json({ positions: results.map(rowOut) });
  }
  if (path === "/api/journal/positions" && method === "POST") {
    const c = clean(await req.json().catch(() => null));
    if (!c) return json({ error: "記録の形が正しくありません" }, 400);
    const now = new Date().toISOString();
    const r = await db.prepare("INSERT INTO positions (data, done, created_at, updated_at) VALUES (?, ?, ?, ?) RETURNING *").bind(c.data, c.done, now, now).first();
    return json({ position: rowOut(r) }, 201);
  }
  const m = path.match(/^\/api\/journal\/positions\/(\d+)$/);
  if (m && method === "PUT") {
    const c = clean(await req.json().catch(() => null));
    if (!c) return json({ error: "記録の形が正しくありません" }, 400);
    const r = await db.prepare("UPDATE positions SET data = ?, done = ?, updated_at = ? WHERE id = ? RETURNING *").bind(c.data, c.done, new Date().toISOString(), Number(m[1])).first();
    return r ? json({ position: rowOut(r) }) : json({ error: "見つかりません" }, 404);
  }
  if (m && method === "DELETE") {
    await db.prepare("DELETE FROM positions WHERE id = ?").bind(Number(m[1])).run();
    return json({ ok: true });
  }
  return json({ error: "not found" }, 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/journal/")) {
      try {
        return await journal(request, env, url.pathname);
      } catch (e) {
        return json({ error: "サーバーで問題が起きました" }, 500);
      }
    }
    return env.ASSETS.fetch(request);
  },
};
