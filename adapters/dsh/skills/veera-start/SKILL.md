---
name: veera-start
description: Optional Veera identity and setup diagnostic for DeepSeek Harness; Build/Fix captures the current DSH session identity automatically and does not require this command.
---

# Veera — optional start diagnostic (DeepSeek Harness)

Build/Fix starts automatically from ordinary software task requests; explicit commands are optional and there is no separate start step. Use this skill only when the user explicitly wants an identity/setup diagnostic.

From the veera package root (`$VEERA_ROOT`, else `C:/Users/VeeraDesktop/Desktop/veera`), run `python scripts/bootstrap.py --dsh`. Report the returned `package_root`, `plugin_data`, `python_executable`, `session_id` and `package_version`. Start alone does not begin a task, grant publication authority, or enroll a session. Do not invent IDs, inspect other sessions, alter native permissions, or manufacture a bootstrap result.
