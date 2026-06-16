# Git history preservation (graft procedure)

The 7 source apps were folded into `suite` by **plain copy** (D13 fallback), so the
original per-app authorship was NOT in `suite`'s history. We restore it by grafting
each source repo's history onto the new `suite/` paths with `git filter-repo`
(path rewrite) + `git merge -s ours --allow-unrelated-histories` (link ancestry
without changing the migrated tree).

## Why `-s ours`, and the one rule that governs timing

`merge -s ours` keeps the **current tree** and only links the rewritten history as
ancestors. `git log --follow <path>` / `git blame` then reach the original authors —
**but only for paths that already exist in the committed `suite` tree at graft time.**

A subtree grafted *before* its files are committed will NOT retroactively connect:
an `-s ours` merge never introduces the file into the mainline tree, so a later
"add" commit has no rename source to cross back into the graft.

> **Rule:** graft a subtree's history only AFTER that subtree exists (is committed) in `suite`.

## Status

- **Backend (all 7): DONE.** Backend code was already committed, so all 7 backend
  histories are grafted (commits `history: graft <app> backend …`). Verified:
  `git log --follow suite/slides/doctype/presentation/presentation.py` reaches
  Gursheen Anand's commits; drive → Safwan Samsudeen/Arjun Choudhary; mail → s-aga-r; etc.
- **Frontend: PENDING, per-port.** The whole `frontend/` is still uncommitted, so no
  frontend history is grafted yet — including slides'. Each app's frontend history is
  grafted as the **final step of its port**, after the port is committed (see below).

## Per-port frontend graft (run after each app's frontend port is committed)

```bash
APP=drive PKG=drive          # source repo dir + python package name
FR=/Users/netchampfaris/Projects/frappe-bench-suite/env/bin/git-filter-repo
SHA=$(git -C apps/$APP rev-parse HEAD)        # migration-base commit (full history behind it)
rm -rf /tmp/suite-hist/$APP-fe
git clone -q apps/$APP /tmp/suite-hist/$APP-fe
( cd /tmp/suite-hist/$APP-fe
  git checkout -q -B graft "$SHA"; git remote remove origin
  for b in $(git branch --format='%(refname:short)' | grep -v '^graft$'); do git branch -qD "$b"; done
  git tag -l | xargs -r git tag -d
  # keep ONLY frontend, rewrite source frontend/src -> the ported path; drop the rest
  "$FR" --force --filename-callback '
n = filename.decode("utf-8","surrogateescape")
if n.startswith("frontend/src/"):
    return ("frontend/src/apps/'"$APP"'/" + n[len("frontend/src/"):]).encode()
return b""' )
git -C apps/suite remote add hist-$APP-fe /tmp/suite-hist/$APP-fe
git -C apps/suite fetch -q hist-$APP-fe
git -C apps/suite merge -s ours --allow-unrelated-histories \
  -m "history: graft $APP frontend authorship under frontend/src/apps/$APP" hist-$APP-fe/graft
git -C apps/suite remote remove hist-$APP-fe
# verify: git -C apps/suite log --follow -- frontend/src/apps/$APP/<some-view>.vue
```

Adjust the `frontend/src/ -> frontend/src/apps/<app>/` rename if the port reorganized
files differently than the source `src/` layout (it's best-effort; rename detection
covers the rest). Path precision only affects how cleanly `--follow` traces a given
current file — **no history is lost either way**, since every commit is grafted as an ancestor.

## Notes / invariants

- **Do not delete the source app repos** (`apps/<app>/`, Phase 4 cleanup) until every
  frontend graft is done — they are the history source. Backend grafts are complete,
  so backend-source deletion is already safe; keep them for the frontend.
- All 7 source repos were un-shallowed and their `origin` remotes restored
  (`github.com/frappe/<app>`), so full history is available locally.
- Rollback anchor for the backend-graft batch: pre-graft `suite` HEAD `5953115a`.
  Each graft is a no-op on the tree (`git diff 5953115a HEAD` = empty).
- Slides is ported but uncommitted; commit the frontend, then run the procedure above
  with `APP=slides PKG=slides` to graft its frontend history.
