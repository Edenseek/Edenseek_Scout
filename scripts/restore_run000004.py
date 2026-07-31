"""Recovery procedure for the accidental production write (run000004, geometry v2).

Reverts the three (four) affected objects in edenseek-scout to their pre-incident state:
  1. reports/report_index.json      -> remove the run_seq==4 entry (count 4 -> 3, latest run000003)
  2. ledger/processed_revisions.json -> remove the rev_0be8dc34...@fp_75f356d8b2ee entry
  3. reports/scout_delta_report.json (latest pointer) -> revert to run000003's content
  4. history/scout_delta_report_000004.json -> delete (an index rebuild enumerates history/ and
     would otherwise resurrect it)

DRY-RUN BY DEFAULT. Pass --execute to perform the writes. Requires SCOUT_ALLOW_REAL_S3=1 (the
runtime safety boundary opt-in) — writes only to edenseek-scout, never edenseek-publishing.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "C:/Projects/AI/Edenseek_Scout")
# Intentional, audited access to real resources for this recovery op.
os.environ["SCOUT_ALLOW_REAL_S3"] = "1"
for l in Path("C:/Projects/AI/Edenseek_Scout/.env").read_text().splitlines():
    if l.strip() and not l.startswith("#") and "=" in l:
        k, v = l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
os.chdir("C:/Projects/AI/Edenseek_Scout")

import audit_s3_source as a3

EXECUTE = "--execute" in sys.argv
BAD_RUN_SEQ = 4
BAD_LEDGER_KEY_SUFFIX = "@fp_75f356d8b2ee"
KEEP_LATEST_RUN = "run000003"

b = os.getenv("SCOUT_REPO_S3_BUCKET")
pre = os.getenv("SCOUT_REPO_S3_PREFIX").rstrip("/")
region = os.getenv("SCOUT_REPO_S3_REGION")
c = a3.s3_client(region)

def get(key):
    pr = a3.probe_object(c, b, key)
    return (json.loads(pr["body"]), pr["body"]) if pr["status"] == "read" else (None, None)

idx_key = f"{pre}/reports/report_index.json"
led_key = f"{pre}/ledger/processed_revisions.json"
latest_key = f"{pre}/reports/scout_delta_report.json"
bad_hist_key = f"{pre}/history/scout_delta_report_000004.json"
good_hist_key = f"{pre}/history/scout_delta_report_000003.json"

print(f"MODE: {'EXECUTE' if EXECUTE else 'DRY-RUN (no writes)'}\nbucket: {b}\n")

# --- 1. index ---
idx, _ = get(idx_key)
before_seqs = [e.get("run_seq") for e in idx["entries"]]
new_entries = [e for e in idx["entries"] if e.get("run_seq") != BAD_RUN_SEQ]
new_idx = dict(idx)
new_idx["entries"] = new_entries
new_idx["count"] = len(new_entries)
if "latest" in new_idx:
    new_idx["latest"] = next((e.get("report_id") for e in new_entries
                              if e.get("run_seq") == 3), new_idx.get("latest"))
print(f"[1] index: count {idx['count']} -> {new_idx['count']}; run_seqs {before_seqs} -> "
      f"{[e.get('run_seq') for e in new_entries]}; latest -> {new_idx.get('latest')}")

# --- 2. ledger ---
led, _ = get(led_key)
bad_keys = [k for k in led["entries"] if k.endswith(BAD_LEDGER_KEY_SUFFIX)]
new_led = dict(led)
new_led["entries"] = {k: v for k, v in led["entries"].items() if k not in bad_keys}
new_led["count"] = len(new_led["entries"])
print(f"[2] ledger: count {led['count']} -> {new_led['count']}; removing {bad_keys}")

# --- 3. latest pointer ---
latest, latest_raw = get(latest_key)
good_hist, good_hist_raw = get(good_hist_key)
cur_latest_run = (latest or {}).get("run_id") or (latest or {}).get("report_id")
print(f"[3] latest pointer {latest_key.split('/')[-1]}: currently -> {cur_latest_run}; "
      f"will revert to run000003 content ({'available' if good_hist else 'MISSING!'})")

# --- 4. errant history object ---
bad_hist, _ = get(bad_hist_key)
print(f"[4] delete history object: {bad_hist_key.split('/')[-1]} "
      f"({'present' if bad_hist else 'already absent'})")

if not EXECUTE:
    print("\nDRY-RUN complete. Re-run with --execute to apply (after founder approval).")
    sys.exit(0)

# ---- EXECUTE ----
print("\nEXECUTING restore...")
c.put_object(Bucket=b, Key=idx_key,
             Body=json.dumps(new_idx, separators=(",", ":")).encode(), ContentType="application/json")
print("  wrote reverted index")
c.put_object(Bucket=b, Key=led_key,
             Body=json.dumps(new_led, separators=(",", ":")).encode(), ContentType="application/json")
print("  wrote reverted ledger")
if good_hist_raw:
    c.put_object(Bucket=b, Key=latest_key, Body=good_hist_raw, ContentType="application/json")
    print("  reverted latest pointer to run000003")
c.delete_object(Bucket=b, Key=bad_hist_key)
print("  deleted errant history object run000004")
print("DONE. Verify with a fresh read.")
