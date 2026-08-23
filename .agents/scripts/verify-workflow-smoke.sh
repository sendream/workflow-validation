#!/usr/bin/env bash

set -euo pipefail

BASE_WORKFLOW_SMOKE_MARKER="base-authoritative-smoke-20260611"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAILURES=0
SMOKE_TMP="$(mktemp -d)"
trap 'rm -rf "$SMOKE_TMP"' EXIT
VALIDATION_LAYER="package-contract"

usage() {
  cat <<'EOF'
Usage: verify-workflow-smoke.sh [--layer package-contract|package-preflight|product-oracles]

Layers:
  package-contract   Default. Runs package-preflight then product-oracles.
                     Existing CI and self-check keep this aggregate.
  package-preflight  Installed files, forbidden-state absences, syntax, JSON,
                     executable bits, and thin-root size budgets.
                     Default Base (no .agents/evals) skips source-assurance
                     files; the source pack still checks the full set.
  product-oracles    Declarative product contracts and bounded helper fixtures.
                     Later mechanism retirements edit this layer, not preflight.

Run deterministic behavior separately with run-workflow-evals.sh, and use
verify-workflow-self-check.sh --all only when a source-repository aggregate is
needed. Base smoke never invokes a behavior suite.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --layer)
      shift
      if [[ $# -eq 0 ]]; then
        printf 'missing value for --layer\n' >&2
        usage >&2
        exit 2
      fi
      VALIDATION_LAYER="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

case "$VALIDATION_LAYER" in
  package-contract|package-preflight|product-oracles) ;;
  *)
    printf 'unknown validation layer: %s\n' "$VALIDATION_LAYER" >&2
    usage >&2
    exit 2
    ;;
esac

INSTALL_CONTRACT=""

# Shared leftover/source-assurance file check. Keep in sync with apply-starter-pack.sh.
# shellcheck source=portable.sh
. "$ROOT/.agents/scripts/portable.sh"

resolve_install_contract() {
  local marker="$ROOT/.agents/install-contract"
  if [[ -f "$marker" ]]; then
    INSTALL_CONTRACT="$(awk -F= '$1=="contract" {print $2; exit}' "$marker")"
    if [[ "$INSTALL_CONTRACT" != "installed-base" && "$INSTALL_CONTRACT" != "source-assurance" ]]; then
      fail "invalid .agents/install-contract: ${INSTALL_CONTRACT:-<empty>}"
      INSTALL_CONTRACT="unknown"
    fi
    return
  fi
  local inspect_status=0
  workflow_assurance_eval_inspect "$ROOT" || inspect_status=$?
  if [[ "$inspect_status" -eq 0 ]]; then
    INSTALL_CONTRACT="source-assurance"
    return
  fi
  if [[ "$inspect_status" -ne 1 ]]; then
    fail "cannot inspect .agents/evals; refuse to infer install-contract"
    INSTALL_CONTRACT="unknown"
    return
  fi
  fail "missing .agents/install-contract and .agents/evals; refuse to infer installed-Base"
  INSTALL_CONTRACT="unknown"
}

assurance_present() {
  [[ "$INSTALL_CONTRACT" == "source-assurance" ]]
}

