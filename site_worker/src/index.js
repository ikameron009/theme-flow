// テーマ別資金フロー: 公開サイトの入口。静的ファイルはそのまま返す。
// /api/journal/* = 本人専用の監視銘柄・売買記録(保存先 D1: trade-journal。表 positions=建玉、watchlist=監視銘柄、pnl_daily/pnl_monthly=損益カレンダー)。パスワードは Worker の秘密の値 JOURNAL_PASSWORD
//   (登録: cd site_worker && npx wrangler@4 secret put JOURNAL_PASSWORD)。ログインすると署名つき Cookie を30日渡す。
// ★いまはログインを省略中(wrangler.toml の [vars] JOURNAL_AUTH = "off")。戻すときは "on" にして push する。
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
const authOff = (env) => String(env.JOURNAL_AUTH || "on").toLowerCase() === "off";
async function signedIn(req, env) {
  if (authOff(env)) return true; // ログイン省略中
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
  if (path === "/api/journal/me") return json({ ok: true, auth: !authOff(env) });
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
  // 監視銘柄。POST は同じ銘柄(市場＋コード)があれば上書き(エントリー予定株価の変更もこれ)
  if (path === "/api/journal/watch" && method === "GET") {
    const { results } = await db.prepare("SELECT * FROM watchlist ORDER BY id").all();
    return json({ watch: results });
  }
  if (path === "/api/journal/watch" && method === "POST") {
    const b = await req.json().catch(() => null);
    const mk = b && (b.mk === "jp" || b.mk === "us") ? b.mk : null;
    const code = b && typeof b.code === "string" ? b.code.trim().slice(0, 16) : "";
    if (!mk || !code) return json({ error: "銘柄の形が正しくありません" }, 400);
    const name = String((b && b.name) || "").slice(0, 120);
    const e = b && b.entry != null && b.entry !== "" ? Number(b.entry) : null;
    const entry = e != null && isFinite(e) && e > 0 ? e : null;
    const now = new Date().toISOString();
    const r = await db
      .prepare("INSERT INTO watchlist (mk, code, name, entry, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (mk, code) DO UPDATE SET name = excluded.name, entry = excluded.entry, updated_at = excluded.updated_at RETURNING *")
      .bind(mk, code, name, entry, now, now)
      .first();
    return json({ item: r });
  }
  const w = path.match(/^\/api\/journal\/watch\/(\d+)$/);
  if (w && method === "DELETE") {
    await db.prepare("DELETE FROM watchlist WHERE id = ?").bind(Number(w[1])).run();
    return json({ ok: true });
  }
  // 損益カレンダー(tools/pnl.html)。GET=全部、POST=変更分をまとめて保存(v が null の行は削除)
  if (path === "/api/journal/pnl" && method === "GET") {
    const [d, m] = await Promise.all([db.prepare("SELECT d, v FROM pnl_daily").all(), db.prepare("SELECT ym, v, ack_s, ack_c FROM pnl_monthly").all()]);
    const daily = {}, monthly = {}, ack = {};
    d.results.forEach((r) => (daily[r.d] = r.v));
    m.results.forEach((r) => {
      monthly[r.ym] = r.v;
      if (r.ack_s != null && r.ack_c != null) ack[r.ym] = { s: r.ack_s, c: r.ack_c };
    });
    return json({ daily, monthly, ack });
  }
  if (path === "/api/journal/pnl" && method === "POST") {
    const b = await req.json().catch(() => null);
    const days = b && Array.isArray(b.days) ? b.days : [], months = b && Array.isArray(b.months) ? b.months : [];
    if (!days.length && !months.length) return json({ ok: true });
    if (days.length + months.length > 1000) return json({ error: "一度に保存できる件数を超えています" }, 400);
    const yen = (x) => (x == null ? null : Number.isInteger(x) && Math.abs(x) < 1e11 ? x : NaN);
    const now = new Date().toISOString(), st = [];
    for (const r of days) {
      const v = yen(r && r.v);
      if (!r || !/^20\d\d-\d\d-\d\d$/.test(r.d) || Number.isNaN(v)) return json({ error: "日の損益の形が正しくありません" }, 400);
      st.push(v == null ? db.prepare("DELETE FROM pnl_daily WHERE d = ?").bind(r.d)
        : db.prepare("INSERT INTO pnl_daily (d, v, updated_at) VALUES (?, ?, ?) ON CONFLICT (d) DO UPDATE SET v = excluded.v, updated_at = excluded.updated_at").bind(r.d, v, now));
    }
    for (const r of months) {
      const v = yen(r && r.v), a = r && r.ack && typeof r.ack === "object" ? r.ack : null;
      const as = a ? yen(a.s) : null, ac = a ? yen(a.c) : null;
      if (!r || !/^20\d\d-\d\d$/.test(r.ym) || Number.isNaN(v) || Number.isNaN(as) || Number.isNaN(ac)) return json({ error: "月の損益の形が正しくありません" }, 400);
      st.push(v == null ? db.prepare("DELETE FROM pnl_monthly WHERE ym = ?").bind(r.ym)
        : db.prepare("INSERT INTO pnl_monthly (ym, v, ack_s, ack_c, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT (ym) DO UPDATE SET v = excluded.v, ack_s = excluded.ack_s, ack_c = excluded.ack_c, updated_at = excluded.updated_at").bind(r.ym, v, as, ac, now));
    }
    await db.batch(st);
    return json({ ok: true, saved: st.length });
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
