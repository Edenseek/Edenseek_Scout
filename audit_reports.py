"""Render Phase 1 audit results to Markdown + machine-readable JSON blocks.

Each report follows ``docs/architecture/REPORT_SPECIFICATION.md`` §4: a human
narrative followed by a deterministic ```json``` block. Filenames are fixed per
type (Phase 1 uses deterministic filenames, not timestamps), so re-running
overwrites in place. Reports are written only under Scout's own ``reports/`` tree.
"""
from pathlib import Path
import json

REPORTS_ROOT = Path("reports")

# report type -> (subdirectory, filename)
REPORT_FILES = {
    "dataset": ("dataset", "dataset_quality_report.md"),
    "character": ("character", "character_analysis_report.md"),
    "dialogue": ("dialogue", "dialogue_analysis_report.md"),
    "retrieval": ("retrieval", "retrieval_readiness_report.md"),
    "weak_artifacts": ("weak_artifacts", "weak_artifact_queue.md"),
    "review_priority": ("review_priority", "review_priority_queue.md"),
    "page_heatmap": ("page_heatmap", "page_heat_map.md"),
    "audit_history": ("audit_history", "audit_history.md"),
    "root_cause": ("root_cause", "root_cause_report.md"),
    "highest_leverage": ("highest_leverage", "highest_leverage_failure_report.md"),
    "failure_clusters": ("failure_clusters", "failure_cluster_report.md"),
    "retrieval_blockers": ("retrieval_blockers", "retrieval_blockers_report.md"),
    "historical": ("historical", "historical_intelligence_report.md"),
    "retrieval_readiness": ("retrieval_readiness", "retrieval_readiness_intel.md"),
}

_ADVISORY = (
    "> Read-only advisory report. Scout inspects, scores, and recommends only; it does not "
    "modify canonical data, approve metadata, or bypass publisher review (Charter §4)."
)


