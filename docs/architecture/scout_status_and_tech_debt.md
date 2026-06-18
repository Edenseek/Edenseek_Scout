# Edenseek Scout — Operational Status & Technical Debt

> Internal tracking document for engineering work and operational milestones.
> Companion to [`scout_v0.3_synopsis.md`](./scout_v0.3_synopsis.md) (current architecture) and
> [`scout_future_vision.md`](./scout_future_vision.md) (long-term direction).

---

## Open / Planned

### Logging
- **Description:** Application relies mostly on console output.
- **Recommended Fix:** Implement logging to `logs/scout.log`.
- **Status:** Planned

### Scheduler Reliability
- **Description:** APScheduler runs in-process and may behave differently after restarts or future
  scaling.
- **Recommended Fix:** Verify scheduler operation and evaluate persistent job storage.
- **Status:** Open

---

## Completed

### Oracle VM Deployment
- **Status:** Complete

### systemd Persistence
- **Status:** Complete

### GitHub Synchronization
- **Status:** Complete

### OpenAI Integration
- **Status:** Complete

---

## Next Security Review

The following items are queued for the next dedicated security pass. Listed in priority order.

1. **Authentication**
   - Add authentication/authorization to the API. `POST /run-scout` (and read endpoints) are
     currently open, allowing anyone with network access to trigger billable OpenAI calls.

2. **Path Traversal Verification**
   - Verify and harden `/report/{filename}`. The filename is joined directly to `reports/` with only
     an existence check, so inputs such as `../.env` could read arbitrary files — including the
     `OPENAI_API_KEY`. Confirm the resolved path stays within `reports/`.

3. **HTTPS**
   - Ensure all traffic is served over TLS (terminate at a reverse proxy or configure directly) so
     credentials and report content are not transmitted in plaintext.

4. **Rate Limiting**
   - Apply rate limiting to `/run-scout` (and other mutating/expensive endpoints) to contain cost
     and denial-of-service exposure from repeated triggering.
