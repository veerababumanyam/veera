## 0.2.0

### Added
- Automatic risk-first Sol/Astra execution for bounded read-only delegates, available in both hosts through the route skill. Includes native model receipts, failure handling and a Codex bridge for Claude. Active coordinator model selection remains controlled by the host.

# Changelog

## 0.1.7 â€” 2026-10-22

### Added
- Native Codex manifest selecting the Codex skills and hooks, including a Windows hook command.
- Sol/Astra task-routing policy: GPT-6.1 Sol for light work and GPT-6 Astra for important work.
- Portable light/important Codex profile templates. Profiles remain opt-in; the policy does not itself switch an active coordinator's model.
- Bootstrap context includes the installed package root and Python executable. Codex bootstrap also provides its model-routing policy.

### Fixed
- Native Windows runtime compatibility: file locking, bounded pipe capture, and verification-child cleanup through Windows jobs. Windows requires Python 3.12 or later.
- Windows path comparisons and shell-path parsing, plus UTF-8 documentation checks.
- Codex skill discovery and namespaced start trigger; the legacy `$veera-start` bootstrap trigger remains accepted.

### Activation
- Install and enable Veera in user scope to make it available across projects. Start each task in its intended Git checkout.
- Codex hooks require native trust review before live bootstrap. An installation or test fixture does not establish a live session's identity.
- Claude-native agents retain the selected Claude model; the GPT routing policy applies to Codex.
