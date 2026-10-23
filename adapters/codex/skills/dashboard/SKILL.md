---
name: dashboard
description: Open the current Veera task dashboard or return its live browser URL and saved address path when the user asks for status, dashboard or tracking.
---

# Veera dashboard

Read `docs/dashboard.md` from the actual installed package root. Use the current task's recorded owner identity, root and capability; never invent identity or enumerate another session. Reuse the current live URL, or call the owner-authorized `dashboard-info` command to obtain its validated URL and absolute record path. Return both as clickable links when the user asks for the path. Start a missing server in a host-tracked background process with `dashboard`; it opens the browser by default. Use native browser controls with its returned URL if needed. Preserve the process handle and terminal shutdown behavior. A browser problem is not an implementation blocker. Do not require Veera bootstrap just to reuse an already-known live link, or claim this request resumes a stopped implementation.
