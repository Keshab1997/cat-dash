# Safe kit updates — explicit, per project

Kit files are copied into game repositories, not magically connected. There is no
background fleet sync, registry, auto-PR, auto-push or CI dispatch. This updater is
for one installed game at a time. Run from a trusted project checkout (Python 3.10+,
Git and internet required).

## 1. Check only

```bash
python3 tool/kit_update.py --check
```

Reads your `unity-kit.lock.json`, clones the fixed public kit repository into a
throwaway directory, reads candidate/baseline files as data, and reports installed
and candidate full SHAs, paths to update, conflicts and required workflow approval.
It does not execute downloaded scripts or change project files during check.
Exit 1 means conflicts/approval or a check error; read the report. It is not a CI loop.

Review the source changes between printed SHAs on GitHub. Changes are a proposal,
not automatically trusted because they are latest. A check may also target a pin:

```bash
python3 tool/kit_update.py --check --ref <full-40-character-commit-sha>
```

## 2. Apply a reviewed version

Commit your existing local work first; apply requires a clean working tree.

```bash
python3 tool/kit_update.py --apply --ref <reviewed-full-40-character-commit-sha>
```

If workflows change, the owner must approve those specific changes first. Only then:

```bash
python3 tool/kit_update.py --apply --ref <reviewed-full-40-character-commit-sha> --approve-workflows
```

The flag is an explicit human approval acknowledgement, not a security permission
system. Agents must not add it on their own. No bypass flag for file conflicts.
Apply refuses moving names such as main/tags/short SHAs; choose the printed exact
commit after reviewing it. No automatic retry or force overwrite.

## Preservation rules

- Only toolkit `tool/`, `agents/`, eligible `docs/`, workflows, managed AGENTS block
  and additive .gitignore changes are considered.
- Runtime game code, all `Assets/` including starter Editor helpers/tests, `Packages/`,
  `ProjectSettings/`, product/package config, game brief, asset register and project
  handoff document are **never updated** by this tool. Migrate these separately.
- Compare files against the actual template at the locked baseline revision. A file
  changed locally AND upstream conflicts. No project writes if conflicts exist.
- Local customization with no upstream change is kept. A manually synced file equal
  to the candidate is accepted. Existing unrelated owner files are not overwritten.
- Update only the managed AGENTS block if it matches baseline; preserve everything
  outside it byte-for-byte. Customized managed blocks require manual merge.
- .gitignore adds missing kit lines, keeping owner lines. No file deletion, even if
  the upstream template removed it. Removed paths are reported for manual review.
- Symlink/non-regular destinations and unsafe paths are rejected.

Apply updates the lockfile's toolkit revision/baselines, then runs the project's
preflight. Source is now the explicitly reviewed version. On handled write/preflight
failure it attempts to restore changed file contents and the old lock. This is not
crash-proof backup: interruption/permission/restore failures require inspection.
Empty created directories may remain after rollback. Use Git history as your backup.
The lockfile records toolkit revision, not proof that protected starter seed files
were upgraded; `protected_seed_files_not_updated` makes that limitation explicit.

After success, review `git diff`, commit and push deliberately as Captain. The updater
never commits/pushes, launches Unity, reads secret values, changes GitHub settings,
creates tags/releases, dispatches CI or uploads anything to Play. Secrets readiness
is a separate manual workflow.

## Already installed before this tool existed?

From a reviewed kit clone, copy only `template/tool/kit_update.py` into the game's
`tool/kit_update.py` (and this guide if desired), review and commit that bootstrap.
Keep the game's existing `unity-kit.lock.json`; do not replace it with a fresh install
receipt. Then run check. The original installer still refuses conflicting files and
is NOT a forced upgrade command. Fresh installs include the updater automatically.
If your lockfile source/revision is invalid or absent, resolve the baseline manually
rather than inventing a SHA or claiming the game is updated.

## বাংলা সংক্ষেপ

প্রথমে `--check` → দেখানো commit-এর changes review → নিজের changes commit →
নির্দিষ্ট full SHA দিয়ে `--apply --ref ...`। Workflow changes হলে আগে owner approval,
তারপর `--approve-workflows`। Conflict হলে কিছু apply হবে না; manual merge করতে হবে।
Game files/secrets untouched; শেষে diff দেখে Captain commit/push করবে।