is_assurance_rel() {
  case "$1" in
    .agents/evals|.agents/evals/*)
      return 0
      ;;
    .agents/scripts/run-workflow-evals.sh|\
    .agents/scripts/workflow-value-report.py|\
    .agents/scripts/harness-benchmark-report.py|\
    .agents/scripts/held-out-manifest-report.py|\
    .agents/scripts/live-eval-profile-report.py|\
    .agents/scripts/tool-surface-budget-report.py|\
    .agents/scripts/agent-state-noise-report.py|\
    .agents/scripts/validate-dynamic-agent-campaign.py|\
    .agents/scripts/validate-harness-experiment.py|\
    .agents/scripts/validate-workflow-evolution.py|\
    .agents/scripts/skill-curator-report.py|\
    .agents/scripts/validate-skill-curator-report.py)
      return 0
      ;;
    .agents/templates/campaign-manifest.json|\
    .agents/templates/campaign-metrics.json|\
    .agents/templates/multi-agent-campaign.md)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

skip_if_assurance_missing() {
  local rel="$1"
  local label="${2:-$1}"
  if ! assurance_present && is_assurance_rel "$rel"; then
    pass "skip installed-Base (assurance not shipped): $label"
    return 0
  fi
  return 1
}

pass() {
  printf 'pass: %s\n' "$1"
}

fail() {
  printf 'fail: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

resolve_install_contract
ASSURANCE_INSPECT_STATUS=0
workflow_assurance_eval_inspect "$ROOT" || ASSURANCE_INSPECT_STATUS=$?
if [[ "$ASSURANCE_INSPECT_STATUS" -eq 0 ]]; then
  if [[ "$INSTALL_CONTRACT" == "installed-base" ]]; then
    fail "install-contract=installed-base but leftover .agents/evals exists; refuse silent downgrade"
  fi
elif [[ "$ASSURANCE_INSPECT_STATUS" -eq 1 ]]; then
  if [[ "$INSTALL_CONTRACT" == "source-assurance" ]]; then
    fail "install-contract=source-assurance but .agents/evals is missing"
  fi
else
  fail "cannot inspect .agents/evals; refuse silent downgrade"
fi

require_file() {
  if skip_if_assurance_missing "$1" "file $1"; then
    return
  fi
  if [[ -f "$ROOT/$1" ]]; then
    pass "file exists: $1"
  else
    fail "missing file: $1"
  fi
}

require_absent_file() {
  if [[ -e "$ROOT/$1" ]]; then
    fail "unexpected file exists: $1"
  else
    pass "file absent: $1"
  fi
}

require_absent_dir() {
  if [[ -d "$ROOT/$1" ]]; then
    fail "unexpected directory exists: $1"
  else
    pass "directory absent: $1"
  fi
}

require_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"

  if skip_if_assurance_missing "$file" "$label"; then
    return
  fi
  if grep -Eq -- "$pattern" "$ROOT/$file"; then
    pass "$label"
  else
    fail "$label"
  fi
}

require_git_or_local_exclude_contains() {
  local pattern="$1"
  local label="$2"
  local local_exclude

  local_exclude="$ROOT/.git/info/exclude"
  if grep -Eq -- "$pattern" "$ROOT/.gitignore"; then
    pass "$label"
    return
  fi

  if [[ -f "$local_exclude" ]] && grep -Eq -- "$pattern" "$local_exclude"; then
    pass "$label"
    return
  fi

  fail "$label"
}

require_not_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"

  if grep -Eiq -- "$pattern" "$ROOT/$file"; then
    fail "$label"
  else
    pass "$label"
  fi
}

python_syntax_check() {
  local filename rel
  for filename in "$@"; do
    rel="${filename#"$ROOT"/}"
    if skip_if_assurance_missing "$rel" "syntax $rel"; then
      continue
    fi
    if ! python3 - "$filename" <<'PY'
import ast
import pathlib
import sys

filename = pathlib.Path(sys.argv[1])
ast.parse(filename.read_text(encoding="utf-8"), filename=str(filename))
PY
    then
      return 1
    fi
  done
  return 0
}


run_package_preflight() {
require_file "AGENTS.md"
require_file "code_review.md"
require_file ".gitignore"
require_file ".codex/hooks.json"
require_file ".graphifyignore"
require_file ".rgignore"
require_file ".geminiignore"
require_file ".repomixignore"
require_file ".aiderignore"
require_file ".agents/scripts/graphify-refresh.sh"
require_file ".agents/scripts/graphify-stale-check.sh"
require_file ".agents/scripts/portable.sh"
require_file ".agents/scripts/verify-workflow-smoke-fast.sh"
require_file ".agents/scripts/run-workflow-evals.sh"
require_file ".agents/scripts/validate-bootstrap.sh"
require_file ".agents/scripts/markdown_table.py"
require_file ".agents/scripts/markdown_document.py"
require_file ".agents/scripts/review_result_contract.py"
require_file ".agents/scripts/validator_result.py"
require_file ".agents/scripts/workflow_routing.py"
require_file ".agents/scripts/tooling-router.py"
require_file ".agents/scripts/classify-worktree-dirty.py"
require_file ".agents/scripts/validate-release-artifact-source.py"
require_file ".agents/scripts/validate-evidence-waivers.py"
require_file ".agents/scripts/validate-reviewer-assessment.py"
require_file ".agents/scripts/validate-review-authorization.py"
require_file ".agents/scripts/validate-active-task-migration.py"
require_file ".agents/scripts/validate-workflow-overlay-boundary.py"
require_file ".agents/scripts/validate-workflow-trace-consistency.py"
require_file ".agents/scripts/validate-dynamic-agent-campaign.py"
require_file ".agents/scripts/validate-task-closeout.py"
require_file ".agents/scripts/validate-doc-fact-drift.py"
require_file ".agents/scripts/validate-task-archive-hygiene.py"
require_file ".agents/scripts/validate-run-manifest.py"
require_file ".agents/scripts/validate-claim-evidence.py"
require_file ".agents/scripts/validate-workflow-evolution.py"
require_file ".agents/scripts/validate-harness-experiment.py"
require_file ".agents/scripts/harness_components.py"
require_file ".agents/scripts/run_manifest_contract.py"
require_file ".agents/scripts/validate-command-catalog.py"
require_file ".agents/scripts/validate-context-references.py"
require_file ".agents/scripts/validate-external-content-boundary.py"
require_file ".agents/scripts/context-select.py"
require_file ".agents/scripts/context_selection_contract.py"
require_file ".agents/scripts/current_task_snapshot.py"
require_file ".agents/scripts/state_compat.py"
require_file ".agents/scripts/state-compat.py"
require_file ".agents/scripts/validate-capability-card.py"
require_file ".agents/evals/behavior/test_current_task_snapshot.py"
require_file ".agents/scripts/skill-curator-report.py"
require_file ".agents/scripts/validate-skill-curator-report.py"
require_file ".agents/scripts/runtime-skill-surface-report.py"
require_file ".agents/scripts/workflow-value-report.py"
require_file ".agents/scripts/agent-state-noise-report.py"
require_file ".agents/scripts/held-out-manifest-report.py"
require_file ".agents/scripts/create-task-archive.py"
require_file ".agents/scripts/search-workflow-history.py"
if [[ -x "$ROOT/.agents/scripts/search-workflow-history.py" ]]; then
  pass "search-workflow-history.py is directly executable"
else
  fail "search-workflow-history.py is directly executable"
fi
require_file ".agents/references/harness-components.md"
require_file ".agents/references/validation-coverage-map.md"
require_file ".agents/references/workflow/gate-cards.md"
require_file ".agents/scripts/validate-local-skills.py"
require_file ".agents/scripts/sensitive-command-guard.py"
require_file ".agents/scripts/sensitive_guard_policy.py"
require_file ".agents/scripts/hook_event_contract.py"
require_file ".agents/scripts/sensitive-edit-guard.py"
require_file ".agents/scripts/trajectory-monitor.py"
require_file ".agents/scripts/verify-hooks-runtime.sh"
require_file ".agents/scripts/capture-run-command.py"
require_file ".agents/scripts/capture-run-script.sh"
require_file ".agents/scripts/archive-legacy-runs.sh"
require_file ".agent-state/README.md"

agents_bytes="$(wc -c < "$ROOT/AGENTS.md" | tr -d ' ')"
if (( agents_bytes <= 28672 )); then
  pass "AGENTS.md byte budget stays thin (${agents_bytes} bytes)"
else
  fail "AGENTS.md exceeds 28 KiB thin-root budget (${agents_bytes} bytes); move details to references"
fi

require_absent_file "component-registry.json"
require_absent_file "workflow-state.json"
require_absent_file "change-manifest.json"

# Case inventory (existence + registration) is owned by run-workflow-evals.sh
# REQUIRED_CASES; smoke does not keep a second case list.
require_file ".agents/evals/held-out/held-out-manifest.example.json"
require_file ".agents/evals/behavior/run_harness_modularization_evals.py"
require_file ".agents/evals/trajectory/case-release-external-system.json"
require_file ".agents/evals/trajectory/case-review-only-no-write.json"
require_file ".agents/evals/trajectory/case-policy-auto-invalid-packet.json"
require_file ".agents/evals/trajectory/case-graphify-no-auto-refresh.json"
require_file ".agents/evals/trajectory/case-dynamic-agent-campaign.json"
require_file ".agents/references/common-pitfalls.md"
require_file ".agents/references/project-conventions.md"
require_file ".agents/references/tooling-map.md"
require_file ".agents/references/validator-map.md"
require_file ".agents/references/workflow-details.md"
require_file ".agents/references/workflow/routing-planning.md"
require_file ".agents/references/workflow/context-memory.md"
require_file ".agents/references/workflow/reviewer-governance.md"
require_file ".agents/references/workflow/verification-evidence.md"
require_file ".agents/references/workflow/lifecycle-recovery.md"
require_file ".agents/references/workflow/tooling-safety.md"
require_file ".agents/references/workflow/evolution-experiments.md"
require_file ".agents/references/command-catalog.md"
require_file ".agents/references/terminology.md"
require_file ".agents/tasks/README.md"
require_file ".agents/runs/README.md"
require_file ".agents/runs/.gitignore"
require_file ".agents/skills/planning-with-files/SKILL.md"
require_file ".agents/skills/requirements-to-plan/SKILL.md"
require_file ".agents/skills/ship-check/SKILL.md"
require_file ".agents/skills/project-context/SKILL.md"
require_file ".agents/templates/project-readme.md"
require_file ".agents/templates/task_plan.core.md"
require_file ".agents/templates/findings.core.md"
require_file ".agents/templates/progress.core.md"
require_file ".agents/templates/multi-agent-campaign.md"
require_file ".agents/templates/campaign-manifest.json"
require_file ".agents/templates/campaign-metrics.json"
require_file ".agents/templates/command-contract.md"
require_file ".agents/templates/task_archive.md"
require_file ".agents/templates/capability-card.md"
require_file ".agents/templates/appendices/task_plan.behavior-appendix.md"
require_file ".agents/templates/appendices/progress.release-appendix.md"
require_file ".agents/templates/appendices/progress.reviewer-appendix.md"
require_file ".agents/templates/appendices/progress.human-decision-appendix.md"
require_file ".agents/templates/appendices/progress.workflow-trace-appendix.md"
require_file ".agents/templates/appendices/workflow-source-change-attribution.md"
require_file ".agents/templates/appendices/findings.knowledge-environment-appendix.md"

require_absent_file "agent-debug-packet.json"
require_absent_file "agent-debug-packet.md"
require_absent_dir "agent-debug-packet"
require_absent_file "agent-view-debug.json"
require_absent_file "agent-view-debug.md"
require_absent_dir "agent-view-debug"
require_absent_file "agent-view-debug-packet.json"
require_absent_file "agent-view-debug-packet.md"
require_absent_dir "agent-view-debug-packet"
require_absent_file "debug-packet.json"
require_absent_file "debug-packet.md"
require_absent_dir "debug-packet"
require_absent_file "memory.md"
require_absent_file "workflow-debug.json"
require_absent_file "workflow-debug.md"
require_absent_dir "workflow-debug"
require_absent_file "workflow-trace.json"
require_absent_file "workflow-plan.json"
require_absent_file "workflow-run.json"
require_absent_file "workflow_trace.json"
require_absent_file "archive-index.json"

agents_lines=$(wc -l < "$ROOT/AGENTS.md" | tr -d ' ')
if [[ "$agents_lines" -le 250 ]]; then
  pass "project AGENTS stays within thin-root line budget: $agents_lines"
else
  fail "project AGENTS exceeds thin-root line budget: $agents_lines"
fi

if command -v python3 >/dev/null 2>&1; then
  if python3 -m json.tool "$ROOT/.codex/hooks.json" >/dev/null; then
    pass ".codex/hooks.json is valid JSON"
  else
    fail ".codex/hooks.json is invalid JSON"
  fi
else
  fail "python3 is required to validate hooks JSON"
fi

if bash -n "$ROOT/.agents/scripts/graphify-refresh.sh"; then
  pass "graphify-refresh.sh syntax"
else
  fail "graphify-refresh.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/graphify-stale-check.sh"; then
  pass "graphify-stale-check.sh syntax"
else
  fail "graphify-stale-check.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/portable.sh"; then
  pass "portable.sh syntax"
else
  fail "portable.sh syntax"
fi

if skip_if_assurance_missing ".agents/scripts/run-workflow-evals.sh" "run-workflow-evals.sh syntax"; then
  :
elif sh -n "$ROOT/.agents/scripts/run-workflow-evals.sh"; then
  pass "run-workflow-evals.sh syntax"
else
  fail "run-workflow-evals.sh syntax"
fi

if bash -n "$ROOT/.agents/scripts/verify-workflow-smoke-fast.sh"; then
  pass "verify-workflow-smoke-fast.sh syntax"
else
  fail "verify-workflow-smoke-fast.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/validate-bootstrap.sh"; then
  pass "validate-bootstrap.sh syntax"
else
  fail "validate-bootstrap.sh syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/tooling-router.py"; then
  pass "tooling-router.py syntax"
else
  fail "tooling-router.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/markdown_table.py"; then
  pass "markdown_table.py syntax"
else
  fail "markdown_table.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/markdown_document.py"; then
  pass "markdown_document.py syntax"
else
  fail "markdown_document.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/review_result_contract.py"; then
  pass "review_result_contract.py syntax"
else
  fail "review_result_contract.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validator_result.py"; then
  pass "validator_result.py syntax"
else
  fail "validator_result.py syntax"
fi

if python3 - "$ROOT/.agents/scripts" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import markdown_table as md
import workflow_routing as wr

row = md.split_markdown_table_row(r"| a\|b | `grep a|b` | ok |")
assert row == ["a|b", "grep a|b", "ok"], row
tables = md.parse_markdown_tables("""| A | B |\n|---|---|\n| one\\|two | `x|y` |\n""", strict=True)
assert tables[0].rows[0] == ["one|two", "x|y"], tables[0].rows
multi_backtick_tables = md.parse_markdown_tables(
    """| kind | command |\n|---|---|\n| shell | ``echo `a|b` `` |\n""",
    strict=True,
)
assert multi_backtick_tables[0].rows[0] == ["shell", "echo `a|b`"], multi_backtick_tables[0].rows
legacy_routing = """## Workflow Routing
| field | value |
| Risk Tier | high |
| Impact Scope | external-system |
"""
assert wr.extract_risk_tier(legacy_routing) == "high"
assert wr.extract_impact_scope(legacy_routing) == "external-system"
try:
    md.parse_markdown_tables("| A | B |\n|---|---|\n| only-one |\n", strict=True)
except md.MarkdownTableError:
    pass
else:
    raise AssertionError("strict parser accepted mismatched columns")
PY
then
  pass "markdown_table.py handles escaped/code pipes and strict column errors"
else
  fail "markdown_table.py handles escaped/code pipes and strict column errors"
fi

if python_syntax_check "$ROOT/.agents/scripts/classify-worktree-dirty.py"; then
  pass "classify-worktree-dirty.py syntax"
else
  fail "classify-worktree-dirty.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/workflow_routing.py"; then
  pass "workflow_routing.py syntax"
else
  fail "workflow_routing.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/context-select.py"; then
  pass "context-select.py syntax"
else
  fail "context-select.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/context_selection_contract.py"; then
  pass "context_selection_contract.py syntax"
else
  fail "context_selection_contract.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/current_task_snapshot.py"; then
  pass "current_task_snapshot.py syntax"
else
  fail "current_task_snapshot.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/state_compat.py" "$ROOT/.agents/scripts/state-compat.py" "$ROOT/.agents/scripts/validate-capability-card.py"; then
  pass "state compatibility and capability-card validator syntax"
else
  fail "state compatibility and capability-card validator syntax"
fi

if skip_if_assurance_missing ".agents/evals/behavior/test_current_task_snapshot.py" "current task snapshot contract tests"; then
  :
elif python3 "$ROOT/.agents/evals/behavior/test_current_task_snapshot.py" >$SMOKE_TMP/current-task-snapshot.out 2>&1; then
  pass "current task snapshot contract tests"
else
  fail "current task snapshot contract tests"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-release-artifact-source.py"; then
  pass "validate-release-artifact-source.py syntax"
else
  fail "validate-release-artifact-source.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-evidence-waivers.py"; then
  pass "validate-evidence-waivers.py syntax"
else
  fail "validate-evidence-waivers.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-reviewer-assessment.py"; then
  pass "validate-reviewer-assessment.py syntax"
else
  fail "validate-reviewer-assessment.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-review-authorization.py"; then
  pass "validate-review-authorization.py syntax"
else
  fail "validate-review-authorization.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-active-task-migration.py"; then
  pass "validate-active-task-migration.py syntax"
else
  fail "validate-active-task-migration.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-workflow-overlay-boundary.py"; then
  pass "validate-workflow-overlay-boundary.py syntax"
else
  fail "validate-workflow-overlay-boundary.py syntax"
fi


if python_syntax_check "$ROOT/.agents/scripts/validate-workflow-trace-consistency.py"; then
  pass "validate-workflow-trace-consistency.py syntax"
else
  fail "validate-workflow-trace-consistency.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-dynamic-agent-campaign.py"; then
  pass "validate-dynamic-agent-campaign.py syntax"
else
  fail "validate-dynamic-agent-campaign.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-task-closeout.py"; then
  pass "validate-task-closeout.py syntax"
else
  fail "validate-task-closeout.py syntax"
fi


if python_syntax_check "$ROOT/.agents/scripts/validate-doc-fact-drift.py"; then
  pass "validate-doc-fact-drift.py syntax"
else
  fail "validate-doc-fact-drift.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-task-archive-hygiene.py"; then
  pass "validate-task-archive-hygiene.py syntax"
else
  fail "validate-task-archive-hygiene.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/create-task-archive.py"; then
  pass "create-task-archive.py syntax"
else
  fail "create-task-archive.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-run-manifest.py"; then
  pass "validate-run-manifest.py syntax"
else
  fail "validate-run-manifest.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-claim-evidence.py"; then
  pass "validate-claim-evidence.py syntax"
else
  fail "validate-claim-evidence.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-workflow-evolution.py"; then
  pass "validate-workflow-evolution.py syntax"
else
  fail "validate-workflow-evolution.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-harness-experiment.py"; then
  pass "validate-harness-experiment.py syntax"
else
  fail "validate-harness-experiment.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/harness_components.py" && python_syntax_check "$ROOT/.agents/scripts/run_manifest_contract.py"; then
  pass "harness component and run manifest contracts syntax"
else
  fail "harness component and run manifest contracts syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-command-catalog.py"; then
  pass "validate-command-catalog.py syntax"
else
  fail "validate-command-catalog.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-context-references.py"; then
  pass "validate-context-references.py syntax"
else
  fail "validate-context-references.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-external-content-boundary.py"; then
  pass "validate-external-content-boundary.py syntax"
else
  fail "validate-external-content-boundary.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/skill-curator-report.py"; then
  pass "skill-curator-report.py syntax"
else
  fail "skill-curator-report.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-skill-curator-report.py"; then
  pass "validate-skill-curator-report.py syntax"
else
  fail "validate-skill-curator-report.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/runtime-skill-surface-report.py"; then
  pass "runtime-skill-surface-report.py syntax"
else
  fail "runtime-skill-surface-report.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/workflow-value-report.py"; then
  pass "workflow-value-report.py syntax"
else
  fail "workflow-value-report.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/agent-state-noise-report.py"; then
  pass "agent-state-noise-report.py syntax"
else
  fail "agent-state-noise-report.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/held-out-manifest-report.py"; then
  pass "held-out-manifest-report.py syntax"
else
  fail "held-out-manifest-report.py syntax"
fi

if [[ -x "$ROOT/.agents/scripts/runtime-skill-surface-report.py" ]]; then
  pass "runtime-skill-surface-report.py is directly executable"
else
  fail "runtime-skill-surface-report.py is directly executable"
fi

if skip_if_assurance_missing ".agents/scripts/workflow-value-report.py" "workflow-value-report.py is directly executable"; then
  :
elif [[ -x "$ROOT/.agents/scripts/workflow-value-report.py" ]]; then
  pass "workflow-value-report.py is directly executable"
else
  fail "workflow-value-report.py is directly executable"
fi

if skip_if_assurance_missing ".agents/scripts/agent-state-noise-report.py" "agent-state-noise-report.py is directly executable"; then
  :
elif [[ -x "$ROOT/.agents/scripts/agent-state-noise-report.py" ]]; then
  pass "agent-state-noise-report.py is directly executable"
else
  fail "agent-state-noise-report.py is directly executable"
fi

if skip_if_assurance_missing ".agents/scripts/held-out-manifest-report.py" "held-out-manifest-report.py is directly executable"; then
  :
elif [[ -x "$ROOT/.agents/scripts/held-out-manifest-report.py" ]]; then
  pass "held-out-manifest-report.py is directly executable"
else
  fail "held-out-manifest-report.py is directly executable"
fi

if skip_if_assurance_missing ".agents/scripts/validate-harness-experiment.py" "validate-harness-experiment.py is directly executable"; then
  :
elif [[ -x "$ROOT/.agents/scripts/validate-harness-experiment.py" ]]; then
  pass "validate-harness-experiment.py is directly executable"
else
  fail "validate-harness-experiment.py is directly executable"
fi

if [[ -x "$ROOT/.agents/scripts/create-task-archive.py" ]]; then
  pass "create-task-archive.py is directly executable"
else
  fail "create-task-archive.py is directly executable"
fi

}

run_product_oracles() {
require_contains "AGENTS.md" '本文件是复杂任务定义的唯一权威来源' "AGENTS remains project routing authority"
require_contains "AGENTS.md" '不为小任务加载三文件' "AGENTS preserves fast-path context budget"
require_contains "AGENTS.md" 'G14_STRUCTURAL_INDEX' "AGENTS indexes Structural Index gate"
require_contains "AGENTS.md" 'G16_ROLE_REVIEWER' "AGENTS indexes Role Reviewer gate"
require_contains "AGENTS.md" 'G18_RELEASE_SOURCE' "AGENTS indexes Release Source gate"
require_contains "AGENTS.md" 'Policy-Auto Reviewer' "AGENTS keeps Policy-Auto reviewer boundary"
require_contains "AGENTS.md" 'Release Artifact Source Gate' "AGENTS keeps release source trigger"
require_contains "AGENTS.md" '不自动生成图谱或代码索引' "AGENTS keeps no-auto-index structural guard"
require_not_contains "AGENTS.md" 'dirty worktree 新包必须包含 `intended-source-files\.json`' "AGENTS does not embed release packet schema details"
require_not_contains "AGENTS.md" '数量上限、typed start result、fallback、packet schema' "AGENTS does not embed reviewer packet implementation details"
require_contains ".agents/references/workflow/lifecycle-recovery.md" '^## Push / Commit / Delivery Cleanup$' "workflow details owns Push / Commit / Delivery Cleanup details"
require_contains ".agents/references/workflow/lifecycle-recovery.md" 'classify-worktree-dirty\.py' "workflow details routes dirty classifier details"
require_contains ".agents/references/workflow/lifecycle-recovery.md" 'Red-team' "workflow details carries Push Gate red-team detail"
require_contains ".agents/references/workflow/lifecycle-recovery.md" 'Tooling gaps' "workflow details carries release tooling gap detail"
require_contains ".agents/references/workflow/lifecycle-recovery.md" 'runtime data' "workflow details carries runtime data blocker detail"
require_contains ".agents/references/harness-components.md" 'reference-only' "harness components registry is reference-only"
require_contains ".agents/references/harness-components.md" 'not a runner' "harness components registry is not a runner"
require_contains ".agents/references/harness-components.md" 'not a state source' "harness components registry is not a state source"
require_contains ".agents/references/harness-components.md" 'not a gate' "harness components registry is not a gate"
require_contains ".agents/references/harness-components.md" 'flow-tax' "harness components registry includes flow-tax"
require_contains ".agents/references/harness-components.md" 'evidence-governance' "harness components registry includes evidence governance"
require_contains ".agents/references/harness-components.md" 'role-reviewer' "harness components registry includes role reviewer"
require_contains ".agents/references/harness-components.md" 'skill-governance' "harness components registry includes skill governance"
require_contains ".agents/references/validation-coverage-map.md" '^## Failure-mode ownership$' "validation coverage map declares ownership table"
require_contains ".agents/references/workflow/gate-cards.md" '^## Rule ownership inventory$' "Gate Cards declare rule ownership inventory"
if PYTHONPATH="$ROOT/.agents/scripts" python3 - "$ROOT/.agents/references/harness-components.md" <<'PY'
import sys
from pathlib import Path

from harness_components import validate_registry_parity

errors = validate_registry_parity(Path(sys.argv[1]))
if errors:
    for error in errors:
        print(f"fail: {error}", file=sys.stderr)
    raise SystemExit(1)
PY
then
  pass "harness component Markdown/Python IDs have complete bidirectional parity"
else
  fail "harness component Markdown/Python ID parity"
fi
require_contains ".agents/references/workflow/evolution-experiments.md" 'component_id.*assumption.*why it exists.*validation signal.*remove-or-relax when' "stale assumption register includes component attribution"
require_contains ".agents/references/workflow/verification-evidence.md" 'public benchmark.*held-out|held-out.*public benchmark' "workflow details documents public benchmark held-out boundary"
require_contains ".agents/references/validator-map.md" 'Harness component registry' "validator map indexes harness component registry"

require_contains ".agents/references/workflow/lifecycle-recovery.md" 'Git HEAD.*index.*upstream' "workflow details uses Git facts directly"

require_contains ".agents/templates/task_plan.core.md" 'Appendix Triggers' "task plan core template points to triggered appendices"
require_contains ".agents/templates/progress.core.md" 'Appendix Triggers' "progress core template points to triggered appendices"
require_contains ".agents/templates/findings.core.md" 'Appendix Triggers' "findings core template points to triggered appendices"
require_contains ".agents/templates/progress.core.md" 'progress\.human-decision-appendix\.md' "progress core template points to human decision appendix"
require_contains ".agents/templates/appendices/progress.human-decision-appendix.md" 'not a second state source' "human decision appendix is not a state source"
require_contains ".agents/templates/appendices/workflow-source-change-attribution.md" 'Optional appendix for workflow-source changes only' "workflow-source attribution appendix is optional"
require_contains ".agents/templates/appendices/workflow-source-change-attribution.md" 'not a runner' "workflow-source attribution appendix is not a runner"
require_contains ".agents/templates/appendices/workflow-source-change-attribution.md" 'reward_hacking_review' "workflow-source attribution appendix includes reward-hacking review field"
require_contains ".agents/templates/appendices/progress.release-appendix.md" 'not task state' "progress release appendix is not a state source"
require_contains ".agents/templates/appendices/progress.release-appendix.md" 'allowed-diff-build' "progress release appendix includes current allowed-diff source mode"
require_not_contains ".agents/templates/appendices/progress.release-appendix.md" 'risk-accepted' "progress release appendix avoids legacy risk-accepted dirty disposition"
require_contains ".agents/templates/appendices/progress.release-appendix.md" 'Explicit user risk acceptance.*none / required / accepted' "progress release appendix uses validator-compatible risk acceptance values"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'not task state' "progress reviewer appendix is not a state source"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'Reviewer Start Authority' "progress reviewer appendix includes reviewer start authority"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'explicit-denied' "progress reviewer appendix includes explicit-denied start result"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'revoked' "progress reviewer appendix includes revoked authorization scope"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'not-retained-after-submission' "progress reviewer appendix defines submitted packet compaction"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'Durable review summary' "progress reviewer appendix requires durable submitted review summary"
require_contains ".agents/templates/appendices/progress.reviewer-appendix.md" 'focus.*verdict.*disposition.*unresolved risk' "progress reviewer appendix summary uses disposition column"
require_contains ".agents/templates/appendices/progress.evidence-waiver-appendix.md" 'MANUAL' "evidence waiver appendix includes manual final evidence status"
require_contains ".agents/templates/appendices/progress.evidence-waiver-appendix.md" 'NOT_APPLICABLE' "evidence waiver appendix includes not-applicable final evidence status"
require_not_contains ".agents/templates/appendices/progress.evidence-waiver-appendix.md" 'normal / negative' "evidence waiver appendix uses current case class taxonomy"
require_contains ".agents/templates/appendices/task_plan.behavior-appendix.md" 'A\. 推荐.*\(Recommended\).*B\.' "behavior appendix puts recommended clarification option first"
require_contains ".agents/templates/appendices/task_plan.behavior-appendix.md" 'permission-deny' "behavior appendix includes current permission-deny case class"
require_not_contains ".agents/templates/appendices/task_plan.behavior-appendix.md" 'normal / negative' "behavior appendix avoids legacy case class taxonomy"
require_contains ".agents/templates/appendices/task_plan.risk-release-appendix.md" 'source mode candidate.*allowed-diff-build' "risk/release planning appendix includes allowed-diff source mode"
require_not_contains ".agents/templates/appendices/task_plan.risk-release-appendix.md" '\| role \| trigger \| packet \| verdict \| main disposition \|' "risk/release planning appendix does not use legacy reviewer disposition table"
require_contains ".agents/templates/appendices/findings.knowledge-environment-appendix.md" 'not task state' "findings knowledge appendix is not a state source"
require_contains ".agents/evals/optional/p2-tool-surface-budget-report.md" '^# P2:' "optional tool surface report is not numbered like a default eval case"
require_contains ".agents/evals/optional/p2-harness-benchmark-suite.md" '^# P2:' "optional benchmark suite is not numbered like a default eval case"
require_contains ".agents/evals/optional/p2-live-eval-experiment-profile.md" '^# P2:' "optional live eval profile is not numbered like a default eval case"
require_contains ".agents/evals/case-61-held-out-manifest-boundary.md" 'metadata-only' "case 61 documents metadata-only held-out boundary"
require_contains ".agents/evals/held-out/held-out-manifest.example.json" '"type": "held-out-eval-manifest"' "held-out example has manifest type"
require_contains ".agents/evals/held-out/held-out-manifest.example.json" '"stores_answers": false' "held-out example does not store answers"
require_contains ".agents/evals/held-out/held-out-manifest.example.json" '"answer_storage": "not-stored"' "held-out example declares no answer storage"
require_contains ".agents/scripts/held-out-manifest-report.py" 'samples_read' "held-out report declares sample read boundary"
require_contains ".agents/scripts/held-out-manifest-report.py" 'answers_read' "held-out report declares answer read boundary"
require_contains ".agents/scripts/held-out-manifest-report.py" 'public/advisory benchmark' "held-out report rejects public/advisory benchmark substitution"
require_contains ".agents/templates/task_archive.md" 'Recall Metadata \(Optional\)' "task archive template supports optional recall metadata"
require_contains ".agents/templates/task_archive.md" 'event.*entities.*source_refs|source_refs.*entities.*event' "task archive template documents event/entities/source_refs"
require_contains ".agents/scripts/search-workflow-history.py" 'FIELD_WEIGHTS' "history search uses field-weighted lexical ranking"
require_contains ".agents/scripts/search-workflow-history.py" 'query_trace' "history search emits query trace"
require_contains ".agents/evals/case-50-archive-memory-layer.md" 'source_refs.*metadata only|metadata only.*source_refs' "case-50 keeps source_refs metadata-only"
require_contains ".agents/templates/progress.md" 'Requirement Reconciliation' "progress template includes requirement reconciliation"
require_contains ".agents/templates/progress.md" 'Source Roots / Repos Touched' "progress template includes source roots touched"
require_contains ".agents/templates/progress.md" 'source_confidence' "progress template records structural index source confidence"
require_contains ".agents/templates/progress.md" 'Active slice id' "progress template records active slice id"
require_contains ".agents/templates/progress.md" 'Rollover state' "progress template records rollover state"
require_contains ".agents/templates/task_plan.md" 'Affected Source Roots' "task plan template includes affected source roots"
require_contains ".agents/templates/task_plan.md" 'Structural Index Query Plan' "task plan uses structural index query plan, not duplicate evidence"
require_contains ".agents/references/project-conventions.md" 'Source Root Registry' "project conventions define source root registry"
require_contains ".agents/references/project-conventions.md" 'per-root freshness|freshness is per-root|freshness 是 per-root' "project conventions define per-root index freshness"
require_contains ".agents/references/workflow/tooling-safety.md" 'source_confidence=source-confirmed / test-confirmed' "workflow details define source confidence confidence ladder"
require_contains ".agents/scripts/validate-task-closeout.py" 'Source Roots / Repos Touched' "task closeout validates source roots touched"
require_contains ".agents/scripts/validate-task-closeout.py" 'git-commit-' "task closeout distinguishes git commit refs from run ids"
require_contains ".agents/scripts/validate-task-closeout.py" 'Skill Curator Closeout' "task closeout surfaces skill curator human-needed decisions"
require_contains ".agents/scripts/validate-task-closeout.py" 'Human Decision Surface' "task closeout surfaces workflow value human decisions"
require_contains ".agents/templates/appendices/progress.human-decision-appendix.md" 'Skill Curator Closeout' "human decision appendix points dedicated skill decisions to skill curator closeout"
require_not_contains ".agents/templates/appendices/progress.human-decision-appendix.md" 'workflow-value-report / skill-curator' "human decision appendix does not duplicate skill curator closeout source"
require_contains ".agents/scripts/validate-skill-curator-report.py" 'plugin/MCP/hook' "skill curator validator treats plugin/MCP/hook capability as human-needed"
require_contains ".agents/references/validator-map.md" 'Runtime skill/plugin surface report' "validator map indexes runtime skill/plugin surface report"
require_contains ".agents/references/validator-map.md" 'does not install, enable, update, remove' "runtime skill/plugin surface report remains report-only"
require_contains ".agents/scripts/validate-release-artifact-source.py" 'historical-packet' "release source validator supports historical packet scope"
require_contains ".agents/evals/case-57-source-roots-and-typed-evidence.md" 'source-file:<root_id>:<path>' "case-57 covers typed source-file evidence refs"
require_contains ".agents/templates/task_plan.md" 'test oracle / independence' "task plan template records test oracle independence"
require_contains ".agents/scripts/validate-traceability.py" 'Requirement Reconciliation' "traceability validator checks requirement reconciliation conflicts"
require_contains ".agents/scripts/validate-traceability.py" 'requires linked acceptance_id or scenario_id' "traceability validator rejects unlinked blocking reconciliation rows"
require_contains ".agents/scripts/validate-traceability.py" 'unknown linked acceptance_id' "traceability validator rejects unknown reconciliation acceptance links"
require_contains ".agents/scripts/validate-traceability.py" 'unknown linked scenario_id' "traceability validator rejects unknown reconciliation scenario links"
require_contains ".agents/scripts/validate-traceability.py" 'test oracle / independence remains' "traceability validator rejects unresolved test oracle PASS rows"
require_contains ".agents/evals/behavior/run_behavior_evals.py" 'needs-human-check with PASS ledger' "behavior eval covers needs-human-check reconciliation conflict"
require_contains ".agents/evals/behavior/run_behavior_evals.py" 'partially unknown reconciliation acceptance link' "behavior eval covers partially unknown reconciliation acceptance link"
require_contains ".agents/evals/behavior/run_behavior_evals.py" 'partially unknown reconciliation scenario link' "behavior eval covers partially unknown reconciliation scenario link"
require_contains ".agents/scripts/run-workflow-evals.sh" 'case-56-requirement-reconciliation.md' "workflow eval required cases include requirement reconciliation"
require_not_contains ".agents/templates/task_plan.md" 'git-slice-ledger|Git slice ledger' "task plan template avoids undefined git-slice-ledger state source"
require_not_contains ".agents/references/workflow-details.md" 'git-slice-ledger|Git slice ledger' "workflow details avoids undefined git-slice-ledger state source"

mkdir -p "$SMOKE_TMP/codex-home"
if "$ROOT/.agents/scripts/runtime-skill-surface-report.py" \
  --root "$ROOT" \
  --codex-home "$SMOKE_TMP/codex-home" \
  --format json \
  | python3 -m json.tool >/dev/null; then
  pass "runtime-skill-surface-report.py emits valid JSON"
else
  fail "runtime-skill-surface-report.py emits valid JSON"
fi

WORKFLOW_VALUE_FIXTURE="$SMOKE_TMP/workflow-value-report-fixture"
mkdir -p "$WORKFLOW_VALUE_FIXTURE"
cat >"$WORKFLOW_VALUE_FIXTURE/task_plan.md" <<'EOF'
# Task Plan

## Risk Tier
- Tier: standard
EOF
cat >"$WORKFLOW_VALUE_FIXTURE/progress.md" <<'EOF'
# Progress

## Workflow Trace
| step | status | evidence |
|---|---|---|
| task_closeout | focused | progress.md |
EOF
cat >"$WORKFLOW_VALUE_FIXTURE/findings.md" <<'EOF'
# Findings

## Real Task Feedback Loop
| signal | source trace / artifact | audit_lens | attribution_type | expected behavior | observed behavior | task_epoch | mechanism_id | introduced_at | workflow_synced_at | applies_from | source_baseline | candidate type | eval guard | disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| not-needed | none | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed | not-needed |
EOF

if skip_if_assurance_missing ".agents/scripts/workflow-value-report.py" "workflow-value-report.py emits valid JSON"; then
  :
elif "$ROOT/.agents/scripts/workflow-value-report.py" \
  --root "$WORKFLOW_VALUE_FIXTURE" \
  --format json \
  | python3 -m json.tool >/dev/null; then
  pass "workflow-value-report.py emits valid JSON"
else
  fail "workflow-value-report.py emits valid JSON"
fi

AGENT_STATE_NOISE_FIXTURE="$SMOKE_TMP/agent-state-noise-fixture"
mkdir -p "$AGENT_STATE_NOISE_FIXTURE/.agent-state/runs/r1" "$AGENT_STATE_NOISE_FIXTURE/.agent-state/runs/r2" "$AGENT_STATE_NOISE_FIXTURE/.agent-state/backups/b1"
cat >"$AGENT_STATE_NOISE_FIXTURE/.agent-state/runs/r1/manifest.json" <<'EOF'
{"schema_version":1,"status":"pass"}
EOF
printf 'large-ish artifact\n' >"$AGENT_STATE_NOISE_FIXTURE/.agent-state/runs/r2/output.log"
AGENT_STATE_NOISE_JSON="$SMOKE_TMP/agent-state-noise.json"
if skip_if_assurance_missing ".agents/scripts/agent-state-noise-report.py" "agent-state-noise-report.py emits report-only JSON"; then
  :
elif "$ROOT/.agents/scripts/agent-state-noise-report.py" \
  --root "$AGENT_STATE_NOISE_FIXTURE" \
  --format json >"$AGENT_STATE_NOISE_JSON" \
  && python3 - "$AGENT_STATE_NOISE_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
assert payload["report_only"] is True
assert payload["state_source"] is False
assert payload["runner"] is False
assert payload["writes_default"] is False
assert payload["cleanup_executed"] is False
assert payload["agent_state"]["present"] is True
assert payload["runs"]["run_count"] == 2
assert payload["runs"]["missing_manifest_count"] == 1
assert payload["recommendations"]
PY
then
  pass "agent-state-noise-report.py emits report-only JSON"
else
  fail "agent-state-noise-report.py emits report-only JSON"
fi

if skip_if_assurance_missing ".agents/scripts/held-out-manifest-report.py" "held-out-manifest-report.py emits valid JSON"; then
  :
elif "$ROOT/.agents/scripts/held-out-manifest-report.py" \
  --root "$ROOT" \
  --manifest ".agents/evals/held-out/held-out-manifest.example.json" \
  --format json \
  | python3 -m json.tool >/dev/null; then
  pass "held-out-manifest-report.py emits valid JSON"
else
  fail "held-out-manifest-report.py emits valid JSON"
fi

ARCHIVE_HELPER_FIXTURE="$SMOKE_TMP/archive-helper-fixture"
mkdir -p "$ARCHIVE_HELPER_FIXTURE/.agent-state/runs/r1"
cat >"$ARCHIVE_HELPER_FIXTURE/task_plan.md" <<'EOF'
# Task Plan

## Workflow Routing
| field | value |
|---|---|
| Risk Tier | standard |
| Impact Scope | visible |

## Verification Matrix
| acceptance / risk | scenario_id | case_class | evidence method | required checks | test oracle / independence | optional tooling | manual QA | blocking | evidence |
|---|---|---|---|---|---|---|---|---|---|
| A1 | not-needed | workflow | artifact | archive helper smoke | independent-fixture | none | none | block | .agent-state/runs/r1/manifest.json |
EOF
cat >"$ARCHIVE_HELPER_FIXTURE/findings.md" <<'EOF'
# Findings

## Knowledge Promotion
| target | decision | action | source | trust level | refresh when | reason / owner |
|---|---|---|---|---|---|---|
| `README.md` | none | not-needed | not-needed | not-needed | not-needed | no durable knowledge |
EOF
cat >"$ARCHIVE_HELPER_FIXTURE/progress.md" <<'EOF'
# Progress

## Current Status
| item | value |
|---|---|
| summary | archive helper smoke fixture |
| Next Action | none |
EOF
echo '{"schema_version":1,"run_id":"r1","status":"pass","summary":"smoke"}' >"$ARCHIVE_HELPER_FIXTURE/.agent-state/runs/r1/manifest.json"

if "$ROOT/.agents/scripts/create-task-archive.py" \
  --root "$ARCHIVE_HELPER_FIXTURE" \
  --task-id 20260629-smoke-archive \
  --completed-at 2026-06-29 \
  --dry-run \
  --format json \
  | python3 -m json.tool >/dev/null \
  && [[ ! -e "$ARCHIVE_HELPER_FIXTURE/.agents/tasks/20260629-smoke-archive" ]]; then
  pass "create-task-archive.py emits valid dry-run JSON without writing archive"
else
  fail "create-task-archive.py emits valid dry-run JSON without writing archive"
fi

if python_syntax_check "$ROOT/.agents/scripts/search-workflow-history.py"; then
  pass "search-workflow-history.py syntax"
else
  fail "search-workflow-history.py syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/validate-local-skills.py"; then
  pass "validate-local-skills.py syntax"
else
  fail "validate-local-skills.py syntax"
fi

if python3 "$ROOT/.agents/scripts/validate-local-skills.py" --root "$ROOT" --strict-quality --require-compatibility-skills >$SMOKE_TMP/validate-local-skills-strict.out 2>&1; then
  pass "repo-local skills satisfy strict compatibility-only workflow metadata contract"
else
  fail "repo-local skills satisfy strict compatibility-only workflow metadata contract"
fi

if python_syntax_check "$ROOT/.agents/scripts/sensitive-command-guard.py" "$ROOT/.agents/scripts/sensitive_guard_policy.py"; then
  pass "sensitive command guard and policy syntax"
else
  fail "sensitive command guard and policy syntax"
fi

if python_syntax_check "$ROOT/.agents/scripts/hook_event_contract.py" "$ROOT/.agents/scripts/sensitive-edit-guard.py" "$ROOT/.agents/scripts/trajectory-monitor.py"; then
  pass "edit guard and trajectory monitor python syntax"
else
  fail "edit guard and trajectory monitor python syntax"
fi

if sh -n "$ROOT/.agents/scripts/verify-hooks-runtime.sh"; then
  pass "verify-hooks-runtime.sh syntax"
else
  fail "verify-hooks-runtime.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/capture-run-script.sh"; then
  pass "capture-run-script.sh syntax"
else
  fail "capture-run-script.sh syntax"
fi

if sh -n "$ROOT/.agents/scripts/archive-legacy-runs.sh"; then
  pass "archive-legacy-runs.sh syntax"
else
  fail "archive-legacy-runs.sh syntax"
fi

# Lives under SMOKE_TMP so the existing EXIT trap cleans it up; a standalone
# mktemp -d here leaked one directory per run (macOS mktemp also ignores
# TMPDIR without a template, hiding the leak in the default temp dir).
hooks_runtime_tmp="$SMOKE_TMP/hooks-runtime-home"
mkdir -p "$hooks_runtime_tmp"
cat > "$hooks_runtime_tmp/config.toml" <<EOF
[features]
codex_hooks = true

[projects."$ROOT"]
trust_level = "trusted"
EOF

if CODEX_HOME="$hooks_runtime_tmp" "$ROOT/.agents/scripts/verify-hooks-runtime.sh" --format json "$ROOT" >$SMOKE_TMP/hooks-runtime-smoke.json; then
  if python3 - <<'PY' $SMOKE_TMP/hooks-runtime-smoke.json
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["status"] == "healthy", data
assert data["checks"]["project_trust"] == "trusted", data
assert data["checks"]["codex_hooks_feature_flag"] == "enabled", data
PY
  then
    pass "hooks runtime self-check recognizes trusted project"
  else
    fail "hooks runtime self-check recognizes trusted project"
  fi
else
  fail "hooks runtime self-check recognizes trusted project"
fi

}

run_package_contract() {
  run_package_preflight
  run_product_oracles
}

printf 'layer %s: start\n' "$VALIDATION_LAYER"
case "$VALIDATION_LAYER" in
  package-preflight)
    run_package_preflight
    ;;
  product-oracles)
    run_product_oracles
    ;;
  package-contract)
    run_package_contract
    ;;
esac
if [[ "$FAILURES" -eq 0 ]]; then
  printf 'layer %s: pass\n' "$VALIDATION_LAYER"
else
  printf 'layer %s: fail\n' "$VALIDATION_LAYER" >&2
fi

if [[ "$FAILURES" -gt 0 ]]; then
  printf '\nSmoke failed: %d failure(s)\n' "$FAILURES" >&2
  exit 1
fi

printf '\nSmoke passed\n'
