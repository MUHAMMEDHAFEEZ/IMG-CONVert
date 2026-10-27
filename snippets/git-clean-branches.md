# Delete merged local branches

```bash
git branch --merged main | grep -vE '^\*|main' | xargs -r git branch -d
```
