# IMG-CONVert 🖼️

تطبيق مجاني ومفتوح المصدر لتحويل الصور بدفعات (Batch Image Converter) مُصمم باستخدام Python و PyQt6.

---

## 🚀 كيفية التشغيل والتحزيم لنظام macOS

لأن نظام macOS يتطلب بناء التطبيق على جهاز Mac (أو عبر GitHub Actions)، لديك خياران لبناء ملف `.app` الخاص بالـ Mac:

### الخيار الأول: البناء على جهاز Mac محلياً
إذا كان لديك جهاز Mac:
1. افتح الـ Terminal وانتقل لمجلد المشروع:
   ```bash
   cd path/to/IMG-CONVert
   ```
2. قم بإعطاء تصريح التشغيل لسكربت البناء:
   ```bash
   chmod +x build_mac.sh
   ```
3. قم بتشغيل السكربت:
   ```bash
   ./build_mac.sh
   ```
4. ستجد التطبيق الناتِج `IMG-CONVert.app` وكذلك الملف المضغوط `IMG-CONVert-macOS.zip` في مجلد `dist/`.

---

### الخيار الثاني: البناء التلقائي بدون Mac (عبر GitHub Actions)
إذا لم يكن لديك جهاز Mac حالياً:
1. ارفع الكود إلى مستودع GitHub (Repository).
2. افتح تبويب **Actions** في مستودع GitHub الخاص بك.
3. ستقوم سيرفرات GitHub تلقائياً ببناء نسختي **Windows (.exe)** و **macOS (.app)**.
4. يمكنك تحميل ملف الـ Mac المضغوط جاهزاً فور انتهاء الـ Build من قائمة Artifacts.

---

## 💻 التشغيل المباشر عبر السكربت (Python)

على أي نظام تشغيل (macOS / Linux / Windows):

```bash
# 1. تثبيت المكتبات المطلوبة
pip install -r requirements.txt

# 2. تشغيل التطبيق
python image_converter.py
```

---

## 🪟 البناء لنظام Windows
على جهاز Windows، قم بتشغيل الملف:
```cmd
build_windows.bat
```
وسيكون الملف التنفيذي `IMG-CONVert.exe` جاهزاً في مجلد `dist/`.
