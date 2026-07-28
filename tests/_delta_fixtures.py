"""Shared deterministic fixtures for the Scout 6.3 delta tests — grounded on the REAL Publisher
emitted shapes captured in publisher_bridge/real_shape_samples.json (+ _addendum.json):

  * generated panel rows carry pixel ``bbox`` [x1,y1,x2,y2] AND normalized ``bounds``;
  * approved page panels are normalized ``{x,y,width,height}`` (+ deleted/isNew);
  * approved SPREAD panels carry ``isSpreadPanel`` + ``stage_geometry`` (page x/y/w/h degenerate);
  * metadata content is nested under ``output.{classification.tags, entities.characters,
    narrative.dialogue, narrative.summary}`` — ``tags`` is NORMALLY a ``{action,mood,setting}``
    dict on BOTH sides (Publisher census: 94-95/97), rarely a flat list (1/97, a human edit), and
    may be ``null`` (2/97). This fixture grounds on that norm: ``1_10`` = dict-vs-dict ACCEPT,
    ``1_3`` = the rare dict-vs-list EDIT outlier, ``1_7`` = null-tags (both sides). Scout's
    shape-agnostic value-equality handles all three;
  * a manual publication carries the sentinel + null generated sides.
Offline; no I/O."""

IDENTITY = {"publisher_id": "edenseek", "title_group_id": "society_universe",
            "series_id": "society_of_killers", "issue_id": "issue_001"}


def _gen_panel(panel_key, page_number, bbox_px, bounds):
    return {"panel_key": panel_key, "page_id": panel_key.rsplit("::", 1)[0], "page_number": page_number,
            "panel_id": panel_key.rsplit("::", 1)[1], "order": page_number, "bbox": bbox_px,
            "bounds": bounds, "coordinate_space": "page", "panel_image": "x.png",
            "width": bbox_px[2], "height": bbox_px[3]}


def _meta_out(artifact_id, tags, characters, dialogue, summary, review_state="unreviewed"):
    """A full nested metadata output (provenance + plumbing + the content subtree)."""
    return {
        "artifact_id": artifact_id, "input_ref": artifact_id, "version": "v1.1",
        "metadata_locked": review_state == "approved", "metadata_review_state": review_state,
        "status": "complete",
        "context_source": [{"material_type": "script", "revision_id": "rev_script"}],
        "geometry_source": {"approved_revision": "rev_geo", "artifact_geometry_hash": "sha256:abc"},
        "output": {"classification": {"tags": tags},
                   "entities": {"characters": characters},
                   "narrative": {"dialogue": dialogue, "summary": summary}},
    }


