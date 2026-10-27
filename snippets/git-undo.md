# Git undo cheatsheet

```bash
git restore --staged <file>   # unstage
git restore <file>            # discard working-tree changes
git reset --soft HEAD~1       # undo last commit, keep changes staged
git revert <sha>              # new commit that undoes <sha>
```
