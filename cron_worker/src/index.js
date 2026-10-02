// theme-flow 定時起動 Worker
// GitHubの定時cronは数時間遅れる/飛ぶため、Cloudflareの Cron Triggers から
// workflow_dispatch を叩いて時刻どおりに起動する。GitHub側のcronは予備として残す
// (予備はWorker起動分が済んでいれば何もしない=各workflowのgateジョブ)。
//
// Secrets(ダッシュボード or `wrangler secret put`):
//   GH_TOKEN        fine-grained PAT。対象repo=theme-flow, vcp-screener / 権限=Actions: Read and write
//   NOTIFY_WEBHOOK  任意。Discord の Webhook URL。未設定なら通知はログのみ
//
// 時刻はすべてUTC(JST-9h)。UTC月-金 = JST火-土(金曜の結果は土曜朝。JST月曜朝はNYがまだ日曜で日付がずれるため)。

const OWNER = "ikameron009";
const TARGETS = [
  { repo: "theme-flow", workflow: "update.yml" },
  { repo: "vcp-screener", workflow: "screen.yml" },
];

// 時刻(UTC)と曜日 → 役割。Cloudflare無料枠の定時実行の登録数(5)を節約するため、cronは1本にまとめて時刻で振り分ける。
// JST = UTC+9。日本株=17:00 JST起動(当日の大引け後) / 米国株=7:00 JST起動(米国の引け後)。見張りは起動の1時間後と3時間後。
const WEEKDAY = [1, 2, 3, 4, 5];          // UTC月-金
const TUE_SAT = [2, 3, 4, 5, 6];
const PLAN = [
  { h: 8, days: WEEKDAY, kind: "dispatch", market: "jp" },             // 17:00 JST 日本株
  { h: 9, days: WEEKDAY, kind: "watch", market: "jp", sinceH: 2 },     // 18:00 JST 確認
  { h: 11, days: WEEKDAY, kind: "watch", market: "jp", sinceH: 4 },    // 20:00 JST 再確認
  { h: 22, days: WEEKDAY, kind: "dispatch", market: "us" },            // 07:00 JST 米国株+世界
  { h: 23, days: WEEKDAY, kind: "watch", market: "us", sinceH: 2 },    // 08:00 JST 確認
  { h: 1, days: TUE_SAT, kind: "watch", market: "us", sinceH: 4 },     // 10:00 JST 再確認
];

const gh = (env, path, init = {}) =>
  fetch(`https://api.github.com/repos/${OWNER}/${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "theme-flow-cron-worker",
      ...(init.headers || {}),
    },
  });

async function dispatch(env, t, market) {
  const r = await gh(env, `${t.repo}/actions/workflows/${t.workflow}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: "main", inputs: { market } }),
  });
  if (r.status !== 204) throw new Error(`${t.repo} dispatch ${market}: HTTP ${r.status} ${await r.text()}`);
}

// 直近 sinceH 時間の、この市場の手動起動ラン(run-name に [jp]/[us]/[both] を含む)
async function recentRuns(env, t, market, sinceH) {
  const since = new Date(Date.now() - sinceH * 3600e3).toISOString().slice(0, 19) + "Z";
  const r = await gh(
    env,
    `${t.repo}/actions/workflows/${t.workflow}/runs?event=workflow_dispatch&created=>=${since}&per_page=20`
  );
  if (!r.ok) throw new Error(`${t.repo} runs: HTTP ${r.status}`);
  const { workflow_runs = [] } = await r.json();
  return workflow_runs.filter((x) => new RegExp(`\\[(${market}|both)\\]`).test(x.display_title || x.name || ""));
}

async function notify(env, text) {
  console.log(text);
  if (!env.NOTIFY_WEBHOOK) return;
  await fetch(env.NOTIFY_WEBHOOK, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: text }),
  }).catch((e) => console.log("notify failed", e));
}

async function runDispatch(env, market) {
  const errs = [];
  for (const t of TARGETS) {
    try {
      await dispatch(env, t, market);
      console.log(`dispatched ${t.repo} ${market}`);
    } catch (e) {
      errs.push(String(e.message || e));
    }
  }
  if (errs.length) await notify(env, `⚠️ テーマ資金フロー: ${market} の起動に失敗\n${errs.join("\n")}`);
}

// 見張り: 成功していなければ1回だけ再起動して通知。実行中なら遅延として通知。
async function runWatch(env, market, sinceH) {
  const lines = [];
  for (const t of TARGETS) {
    try {
      const runs = await recentRuns(env, t, market, sinceH);
      const ok = runs.some((x) => x.conclusion === "success");
      const running = runs.some((x) => x.status !== "completed");
      if (ok) continue;
      if (running) {
        lines.push(`⏳ ${t.repo} ${market}: まだ実行中`);
      } else {
        await dispatch(env, t, market);
        const why = runs.length ? `前回=${runs[0].conclusion}` : "起動されていない";
        lines.push(`🔁 ${t.repo} ${market}: ${why} → 再実行しました`);
      }
    } catch (e) {
      lines.push(`⚠️ ${t.repo} ${market}: 確認失敗 ${e.message || e}`);
    }
  }
  if (lines.length) await notify(env, `テーマ資金フロー 見張り\n${lines.join("\n")}`);
}

export default {
  async scheduled(event, env, ctx) {
    const t = new Date(event.scheduledTime);
    const job = PLAN.find((p) => p.h === t.getUTCHours() && p.days.includes(t.getUTCDay()));
    if (!job) return console.log("no job at", t.toISOString());
    if (!env.GH_TOKEN) return notify(env, "⚠️ GH_TOKEN が未設定です");
    if (job.kind === "dispatch") ctx.waitUntil(runDispatch(env, job.market));
    else ctx.waitUntil(runWatch(env, job.market, job.sinceH));
  },

  // 動作確認用: GET /status で直近の状況を返す(起動はしない)
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname !== "/status") return new Response("theme-flow cron worker", { status: 200 });
    const out = {};
    for (const t of TARGETS)
      for (const m of ["jp", "us"]) {
        try {
          const runs = await recentRuns(env, t, m, 30);
          out[`${t.repo}:${m}`] = runs.slice(0, 3).map((x) => ({
            created: x.created_at, status: x.status, conclusion: x.conclusion,
          }));
        } catch (e) {
          out[`${t.repo}:${m}`] = String(e.message || e);
        }
      }
    return Response.json(out);
  },
};
