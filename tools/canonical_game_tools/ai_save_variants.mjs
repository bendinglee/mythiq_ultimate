import fs from "fs";
import path from "path";
import { spawnSync } from "child_process";

function _latestDreamRunJson(){
  const dir = "/Users/bendingle/dream_ai_core/runs";
  try {
    const files = fs.readdirSync(dir)
      .filter(f => f.endsWith(".json"))
      .map(f => ({ f, t: fs.statSync(dir + "/" + f).mtimeMs }))
      .sort((a,b) => b.t - a.t);
    return files[0] ? (dir + "/" + files[0].f) : null;
  } catch (e) {
    return null;
  }
}

function _pickWinnerFromStdout(){
  const runJson = _latestDreamRunJson();
  if (!runJson) return { ok:false, error:"no dream_ai_core runs found" };

  // Call the local picker. It reads stdout from AI_STDOUT_FILE and prints {ok,winner,reason}.
  const res = spawnSync(
    "node",
    ["tools/ai_auto_pick.mjs"],
    {
      env: { ...process.env, AI_STDOUT_FILE: runJson },
      encoding: "utf-8"
    }
  );

  const out = (res.stdout || "").trim();
  try { return JSON.parse(out); } catch { return { ok:false, error:"picker returned non-json", out }; }
}

const ROOT = process.cwd();
const prompt = process.argv.slice(2).join(" ").trim() || "topdown shooter waves coins juice";
const patternId = process.env.AI_PATTERN || "topdown_shooter_v1";

function ensureDir(p){ fs.mkdirSync(p, { recursive: true }); }

const base = path.join(ROOT, "libs/game/patterns", patternId);
ensureDir(base);

for (const v of ["A","B"]) {
  const srcDir = path.join(ROOT, "variants", v);
  const outDir = path.join(base, "variant_" + v);
  ensureDir(outDir);
  for (const f of ["game.js", "MainScene.js"]) {
    const inP = path.join(srcDir, f);
    if (fs.existsSync(inP)) fs.copyFileSync(inP, path.join(outDir, f));
  }
  fs.writeFileSync(path.join(outDir, "meta.json"), JSON.stringify({
    pattern: patternId,
    variant: v,
    prompt,
    saved_at: new Date().toISOString()
  }, null, 2));
}


const pick = _pickWinnerFromStdout();
const winner = (pick && pick.ok && (pick.winner==="A"||pick.winner==="B")) ? pick.winner : "A";
const reason = (pick && pick.ok && pick.reason) ? pick.reason : "picker failed; default A";
console.log(JSON.stringify({ ok: true, prompt, winner, reason }, null, 2));

