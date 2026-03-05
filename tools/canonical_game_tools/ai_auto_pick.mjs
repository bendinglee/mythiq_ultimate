import fs from "fs";
import path from "path";

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function num(x) {
  if (typeof x === "number") return Number.isFinite(x) ? x : null;
  if (x == null) return null;
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

function getScore(r) {
  if (!r) return null;
  const v = (r.score !== undefined) ? r.score : (r.metrics && r.metrics.score);
  return num(v);
}

function okBool(v) {
  if (v === undefined) return true;
  return v === true;
}

function isPassing(r) {
  if (!r) return false;
  return okBool(r.buildOk) && okBool(r.runtimeOk) && okBool(r.parsedMetrics);
}

// Extract JSON objects printed in stdout.
// We only care about objects that include: { ok:true, variant:"A"/"B", score:... }
function extractVariantObjects(stdout) {
  const out = { A: null, B: null };

  // Heuristic: scan lines and try to JSON-parse blocks that start with "{" and end with "}"
  // Works with the pretty-printed blocks in your stdout.
  const lines = stdout.split("\n");
  let buf = [];
  let depth = 0;

  function flush() {
    if (!buf.length) return;
    const txt = buf.join("\n");
    buf = [];
    try {
      const obj = JSON.parse(txt);
      if (obj && obj.ok === true && (obj.variant === "A" || obj.variant === "B")) {
        out[obj.variant] = obj;
      }
    } catch (_) {
      // ignore non-json blocks
    }
  }

  for (const line of lines) {
    const t = line.trim();

    // Start of a JSON object block
    if (depth === 0 && t.startsWith("{")) {
      buf = [line];
      depth = (t.match(/\{/g) || []).length - (t.match(/\}/g) || []).length;
      if (depth === 0 && t.endsWith("}")) flush();
      continue;
    }

    if (depth > 0) {
      buf.push(line);
      depth += (line.match(/\{/g) || []).length - (line.match(/\}/g) || []).length;
      if (depth === 0) flush();
    }
  }

  return out;
}

function pickWinner(A, B) {
  const aPass = isPassing(A);
  const bPass = isPassing(B);
  const aScore = getScore(A);
  const bScore = getScore(B);

  let winner = "A";
  let reason = "default";

  if (aPass || bPass) {
    if (aPass && bPass) {
      if (aScore != null && bScore != null) {
        winner = (bScore > aScore) ? "B" : "A";
        reason = `both passing; picked by score A=${aScore.toFixed(2)} B=${bScore.toFixed(2)}`;
      } else {
        winner = "A";
        reason = "both passing; missing score; default A";
      }
    } else if (bPass) {
      winner = "B";
      reason = "B passing; A not passing";
    } else {
      winner = "A";
      reason = "A passing; B not passing";
    }
  } else {
    if (aScore != null && bScore != null) {
      winner = (bScore > aScore) ? "B" : "A";
      reason = `no passing runs; picked by score A=${aScore.toFixed(2)} B=${bScore.toFixed(2)}`;
    } else if (bScore != null) {
      winner = "B";
      reason = `no passing runs; picked by score B=${bScore.toFixed(2)}`;
    } else if (aScore != null) {
      winner = "A";
      reason = `no passing runs; picked by score A=${aScore.toFixed(2)}`;
    } else {
      winner = "A";
      reason = "no passing runs found; default A";
    }
  }

  return { winner, reason };
}

function main() {
  // Provide one of:
  // - AI_STDOUT_FILE=/abs/path/to/runs/<run_id>.json   (dream_ai_core run json)
  // - AI_STDOUT=/path/to/stdout.txt (raw stdout)
  // - otherwise: try to read ../dream_ai_core/runs latest (relative to this repo)
  const stdoutFile = process.env.AI_STDOUT_FILE || "";
  const rawStdoutPath = process.env.AI_STDOUT || "";

  let stdout = "";

  if (stdoutFile) {
    const d = readJson(stdoutFile);
    stdout = d.stdout || "";
  } else if (rawStdoutPath) {
    stdout = fs.readFileSync(rawStdoutPath, "utf-8");
  } else {
    // try to find latest dream_ai_core runs relative to this output repo:
    // /Users/bendingle/mythiq_10x/games/output/<id>  ->  /Users/bendingle/dream_ai_core/runs
    const guessRuns = path.resolve("/Users/bendingle/dream_ai_core/runs");
    if (!fs.existsSync(guessRuns)) {
      console.log(JSON.stringify({ ok: false, error: "set AI_STDOUT_FILE or AI_STDOUT; could not find /Users/bendingle/dream_ai_core/runs" }, null, 2));
      process.exit(2);
    }
    const files = fs.readdirSync(guessRuns)
      .filter(f => f.endsWith(".json"))
      .map(f => path.join(guessRuns, f))
      .sort((a,b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);

    if (!files[0]) {
      console.log(JSON.stringify({ ok: false, error: "no run json files found in /Users/bendingle/dream_ai_core/runs" }, null, 2));
      process.exit(2);
    }
    const d = readJson(files[0]);
    stdout = d.stdout || "";
  }

  const { A, B } = extractVariantObjects(stdout);

  if (!A || !B) {
    console.log(JSON.stringify({
      ok: false,
      error: "could not extract A/B variant objects from stdout",
      haveA: !!A,
      haveB: !!B
    }, null, 2));
    process.exit(2);
  }

  const { winner, reason } = pickWinner(A, B);
  console.log(JSON.stringify({ ok: true, winner, reason }, null, 2));
}

main();
