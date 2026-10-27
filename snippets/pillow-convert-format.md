# Convert image formats with Pillow

```python
from PIL import Image

with Image.open("in.png") as im:
    im.convert("RGB").save("out.jpg", quality=90)  # JPEG has no alpha channel
```