def _json_block(obj):
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```\n"


def _findings_lines(findings, key="issue"):
    if not findings:
        return ["- None"]
    lines = []
    for f in findings:
        ref = f.get("artifact_id") or f.get("packet_id")
        prefix = f"`{ref}` — " if ref else ""
        text = f.get(key) or f.get("gap") or ""
        rec = f.get("recommendation")
        line = f"- **[{f.get('severity', 'info')}]** {prefix}{text}"
        if rec:
            line += f" _→ {rec}_"
        lines.append(line)
    return lines


def _render_dataset(block, generated_at):
    b = block
    c = b["completeness"]
    cov = b["coverage"]
    lines = [
        f"# Dataset Quality Report — {b['dataset']}",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Dataset: {b['dataset']}",
        f"- Artifacts: {b['artifact_count']}",
        f"- Overall quality score: {b['quality_score']}/100",
        "",
        "## Metadata Completeness",
        f"- Fields present: {c['metadata_fields_present']} / {c['metadata_fields_required']}",
        f"- Fields ever missing: {', '.join(c['fields_missing']) if c['fields_missing'] else 'none'}",
        "",
        "## Coverage",
        f"- Approved: {cov['approved']} / {cov['total']}",
        f"- Reviewed: {cov['reviewed']} / {cov['total']}",
        f"- Locked: {cov['locked']} / {cov['total']}",
        "",
        "## Findings",
        *_findings_lines(b["findings"]),
        "",
    ]
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_character(block, generated_at):
    b = block
    rc = b["recognition_coverage"]
    lines = [
        "# Character Analysis Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Recognition coverage (consistency_score): {b['consistency_score']}/100",
        f"- Artifacts with characters: {rc['artifacts_with_characters']} / {rc['artifacts_total']}",
        "",
        "## Reference Utilization",
        f"- Available: {', '.join(b['reference_materials']['available']) or 'none'}",
        f"- Unused: {', '.join(b['reference_materials']['unused']) or 'none'}",
        "",
        "## Findings",
        *_findings_lines(b["findings"]),
        "",
    ]
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_dialogue(block, generated_at):
    b = block
    pc = b["population_coverage"]
    lines = [
        "# Dialogue Analysis Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Dialogue population coverage (completeness_score): {b['dialogue_completeness_score']}/100",
        f"- Artifacts with dialogue: {pc['artifacts_with_dialogue']} / {pc['artifacts_total']}",
        "",
        "## Findings",
        *_findings_lines(b["findings"]),
        "",
    ]
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_retrieval(block, generated_at):
    b = block
    lines = [
        "# Retrieval Readiness Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Retrieval readiness score: {b['retrieval_readiness_score']}/100",
        f"- Packets evaluated: {b['packets_evaluated']}",
        "",
        "## Findings",
        *_findings_lines(b["findings"]),
        "",
        "_Scout assesses readiness only; it never performs or alters retrieval (Charter §4)._",
        "",
    ]
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_weak(block, generated_at):
    b = block
    sev = b["by_severity"]
    lines = [
        "# Weak Artifact Queue",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Total flagged: {b['total_flagged']}",
        f"- By severity: critical {sev['critical']}, high {sev['high']}, medium {sev['medium']}, low {sev['low']}",
        "",
        "## Queue (advisory worklist for human review)",
    ]
    if b["queue"]:
        lines.append("")
        lines.append("| Artifact | Score | Severity | Weakness | Suggested action |")
        lines.append("|----------|-------|----------|----------|------------------|")
        for q in b["queue"]:
            lines.append(
                f"| `{q['artifact_id']}` | {q['score']} | {q['severity']} | {q['weakness']} | {q['suggested_action']} |"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _page_label(page):
    return "unpaged" if not isinstance(page, int) else str(page)


def _render_review_priority(block, generated_at):
    b = block
    bi = b["by_impact"]
    lines = [
        "# Review Priority Queue",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Total ranked: {b['total']}",
        f"- By estimated impact: high {bi['high']}, medium {bi['medium']}, low {bi['low']}",
        "",
        "## Queue (ranked; review top-down)",
    ]
    if b["queue"]:
        lines.append("")
        lines.append("| Rank | Artifact | Page | Impact | Severity | Effort | Primary weakness | Suggested action |")
        lines.append("|------|----------|------|--------|----------|--------|------------------|------------------|")
        for q in b["queue"]:
            lines.append(
                f"| {q['priority_rank']} | `{q['artifact_id']}` | {_page_label(q['page'])} | "
                f"{q['estimated_impact']} | {q['severity']} | {q['effort']} | "
                f"{q['primary_weakness']} | {q['suggested_action']} |"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_page_heatmap(block, generated_at):
    b = block
    lines = [
        "# Page Heat Map",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Pages covered: {len(b['pages'])}",
        f"- Unpaged artifacts: {b['unpaged_count']}",
        "",
        "## Pages (worst first)",
        "",
        "| Page | Artifacts | Weak | Impact | critical | high | medium | low |",
        "|------|-----------|------|--------|----------|------|--------|-----|",
    ]
    for p in b["pages"]:
        s = p["by_severity"]
        lines.append(
            f"| {_page_label(p['page'])} | {p['artifact_count']} | {p['weak_count']} | "
            f"{p['page_impact']} | {s['critical']} | {s['high']} | {s['medium']} | {s['low']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_audit_history(block, generated_at):
    b = block
    delta = b.get("latest_delta")
    lines = [
        "# Audit History",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Trend",
    ]
    if delta:
        lines.append(f"- Latest quality change: {delta['quality_score_change']:+d} ({delta['direction']})")
    else:
        lines.append("- Not enough history yet for a trend (need at least two audits).")
    lines += [
        "",
        "## Snapshots (oldest → newest)",
        "",
        "| Timestamp | Quality | Metadata | Character | Dialogue | Retrieval | Weak flagged |",
        "|-----------|---------|----------|-----------|----------|-----------|--------------|",
    ]
    for h in b["history"]:
        sc = h["scores"]
        lines.append(
            f"| {h['timestamp']} | {h['quality_score']} | {sc['metadata_completeness']} | "
            f"{sc['character_consistency']} | {sc['dialogue_completeness']} | "
            f"{sc['retrieval_readiness']} | {h['weak_total_flagged']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _ids_sample(failure):
    ids = failure["affected_artifact_ids"]
    shown = ", ".join(f"`{i}`" for i in ids[:10])
    extra = failure["affected_count"] - min(10, len(ids))
    return shown + (f" … (+{extra} more)" if extra > 0 else "")


def _render_root_cause(block, generated_at):
    b = block
    lines = [
        "# Root Cause Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Artifacts: {b['artifact_count']}",
        f"- Failure categories: {len(b['failures'])}",
        "",
        "_Diagnostic only: Scout explains where the dataset fails; it does not prescribe "
        "engineering actions or predict score changes._",
        "",
        "## Failures (most prevalent first)",
        "",
        "| Failure | Domain | Severity | Impact | Affected | % | Pages |",
        "|---------|--------|----------|--------|----------|---|-------|",
    ]
    for f in b["failures"]:
        pages = ", ".join(str(p) for p in f["affected_pages"]) or "—"
        lines.append(
            f"| {f['failure_type']} | {f['domain']} | {f['severity']} | {f['estimated_impact']} | "
            f"{f['affected_count']} | {f['affected_percent']} | {pages} |"
        )
    lines.append("")
    lines.append("### Affected artifacts (sample)")
    for f in b["failures"]:
        lines.append(f"- **{f['failure_type']}** ({f['affected_count']}): {_ids_sample(f)}")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_highest_leverage(block, generated_at):
    b = block
    top = b["highest_leverage_failure"]
    lines = [
        "# Highest Leverage Failure Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Largest content-quality failure",
    ]
    if top:
        lines += [
            f"- **{top['failure_type']}** ({top['domain']})",
            f"- Affected: {top['affected_count']} ({top['affected_percent']}%)",
            f"- Impact band: {top['estimated_impact']}",
            f"- {top['rationale']}",
        ]
    else:
        lines.append("- No content-quality failures detected.")
    lines += [
        "",
        "_Diagnostic only: this names the dominant failure and its scale. It does not "
        "prescribe engineering actions or predict numeric score changes._",
        "",
        "## Ranked content failures",
        "",
        "| Failure | Domain | Affected | % | Impact |",
        "|---------|--------|----------|---|--------|",
    ]
    for f in b["ranked_failures"]:
        lines.append(
            f"| {f['failure_type']} | {f['domain']} | {f['affected_count']} | "
            f"{f['affected_percent']} | {f['estimated_impact']} |"
        )
    lines += ["", "## Process backlog (publisher workflow, reported separately)"]
    if b["process_backlog"]:
        for k, v in b["process_backlog"].items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_failure_clusters(block, generated_at):
    b = block
    t = b["thresholds"]
    lines = [
        "# Failure Cluster Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Artifacts: {b['artifact_count']}",
        f"- Thresholds: issue-wide ≥ {t['issue_wide_percent']}%, page cluster ≥ "
        f"{int(t['page_fraction'] * 100)}% of page (min {t['min_count']})",
        "",
        "_Diagnostic only: locates where failures concentrate. Workflow failures are shown "
        "and tagged separately from content failures._",
        "",
        "## Issue-wide failures (systemic)",
        "",
        "| Failure | Category | Domain | Severity | Affected | % | Impact |",
        "|---------|----------|--------|----------|----------|---|--------|",
    ]
    for f in b["issue_wide_failures"]:
        lines.append(
            f"| {f['failure_type']} | {f['category']} | {f['domain']} | {f['severity']} | "
            f"{f['affected_count']} | {f['affected_percent']} | {f['estimated_impact']} |"
        )
    lines += ["", "## Page clusters (localized)"]
    if b["page_clusters"]:
        lines += [
            "",
            "| Page | Failure | Category | Affected | Page total | Concentration | Impact |",
            "|------|---------|----------|----------|------------|---------------|--------|",
        ]
        for c in b["page_clusters"]:
            lines.append(
                f"| {c['page']} | {c['failure_type']} | {c['category']} | {c['affected_count']} | "
                f"{c['page_artifact_count']} | {c['concentration_percent']}% | {c['estimated_impact']} |"
            )
    else:
        lines.append("- None (failures are systemic, not page-localized).")
    lines += ["", "## Unpaged bucket (artifact identity / page-mapping)"]
    if b["unpaged_cluster"]:
        uc = b["unpaged_cluster"]
        lines.append(f"- Unpaged artifacts: {uc['artifact_count']}")
        for f in uc["failures"]:
            lines.append(f"  - {f['failure_type']} ({f['category']}): {f['affected_count']}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_retrieval_blockers(block, generated_at):
    b = block
    pc = b["packet_coverage"]
    lines = [
        "# Retrieval Blockers Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Retrieval readiness score: {b['retrieval_readiness_score']}/100",
        f"- Packet coverage: {pc['artifacts_referenced']} / {pc['artifact_count']} artifacts "
        f"({pc['coverage_percent']}%), {pc['packets_evaluated']} packet(s)",
        "",
        "_Scout assesses readiness only; it never performs or implements retrieval (Charter §4)._",
        "",
        "## Packet blockers",
    ]
    if b["packet_blockers"]:
        for pb in b["packet_blockers"]:
            detail = f" — {pb['detail']}" if pb.get("detail") else ""
            lines.append(f"- **[{pb['severity']}]** {pb['blocker']} (packets: {pb['affected_packets']}){detail}")
    else:
        lines.append("- None")
    lines += [
        "",
        "## Artifact blockers (dataset readiness for grounding)",
        "",
        "| Blocker | Severity | Affected | % | Impact |",
        "|---------|----------|----------|---|--------|",
    ]
    for ab in b["artifact_blockers"]:
        lines.append(
            f"| {ab['blocker_type']} | {ab['severity']} | {ab['affected_count']} | "
            f"{ab['affected_percent']} | {ab['estimated_impact']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_historical(block, generated_at):
    b = block
    w = b["window"]
    lines = [
        "# Historical Intelligence Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Summary",
        f"- Dataset: {b['dataset_id']}",
        f"- Snapshots analyzed: {b['snapshots_analyzed']}",
        f"- Confidence: {b['confidence']}",
        f"- Window: {w['first']} → {w['last']}",
        "",
        f"_{b['note']}_",
    ]
    if b["confidence"] == "insufficient_history":
        return "\n".join(lines) + "\n\n" + _json_block(b)

    lines += [
        "",
        "## Metric trends",
        "",
        "| Metric | First | Last | Change | Direction | Consistency |",
        "|--------|-------|------|--------|-----------|-------------|",
    ]
    for m in b["metrics"]:
        lines.append(
            f"| {m['name']} | {m['first']} | {m['last']} | {m['change']:+d} | "
            f"{m['direction']} | {m['consistency']} |"
        )

    lines += ["", "## Failure-category trends (% of artifacts)", "",
              "| Failure | Domain | First % | Last % | Change | Direction |",
              "|---------|--------|---------|--------|--------|-----------|"]
    for f in b["failure_trends"]:
        lines.append(
            f"| {f['failure_type']} | {f['domain']} | {f['first_percent']} | "
            f"{f['last_percent']} | {f['change']:+d} | {f['direction']} |"
        )

    lines += ["",
              f"- New failures since first audit: {', '.join(b['new_failures']) or 'none'}",
              f"- Resolved failures: {', '.join(b['resolved_failures']) or 'none'}",
              "",
              "## Stagnant pipeline areas"]
    if b["stagnant_domains"]:
        for d in b["stagnant_domains"]:
            lines.append(f"- {d['domain']}: {d['first_percent']}% → {d['last_percent']}% ({d['change']:+d})")
    else:
        lines.append("- None")

    delta = b["delta"]
    lines += ["", "## Since previous audit"]
    if delta:
        lines.append(f"- {delta['from']} → {delta['to']}")
        qd = delta["metrics"].get("quality_score", 0)
        lines.append(f"- Quality change: {qd:+d}")
        moved = {k: v for k, v in delta["failures"].items() if v != 0}
        lines.append("- Failure % changes: " +
                     (", ".join(f"{k} {v:+d}" for k, v in sorted(moved.items())) or "none"))

    lines += ["", "## Observed correlations (observational only — not causal)"]
    if b["observed_correlations"]:
        for c in b["observed_correlations"]:
            changes = ", ".join(f"{k} {v}" for k, v in sorted(c["inferred_changes"].items()))
            lines.append(f"- {c['interval']['from']} → {c['interval']['to']}: "
                         f"quality {c['quality_change']:+d}; co-occurring: {changes}")
    else:
        lines.append("- None observed")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


def _render_retrieval_readiness(block, generated_at):
    b = block
    lines = [
        "# Retrieval Readiness Intelligence Report",
        "",
        f"Generated: {generated_at}",
        "",
        _ADVISORY,
        "",
        "## Verdict",
        f"- **{b['verdict']}**",
        f"- Readiness score: {b['readiness_score']}/100",
        f"- {b['explanation']}",
        "",
        "_Assesses readiness only; Scout never performs or implements retrieval, and makes no "
        "recommendations or predictions._",
        "",
        "## Dimensions",
        "",
        "| Dimension | Status | Measured | Evidence |",
        "|-----------|--------|----------|----------|",
    ]
    for d in b["dimensions"]:
        lines.append(
            f"| {d['dimension']} | {d['status']} | {d['measured_percent']}% | {d['evidence']} |"
        )
    lines += [
        "",
        f"- Strengths: {', '.join(b['strengths']) or 'none'}",
        f"- Weaknesses: {', '.join(b['weaknesses']) or 'none'}",
        "",
        "## Readiness trend",
    ]
    if b["trend"]:
        lines.append(f"- retrieval_readiness: {b['trend'].get('retrieval_readiness')} "
                     f"(confidence: {b['trend'].get('confidence')})")
    else:
        lines.append("- Insufficient history for a readiness trend.")
    lines.append("")
    return "\n".join(lines) + "\n" + _json_block(b)


_RENDERERS = {
    "dataset": _render_dataset,
    "character": _render_character,
    "dialogue": _render_dialogue,
    "retrieval": _render_retrieval,
    "weak_artifacts": _render_weak,
    "review_priority": _render_review_priority,
    "page_heatmap": _render_page_heatmap,
    "audit_history": _render_audit_history,
    "root_cause": _render_root_cause,
    "highest_leverage": _render_highest_leverage,
    "failure_clusters": _render_failure_clusters,
    "retrieval_blockers": _render_retrieval_blockers,
    "historical": _render_historical,
    "retrieval_readiness": _render_retrieval_readiness,
}


def render_report(report_type, block, generated_at):
    """Return the full Markdown (with JSON block) for one report type."""
    return _RENDERERS[report_type](block, generated_at)


def write_reports(result, reports_root=REPORTS_ROOT, generated_at=""):
    """Write all five reports under ``reports_root``; return {type: relpath}."""
    reports_root = Path(reports_root)
    written = {}
    for report_type, (subdir, filename) in REPORT_FILES.items():
        block = result["blocks"][report_type]
        target_dir = reports_root / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        target.write_text(render_report(report_type, block, generated_at), encoding="utf-8")
        written[report_type] = str(target.as_posix())
    return written
