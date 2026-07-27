# User-only Skill Invocation Implementation Plan

**Goal:** Honor `disable-model-invocation: true` without weakening explicit
skill invocation or prompt caching.

**Architecture:** One metadata predicate in `agent/skill_utils.py` feeds the
existing prompt and listing scanners. Discovery records canonical precedence
before applying the autonomous-visibility filter.

**Tech stack:** Python, YAML frontmatter, pytest through
`scripts/run_tests.sh`.

## Constraints

- No model tool, plugin, environment variable, or mid-session prompt mutation.
- Local/profile skills retain precedence over external directories.
- Tests assert behavior and relationships, not catalog snapshots.
- The existing config raw-cache failure remains out of scope.

## Task 1: Specify autonomous visibility

**Files**

- Modify: `tests/agent/test_prompt_builder.py`
- Modify: `tests/agent/test_external_skills.py`

1. Add a prompt contract showing a user-only skill is hidden while a normal
   skill is offered.
2. Exercise the disk snapshot path with the same contract.
3. Add a local-user-only/external-model-invoked collision contract.
4. Run the exact new tests and confirm they fail because the skills are still
   offered.

## Task 2: Specify explicit invocation and cache stability

**Files**

- Modify: `tests/agent/test_external_skills.py`
- Modify: `tests/agent/test_skill_commands.py`
- Modify: `tests/agent/test_skill_commands_reload.py`
- Modify: `tests/tools/test_skills_tool.py`

1. Prove `skill_view(name)` loads user-only content.
2. Prove slash-command discovery and invocation load user-only content.
3. Prove `skills_list` omits user-only skills.
4. Build a prompt, reload slash commands after changing the user-only skill,
   and prove the cached prompt is byte-identical.
5. Run the new tests; existing explicit-load tests may already pass, while the
   autonomous-listing contract must fail.

## Task 3: Implement the metadata policy

**Files**

- Modify: `agent/skill_utils.py`
- Modify: `agent/prompt_builder.py`
- Modify: `tools/skills_tool.py`

1. Add `skill_allows_model_invocation(frontmatter)`.
2. Add the normalized flag to prompt snapshot entries and bump the snapshot
   schema version.
3. Exclude user-only entries from prompt rendering while reserving names before
   filtering.
4. Let `_find_all_skills` optionally exclude user-only entries; use that mode
   only from `skills_list`.
5. Run each new test to green, then the targeted and broader skill suites.

## Task 4: Verify and commit

1. Run:
   `scripts/run_tests.sh tests/agent/test_prompt_builder.py tests/agent/test_skill_utils.py tests/agent/test_external_skills.py tests/agent/test_skill_commands.py tests/agent/test_skill_commands_reload.py tests/tools/test_skills_tool.py -q`
2. Report the known baseline failure separately if it remains the only failure.
3. Inspect `git diff --check`, scoped diff, and `git status --short`.
4. Commit the spec, plan, tests, and implementation on
   `feat/user-only-skill-invocation`.
