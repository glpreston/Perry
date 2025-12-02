# Changelog

## [Unreleased]
Refactor: split `config.py` into `agents.py`, `orchestrator.py`, `server_utils.py`, `router.py`, and `prompt_builder.py`.
Compatibility: `config.py` now re-exports key symbols to preserve existing imports.
Fixed: memory injection sanitization to strip leading agent name prefixes.
## 0.2.0
- Initial working prototype.
