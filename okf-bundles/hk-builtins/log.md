# Update Log

## 2026-11-14

- **Create**: Established hk builtins offline documentation bundle
- **Create**: Added lychee.md - Fast, async, stream-based link checker
- **Create**: Added lychee-extended.md - Flint's repository-aware link check
- **Create**: Added index.md - Bundle overview and quick reference
- **Create**: Added lychee-vs-lychee-extended.md - Comparison & recommendation
- **Source**: hk.jdx.dev/builtins.html (v2.12.0, last updated 2026-11-09)
- **Decision**: Recommend **lychee** for cpp-core (simpler, sufficient for our flat doc structure)

## 2026-11-14 (later)

- **Configure**: Added lychee builtin to hk.pkl (check, pre-commit, pre-push hooks)
- **Create**: Added lychee.toml with URL exclusions for unreliable/404 links
- **Update**: lychee.md with cpp-core specific configuration example
- **Update**: lychee-vs-lychee-extended.md with actual deployed config
- **Verify**: All 27 hk checks pass including lychee
