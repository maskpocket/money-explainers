// Fricomind TikTok bridge: keeps the TikTok client secret and tokens off the web page and out of GitHub.
// Secrets: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, ADMIN_KEY (shared with the GitHub workflow).
const SITE = "https://maskpocket.github.io";
const REDIRECT = SITE + "/money-explainers/callback.html";
const API = "https://open.tiktokapis.com";
const SCOPES = "user.info.basic,video.publish";

const cors = { "Access-Control-Allow-Origin": SITE, "Access-Control-Allow-Headers": "authorization,content-type,x-title,x-privacy,x-flags", "Access-Control-Allow-Methods": "GET,POST,OPTIONS" };
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { ...cors, "content-type": "application/json" } });

async function tt(path, token, body) {
  const r = await fetch(API + path, { method: body ? "POST" : "GET", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json; charset=UTF-8" }, body: body ? JSON.stringify(body) : undefined });
  return r.json();
}

async function tokenCall(env, params) {
  const r = await fetch(API + "/v2/oauth/token/", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_key: env.TIKTOK_CLIENT_KEY, client_secret: env.TIKTOK_CLIENT_SECRET, ...params }) });
  return r.json();
}

async function saveTokens(env, t) {
  const rec = { access: t.access_token, refresh: t.refresh_token, exp: Date.now() + (t.expires_in - 300) * 1000 };
  await env.TOKENS.put("acct:" + t.open_id, JSON.stringify(rec));
  return rec;
}

async function accessFor(env, openId) {
  const rec = JSON.parse((await env.TOKENS.get("acct:" + openId)) || "null");
  if (!rec) return null;
  if (Date.now() < rec.exp) return rec.access;
  const t = await tokenCall(env, { grant_type: "refresh_token", refresh_token: rec.refresh });
  if (!t.access_token) return null;
  t.open_id = openId;
  return (await saveTokens(env, t)).access;
}

async function publish(env, openId, video, opts) {
  const token = await accessFor(env, openId);
  if (!token) return { error: "not connected" };
  const info = await tt("/v2/post/publish/creator_info/query/", token, {});
  const levels = info.data?.privacy_level_options || [];
  const privacy = levels.includes(opts.privacy) ? opts.privacy : levels[levels.length - 1] || "SELF_ONLY";
  const size = video.byteLength;
  const init = await tt("/v2/post/publish/video/init/", token, {
    post_info: { title: (opts.title || "").slice(0, 2200), privacy_level: privacy, disable_comment: !!opts.noComment, disable_duet: !!opts.noDuet, disable_stitch: !!opts.noStitch, is_aigc: true },
    source_info: { source: "FILE_UPLOAD", video_size: size, chunk_size: size, total_chunk_count: 1 },
  });
  if (!init.data?.upload_url) return { error: "init failed", detail: init };
  const up = await fetch(init.data.upload_url, { method: "PUT", body: video,
    headers: { "Content-Type": "video/mp4", "Content-Length": String(size), "Content-Range": `bytes 0-${size - 1}/${size}` } });
  if (!up.ok) return { error: "upload failed", status: up.status, detail: (await up.text()).slice(0, 300) };
  return { ok: true, publish_id: init.data.publish_id, privacy };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    const auth = (req.headers.get("authorization") || "").replace("Bearer ", "");

    if (url.pathname === "/api/config") return json({ client_key: env.TIKTOK_CLIENT_KEY, redirect: REDIRECT, scope: SCOPES });

    if (url.pathname === "/api/callback" && req.method === "POST") {
      const { code } = await req.json();
      const t = await tokenCall(env, { code, grant_type: "authorization_code", redirect_uri: REDIRECT });
      if (!t.access_token) return json({ error: t.error_description || "token exchange failed" }, 400);
      await saveTokens(env, t);
      const session = crypto.randomUUID();
      await env.TOKENS.put("sess:" + session, t.open_id, { expirationTtl: 3600 });
      const u = await tt("/v2/user/info/?fields=open_id,display_name,avatar_url", t.access_token);
      return json({ session, user: u.data?.user || {} });
    }

    if (url.pathname === "/api/creator") {
      const openId = await env.TOKENS.get("sess:" + auth);
      const token = openId && (await accessFor(env, openId));
      if (!token) return json({ error: "not connected" }, 401);
      return json((await tt("/v2/post/publish/creator_info/query/", token, {})).data || {});
    }

    if (url.pathname === "/api/publish" && req.method === "POST") {
      const flags = (req.headers.get("x-flags") || "").split(",");
      const opts = { title: decodeURIComponent(req.headers.get("x-title") || ""), privacy: req.headers.get("x-privacy"),
        noComment: flags.includes("nocomment"), noDuet: flags.includes("noduet"), noStitch: flags.includes("nostitch") };
      let openId = await env.TOKENS.get("sess:" + auth);
      // automation: admin key posts to the connected owner account
      if (!openId && auth && auth === env.ADMIN_KEY) openId = await env.TOKENS.get("owner");
      if (!openId) return json({ error: "not connected" }, 401);
      const res = await publish(env, openId, await req.arrayBuffer(), opts);
      return json(res, res.ok ? 200 : 502);
    }

    if (url.pathname === "/api/status" && req.method === "POST") {
      const openId = (await env.TOKENS.get("sess:" + auth)) || (auth === env.ADMIN_KEY ? await env.TOKENS.get("owner") : null);
      const token = openId && (await accessFor(env, openId));
      if (!token) return json({ error: "not connected" }, 401);
      const { publish_id } = await req.json();
      return json((await tt("/v2/post/publish/status/fetch/", token, { publish_id })).data || {});
    }

    // one-time: mark the connected account as the automation owner (needs the admin key)
    if (url.pathname === "/api/owner" && req.method === "POST") {
      if (!auth || auth !== env.ADMIN_KEY) return json({ error: "forbidden" }, 403);
      const { session } = await req.json();
      const openId = await env.TOKENS.get("sess:" + session);
      if (!openId) return json({ error: "no such session" }, 400);
      await env.TOKENS.put("owner", openId);
      return json({ ok: true });
    }
    return json({ error: "not found" }, 404);
  },
};
