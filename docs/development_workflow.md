# Development Workflow

## Feature Specs
Features are specified and ordered in [feats/README.md](feats/README.md). Tackle them in numbered order; each spec lists its dependencies, requirements, and acceptance criteria. Resolve a spec's `TODO:` items before or during its implementation.

## Adding Features
1. **Plan:** State intent and architectural impact in 2 sentences.
2. **Verify:** Check the relevant `docs/feats/NN_*.md` spec and existing `docs/` files for constraints before writing.
3. **Execute:** Modify only the affected files.

## Token Saving Strategy
- Do not request full file rewrites unless the file is under 50 lines.
- For bug fixes, ask for "incremental diffs" or "function-only updates."
- If stuck, run `grep` or search within the project to identify relevant code blocks before asking for help.