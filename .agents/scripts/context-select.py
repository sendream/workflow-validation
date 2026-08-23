#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import context_selection_contract as selection_contract
from current_task_snapshot import CurrentTaskSnapshot, load_current_task_snapshot
import workflow_routing as wr


DEFAULT_BUDGETS = {
    "fast": 8000,
    "standard": 12000,
    "high": 20000,
    "release": 20000,
}

BASE_FORBIDDEN = (
    ".agent-state/** raw logs",
    ".agents/tasks/** full archives",
    "graphify-out/**",
    ".codegraph/**",
    "codegraph-out/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "target/**",
    "coverage/**",
)
GATE_CARD_PATH = ".agents/references/workflow/gate-cards.md"


@dataclass
class ContextItem:
    path: str
    reason: str


def file_estimated_tokens(root: Path, path: str) -> int:
    target = root / path
    if not target.is_file():
        return 0
    try:
        return max(1, target.stat().st_size // 4)
    except OSError:
        return 0


def normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def is_doc_only_prompt(prompt: str) -> bool:
    return contains_any(
        prompt,
        (
            "文档",
            "说明",
            "readme",
            "docs",
            "documentation",
            "typo",
            "错别字",
            "拼写",
        ),
    ) and not contains_any(
        prompt,
        (
            "external-system",
            "external system",
            "外部系统",
            "生产",
            "prod",
            "production",
            "rollback",
            "回滚",
            "artifact",
            "交付包",
            "发布包",
            "上线",
            "发版",
        ),
    )


def has_release_signal(prompt: str) -> bool:
    signals = selection_contract.classify_prompt_signals(prompt)
    return "release" in selection_contract.signal_values(signals, kind="risk") and not is_doc_only_prompt(prompt)


EVOLUTION_DOMAIN_SIGNALS = (
    "evolution",
    "harness-experiment",
    "held-out",
    "workflow value",
    "workflow-value",
    "stale-assumption",
    "进化",
)


def is_eval_or_test_path(path: str) -> bool:
    """Behavior/oracle tests are verification assets, not evolution by themselves."""

    lowered = path.replace("\\", "/").lower()
    name = lowered.rsplit("/", 1)[-1]
    return (
        "/evals/" in f"/{lowered}"
        or lowered.startswith("evals/")
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name in {"run_behavior_evals.py", "run_harness_modularization_evals.py"}
    )


def domain_evidence_blob(prompt: str, explicit_paths: list[str] | None = None) -> str:
    production_paths = [path for path in (explicit_paths or []) if not is_eval_or_test_path(path)]
    return " ".join([prompt, *production_paths])


def workflow_domain(prompt: str, explicit_paths: list[str] | None = None) -> str:
    """Classify a workflow-maintenance task by changed domain, not by task class."""

    paths = explicit_paths or []
    blob = domain_evidence_blob(prompt, paths)
    if contains_any(blob, EVOLUTION_DOMAIN_SIGNALS):
        return "evolution"
    if has_external_skill_intake_signal(blob):
        return "external-skill"
    if contains_any(
        blob,
        (
            "hooks.json",
            "hook-preset",
            "workflow.manifest",
            "apply-starter-pack",
            "profile",
            "merge-hooks",
        ),
    ):
        return "tooling"
    if contains_any(blob, ("archive", "closeout", "overlay", "lifecycle", "归档", "收口")):
        return "lifecycle"
    if contains_any(
        blob,
        (
            "evidence",
            "validator",
            "waiver",
            "claim-evidence",
            "verification",
            "traceability",
            "证据",
        ),
    ):
        return "verification"
    if paths and all(is_eval_or_test_path(path) for path in paths):
        return "verification"
    return "routing"


def has_negated_behavior_language(prompt: str) -> bool:
    return contains_any(
        prompt,
        (
            "no behavior change",
            "without behavior change",
            "without changing behavior",
            "does not change behavior",
            "不改行为",
            "不改变行为",
            "无行为变化",
        ),
    )


def has_strong_contract_signal(prompt: str) -> bool:
    return contains_any(
        prompt,
        (
            "api",
            "field contract",
            "permission",
            "compatibility",
            "negative-boundary",
            "字段",
            "契约",
            "权限",
            "认证",
            "导入",
            "导出",
            "跨层",
            "负向",
            "边界场景",
        ),
    )


def has_weak_behavior_signal(prompt: str) -> bool:
    return contains_any(
        prompt,
        (
            "behavior contract",
            "observable behavior",
            "behavior scenario",
            "行为合同",
            "可观察行为",
        ),
    )


def has_packaging_or_overlay_signal(prompt: str) -> bool:
    return contains_any(
        prompt,
        (
            "overlay",
            "packaging",
            "install-contract",
            "交付包",
            "发布包",
            "hooks.json",
            "deployable artifact",
            "release source",
            "部署包",
        ),
    )


def behavior_contract_state(prompt: str, task_class: str = "", domain: str = "") -> str:
    """Return yes / no / unknown. Unknown lets high/release keep a conservative G09."""

    negated = has_negated_behavior_language(prompt)
    strong = has_strong_contract_signal(prompt)
    weak = has_weak_behavior_signal(prompt)
    if is_doc_only_prompt(prompt):
        return "no"
    if negated and (strong or weak):
        return "unknown"
    if negated:
        return "no"
    if strong or weak:
        return "yes"
    if has_packaging_or_overlay_signal(prompt):
        return "no"
    if task_class == "workflow" and domain in {"routing", "tooling", "lifecycle", "evolution"}:
        return "no"
    return "unknown"


def has_external_skill_intake_signal(prompt: str) -> bool:
    if contains_any(
        prompt,
        (
            "external skill",
            "external-skill",
            "mcp",
            "connector",
            "外部 skill",
            "外部插件",
            "外部工具",
            "install skill",
        ),
    ):
        return True
    return contains_any(prompt, ("plugin", "插件")) and contains_any(prompt, ("external", "外部"))


def infer_task_class(prompt: str, explicit: str | None) -> str:
    value = normalize(explicit)
    if value in {"fast", "complex", "review", "release", "workflow"}:
        return value
    if has_release_signal(prompt):
        return "release"
    if contains_any(prompt, ("review", "audit", "审查", "评估", "复盘", "核查")):
        return "review"
    if contains_any(prompt, ("workflow", "starter-pack", "validator", "工作流")):
        return "workflow"
    if contains_any(prompt, ("跨模块", "迁移", "重构", "多阶段", "handoff")):
        return "complex"
    return "fast"


def inferred_routing(
    root: Path,
    risk_tier: str | None,
    impact_scope: str | None,
    task_class: str,
    prompt: str,
    use_active_task: bool,
    snapshot: CurrentTaskSnapshot | None,
) -> tuple[str, str, list[str], list[str]]:
    explicit_risk = normalize(risk_tier)
    explicit_impact = normalize(impact_scope)
    active_snapshot_complete = bool(
        use_active_task and snapshot is not None and snapshot.source_status == "complete"
    )
    active_risk = snapshot.risk_tier if active_snapshot_complete and snapshot is not None else None
    active_impact = snapshot.impact_scope if active_snapshot_complete and snapshot is not None else None
    signals = selection_contract.classify_prompt_signals(prompt)
    positive_signals = list(signals["positive"])
    routing_evidence = [f"negated:{entry}" for entry in signals["negated"]]
    if is_doc_only_prompt(prompt):
        suppressed = [entry for entry in positive_signals if entry.startswith(("risk:release:", "impact:external-system:"))]
        positive_signals = [entry for entry in positive_signals if entry not in suppressed]
        routing_evidence.extend(f"doc-only-suppressed:{entry}" for entry in suppressed)
    routing_evidence.extend(f"candidate:{entry}" for entry in positive_signals)
    routing_evidence.extend(f"explicit:risk:{explicit_risk}" for _ in [0] if explicit_risk)
    routing_evidence.extend(f"explicit:impact:{explicit_impact}" for _ in [0] if explicit_impact)
    if use_active_task and snapshot is not None:
        routing_evidence.append(f"active-task:source-status:{snapshot.source_status}")
    routing_evidence.extend(f"active-task:risk:{active_risk}" for _ in [0] if active_risk)
    routing_evidence.extend(f"active-task:impact:{active_impact}" for _ in [0] if active_impact)

    default_risk = "low" if task_class == "fast" else "standard"
    default_impact = "visible"
    risk = explicit_risk or active_risk or default_risk
    impact = explicit_impact or active_impact or default_impact
    positive_impact_values = selection_contract.signal_values({"positive": positive_signals}, kind="impact")
    if not explicit_impact and not active_impact and "cross-package" in positive_impact_values:
        # This is a conservative advisory default for source-range planning,
        # not authorization to perform a cross-package change.
        impact = "cross-package"

    # Confirmation is field-specific.  An explicit risk tier cannot verify an
    # external-system impact candidate (and vice versa); otherwise a partial
    # CLI/task record would silently hide an irreversible-scope signal.
    verified_by_kind = {
        "risk": explicit_risk or active_risk,
        "impact": explicit_impact or active_impact,
    }
    needs_confirmation: list[str] = []
    if use_active_task and snapshot is not None and snapshot.source_status != "complete":
        needs_confirmation.append(f"active-task:source-status:{snapshot.source_status}")
    for entry in positive_signals:
        parts = entry.split(":", 2)
        if len(parts) != 3:
            continue
        kind, value, _matched_text = parts
        if verified_by_kind.get(kind) != value:
            needs_confirmation.append(entry)
    if risk not in wr.VALID_RISK_TIERS:
        risk = "standard"
    if impact not in wr.VALID_IMPACT_SCOPES:
        impact = "visible"
    return risk, impact, routing_evidence, needs_confirmation


def current_stage_estimate(phase: str, required_stages: list[dict[str, Any]]) -> int:
    phase_stage = {
        "validation": "verification",
        "verification": "verification",
        "test": "verification",
        "testing": "verification",
        "review": "review",
        "audit": "review",
        "closeout": "lifecycle",
        "delivery": "lifecycle",
        "handoff": "lifecycle",
    }.get(phase, "current")
    for stage in required_stages:
        if stage.get("stage") == phase_stage:
            return int(stage.get("tokens", 0))
    for stage in required_stages:
        if stage.get("stage") == "current":
            return int(stage.get("tokens", 0))
    return 0


def required_budget_stages(root: Path, must_read: list[ContextItem], required_paths: list[str]) -> list[dict[str, Any]]:
    required = set(required_paths)
    stages: list[tuple[str, list[str]]] = [("current", [item.path for item in must_read if item.path in required])]
    group_specs = (
        ("active-state", ("task_plan.md", "progress.md", "findings.md")),
        ("review", ("code_review.md", "reviewer-governance.md")),
        ("verification", ("verification-evidence.md", "validator-map.md")),
        ("lifecycle", ("lifecycle-recovery.md",)),
        ("tooling", ("tooling-safety.md",)),
        ("evolution", ("evolution-experiments.md",)),
    )
    assigned = set(stages[0][1])
    for name, suffixes in group_specs:
        paths = [path for path in required_paths if path not in assigned and any(path.endswith(suffix) for suffix in suffixes)]
        if paths:
            stages.append((name, paths))
            assigned.update(paths)
    for path in required_paths:
        if path not in assigned:
            stages.append((f"required-{len(stages) + 1}", [path]))
            assigned.add(path)
    return [
        {
            "stage": name,
            "paths": paths,
            "tokens": sum(file_estimated_tokens(root, path) for path in paths),
        }
        for name, paths in stages
        if paths
    ]


def add_unique(items: list[ContextItem], path: str, reason: str) -> None:
    if not any(item.path == path for item in items):
        items.append(ContextItem(path, reason))


def add_gate_card(cards: list[dict[str, str]], gate_id: str, reason: str) -> None:
    """Expose one on-demand Gate Card anchor without adding its whole file to context."""

    if not any(card["id"] == gate_id for card in cards):
        cards.append({"id": gate_id, "path": f"{GATE_CARD_PATH}#{gate_id}", "reason": reason})


def build_selection(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    prompt = args.prompt or ""
    task_class = infer_task_class(prompt, args.task_class)
    use_active_task = bool(args.use_active_task or task_class != "fast")
    snapshot = load_current_task_snapshot(root) if use_active_task else None
    risk_tier, impact_scope, routing_evidence, needs_confirmation = inferred_routing(
        root,
        args.risk_tier,
        args.impact_scope,
        task_class,
        prompt,
        use_active_task,
        snapshot,
    )
    phase = normalize(args.phase) or "unspecified"

    must_read: list[ContextItem] = []
    conditional_read: list[ContextItem] = []
    manifest_refs: list[ContextItem] = []
    route_required: list[str] = []
    selected_gate_cards: list[dict[str, str]] = []
    history_queries: list[str] = []
    structural_index_decision = "not-needed"

    add_unique(must_read, "AGENTS.md", "top-level project workflow routing and hard boundaries")

    explicit_paths = [path.strip() for path in args.explicit_path if path.strip()]
    domain = workflow_domain(prompt, explicit_paths) if task_class == "workflow" else ""
    complex_like = task_class in {"complex", "release", "workflow"} or risk_tier in {"high", "release"} or impact_scope in {"cross-package", "external-system"}
    review_like = task_class == "review"
    release_like = task_class == "release" or risk_tier == "release" or impact_scope == "external-system"

    if complex_like:
        primary_module = ".agents/references/workflow/routing-planning.md"
        primary_reason = "complex-task routing, clarification, scope, and planning contract"
        if task_class == "workflow":
            if domain == "verification" or phase in {"validation", "verification", "test", "testing"}:
                primary_module = ".agents/references/workflow/verification-evidence.md"
                primary_reason = "workflow verification or evidence-contract change"
            elif domain == "lifecycle" or phase in {"closeout", "delivery", "handoff"}:
                primary_module = ".agents/references/workflow/lifecycle-recovery.md"
                primary_reason = "workflow lifecycle, archive, or overlay change"
            elif domain in {"tooling", "external-skill"}:
                primary_module = ".agents/references/workflow/tooling-safety.md"
                primary_reason = "workflow hook, profile, or installer change"
            elif domain == "evolution":
                primary_module = ".agents/references/workflow/evolution-experiments.md"
                primary_reason = "workflow eval or evolution-mechanism change"
            else:
                primary_reason = "workflow routing, gate, or template change"
        elif phase in {"validation", "verification", "test", "testing"}:
            primary_module = ".agents/references/workflow/verification-evidence.md"
            primary_reason = "current validation phase evidence and verification contract"
        elif phase in {"review", "audit"}:
            primary_module = ".agents/references/workflow/reviewer-governance.md"
            primary_reason = "current review phase authorization and reviewer contract"
        elif phase in {"closeout", "delivery", "handoff"}:
            primary_module = ".agents/references/workflow/lifecycle-recovery.md"
            primary_reason = "current closeout phase lifecycle and recovery contract"
        add_unique(must_read, primary_module, primary_reason)
        route_required.append(primary_module)
        add_unique(conditional_read, ".agents/references/workflow/context-memory.md", "context, handoff, archive, and long-term knowledge only when needed")
        add_unique(conditional_read, ".agents/references/workflow/verification-evidence.md", "verification and evidence gates when implementation or validation starts")
        add_unique(conditional_read, ".agents/references/workflow/lifecycle-recovery.md", "failure recovery, lifecycle, and closeout when the matching phase starts")
        add_unique(conditional_read, "task_plan.md", "active task contract when an active complex task exists")
        add_unique(conditional_read, "progress.md", "active task status and evidence when an active complex task exists")
        add_unique(conditional_read, "findings.md", "active findings and knowledge-promotion rows when an active complex task exists")
        if use_active_task and snapshot is not None and snapshot.task_id is not None:
            route_required.extend(("task_plan.md", "progress.md", "findings.md"))

    if impact_scope in {"cross-package", "external-system"}:
        add_gate_card(selected_gate_cards, "G04_SCOPE_BRAKE", "impact scope can expand beyond a minimal local slice")

    explicit_reviewer = review_like or contains_any(
        prompt,
        (
            "role reviewer",
            "isolated reviewer",
            "policy-auto",
            "只读挑战",
            "只读 reviewer",
            "role-review",
            "residual semantic",
        ),
    )
    if review_like or risk_tier in {"high", "release"} or (risk_tier == "standard" and task_class != "fast"):
        add_unique(conditional_read, "code_review.md", "code review tier and local/enhanced review checklist")
    if review_like or explicit_reviewer or phase in {"review", "audit"}:
        add_unique(conditional_read, ".agents/references/workflow/reviewer-governance.md", "review authorization, reviewer policy, and human decision boundary")
        add_gate_card(selected_gate_cards, "G00_REVIEW_AUTH", "review/audit output must remain within its write authorization")
        add_gate_card(selected_gate_cards, "G19_CODE_REVIEW", "current route needs a proportionate review tier")
        route_required.extend(("code_review.md", ".agents/references/workflow/reviewer-governance.md"))
    if explicit_reviewer:
        add_gate_card(selected_gate_cards, "G16_ROLE_REVIEWER", "explicit read-only reviewer challenge or residual semantic risk")

    if release_like:
        add_gate_card(selected_gate_cards, "G17_SHIP_CHECK", "explicit delivery needs a yes/conditional/no bound to the contract")
        add_unique(conditional_read, ".agents/references/validator-map.md", "select release/evidence/reviewer validators without loading every validator")
        manifest_refs.append(ContextItem(".agent-state/runs/<run_id>/manifest.json", "read only run manifests referenced by progress/task_plan evidence fields"))
        route_required.extend(
            (
                ".agents/references/workflow/verification-evidence.md",
                ".agents/references/workflow/lifecycle-recovery.md",
                ".agents/references/validator-map.md",
            )
        )

    if risk_tier in {"high", "release"} or impact_scope == "external-system":
        add_gate_card(selected_gate_cards, "G10_TEST_EVIDENCE", "high-risk or external route requires evidence or a typed waiver")
    contract_state = behavior_contract_state(prompt, task_class, domain)
    if contract_state == "yes" or (
        contract_state == "unknown"
        and (risk_tier in {"high", "release"} or impact_scope == "external-system")
    ):
        add_gate_card(
            selected_gate_cards,
            "G09_BEHAVIOR_CONTRACT",
            "observable behavior change needs a scenario or explicit not-needed",
        )

    if release_like and contains_any(prompt, ("artifact", "产物", "deployable", "部署包", "交付包", "container", "镜像", "jar", "dist")):
        add_gate_card(selected_gate_cards, "G18_RELEASE_SOURCE", "deployable artifact requires source provenance")

    if phase in {"closeout", "delivery", "handoff"}:
        add_gate_card(selected_gate_cards, "G21_TASK_CLOSEOUT", "terminal lifecycle phase requires bounded closeout")

    if contains_any(prompt, ("commit", "push", "提交", "推送", "staged", "暂存")):
        add_gate_card(selected_gate_cards, "G20_PUSH_OVERLAY", "delivery action needs overlay and staged-scope protection")

    if contains_any(prompt, ("需求", "prd", "requirement", "验收", "acceptance")):
        add_gate_card(selected_gate_cards, "G03_CLARIFICATION", "requirements or acceptance wording may need a decision-ready contract")

    if contains_any(prompt, ("历史", "archive", "归档", "previous task", "长期知识", "knowledge")):
        history_queries.append(args.history_query or "<derive targeted query from task terms>")
        add_unique(conditional_read, ".agents/references/validator-map.md", "history search boundary and archive/run manifest validators")

    if task_class != "fast" and contains_any(
        prompt,
        (
            "wsl",
            "ssh",
            "构建",
            "部署",
            "maven",
            "pnpm",
            "known-bad",
            "坏路径",
            "环境债务",
            "environment debt",
        ),
    ):
        add_unique(conditional_read, ".agents/references/project-conventions.md", "stable execution matrix and known-bad paths before retrying a toolchain")
        add_unique(conditional_read, ".agents/references/common-pitfalls.md", "verified pitfalls and wrong shortcuts to skip")
        add_unique(conditional_read, ".agents/references/workflow/context-memory.md", "durable knowledge write path; no promotion table")

    if task_class != "fast" and contains_any(prompt, ("graphify", "codegraph", "structural index", "调用链", "影响面", "全仓", "结构索引")):
        structural_index_decision = "explicit-read-only-query"
        add_gate_card(selected_gate_cards, "G14_STRUCTURAL_INDEX", "explicit structure query remains read-only and source-confirmed")
        add_unique(conditional_read, ".agents/references/tooling-map.md", "structural index read-only query class and tool boundaries")
        add_unique(conditional_read, ".agents/references/workflow/tooling-safety.md", "Structural Index Decision and stale/source-confirmation rules")

    internal_tooling_safety = task_class != "fast" and (
        domain in {"tooling", "external-skill"}
        or contains_any(
            prompt,
            (
                "node_modules",
                "patch-package",
                "dom adapter",
                "browser patch",
                "浏览器补丁",
                "hooks.json",
                "apply-starter-pack",
                "workflow.manifest",
            ),
        )
    )
    if internal_tooling_safety:
        add_unique(
            conditional_read,
            ".agents/references/workflow/tooling-safety.md",
            "internal hook, installer, or repo-local tool safety; not External Skill intake",
        )
        route_required.append(".agents/references/workflow/tooling-safety.md")
    if has_external_skill_intake_signal(prompt) or domain == "external-skill":
        add_gate_card(selected_gate_cards, "G22_EXTERNAL_SKILL", "external skill, plugin, connector, or MCP candidate")
        add_unique(conditional_read, ".agents/references/workflow/tooling-safety.md", "external capability intake and authorization boundary")
        route_required.append(".agents/references/workflow/tooling-safety.md")

    if domain == "evolution" or (
        task_class != "fast"
        and contains_any(
            prompt,
            (
                "进化",
                "evolution",
                "harness-experiment",
                "workflow value",
                "workflow effect",
                "workflow 效果",
                "真实项目 workflow",
                "task_epoch",
            ),
        )
    ):
        add_unique(conditional_read, ".agents/references/workflow/evolution-experiments.md", "workflow value, experiment, stale-assumption, and promotion boundaries")
        route_required.append(".agents/references/workflow/evolution-experiments.md")

    for path in explicit_paths:
        add_unique(must_read, path, "explicitly supplied by user/task")

    must_paths = {item.path for item in must_read}
    conditional_read = [item for item in conditional_read if item.path not in must_paths]

    required_paths = list(dict.fromkeys([item.path for item in must_read] + route_required))
    unresolved_required = [path for path in required_paths if not (root / path).is_file()]
    must_tokens = sum(file_estimated_tokens(root, item.path) for item in must_read)
    conditional_tokens = sum(file_estimated_tokens(root, item.path) for item in conditional_read)
    forecast_total = must_tokens + conditional_tokens
    budget_key = "fast" if task_class == "fast" and risk_tier in {"low", "standard"} else risk_tier
    budget = DEFAULT_BUDGETS.get(budget_key, DEFAULT_BUDGETS["standard"])
    required_stages = required_budget_stages(root, must_read, required_paths)
    budget_report = selection_contract.build_budget_report(
        initial_load_estimate=must_tokens,
        current_stage_estimate=current_stage_estimate(phase, required_stages),
        forecast_total_estimate=forecast_total,
        budget_tokens=budget,
        measurement_status="inferred",
        required_stages=required_stages,
        unresolved=bool(unresolved_required),
    )

    return {
        "kind": "context-selection",
        "selector_kind": "workflow-reference",
        "code_context": "not-implemented",
        "source_of_truth": "AGENTS.md routing plus explicit user/task inputs; prompt text is advisory evidence only",
        "not_a_gate": True,
        "not_a_runner": True,
        "root": str(root),
        "inputs": {
            "task_class": task_class,
            "risk_tier": risk_tier,
            "impact_scope": impact_scope,
            "phase": phase,
            "prompt_supplied": bool(prompt),
            "used_active_task_routing": use_active_task,
            "active_task_source_status": snapshot.source_status if snapshot is not None else "not-used",
            "explicit_paths": explicit_paths,
        },
        "must_read": [asdict(item) for item in must_read],
        "conditional_read": [asdict(item) for item in conditional_read],
        "selected_gate_cards": selected_gate_cards,
        "do_not_read_by_default": list(BASE_FORBIDDEN),
        "history_queries": history_queries,
        "structural_index_decision": structural_index_decision,
        "manifest_refs": [asdict(item) for item in manifest_refs],
        "required_when_reached": required_paths,
        "unresolved_required": unresolved_required,
        "routing_evidence": routing_evidence,
        "needs_confirmation": needs_confirmation,
        "budget": budget_report,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Produce a report-only context read plan for the current task.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--task-class", choices=("fast", "complex", "review", "release", "workflow"), help="Task class hint.")
    parser.add_argument("--risk-tier", choices=wr.VALID_RISK_TIERS, help="Risk tier hint.")
    parser.add_argument("--impact-scope", choices=wr.VALID_IMPACT_SCOPES, help="Impact scope hint.")
    parser.add_argument("--phase", help="Current phase, for reporting only.")
    parser.add_argument("--prompt", help="Short task prompt or summary used only for routing hints.")
    parser.add_argument("--history-query", help="Explicit summary/manifest history query to suggest.")
    parser.add_argument("--explicit-path", action="append", default=[], help="User-specified file/path that must be read.")
    parser.add_argument("--use-active-task", action="store_true", help="Allow task_plan.md to influence routing even for fast task hints.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser.parse_args(argv)


def emit_text(selection: dict[str, Any]) -> None:
    inputs = selection["inputs"]
    print(f"Context selection: {inputs['task_class']} / {inputs['risk_tier']} / {inputs['impact_scope']}")
    budget = selection["budget"]
    print(
        "Budget: "
        f"initial={budget['initial_status']} ({budget['initial_load_estimate']}/{budget['budget_tokens']} inferred), "
        f"forecast={budget['forecast_status']} ({budget['forecast_total_estimate']}/{budget['budget_tokens']} inferred)"
    )
    print("Must read:")
    for item in selection["must_read"]:
        print(f"- {item['path']}: {item['reason']}")
    print("Conditional read:")
    for item in selection["conditional_read"]:
        print(f"- {item['path']}: {item['reason']}")
    print("Selected Gate Cards:")
    for card in selection["selected_gate_cards"]:
        print(f"- {card['id']}: {card['path']} ({card['reason']})")
    print("Do not read by default:")
    for item in selection["do_not_read_by_default"]:
        print(f"- {item}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    selection = build_selection(args)
    if args.format == "text":
        emit_text(selection)
    else:
        json.dump(selection, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 1 if selection["unresolved_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
