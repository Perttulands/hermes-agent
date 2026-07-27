# User-only skill invocation

## Problem

Hermes currently offers every installed skill to the model through the system
prompt and `skills_list`. Agent Skills packages marked
`disable-model-invocation: true` therefore add autonomous prompt interference
even though their authors intended them for explicit user invocation.

## Decision

Normalize `disable-model-invocation` in `agent.skill_utils`, the existing
lightweight metadata seam shared by skill discovery paths.

- A value of `true` makes the skill user-only.
- Missing or false values preserve current model-invoked behavior.
- The system/compact prompt and `skills_list` exclude user-only skills.
- `skill_view(name)`, slash commands, stacked slash commands, and explicit
  preloading continue to load user-only skills.
- Local/profile skills reserve their canonical names before visibility
  filtering, so a hidden local skill still shadows an external skill with the
  same name.
- Reloading slash commands does not clear or rebuild a conversation's cached
  system prompt. A changed policy takes effect in a new prompt/session.

The top-level Agent Skills field is sufficient for this change. Hermes does not
need to read editor-specific policy files or add another metadata source.

## Alternatives rejected

- Filtering only in prompt rendering would leave `skills_list` as an
  autonomous discovery backdoor.
- Parsing the field independently in each scanner would duplicate policy and
  invite drift.
- A new model tool, plugin, environment variable, or prompt mutation would
  expand the core and violate prompt-cache stability.

## Acceptance

Behavior tests prove that a user-only skill:

1. is absent from cold and snapshot-backed system-prompt discovery;
2. is absent from `skills_list`;
3. remains loadable with `skill_view(name)` and by slash command;
4. keeps the cached prompt byte-stable after a slash-command reload; and
5. preserves local-over-external precedence without leaking the external copy.

The targeted skill suite passes apart from the separately recorded rapid
config-rewrite cache baseline failure.
