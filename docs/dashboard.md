# Opening and finding the live dashboard

## Start automatically with implementation

After successful task init, the coordinator starts `delivery.py dashboard` in a host-tracked background process **before the first implementation edit**. The command opens the loopback dashboard in the default browser automatically, saves its address in `TASK/.veera/dashboard.json`, and prints both the URL and the absolute record path. Use the actual task, interpreter, session and owner capability from bootstrap/workspace. This is part of every standard-lane Build/Fix workflow; do not ask the user to request it or approve a routine local preview again.

Capture that output, retain the host process handle, and give the user a clickable **Live dashboard** link immediately. Confirm that it opens; a browser-launch request alone does not prove the page loaded. On Codex desktop, use the native browser-opening tool with the returned URL if the default browser did not open. On a headless host use `--no-open`, provide the address and explain the available browser path. A browser-opening failure does not stop implementation: continue with the valid address visible to the user.

Run only one dashboard for the task. A repeated dashboard invocation reuses the existing server/address. The server remains local, requires the URL's random token, and closes 60 seconds after the task becomes terminal. Preserve the URL as private task context, not in commits or external messages. The saved JSON is an address record, not a standalone/offline dashboard.

The small lane (one bounded, unpublished defect) does not launch the dashboard: the run is short and its evidence lives in the task state. Start it only if the user asks, through the same command.

## When the user asks for the dashboard or its path

Use `delivery.py dashboard-info --root TASK --session-id ACTUAL_ID --capability-file OWNER_FILE`. It checks only the current owned task and returns `dashboard_url`, the absolute `record_path`, and liveness. Return the live URL as a clickable link and the record path as a file link. Never guess a port or fabricate a URL, scan other task records, or offer `web/index.html` as though it were a live dashboard.

If no current server is running for an active owned task, start it through the same background workflow and return the new address. A stale address is not a working dashboard. Successful completion releases the task binding: afterward reuse the already-returned link during its grace period, or provide the saved task-local record path from known task context. Do not call owner-only dashboard-info with a released capability or restart an expired task merely to get a link. Reporting the path never resumes implementation or grants additional authority.

## Workflow command forms

Replace the placeholders with actual values and use the returned absolute interpreter on Windows. The first command keeps serving and belongs in the host's tracked background task facility, not a blocking foreground call.

```text
PYTHON PACKAGE/scripts/delivery.py dashboard --root TASK --session-id ACTUAL_ID --capability-file OWNER_FILE
PYTHON PACKAGE/scripts/delivery.py dashboard-info --root TASK --session-id ACTUAL_ID --capability-file OWNER_FILE
```

The new dashboard skill handles explicit requests to open, find or share this task's local dashboard address. Automatic launch is prescribed by Build/Fix skill orchestration; the bare `init` library function stays free of browser/process side effects for embedded use and tests.
