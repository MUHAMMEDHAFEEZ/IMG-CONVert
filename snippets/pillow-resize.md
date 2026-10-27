# Resize with Pillow

```python
from PIL import Image

with Image.open("in.png") as im:
    im.thumbnail((1024, 1024))  # keeps aspect ratio, never upscales
    im.save("out.png", optimize=True)
```
