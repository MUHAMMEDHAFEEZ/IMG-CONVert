import sys
import os
from pathlib import Path
from PIL import Image

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QLabel,
                             QProgressBar, QFileDialog, QMessageBox, QFrame, QHeaderView,
                             QSlider, QAbstractItemView, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QBrush


def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_image_thumbnail(file_path, size=(44, 44)):
    try:
        with Image.open(file_path) as img:
            img.thumbnail(size)
            img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
    except Exception:
        return QPixmap()


# Vector icon generator using QPainter
def create_vector_icon(icon_type, color="#8b949e", size=24):
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color))
    pen.setWidthF(2.0 * 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    s = size * 2
    pad = s * 0.2

    if icon_type == "add":
        painter.drawLine(int(s / 2), int(pad), int(s / 2), int(s - pad))
        painter.drawLine(int(pad), int(s / 2), int(s - pad), int(s / 2))
    elif icon_type == "folder":
        path = QPainterPath()
        path.moveTo(pad, pad * 1.2)
        path.lineTo(s * 0.45, pad * 1.2)
        path.lineTo(s * 0.55, pad * 1.8)
        path.lineTo(s - pad, pad * 1.8)
        path.lineTo(s - pad, s - pad)
        path.lineTo(pad, s - pad)
        path.closeSubpath()
        painter.drawPath(path)
    elif icon_type == "trash":
        painter.drawLine(int(pad * 1.2), int(pad * 1.5), int(s - pad * 1.2), int(pad * 1.5))
        painter.drawLine(int(s * 0.35), int(pad * 1.5), int(s * 0.35), int(pad))
        painter.drawLine(int(s * 0.35), int(pad), int(s * 0.65), int(pad))
        painter.drawLine(int(s * 0.65), int(pad), int(s * 0.65), int(pad * 1.5))
        path = QPainterPath()
        path.moveTo(pad * 1.5, pad * 1.5)
        path.lineTo(pad * 1.7, s - pad)
        path.lineTo(s - pad * 1.7, s - pad)
        path.lineTo(s - pad * 1.5, pad * 1.5)
        painter.drawPath(path)
    elif icon_type == "close":
        painter.drawLine(int(pad * 1.2), int(pad * 1.2), int(s - pad * 1.2), int(s - pad * 1.2))
        painter.drawLine(int(s - pad * 1.2), int(pad * 1.2), int(pad * 1.2), int(s - pad * 1.2))
    elif icon_type == "convert":
        path = QPainterPath()
        path.moveTo(s * 0.35, pad)
        path.lineTo(s * 0.75, s / 2)
        path.lineTo(s * 0.35, s - pad)
        path.closeSubpath()
        painter.setBrush(QBrush(QColor(color)))
        painter.drawPath(path)
    elif icon_type == "image":
        rect = QRectF(pad, pad, s - pad * 2, s - pad * 2)
        painter.drawRoundedRect(rect, 4 * 2, 4 * 2)
        painter.drawEllipse(QRectF(s * 0.32, s * 0.32, s * 0.12, s * 0.12))
        path = QPainterPath()
        path.moveTo(pad, s * 0.7)
        path.lineTo(s * 0.4, s * 0.45)
        path.lineTo(s * 0.65, s * 0.65)
        path.lineTo(s * 0.78, s * 0.55)
        path.lineTo(s - pad, s * 0.75)
        painter.drawPath(path)

    painter.end()
    pix.setDevicePixelRatio(2.0)
    return QIcon(pix)


class ConversionWorker(QThread):
    item_progress = pyqtSignal(int, str, bool, str)
    total_progress = pyqtSignal(int)
    finished_all = pyqtSignal()

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks

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
                    if img.mode in ('RGBA', 'LA', 'P') and out_fmt in ('JPEG', 'JPG'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB' and out_fmt in ('JPEG', 'JPG'):
                        img = img.convert('RGB')

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
                    self.item_progress.emit(i, "Completed", True, "")
            except Exception as e:
                self.item_progress.emit(i, "Failed", False, str(e))

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


# Modern Dark Design System
MODERN_THEME = """
QMainWindow {
    background-color: #0d1117;
}
QWidget {
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}
QFrame#HeaderFrame {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 10px 16px;
}
QLabel#AppTitle {
    color: #f0f6fc;
    font-size: 18px;
    font-weight: 700;
}
QLabel#AppSubtitle {
    color: #8b949e;
    font-size: 12px;
}
QLabel#BadgeLabel {
    background-color: #21262d;
    color: #58a6ff;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 12px;
}
QFrame#DropZoneCard {
    background-color: #161b22;
    border: 2px dashed #30363d;
    border-radius: 14px;
}
QFrame#DropZoneCard:hover {
    border-color: #58a6ff;
    background-color: #1c2128;
}
QTableWidget {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    gridline-color: #21262d;
    color: #e6edf3;
    outline: none;
}
QTableWidget::item {
    padding: 4px;
    border-bottom: 1px solid #21262d;
}
QTableWidget::item:selected {
    background-color: #21262d;
    color: #f0f6fc;
}
QHeaderView::section {
    background-color: #0d1117;
    color: #8b949e;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 11px;
    border: none;
    border-bottom: 1px solid #21262d;
}
QFrame#ControlsFrame {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 12px 16px;
}
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #30363d;
    color: #f0f6fc;
    border-color: #8b949e;
}
QPushButton#PrimaryBtn {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
}
QPushButton#PrimaryBtn:hover {
    background-color: #2ea043;
}
QPushButton#ConvertBtn {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton#ConvertBtn:hover {
    background-color: #2ea043;
}
QPushButton#ConvertBtn:disabled {
    background-color: #21262d;
    color: #484f58;
    border-color: #30363d;
}
QPushButton#RemoveBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
}
QPushButton#RemoveBtn:hover {
    background-color: #da3633;
}
QComboBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 10px;
    color: #e6edf3;
}
QComboBox:hover {
    border-color: #58a6ff;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #21262d;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #58a6ff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #79c0ff;
}
QProgressBar {
    border: none;
    background-color: #21262d;
    border-radius: 5px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #238636;
    border-radius: 5px;
}
"""


class ImageConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_items = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("IMG-CONVert")
        self.resize(980, 650)
        self.setStyleSheet(MODERN_THEME)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("IMG-CONVert")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Fast & local batch image format converter")
        subtitle.setObjectName("AppSubtitle")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.count_badge = QLabel("0 files")
        self.count_badge.setObjectName("BadgeLabel")
        header_layout.addWidget(self.count_badge)

        main_layout.addWidget(header_frame)

        # Stacked Widget (Dropzone vs Table view)
        self.stack = QStackedWidget()

        # 0. DropZone View (Empty State)
        self.dropzone_card = QFrame()
        self.dropzone_card.setObjectName("DropZoneCard")
        self.dropzone_card.setAcceptDrops(True)

        dz_layout = QVBoxLayout(self.dropzone_card)
        dz_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(create_vector_icon("image", "#58a6ff", 48).pixmap(48, 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dz_title = QLabel("Drag & drop images here")
        dz_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f0f6fc;")
        dz_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dz_sub = QLabel("Supports PNG, JPEG, WEBP, BMP, GIF, TIFF, ICO")
        dz_sub.setStyleSheet("color: #8b949e; font-size: 12px;")
        dz_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_dz_browse = QPushButton("Browse Files")
        self.btn_dz_browse.setObjectName("PrimaryBtn")
        self.btn_dz_browse.setIcon(create_vector_icon("add", "#ffffff", 14))
        self.btn_dz_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dz_browse.clicked.connect(self.browse_files)

        dz_layout.addWidget(icon_lbl)
        dz_layout.addWidget(dz_title)
        dz_layout.addWidget(dz_sub)
        dz_layout.addWidget(self.btn_dz_browse, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(self.dropzone_card)

        # 1. Table View (Populated State)
        self.table = DragDropTableWidget()
        self.table.files_dropped.connect(self.add_files)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Preview", "File Details", "Target Format", "Destination Folder", "Status", ""
        ])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(5, 40)

        self.stack.addWidget(self.table)
        main_layout.addWidget(self.stack)

        # Action Bar (Add & Clear)
        action_bar = QHBoxLayout()
        self.btn_add = QPushButton("Add Files")
        self.btn_add.setObjectName("PrimaryBtn")
        self.btn_add.setIcon(create_vector_icon("add", "#ffffff", 14))
        self.btn_add.clicked.connect(self.browse_files)

        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.setIcon(create_vector_icon("trash", "#c9d1d9", 14))
        self.btn_clear.clicked.connect(self.clear_queue)

        action_bar.addWidget(self.btn_add)
        action_bar.addWidget(self.btn_clear)
        action_bar.addStretch()
        main_layout.addLayout(action_bar)

        # Settings Controls Panel
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("ControlsFrame")
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(12, 10, 12, 10)
        ctrl_layout.setSpacing(16)

        # Bulk Format Override
        fmt_box = QVBoxLayout()
        fmt_box.setSpacing(4)
        fmt_lbl = QLabel("Convert All To:")
        fmt_lbl.setStyleSheet("color: #8b949e; font-weight: 600; font-size: 11px;")
        self.global_fmt_combo = QComboBox()
        self.global_fmt_combo.addItems(["Select Format...", "PNG", "JPEG", "JPG", "WEBP", "BMP", "GIF", "TIFF", "ICO"])
        self.global_fmt_combo.currentIndexChanged.connect(self.apply_global_format)
        fmt_box.addWidget(fmt_lbl)
        fmt_box.addWidget(self.global_fmt_combo)
        ctrl_layout.addLayout(fmt_box)

        # Bulk Output Directory
        dir_box = QVBoxLayout()
        dir_box.setSpacing(4)
        dir_lbl = QLabel("Output Folder:")
        dir_lbl.setStyleSheet("color: #8b949e; font-weight: 600; font-size: 11px;")
        self.btn_global_dir = QPushButton("Choose Folder")
        self.btn_global_dir.setIcon(create_vector_icon("folder", "#c9d1d9", 14))
        self.btn_global_dir.clicked.connect(self.apply_global_output_dir)
        dir_box.addWidget(dir_lbl)
        dir_box.addWidget(self.btn_global_dir)
        ctrl_layout.addLayout(dir_box)

        # Quality Slider
        quality_box = QVBoxLayout()
        quality_box.setSpacing(4)
        self.quality_lbl = QLabel("Quality: 90%")
        self.quality_lbl.setStyleSheet("color: #8b949e; font-weight: 600; font-size: 11px;")
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_lbl.setText(f"Quality: {v}%"))
        quality_box.addWidget(self.quality_lbl)
        quality_box.addWidget(self.quality_slider)
        ctrl_layout.addLayout(quality_box)

        # Scale Combo
        scale_box = QVBoxLayout()
        scale_box.setSpacing(4)
        scale_lbl = QLabel("Resize Scale:")
        scale_lbl.setStyleSheet("color: #8b949e; font-weight: 600; font-size: 11px;")
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["100% (Original)", "75%", "50%", "25%"])
        scale_box.addWidget(scale_lbl)
        scale_box.addWidget(self.scale_combo)
        ctrl_layout.addLayout(scale_box)

        main_layout.addWidget(ctrl_frame)

        # Bottom Bar & Progress
        bottom_layout = QHBoxLayout()

        progress_vbox = QVBoxLayout()
        progress_vbox.setSpacing(4)
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_vbox.addWidget(self.status_lbl)
        progress_vbox.addWidget(self.progress_bar)
        bottom_layout.addLayout(progress_vbox)

        self.btn_convert = QPushButton("Convert All")
        self.btn_convert.setObjectName("ConvertBtn")
        self.btn_convert.setIcon(create_vector_icon("convert", "#ffffff", 14))
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
                continue

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
                'status': 'Ready'
            }
            self.file_items.append(item_data)
            self.insert_table_row(len(self.file_items) - 1, item_data)

        self.update_view_state()

    def insert_table_row(self, row_idx, item):
        self.table.insertRow(row_idx)
        self.table.setRowHeight(row_idx, 52)

        # 0. Thumbnail Preview
        pm = get_image_thumbnail(item['path'])
        pm_label = QLabel()
        pm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not pm.isNull():
            pm_label.setPixmap(pm)
        else:
            pm_label.setPixmap(create_vector_icon("image", "#8b949e", 24).pixmap(24, 24))
        self.table.setCellWidget(row_idx, 0, pm_label)

        # 1. File Details
        info_widget = QWidget()
        info_vbox = QVBoxLayout(info_widget)
        info_vbox.setContentsMargins(6, 2, 6, 2)
        info_vbox.setSpacing(2)
        fname_lbl = QLabel(item['name'])
        fname_lbl.setStyleSheet("font-weight: 600; color: #f0f6fc;")
        meta_lbl = QLabel(f"{item['orig_fmt']}  •  {item['dim_str']}  •  {item['size_str']}")
        meta_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        info_vbox.addWidget(fname_lbl)
        info_vbox.addWidget(meta_lbl)
        self.table.setCellWidget(row_idx, 1, info_widget)

        # 2. Target Format Combo
        combo = QComboBox()
        combo.addItems(["PNG", "JPEG", "JPG", "WEBP", "BMP", "GIF", "TIFF", "ICO"])
        idx = combo.findText(item['out_fmt'])
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentTextChanged.connect(lambda txt, r=row_idx: self.on_row_format_changed(r, txt))
        self.table.setCellWidget(row_idx, 2, combo)

        # 3. Target Directory Button + Label
        dir_widget = QWidget()
        dir_hbox = QHBoxLayout(dir_widget)
        dir_hbox.setContentsMargins(4, 2, 4, 2)
        dir_lbl = QLabel(item['out_dir'])
        dir_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        dir_btn = QPushButton()
        dir_btn.setIcon(create_vector_icon("folder", "#c9d1d9", 14))
        dir_btn.setFixedSize(26, 26)
        dir_btn.clicked.connect(lambda _, r=row_idx, lbl=dir_lbl: self.choose_row_output_dir(r, lbl))
        dir_hbox.addWidget(dir_lbl)
        dir_hbox.addWidget(dir_btn)
        self.table.setCellWidget(row_idx, 3, dir_widget)

        # 4. Status Badge
        status_lbl = QLabel(item['status'])
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setStyleSheet("color: #58a6ff; font-weight: 600; font-size: 11px;")
        self.table.setCellWidget(row_idx, 4, status_lbl)

        # 5. Delete Action Button
        del_btn = QPushButton()
        del_btn.setObjectName("RemoveBtn")
        del_btn.setIcon(create_vector_icon("close", "#8b949e", 12))
        del_btn.setFixedSize(26, 26)
        del_btn.clicked.connect(lambda _, r=row_idx: self.remove_row(r))
        self.table.setCellWidget(row_idx, 5, del_btn)

    def on_row_format_changed(self, row, new_fmt):
        if row < len(self.file_items):
            self.file_items[row]['out_fmt'] = new_fmt

    def choose_row_output_dir(self, row, label_widget):
        chosen = QFileDialog.getExistingDirectory(self, "Select Folder")
        if chosen and row < len(self.file_items):
            self.file_items[row]['out_dir'] = chosen
            label_widget.setText(chosen)

    def remove_row(self, row):
        if row < len(self.file_items):
            self.file_items.pop(row)
            self.rebuild_table()
            self.update_view_state()

    def rebuild_table(self):
        self.table.setRowCount(0)
        for i, item in enumerate(self.file_items):
            self.insert_table_row(i, item)

    def clear_queue(self):
        self.file_items.clear()
        self.table.setRowCount(0)
        self.update_view_state()

    def update_view_state(self):
        cnt = len(self.file_items)
        self.count_badge.setText(f"{cnt} file{'s' if cnt != 1 else ''}")
        if cnt == 0:
            self.stack.setCurrentIndex(0)  # Show DropZone
        else:
            self.stack.setCurrentIndex(1)  # Show Table

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
        self.status_lbl.setText("Converting...")

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
                color = "#3fb950" if success else "#f85149"
                status_w.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 11px;")

    def on_finished_all(self):
        self.progress_bar.setVisible(False)
        self.btn_convert.setEnabled(True)
        self.status_lbl.setText("Completed")
        QMessageBox.information(self, "Success", "All images converted successfully!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageConverterApp()
    window.show()
    sys.exit(app.exec())
