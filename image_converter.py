import sys
import os
from pathlib import Path
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QComboBox, QLabel, QProgressBar,
                             QFileDialog, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent


class DropListWidget(QListWidget):
    """Custom ListWidget with Drag & Drop support for image files."""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

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
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico')
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path) and file_path.lower().endswith(valid_extensions):
                files.append(file_path)
            elif os.path.isdir(file_path):
                for root, _, filenames in os.walk(file_path):
                    for filename in filenames:
                        if filename.lower().endswith(valid_extensions):
                            files.append(os.path.join(root, filename))
        if files:
            self.files_dropped.emit(files)


class ConversionThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, files, output_dir, output_format, quality=95):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.output_format = output_format
        self.quality = quality

    def run(self):
        total = len(self.files)
        for i, file_path in enumerate(self.files):
            try:
                img = Image.open(file_path)
                if img.mode in ('RGBA', 'P') and self.output_format.upper() in ('JPEG', 'JPG'):
                    img = img.convert('RGB')
                stem = Path(file_path).stem
                output_path = os.path.join(self.output_dir, f"{stem}.{self.output_format.lower()}")
                img.save(output_path, format=self.output_format.upper(), quality=self.quality)
            except Exception as e:
                self.error.emit(f"Error converting {Path(file_path).name}: {str(e)}")
            self.progress.emit(int((i + 1) / total * 100))
        self.finished.emit()


MODERN_STYLE = """
QMainWindow {
    background-color: #0f172a;
}
QWidget {
    color: #f8fafc;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}
QLabel {
    color: #94a3b8;
    font-weight: 500;
}
QLabel#HeaderLabel {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 700;
}
QLabel#CountLabel {
    color: #38bdf8;
    font-weight: 600;
}
QListWidget {
    background-color: #1e293b;
    border: 2px dashed #334155;
    border-radius: 12px;
    padding: 8px;
    color: #e2e8f0;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 4px;
    background-color: #0f172a;
}
QListWidget::item:hover {
    background-color: #334155;
}
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton#SecondaryBtn {
    background-color: #334155;
    color: #e2e8f0;
}
QPushButton#SecondaryBtn:hover {
    background-color: #475569;
}
QPushButton#ConvertBtn {
    background-color: #10b981;
    font-size: 14px;
    padding: 12px 24px;
}
QPushButton#ConvertBtn:hover {
    background-color: #059669;
}
QPushButton#ConvertBtn:disabled {
    background-color: #334155;
    color: #64748b;
}
QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 12px;
    color: #f8fafc;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #3b82f6;
}
QComboBox::drop-down {
    border: none;
}
QProgressBar {
    border: none;
    background-color: #1e293b;
    border-radius: 6px;
    height: 12px;
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
        self.files = []
        self.output_dir = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("IMG-CONVert - Batch Image Converter")
        self.resize(750, 580)
        self.setStyleSheet(MODERN_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("🖼️ IMG-CONVert")
        title_label.setObjectName("HeaderLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.count_label = QLabel("0 files selected")
        self.count_label.setObjectName("CountLabel")
        header_layout.addWidget(self.count_label)
        layout.addLayout(header_layout)

        # Drag & drop list widget
        self.list_widget = DropListWidget()
        self.list_widget.files_dropped.connect(self.add_dropped_files)
        layout.addWidget(self.list_widget)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("📁 Add Images")
        self.btn_add.clicked.connect(self.add_images)
        self.btn_clear = QPushButton("🗑️ Clear List")
        self.btn_clear.setObjectName("SecondaryBtn")
        self.btn_clear.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Settings frame
        settings_frame = QFrame()
        settings_frame.setStyleSheet("background-color: #1e293b; border-radius: 10px; padding: 12px;")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setSpacing(12)

        format_layout = QHBoxLayout()
        fmt_title = QLabel("Target Format:")
        fmt_title.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        format_layout.addWidget(fmt_title)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "JPG", "WEBP", "BMP", "GIF", "TIFF", "ICO"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        settings_layout.addLayout(format_layout)

        dir_layout = QHBoxLayout()
        self.btn_dir = QPushButton("📂 Output Directory")
        self.btn_dir.setObjectName("SecondaryBtn")
        self.btn_dir.clicked.connect(self.select_output_dir)
        self.lbl_dir = QLabel("Output: Original Folder (Default)")
        self.lbl_dir.setStyleSheet("color: #94a3b8;")
        dir_layout.addWidget(self.btn_dir)
        dir_layout.addWidget(self.lbl_dir)
        dir_layout.addStretch()
        settings_layout.addLayout(dir_layout)

        layout.addWidget(settings_frame)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Convert button
        self.btn_convert = QPushButton("⚡ Convert All Images")
        self.btn_convert.setObjectName("ConvertBtn")
        self.btn_convert.clicked.connect(self.convert_images)
        layout.addWidget(self.btn_convert)

    def add_dropped_files(self, new_files):
        for f in new_files:
            if f not in self.files:
                self.files.append(f)
                self.list_widget.addItem(f"{Path(f).name}  ({Path(f).suffix.upper()})")
        self.update_count()

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.ico *.tif)"
        )
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.list_widget.addItem(f"{Path(f).name}  ({Path(f).suffix.upper()})")
        self.update_count()

    def clear_list(self):
        self.files.clear()
        self.list_widget.clear()
        self.update_count()

    def update_count(self):
        count = len(self.files)
        self.count_label.setText(f"{count} file{'s' if count != 1 else ''} selected")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if dir_path:
            self.output_dir = dir_path
            self.lbl_dir.setText(f"Output: {dir_path}")

    def convert_images(self):
        if not self.files:
            QMessageBox.warning(self, "No Images", "Please add images to convert.")
            return

        output_dir = self.output_dir or os.path.dirname(self.files[0])
        output_format = self.format_combo.currentText()

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_convert.setEnabled(False)

        self.thread = ConversionThread(self.files, output_dir, output_format)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.show_error)
        self.thread.start()

    def on_finished(self):
        self.progress_bar.setVisible(False)
        self.btn_convert.setEnabled(True)
        QMessageBox.information(self, "Success", "All images converted successfully!")

    def show_error(self, msg):
        QMessageBox.warning(self, "Error", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageConverterApp()
    window.show()
    sys.exit(app.exec())

