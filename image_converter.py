import sys
import os
from pathlib import Path
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QComboBox, QLabel, QProgressBar,
                             QFileDialog, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


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


class ImageConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("IMG-CONVert - Batch Image Converter")
        self.setMinimumSize(600, 500)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.label = QLabel("Select images to convert:")
        layout.addWidget(self.label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Images")
        self.btn_add.clicked.connect(self.add_images)
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "JPG", "BMP", "GIF", "TIFF", "WEBP", "ICO"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        dir_layout = QHBoxLayout()
        self.btn_dir = QPushButton("Select Output Folder")
        self.btn_dir.clicked.connect(self.select_output_dir)
        self.lbl_dir = QLabel("Output: Same as input")
        self.output_dir = None
        dir_layout.addWidget(self.btn_dir)
        dir_layout.addWidget(self.lbl_dir)
        layout.addLayout(dir_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.btn_convert = QPushButton("Convert All")
        self.btn_convert.clicked.connect(self.convert_images)
        layout.addWidget(self.btn_convert)

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.ico *.tif)"
        )
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.list_widget.addItem(f)

    def clear_list(self):
        self.files.clear()
        self.list_widget.clear()

    def select_output_dir(self):
        dir = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if dir:
            self.output_dir = dir
            self.lbl_dir.setText(f"Output: {dir}")

    def convert_images(self):
        if not self.files:
            QMessageBox.warning(self, "No Images", "Please add images first.")
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
        QMessageBox.information(self, "Done", "All images converted successfully!")

    def show_error(self, msg):
        QMessageBox.warning(self, "Error", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageConverterApp()
    window.show()
    sys.exit(app.exec())
