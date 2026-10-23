// One-time local login: opens Google's consent page, catches the code on localhost, and saves the
// refresh token straight into the repo secret YT_REFRESH_TOKEN (never printed).
// Usage: node tools/yt_login.js <client_secret.json>
const http = require("http"), fs = require("fs"), { execSync, spawnSync } = require("child_process");
const c = JSON.parse(fs.readFileSync(process.argv[2], "utf8")).installed;
const PORT = 8765, redirect = `http://localhost:${PORT}`;
const url = "https://accounts.google.com/o/oauth2/v2/auth?" + new URLSearchParams({
  client_id: c.client_id, redirect_uri: redirect, response_type: "code", access_type: "offline", prompt: "consent",
  scope: "https://www.googleapis.com/auth/youtube.upload" });
http.createServer(async (req, res) => {
  const code = new URL(req.url, redirect).searchParams.get("code");
  if (!code) { res.end("Waiting..."); return; }
  const r = await fetch(c.token_uri, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ code, client_id: c.client_id, client_secret: c.client_secret, redirect_uri: redirect, grant_type: "authorization_code" }) });
  const j = await r.json();
  if (!j.refresh_token) { res.end("No refresh token: " + (j.error || "unknown")); console.log("failed", j.error); process.exit(1); }
  const s = spawnSync("gh", ["secret", "set", "YT_REFRESH_TOKEN", "-R", "maskpocket/money-explainers"], { input: j.refresh_token, encoding: "utf8" });
  res.end(s.status === 0 ? "Done. You can close this tab." : "Could not save the secret.");
  console.log(s.status === 0 ? "YT_REFRESH_TOKEN saved" : "gh failed: " + s.stderr);
  process.exit(0);
}).listen(PORT, () => { console.log("Opening browser..."); execSync(`start "" "${url}"`, { shell: "cmd.exe" }); });
