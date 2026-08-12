---
name: manage-materialbin-version
description: Manage Material Bin's synchronized semantic version, Git hooks, release tags, and GHCR image release flow. Use when making commits that affect the product version, installing or troubleshooting version hooks, manually raising the minor or major version, creating vX.Y.Z release tags, amending versioned commits, validating version fields, or repairing version mismatches.
---

# Manage Material Bin Version

Run all commands from the repository root. Treat `VERSION` as the repository's only product
version source and use `.githooks/versioning.py` to update its synchronized copies.

## Preserve Invariants

- Accept only `MAJOR.MINOR.PATCH` versions.
- Let the Git hook increment `PATCH` for ordinary commits.
- Raise `MAJOR` or `MINOR` only by an explicit maintainer decision and reset `PATCH` to `0`.
- Keep a release tag in the form `vX.Y.Z` exactly equal to the commit's `VERSION`.
- Never edit only one managed version field or bypass the hook with `--no-verify`.
- Do not move or reuse a published version tag. Publish a new patch version to correct a release.
- Do not define `VERSION` in `.env` or `.env.example`. Let source runs use the synchronized
  application default and let container builds inject `APP_VERSION` as runtime `VERSION`.

## Inspect Version State

Print and validate the current version before release operations:

```bash
python3 .githooks/versioning.py current
python3 .githooks/versioning.py check
```

List every synchronized file when staging or diagnosing a mismatch:

```bash
python3 .githooks/versioning.py paths
```

## Enable Automatic Patch Bumps

Enable the tracked hooks once after each clone:

```bash
./.githooks/install.sh
git config --get core.hooksPath
```

Require the second command to return `.githooks`.

Create an ordinary commit without editing the version manually:

```bash
git add <files>
git commit -m "fix: describe the change"
```

Allow `pre-commit` to select the next patch, synchronize all managed fields, and stage those
fields in the same commit. If it reports unstaged changes in managed files, stage or restore
those changes before retrying.

Create final `master` commits in a local clone with the hook enabled. GitHub-created commits and
merge commits do not run local hooks, and the container workflow rejects invalid transitions.

## Raise Minor Or Major

Choose a version above the current major/minor line with patch `0`, then synchronize it. For
example:

```bash
python3 .githooks/versioning.py set 1.5.0
python3 .githooks/versioning.py check
git add -- $(python3 .githooks/versioning.py paths)
git commit -m "chore: release 1.5.0"
```

Use the same sequence for a major release such as `2.0.0`. The hook recognizes the legal manual
transition and preserves it instead of adding another patch.

Push `master`, wait for the container workflow to pass, then create and push the matching
annotated tag:

```bash
git push origin master
git tag -a v1.5.0 -m "Release v1.5.0"
git push origin v1.5.0
```

Expect a `master` push to publish the exact version, `sha-*`, and `edge`. Expect the formal tag to
also publish `MAJOR.MINOR` and `latest`.

## Build Versioned Images Locally

Build through both Compose files so one image receives the moving runtime tag and the immutable
product version tag:

```bash
docker compose --env-file .env.docker -f compose.yaml -f compose.build.yaml build
```

Keep only the repository and runtime tag in `.env.docker`:

```env
MATERIALBIN_IMAGE_REPOSITORY=ghcr.io/fifcom/materialbin
MATERIALBIN_IMAGE_TAG=latest
```

Let the hook synchronize the `APP_VERSION` default and matching `build.tags` entry in
`compose.build.yaml`. Do not put `APP_VERSION` in the long-lived deployment environment file.
After a build, require both `${MATERIALBIN_IMAGE_REPOSITORY}:${MATERIALBIN_IMAGE_TAG}` and
`${MATERIALBIN_IMAGE_REPOSITORY}:${APP_VERSION}` to point to the same image ID.

## Amend Or Repair

Preserve the current version when amending a commit instead of creating a new version:

```bash
MATERIALBIN_KEEP_VERSION=1 git commit --amend
```

Repair synchronized fields from `VERSION`, then validate them:

```bash
python3 .githooks/versioning.py set "$(python3 .githooks/versioning.py current)"
python3 .githooks/versioning.py check
```

Do not add `VERSION` to `.env` or `.env.example`. The version tool and commit hook remove that line
when found, while preserving every other environment setting. This keeps long-lived production
environment files independent from application releases.
