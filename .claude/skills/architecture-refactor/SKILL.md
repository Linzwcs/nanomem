---
name: architecture-refactor
description: Drive a structural code-architecture refactor across folder layout, interface seams, error hierarchy, and module boundaries. Use when the user explicitly asks for architecture optimization, structural cleanup, or "refactor" beyond a single file. Enforces audit → diagnose → propose → sequence → execute-with-review using subagents for context isolation and reviewer-implementer separation.
---

# Architecture Refactor

A disciplined workflow for restructuring a codebase without breaking it.

The goal is **elegant + extensible**: small interfaces in the right places, layers that match the documented architecture, dead seams removed, missing seams added. Not "rewrite". Not "modernize stack". Structural surgery, smallest blast radius first, with independent review between batches.

## When to invoke

Invoke when the user asks for any of:

- "优化代码架构" / "refactor architecture"
- "整理目录结构" / "restructure folders"
- "拆 contracts" / "split this module"
- "补接口" / "add interface seams"
- "消除分层违规" / "fix layering violations"
- Any task that touches **more than 5 files across more than 2 subpackages** and is structural, not feature-driven.

**Do NOT invoke for**:

- Single-file refactors → use direct Edit
- Renaming one symbol → use Edit with `replace_all`
- Bug fixes → those are not refactors
- Feature additions disguised as refactor → split into separate task

## Phase 1 — Inventory

**Goal**: get the actual current state, not the documented state. Documents drift.

**Always launch 2 Explore agents in parallel** (single message, two `Agent` tool calls):

### Explore agent A — import graph & layering

```
Audit the internal import graph of the <package> at <path>. I'm preparing
a structural refactor and need to know exact module-level dependencies.

For EACH top-level subpackage and top-level module, report:
1. What internal imports it makes (only same-package)
2. Which other modules import it (reverse direction)

Focus questions (refactor decisions hinge on these):
- Is <pkg_A> used outside <pkg_B>? (decides whether to merge)
- Does <pkg_X> import from <pkg_Y> or vice versa? (decides direction of dependency)
- Are there layering violations against <documented_rule>? (e.g., does
  server/ import store/ directly when it should go through service/?)
- Are cross-pipeline imports clean? (e.g., does read.py import capture.py?)
- Is <contracts_module> the only inter-module data exchange surface?
- Is <serialization_module> the only JSON/dict conversion surface?

For each finding give file paths and line numbers. Flag surprises
against documented architecture. Under 600 words. Punch list, not prose.
```

### Explore agent B — test coverage & existing seams

```
Two parallel audits on <repo_path>.

## Audit 1: test coverage map
For each top-level subpackage under <src_root>, find tests under <test_root>:
- which files have direct tests (refactor-safe)
- which files have NO direct tests (refactor risk — must add before moving)
- which tests cross packages (integration — break first when modules move)

Specifically: <list_of_pkgs_with_known_thin_coverage>

## Audit 2: existing interface seams
For each subpackage with a base.py / interface file, report the actual
abstract surface (class name, methods, key types).
For subpackages WITHOUT a base.py, report whether the concrete class
could become a Protocol (single impl? duck-typed siblings?).

## Audit 3: inline strings / prompts / configs that should be modules
Search for: large inline string constants (prompts, regexes, templates)
that look like they should be in their own file. Report locations.

## Audit 4: default/factory wiring
Where do defaults live? In factory.py? In service __init__? Both?
(Dual-source defaults are a refactor target.)

Report in under 800 words. File paths and line numbers required.
```

**Synthesize the audits before moving on.** Audits often invalidate prior assumptions ("I thought X was dead code, it's actually used by Y").

## Phase 2 — Diagnose

Cross-check the audits against this 5-category checklist:

1. **Missing interface seams** — concrete classes that are hard-wired but should be Protocols. Symptom: a `from X import ConcreteClass` in a high-level module (e.g., `service/`) when it should be `from X import Protocol`.

2. **Duplicate / fuzzy boundaries** — two subpackages doing the same thing under different names. Verify by import graph: if A imports B but B doesn't import A, **A is a consumer of B, not a sibling** — don't merge.

3. **Layering violations** — module imports across documented layer boundaries. Common cause: a `manager` or `admin` route that needs control-plane data and shortcuts past the service layer.

4. **Inline-what-should-be-extracted** — prompts, regex patterns, JSON schemas, template strings buried in implementation files. They block versioning, A/B, and testing.

5. **Forced future migrations** — design choices that block a clearly-coming need: sync interface that will need async; single-file module that will need to grow; ad-hoc errors that will need a hierarchy.

For each finding, note: (a) the cost to fix now, (b) the cost to fix later, (c) the blast radius. If `later_cost > now_cost` and blast radius is bounded, it goes in the plan.

## Phase 3 — Propose target shape

Write three artifacts:

1. **Target folder tree** — annotated with `NEW` / `MOVED` / `DELETED` / `unchanged` next to every entry. No surprises.

2. **Key new interfaces** — actual Python (or whatever language) signatures, not "we'll add an interface". Concrete enough that the reviewer can check them.

3. **Rename map** — `old.path.X → new.path.X` for every breaking change. Used by reviewer agent to verify nothing leaked.

