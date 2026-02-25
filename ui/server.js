import express from "express";

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true })); // <-- enable HTML form posts
app.use(express.static("public"));

function apiBase() {
  return process.env.NEXT_PUBLIC_API_BASE || "http://api:7777";
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

app.get("/library", async (_req, res) => {
  const API = apiBase();
  try {
    const r = await fetch(`${API}/v1/library`);
    const j = await r.json();

    const rows = Array.isArray(j.rows) ? j.rows : [];
    const htmlRows = rows
      .map(
        (x) => `
<tr>
  <td style="padding:6px 8px;border-bottom:1px solid #eee;"><code>${esc(x.pattern_id)}</code></td>
  <td style="padding:6px 8px;border-bottom:1px solid #eee;">${esc(x.status)}</td>
  <td style="padding:6px 8px;border-bottom:1px solid #eee;">${esc(x.last_updated)}</td>
</tr>`
      )
      .join("");

    res.setHeader("content-type", "text/html; charset=utf-8");
    res.end(`<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Mythiq Library</title>
</head>
<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:20px;">
  <h2 style="margin:0 0 12px 0;">Pattern Library</h2>
  <div style="margin:0 0 12px 0;color:#444;">API: <code>${esc(API)}</code></div>

  <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;">
    <div style="flex:1;min-width:360px;">
      <table style="width:100%;border-collapse:collapse;border:1px solid #ddd;">
        <thead>
          <tr>
            <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd;">pattern_id</th>
            <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd;">status</th>
            <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd;">last_updated</th>
          </tr>
        </thead>
        <tbody>
          ${htmlRows || `<tr><td colspan="3" style="padding:10px;">No patterns yet.</td></tr>`}
        </tbody>
      </table>
    </div>

    <div style="width:420px;max-width:100%;border:1px solid #ddd;padding:12px;border-radius:8px;">
      <div style="font-weight:700;margin-bottom:8px;">Run (logs pattern + signals)</div>
      <form method="POST" action="/library/run">
        <div style="display:flex;flex-direction:column;gap:8px;">
          <label>pattern_id <input name="pattern_id" value="loop_v1" style="width:100%;padding:8px;"></label>
          <label>prompt <textarea name="prompt" rows="4" style="width:100%;padding:8px;">Give 3 ideas for a tiny arcade loop.</textarea></label>
          <label>user_rating (1..5) <input name="user_rating" value="5" style="width:100%;padding:8px;"></label>
          <label>implicit_score (0..1) <input name="implicit_score" value="0.8" style="width:100%;padding:8px;"></label>
          <label>ab_winner (0/1) <input name="ab_winner" value="1" style="width:100%;padding:8px;"></label>
          <button type="submit" style="padding:10px;font-weight:700;">Run</button>
        </div>
      </form>
      <div style="margin-top:10px;font-size:12px;color:#555;">
        Submits to <code>${esc(API)}/v1/run</code>, then returns here.
      </div>
    </div>
  </div>

  <div style="margin-top:14px;">
    <a href="/" style="color:#06c;">Home</a>
  </div>
</body>
</html>`);
  } catch (e) {
    res.status(500).type("text/plain").send(String(e));
  }
});

app.post("/library/run", async (req, res) => {
  const API = apiBase();
  try {
    const body = {
      feature: "text",
      prompt: req.body?.prompt || "",
      pattern_id: req.body?.pattern_id || null,
      user_rating: req.body?.user_rating ? Number(req.body.user_rating) : null,
      implicit_score: req.body?.implicit_score ? Number(req.body.implicit_score) : null,
      ab_winner: req.body?.ab_winner ? Number(req.body.ab_winner) : null,
    };

    await fetch(`${API}/v1/run`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

    res.redirect(302, "/library");
  } catch (e) {
    res.status(500).type("text/plain").send(String(e));
  }
});



// ---- API proxy helpers (browser -> UI -> API) ----
app.post("/chat", async (req, res) => {
  const API = apiBase();
  try {
    const payload = {
      prompt: req.body?.prompt ?? "",
      temperature: req.body?.temperature ?? 0.2,
      max_tokens: req.body?.max_tokens ?? 256,
    };
    const r = await fetch(`${API}/v1/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    res.json(j);
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.get("/status", async (_req, res) => {
  const API = apiBase();
  try {
    const r = await fetch(`${API}/v1/status`);
    const j = await r.json();
    res.json(j);
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.get("/metrics", async (req, res) => {
  const API = apiBase();
  const n = Number(req.query?.n ?? 50);
  try {
    const r = await fetch(`${API}/v1/metrics/tail?n=${encodeURIComponent(String(n))}`);
    const j = await r.json();
    res.json(j);
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.post("/warmup", async (_req, res) => {
  const API = apiBase();
  try {
    const r = await fetch(`${API}/v1/warmup`, { method: "POST" });
    const j = await r.json();
    res.json(j);
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.listen(3000, () => console.log("UI on http://127.0.0.1:3000"));
