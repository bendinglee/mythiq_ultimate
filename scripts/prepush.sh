#!/usr/bin/env bash
set -x
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

# Ensure server is up for smokes; always stop on exit
"$ROOT/scripts/run_stable.sh" start >/dev/null
trap '"$ROOT/scripts/run_stable.sh" stop >/dev/null 2>&1 || true' EXIT

# Optional: quick sanity
curl -fsS "$BASE/readyz" >/dev/null

# Run existing smokes (keep whatever you already had; add AB smoke too)
if test -x "$ROOT/scripts/smoke_openapi.sh"; then
  "$ROOT/scripts/smoke_openapi.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_ab_patterns.sh"; then
  "$ROOT/scripts/smoke_ab_patterns.sh" >/dev/null
fi
if test -x "$ROOT/scripts/index_libs_qdrant.sh"; then
  if curl -fsS http://127.0.0.1:6333/collections >/dev/null 2>&1; then
    "$ROOT/scripts/index_libs_qdrant.sh"
  else
    echo "⚠️ skipping qdrant indexing: Qdrant not reachable on 127.0.0.1:6333"
  fi
fi
test -x "$ROOT/scripts/smoke_router.sh"
"$ROOT/scripts/smoke_router.sh"
if test -x "$ROOT/scripts/smoke_execute_core.sh"; then
  "$ROOT/scripts/smoke_execute_core.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_multimodal_core.sh"; then
  "$ROOT/scripts/smoke_multimodal_core.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_project_export.sh"; then
  "$ROOT/scripts/smoke_project_export.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_project_zip.sh"; then
  "$ROOT/scripts/smoke_project_zip.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_builder_plan.sh"; then
  "$ROOT/scripts/smoke_builder_plan.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_manifest_regression.sh"; then
  "$ROOT/scripts/smoke_manifest_regression.sh" >/dev/null
fi
if test -x "$ROOT/scripts/smoke_manifest_live.sh"; then
  "$ROOT/scripts/smoke_manifest_live.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_project_resume.sh"; then
  "$ROOT/scripts/smoke_project_resume.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_stage_dependencies.sh"; then
  "$ROOT/scripts/smoke_stage_dependencies.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_project_approval.sh"; then
  "$ROOT/scripts/smoke_project_approval.sh" >/dev/null
fi

test -x "$ROOT/scripts/smoke_library_budget.sh"
"$ROOT/scripts/smoke_library_budget.sh"

if test -x "$ROOT/scripts/smoke_builder_scaffold.sh"; then
  "$ROOT/scripts/smoke_builder_scaffold.sh" >/dev/null
fi


test -x "$ROOT/scripts/smoke_code_generate.sh" && "$ROOT/scripts/smoke_code_generate.sh"
test -x "$ROOT/scripts/smoke_docs_generate.sh" && "$ROOT/scripts/smoke_docs_generate.sh"
test -x "$ROOT/scripts/smoke_shorts_local.sh" && "$ROOT/scripts/smoke_shorts_local.sh"
test -x "$ROOT/scripts/smoke_shorts_generate.sh" && "$ROOT/scripts/smoke_shorts_generate.sh"
test -x "$ROOT/scripts/smoke_image_generate.sh" && "$ROOT/scripts/smoke_image_generate.sh"
test -x "$ROOT/scripts/smoke_game_generate.sh" && "$ROOT/scripts/smoke_game_generate.sh"
test -x "$ROOT/scripts/smoke_animation_generate.sh" && "$ROOT/scripts/smoke_animation_generate.sh"
test -x "$ROOT/scripts/smoke_text_generate.sh" && "$ROOT/scripts/smoke_text_generate.sh"
test -x "$ROOT/scripts/smoke_features_registry.sh" && "$ROOT/scripts/smoke_features_registry.sh"
test -x "$ROOT/scripts/smoke_generate_generic.sh" && "$ROOT/scripts/smoke_generate_generic.sh"
test -x "$ROOT/scripts/smoke_artifacts.sh" && "$ROOT/scripts/smoke_artifacts.sh"
test -x "$ROOT/scripts/smoke_artifact_export.sh" && "$ROOT/scripts/smoke_artifact_export.sh"
test -x "$ROOT/scripts/smoke_artifact_registry_backfill.sh" && "$ROOT/scripts/smoke_artifact_registry_backfill.sh"
test -x "$ROOT/scripts/smoke_artifact_detail.sh" && "$ROOT/scripts/smoke_artifact_detail.sh"
