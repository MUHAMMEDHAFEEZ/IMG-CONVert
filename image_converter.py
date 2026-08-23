import sys
import os
from pathlib import Path
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QLabel,
                             QProgressBar, QFileDialog, QMessageBox, QFrame, QHeaderView,
                             QSlider, QSpinBox, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage, QColor, QFont, QIcon


def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_image_thumbnail(file_path, size=(48, 48)):
    try:
        with Image.open(file_path) as img:
            img.thumbnail(size)
            img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
    except Exception:
        return QPixmap()


class ConversionWorker(QThread):
    item_progress = pyqtSignal(int, str, bool, str)  # row_idx, status, success, err_msg
    total_progress = pyqtSignal(int)
    finished_all = pyqtSignal()

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks  # list of dicts with task metadata

    def run(self):
        total = len(self.tasks)
        for i, task in enumerate(self.tasks):
            file_path = task['path']
            out_dir = task['out_dir']
            out_fmt = task['out_fmt'].upper()
            quality = task['quality']
            scale = task['scale']

            self.item_progress.emit(i, "Converting...", True, "")
            try:
                with Image.open(file_path) as img:
                    # Handle transparency for JPEG
                    if img.mode in ('RGBA', 'LA', 'P') and out_fmt in ('JPEG', 'JPG'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB' and out_fmt in ('JPEG', 'JPG'):
                        img = img.convert('RGB')

                    # Scale image if requested
                    if scale != 100:
                        new_w = max(1, int(img.width * (scale / 100.0)))
                        new_h = max(1, int(img.height * (scale / 100.0)))
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    stem = Path(file_path).stem
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, f"{stem}.{out_fmt.lower()}")

                    save_kwargs = {}
                    if out_fmt in ('JPEG', 'JPG', 'WEBP'):
                        save_kwargs['quality'] = quality

                    img.save(out_path, format=out_fmt, **save_kwargs)
                    self.item_progress.emit(i, "Completed ✓", True, "")
            except Exception as e:
                self.item_progress.emit(i, "Failed ❌", False, str(e))

            self.total_progress.emit(int((i + 1) / total * 100))

        self.finished_all.emit()


