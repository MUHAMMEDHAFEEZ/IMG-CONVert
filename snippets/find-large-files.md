# Find the biggest files

```bash
find . -type f -printf '%s %p\n' | sort -nr | head -20
```