## Phase 4 — Sequence by blast radius

Order batches **smallest blast radius first**:

1. Pure additions (new test files, new module files that nothing yet imports)
2. New interface extractions (Protocols + type annotations — runtime unchanged)
3. New module promotions (split file into package with back-compat re-export — external API stable)
4. Internal migrations (replace ad-hoc patterns with new utilities — internal only)
5. Renames / moves (back-compat shim during one alpha cycle)
6. Layering fixes (introduce facade, rewire callers)
7. Default consolidation (remove dual-source — touches tests)
8. Polish + version bump + CHANGELOG

**Each batch = one commit.** `pytest` + `compileall` must be green between batches.

**A batch's blast radius is the public-API surface it changes plus the test sites it requires editing.** Estimate before starting; if blast radius exceeds plan, split the batch.

## Phase 5 — Execute

Per batch:

1. Mark task in_progress.
2. Make the edits. Use existing utilities (`serde.py`, `ids.py`, `time.py`, existing `base.py` Protocols) as templates for new code — don't reinvent shape.
3. Run `pytest` + `compileall`. Both green or the batch isn't done.
4. Commit with imperative subject + brief body referencing the plan batch number.
5. Launch reviewer subagent (next phase).
6. Mark task completed only after reviewer green-lights.

**Don't batch-batch** — one commit per batch keeps `git revert` clean.

## Phase 6 — Per-batch review

Launch a **general-purpose** subagent (not the implementer's context) to review each commit.

Reviewer prompt template:

```
Review commit <sha> against batch <N> of the plan at <plan_path>.

Check:
1. Only files listed in the batch (Part E for batch N) were touched.
   Run: git diff --stat <prev_sha> <sha>
2. Public API at `from <pkg> import X` is preserved for X in <preserved_list>.
   Run: python -c "from <pkg> import <preserved_list>"
3. No new `raise ValueError` / `raise KeyError` at cross-module boundaries
   (we have <errors_module>).
4. Tests pass: pytest must be green.
5. No scope leakage — refactor should NOT be touching <out_of_scope_list>.

Report: green / red, with any issues found. Under 200 words.
```

If reviewer returns red: fix in the same batch, do NOT roll forward.

## Phase 7 — Document

After all batches:

1. `CHANGELOG.md` — breaking changes first, with migration snippet for each.
2. **ADR for non-trivial decisions** — if any batch's design choice was non-obvious (e.g., "kept integrations/ separate from adapters/ because import graph shows consumer relationship"), write a 1-page Architecture Decision Record.
3. Update top-level docs map / README architecture section if structure changed.
4. Bump version (semver-pre-release: `0.X.0 → 0.X+1.0a1` for breaking pre-release).

## Anti-patterns to refuse

- **One big-bang PR** — refuse. Each batch must commit independently and pass tests.
- **Skip the test safety net** — refuse. If a subpackage has no tests and you're moving it, add baseline tests first (Batch 1 in this plan).
- **Change `contracts.py` shape without confirmation** — even in alpha. Contracts changes deserve explicit sign-off.
- **"While we're here..."** — refuse. Out-of-scope edits go in a separate session. Scope leakage is how refactors fail.
- **Implement while reviewing** — the reviewer subagent reviews. The implementer implements. Same model in both seats defeats the purpose.
- **Skip the back-compat shim** — when moving a public-ish module, leave a one-cycle shim with `DeprecationWarning`. Cost: 5 lines. Benefit: user trust.

## Quick reference

```
Inventory (Explore × 2 parallel)
  ↓
Diagnose (5-category checklist)
  ↓
Propose (target tree + interfaces + rename map)
  ↓
Sequence (smallest blast radius first)
  ↓
For each batch:
  Implement → pytest+compileall → commit → review → next
  ↓
Document (CHANGELOG + ADRs + version bump)
```

## Subagent allocation

| Phase | Agent type | Count | Why |
|------|-----------|------|-----|
| Inventory | Explore | 2 parallel | context isolation + speed; one for graph, one for tests/seams |
| Diagnose | (main) | — | synthesis happens in main session |
| Propose | (main) or Plan | optional 1 | for very large refactors, one Plan agent to sanity-check sequencing |
| Implement | (main) | — | small batches don't justify worktrees |
| Review | general-purpose | 1 per batch | reviewer-implementer separation |
| Final integration | general-purpose | 1 | full smoke + cross-test |

If batches are independent (rare for refactors — usually sequenced), parallel implementer worktrees can be used. Default: don't.

## What "elegant + extensible" means here

- **Elegant** = small interfaces in the right places. A `render/base.py` with one `render()` method beats a `RendererManager` that wraps `RendererFactory` that builds `RendererStrategy`.
- **Extensible** = future additions need only one new file. Adding `TemporalMergedRenderer` should be one new file in `render/`, not changes across `service/`, `factory.py`, `__init__.py`, and `config.py`.
- **Not extensible** = config switches with N hard-coded branches inside one concrete class. Push to N classes behind a Protocol instead.

The test for both: after this refactor, can you add a new capability (renderer / ranker / extractor / store / index / embedding) by writing exactly one new file plus one factory branch? If yes, the refactor succeeded.
