import { spawnSync } from "child_process";
import fs from "fs";
import path from "path";

function sh(cmd, args) {
  const r = spawnSync(cmd, args, { stdio: "inherit" });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

const prompt = process.argv.slice(2).join(" ").trim() || "topdown shooter waves coins juice";

// Variant A: current generator (shooter)
sh("node", ["tools/ai_game_build.mjs", prompt]);

// Snapshot variant A outputs
fs.mkdirSync("variants/A", { recursive: true });
for (const f of ["src/game.js", "src/MainScene.js"]) {
  if (fs.existsSync(f)) fs.copyFileSync(f, path.join("variants/A", path.basename(f)));
}

// Variant B: simple mutation (faster spawn + different colors) by patching MainScene.js after generation
// (Still library-first; this is an example of deterministic variant creation.)
let s = fs.readFileSync("src/MainScene.js", "utf-8");
s = s.replace('this.cameras.main.setBackgroundColor("#0b0f1a");', 'this.cameras.main.setBackgroundColor("#120b1a");');
s = s.replace("delay: 1600", "delay: 1200");
fs.writeFileSync("src/MainScene.js", s, "utf-8");

// Snapshot variant B outputs
fs.mkdirSync("variants/B", { recursive: true });
for (const f of ["src/game.js", "src/MainScene.js"]) {
  if (fs.existsSync(f)) fs.copyFileSync(f, path.join("variants/B", path.basename(f)));
}

console.log(JSON.stringify({ ok: true, prompt, variants: ["A","B"] }, null, 2));