def review_generated():
    """Generated publication Review Record (C): 3 matching page panels + 1 approved-only NEW page
    panel (missing) + 1 approved spread panel (missing). Metadata grounded on the Publisher tags
    census: ``1_10`` tags dict-vs-dict ACCEPT (the norm) + dialogue added; ``1_3`` the rare
    dict-vs-list tags EDIT outlier (+ chars/summary edited); ``1_7`` null-tags on both sides."""
    return {
        "review_report_version": "v1",
        "issue_identity": IDENTITY,
        "review_id": "rev_abc123def456",
        "generated_geometry": {
            "property_id": "society_of_killers", "issue_number": 1,
            "total_pages": 24, "total_story_pages": 22, "total_panels": 3,
            "panels": [
                _gen_panel("society_of_killers_1_10::p1", 10, [0, 0, 2063, 2864],
                           {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.9092}),
                _gen_panel("society_of_killers_1_3::p1", 3, [70, 57, 1997, 723],
                           {"x": 0.03, "y": 0.02, "width": 0.93, "height": 0.23}),
                _gen_panel("society_of_killers_1_7::p1", 7, [206, 286, 1238, 1719],
                           {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}),
            ],
        },
        "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": [
            # tags dict {action,mood,setting} == approved dict -> ACCEPT (the norm)
            _meta_out("society_of_killers_1_10::p1",
                      {"action": "observation", "mood": "tense", "setting": "holding pen"},
                      ["Quentin Larouche"], [], "Guards stand around a cage."),
            _meta_out("society_of_killers_1_3::p1",
                      {"action": "smoking", "mood": "edgy", "setting": "design"},
                      ["Astrid"], [], "Astrid, stylized."),
            # tags null on both sides -> the null path (neither accept nor edit)
            _meta_out("society_of_killers_1_7::p1", None,
                      ["Marlowe"], [], "A quiet room."),
        ]},
        "approved_geometry": {
            # matched pairs (normalized 0..1)
            "society_of_killers_1_10::p1": {"x": 0, "y": 0, "width": 1, "height": 0.9999, "approved": True},
            "society_of_killers_1_3::p1": {"x": 0.03, "y": 0.02, "width": 0.93, "height": 0.23, "approved": True},
            "society_of_killers_1_7::p1": {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5, "approved": True},
            # approved-only drawn page panel -> missing
            "11::NEW::1": {"x": 0.65, "y": 0.74, "width": 0.34, "height": 0.23, "isNew": True, "deleted": False},
            # approved spread panel -> always missing (stage_geometry; page coords degenerate)
            "spread_12_13::p1": {"isSpreadPanel": True, "page_range": [12, 13], "deleted": False,
                                 "x": 0, "y": 0, "width": 0.01, "height": 0.01,
                                 "stage_geometry": {"x": 0.006, "y": 0.057, "width": 0.247, "height": 0.385}},
        },
        "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": [
            # panel_10: tags dict==dict ACCEPT, characters accepted, dialogue added, summary accepted
            _meta_out("society_of_killers_1_10::p1",
                      {"action": "observation", "mood": "tense", "setting": "holding pen"},
                      ["Quentin Larouche"], ["Get back!"], "Guards stand around a cage.", "approved"),
            # panel_3: tags dict->list (the rare human EDIT outlier), characters + summary edited
            _meta_out("society_of_killers_1_3::p1", ["character design"],
                      ["Astrid St. James"], [], "Astrid St. James, stylized character design.", "approved"),
            # panel_7: tags null==null (no-op), characters + summary accepted
            _meta_out("society_of_killers_1_7::p1", None,
                      ["Marlowe"], [], "A quiet room.", "approved"),
            # approved-only metadata artifacts (the NEW + spread)
            _meta_out("11::NEW::1", ["Coat of Arms"], ["None"], ["None"], "Coat of arms.", "approved"),
            _meta_out("spread_12_13::p1", ["splash"], ["None"], [], "A spread.", "approved"),
        ]},
        "provenance": {"published_revision_id": "rev_abc123def456aaaabbbb",
                       "generated_vs_approved": {"state": "generated_publication",
                                                 "generated_snapshot_revision_id": "rev_gen0000"}},
    }


def review_manual():
    """Manual publication Review Record (C): generated sides null + manual sentinel
    (grounded on real rev_65d5f1059e0a)."""
    return {
        "review_report_version": "v1",
        "issue_identity": IDENTITY,
        "review_id": "rev_65d5f1059e0a",
        "generated_geometry": None,
        "generated_metadata": None,
        "approved_geometry": {"society_of_killers_1_1::p1": {"x": 0, "y": 0, "width": 1, "height": 1}},
        "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": [
            _meta_out("society_of_killers_1_1::p1", ["cover"], ["None"], [], "Cover.", "approved")]},
        "provenance": {"published_revision_id": "rev_65d5f1059e0affff",
                       "generated_vs_approved": "not_applicable_manual_publication"},
    }


def platform_approval():
    return {
        "platform_approval_version": "v1",
        "review_id": "rev_abc123def456",
        "published_revision_id": "rev_abc123def456aaaabbbb",
        "canonical_dataset_state": "edenseek_approved",
        "state_transition": ["creator_approved", "edenseek_approved"],
        "platform_authority": {"actor": "Edenseek Platform - Derek", "approved_at": "2026-07-27T22:46:31Z"},
        "readiness": {"readiness_version": "v1", "geometry_artifact_count": 5,
                      "metadata_artifact_count": 5, "hard_failures": [], "warnings": [],
                      "passes_integrity": True},
        "certifies_review_report_key":
            "publishers/edenseek/.../issues/issue_001/reviews/rev_abc123def456/review_report.json",
    }
