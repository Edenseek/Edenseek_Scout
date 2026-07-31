"""Correction Ledger (Scout 6.3, Phase A).

Deterministic, structured audit record built purely from the geometry + metadata deltas. Each
entry cites the object (``artifact_id``), the ``stage`` it belongs to, the ``operation`` (the
correction the human approval represents relative to automation), a short ``evidence`` string,
and the ``delta`` payload. Advisory only; no I/O, no LLM. Entries are emitted in a stable
sorted order so the ledger is byte-reproducible from frozen inputs.
"""


def build_correction_ledger(geometry_delta, metadata_delta):
    """Assemble the Correction Ledger from the two deltas. Not-applicable (manual) deltas
    contribute no entries. Returns a list sorted by ``(stage, artifact_id, operation)``."""
    entries = []

    def add(artifact_id, stage, operation, evidence, delta):
        entries.append({
            "artifact_id": artifact_id, "stage": stage, "operation": operation,
            "evidence": evidence, "delta": delta,
        })

    if geometry_delta.get("applicable"):
        thr = {"iou_threshold": geometry_delta["iou_threshold"]}
        for aid in geometry_delta["missing_page_artifact_ids"]:
            add(aid, "geometry", "missing_panel",
                "approved page panel with no matching automated panel (recall gap)", thr)
        for aid in geometry_delta["spread_missing_artifact_ids"]:
            add(aid, "geometry", "spread_missing_panel",
                "approved spread panel with no matching automated spread (spread-frame recall gap)",
                {**thr, "note": "matched spread-to-spread within page_range (spread-canvas geometry)"})
        for aid in geometry_delta["false_artifact_ids"]:
            add(aid, "geometry", "false_panel",
                "automated panel with no matching approved panel (precision gap)", thr)
        for aid in geometry_delta["split_artifact_ids"]:
            add(aid, "geometry", "panel_split",
                "approved panel covered by more than one automated panel", thr)
        for aid in geometry_delta["merge_artifact_ids"]:
            add(aid, "geometry", "panel_merge",
                "automated panel covering more than one approved panel", thr)

    if metadata_delta.get("applicable"):
        for aid in metadata_delta["generated_only_artifact_ids"]:
            add(aid, "metadata", "artifact_removed_at_approval",
                "automated metadata artifact absent from the approved set", {})
        for aid in metadata_delta["approved_only_artifact_ids"]:
            add(aid, "metadata", "artifact_added_at_approval",
                "approved metadata artifact absent from automation", {})
        for aid in metadata_delta["schema_version_mismatch_artifact_ids"]:
            add(aid, "metadata", "schema_version_mismatch",
                "generated vs approved metadata schema versions differ; excluded from field metrics", {})
        for aid, t in sorted(metadata_delta.get("per_artifact", {}).items()):
            if t["edited"] or t["deleted"] or t["added"]:
                add(aid, "metadata", "fields_corrected",
                    "approval edited/removed/added metadata fields relative to automation",
                    {"edited": t["edited"], "deleted": t["deleted"], "added": t["added"]})

    entries.sort(key=lambda e: (e["stage"], str(e["artifact_id"]), e["operation"]))
    return entries