class DragDropTableWidget(QTableWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico')
        files = []
        for url in event.mimeData().urls():
            f_path = url.toLocalFile()
            if os.path.isfile(f_path) and f_path.lower().endswith(valid_exts):
                files.append(f_path)
            elif os.path.isdir(f_path):
                for root, _, filenames in os.walk(f_path):
                    for fname in filenames:
                        if fname.lower().endswith(valid_exts):
                            files.append(os.path.join(root, fname))
        if files:
            self.files_dropped.emit(files)


PRO_STYLE = """
QMainWindow {
    background-color: #0b0f19;
}
QWidget {
    color: #f8fafc;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}
QFrame#HeaderCard {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 12px 18px;
}
QLabel#HeaderTitle {
    color: #38bdf8;
    font-size: 20px;
    font-weight: 800;
}
QLabel#Subtitle {
    color: #64748b;
    font-size: 12px;
}
QLabel#CountBadge {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #3b82f6;
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 700;
}
QTableWidget {
    background-color: #0f172a;
    border: 2px dashed #1e293b;
    border-radius: 12px;
    gridline-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #1e293b;
}
QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #1e293b;
}
QHeaderView::section {
    background-color: #111827;
    color: #94a3b8;
    padding: 8px 12px;
    font-weight: 700;
    border: none;
    border-bottom: 2px solid #1e293b;
}
QFrame#ControlPanel {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 14px;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton#SecondaryBtn {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
}
QPushButton#SecondaryBtn:hover {
    background-color: #334155;
    color: #ffffff;
}
QPushButton#DangerBtn {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#DangerBtn:hover {
    background-color: #dc2626;
}
QPushButton#ConvertBtn {
    background-color: #10b981;
    font-size: 15px;
    font-weight: 700;
    padding: 12px 28px;
    border-radius: 10px;
}
QPushButton#ConvertBtn:hover {
    background-color: #059669;
}
QPushButton#ConvertBtn:disabled {
    background-color: #1e293b;
    color: #475569;
}
QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 10px;
    color: #f8fafc;
}
QComboBox:hover {
    border-color: #38bdf8;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #38bdf8;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QProgressBar {
    border: none;
    background-color: #1e293b;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #10b981);
    border-radius: 6px;
}
"""


class ImageConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_items = []  # metadata list per file
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("IMG-CONVert Pro - Batch Image Studio")
        self.resize(1000, 680)
        self.setStyleSheet(PRO_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Card
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)

        title_vbox = QVBoxLayout()
        title = QLabel("🖼️ IMG-CONVert Pro")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Advanced Multi-Format Batch Conversion Engine")
        subtitle.setObjectName("Subtitle")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.count_badge = QLabel("0 files loaded")
        self.count_badge.setObjectName("CountBadge")
        header_layout.addWidget(self.count_badge)

        main_layout.addWidget(header_card)

        # Main Table View (Drag & Drop)
        self.table = DragDropTableWidget()
        self.table.files_dropped.connect(self.add_files)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Preview", "File Details", "Target Format", "Destination Folder", "Status", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 64)
        self.table.setColumnWidth(5, 54)
        self.table.setRowHeight(0, 60)

        main_layout.addWidget(self.table)

        # Batch Action Buttons
        top_btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("📁 Add Files / Folders")
        self.btn_add.clicked.connect(self.browse_files)
        self.btn_clear = QPushButton("🗑️ Clear Queue")
        self.btn_clear.setObjectName("SecondaryBtn")
        self.btn_clear.clicked.connect(self.clear_queue)

        top_btn_layout.addWidget(self.btn_add)
        top_btn_layout.addWidget(self.btn_clear)
        top_btn_layout.addStretch()
        main_layout.addLayout(top_btn_layout)

        # Global Settings Controls Frame
        ctrl_panel = QFrame()
        ctrl_panel.setObjectName("ControlPanel")
        ctrl_layout = QHBoxLayout(ctrl_panel)
        ctrl_layout.setSpacing(20)

        # Global Format Quick Apply
        fmt_box = QVBoxLayout()
        fmt_lbl = QLabel("Bulk Format Override:")
        fmt_lbl.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.global_fmt_combo = QComboBox()
        self.global_fmt_combo.addItems(["Apply to All...", "PNG", "JPEG", "JPG", "WEBP", "BMP", "GIF", "TIFF", "ICO"])
        self.global_fmt_combo.currentIndexChanged.connect(self.apply_global_format)
        fmt_box.addWidget(fmt_lbl)
        fmt_box.addWidget(self.global_fmt_combo)
        ctrl_layout.addLayout(fmt_box)

        # Global Output Dir Quick Apply
        dir_box = QVBoxLayout()
        dir_lbl = QLabel("Bulk Output Folder:")
        dir_lbl.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.btn_global_dir = QPushButton("📂 Choose Folder for All")
        self.btn_global_dir.setObjectName("SecondaryBtn")
        self.btn_global_dir.clicked.connect(self.apply_global_output_dir)
        dir_box.addWidget(dir_lbl)
        dir_box.addWidget(self.btn_global_dir)
        ctrl_layout.addLayout(dir_box)

        # Quality Slider
        quality_box = QVBoxLayout()
        self.quality_lbl = QLabel("Quality: 90%")
        self.quality_lbl.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_lbl.setText(f"Quality: {v}%"))
        quality_box.addWidget(self.quality_lbl)
        quality_box.addWidget(self.quality_slider)
        ctrl_layout.addLayout(quality_box)

        # Resize Scale
        scale_box = QVBoxLayout()
        scale_lbl = QLabel("Scale Output:")
        scale_lbl.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["100% (Original)", "75%", "50%", "25%"])
        scale_box.addWidget(scale_lbl)
        scale_box.addWidget(self.scale_combo)
        ctrl_layout.addLayout(scale_box)

        main_layout.addWidget(ctrl_panel)

        # Bottom Bar & Progress
        bottom_layout = QHBoxLayout()

        progress_vbox = QVBoxLayout()
        self.status_lbl = QLabel("Ready to convert")
        self.status_lbl.setStyleSheet("color: #64748b; font-weight: 600;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_vbox.addWidget(self.status_lbl)
        progress_vbox.addWidget(self.progress_bar)
        bottom_layout.addLayout(progress_vbox)

        self.btn_convert = QPushButton("⚡ Convert All Items")
        self.btn_convert.setObjectName("ConvertBtn")
        self.btn_convert.clicked.connect(self.start_conversion)
        bottom_layout.addWidget(self.btn_convert)

        main_layout.addLayout(bottom_layout)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.ico *.tif)"
        )
        if files:
            self.add_files(files)

    def add_files(self, new_files):
        for f_path in new_files:
            if any(item['path'] == f_path for item in self.file_items):
                continue  # avoid duplicates

            try:
                with Image.open(f_path) as img:
                    width, height = img.size
                    fmt = img.format or Path(f_path).suffix.replace('.', '').upper()
            except Exception:
                width, height = 0, 0
                fmt = "UNKNOWN"

            file_size = os.path.getsize(f_path) if os.path.exists(f_path) else 0
            default_out_dir = os.path.dirname(f_path)
            default_out_fmt = "WEBP" if fmt in ("PNG", "JPEG", "JPG") else "PNG"

            item_data = {
                'path': f_path,
                'name': Path(f_path).name,
                'size_str': format_bytes(file_size),
                'dim_str': f"{width}x{height} px",
                'orig_fmt': fmt,
                'out_fmt': default_out_fmt,
                'out_dir': default_out_dir,
                'status': 'Pending'
            }
            self.file_items.append(item_data)
            self.insert_table_row(len(self.file_items) - 1, item_data)

        self.update_count_badge()

    def insert_table_row(self, row_idx, item):
        self.table.insertRow(row_idx)
        self.table.setRowHeight(row_idx, 58)

        # 0. Thumbnail Preview
        pm = get_image_thumbnail(item['path'])
        pm_label = QLabel()
        pm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not pm.isNull():
            pm_label.setPixmap(pm)
        else:
            pm_label.setText("🖼️")
        self.table.setCellWidget(row_idx, 0, pm_label)

        # 1. File Details
        info_widget = QWidget()
        info_vbox = QVBoxLayout(info_widget)
        info_vbox.setContentsMargins(6, 4, 6, 4)
        info_vbox.setSpacing(2)
        fname_lbl = QLabel(item['name'])
        fname_lbl.setStyleSheet("font-weight: 700; color: #f8fafc;")
        meta_lbl = QLabel(f"{item['orig_fmt']}  •  {item['dim_str']}  •  {item['size_str']}")
        meta_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        info_vbox.addWidget(fname_lbl)
        info_vbox.addWidget(meta_lbl)
        self.table.setCellWidget(row_idx, 1, info_widget)

        # 2. Target Format Combo (Per Image)
        combo = QComboBox()
        combo.addItems(["PNG", "JPEG", "JPG", "WEBP", "BMP", "GIF", "TIFF", "ICO"])
        idx = combo.findText(item['out_fmt'])
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentTextChanged.connect(lambda txt, r=row_idx: self.on_row_format_changed(r, txt))
        self.table.setCellWidget(row_idx, 2, combo)

        # 3. Target Directory Button + Label (Per Image)
        dir_widget = QWidget()
        dir_hbox = QHBoxLayout(dir_widget)
        dir_hbox.setContentsMargins(4, 4, 4, 4)
        dir_lbl = QLabel(item['out_dir'])
        dir_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        dir_btn = QPushButton("📁")
        dir_btn.setObjectName("SecondaryBtn")
        dir_btn.setFixedSize(28, 28)
        dir_btn.clicked.connect(lambda _, r=row_idx, lbl=dir_lbl: self.choose_row_output_dir(r, lbl))
        dir_hbox.addWidget(dir_lbl)
        dir_hbox.addWidget(dir_btn)
        self.table.setCellWidget(row_idx, 3, dir_widget)

        # 4. Status Badge
        status_lbl = QLabel(item['status'])
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setStyleSheet("color: #38bdf8; font-weight: 600;")
        self.table.setCellWidget(row_idx, 4, status_lbl)

        # 5. Delete Action Button
        del_btn = QPushButton("❌")
        del_btn.setObjectName("DangerBtn")
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda _, r=row_idx: self.remove_row(r))
        self.table.setCellWidget(row_idx, 5, del_btn)

    def on_row_format_changed(self, row, new_fmt):
        if row < len(self.file_items):
            self.file_items[row]['out_fmt'] = new_fmt

    def choose_row_output_dir(self, row, label_widget):
        chosen = QFileDialog.getExistingDirectory(self, "Select Target Folder")
        if chosen and row < len(self.file_items):
            self.file_items[row]['out_dir'] = chosen
            label_widget.setText(chosen)

    def remove_row(self, row):
        if row < len(self.file_items):
            self.file_items.pop(row)
            self.rebuild_table()
            self.update_count_badge()

    def rebuild_table(self):
        self.table.setRowCount(0)
        for i, item in enumerate(self.file_items):
            self.insert_table_row(i, item)

    def clear_queue(self):
        self.file_items.clear()
        self.table.setRowCount(0)
        self.update_count_badge()

    def update_count_badge(self):
        cnt = len(self.file_items)
        self.count_badge.setText(f"{cnt} file{'s' if cnt != 1 else ''} loaded")

    def apply_global_format(self, index):
        if index <= 0:
            return
        selected_fmt = self.global_fmt_combo.currentText()
        for i, item in enumerate(self.file_items):
            item['out_fmt'] = selected_fmt
            combo = self.table.cellWidget(i, 2)
            if isinstance(combo, QComboBox):
                c_idx = combo.findText(selected_fmt)
                if c_idx >= 0:
                    combo.setCurrentIndex(c_idx)
        self.global_fmt_combo.setCurrentIndex(0)

    def apply_global_output_dir(self):
        chosen_dir = QFileDialog.getExistingDirectory(self, "Select Global Output Folder")
        if not chosen_dir:
            return
        for i, item in enumerate(self.file_items):
            item['out_dir'] = chosen_dir
            dir_w = self.table.cellWidget(i, 3)
            if dir_w:
                lbl = dir_w.findChild(QLabel)
                if lbl:
                    lbl.setText(chosen_dir)

    def start_conversion(self):
        if not self.file_items:
            QMessageBox.warning(self, "Empty Queue", "Please add image files first.")
            return

        scale_text = self.scale_combo.currentText()
        scale_val = 100
        if "75%" in scale_text:
            scale_val = 75
        elif "50%" in scale_text:
            scale_val = 50
        elif "25%" in scale_text:
            scale_val = 25

        quality_val = self.quality_slider.value()

        tasks = []
        for item in self.file_items:
            tasks.append({
                'path': item['path'],
                'out_dir': item['out_dir'],
                'out_fmt': item['out_fmt'],
                'quality': quality_val,
                'scale': scale_val
            })

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_convert.setEnabled(False)
        self.status_lbl.setText("Converting batch...")

        self.worker = ConversionWorker(tasks)
        self.worker.item_progress.connect(self.on_item_progress)
        self.worker.total_progress.connect(self.progress_bar.setValue)
        self.worker.finished_all.connect(self.on_finished_all)
        self.worker.start()

    def on_item_progress(self, row, status_text, success, err_msg):
        if row < len(self.file_items):
            self.file_items[row]['status'] = status_text
            status_w = self.table.cellWidget(row, 4)
            if isinstance(status_w, QLabel):
                status_w.setText(status_text)
                color = "#10b981" if success else "#ef4444"
                status_w.setStyleSheet(f"color: {color}; font-weight: 700;")

    def on_finished_all(self):
        self.progress_bar.setVisible(False)
        self.btn_convert.setEnabled(True)
        self.status_lbl.setText("Batch conversion completed successfully! ✓")
        QMessageBox.information(self, "Success", "All images converted successfully!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageConverterApp()
    window.show()
    sys.exit(app.exec())
