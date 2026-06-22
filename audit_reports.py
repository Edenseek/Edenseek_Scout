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


_RENDERERS = {
    "dataset": _render_dataset,
    "character": _render_character,
    "dialogue": _render_dialogue,
    "retrieval": _render_retrieval,
    "weak_artifacts": _render_weak,
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
