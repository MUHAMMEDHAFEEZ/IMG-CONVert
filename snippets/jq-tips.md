# jq tips

```bash
jq -r '.items[] | [.name, .size] | @tsv' data.json   # JSON to TSV
jq 'map(select(.active))' data.json                    # filter
```
