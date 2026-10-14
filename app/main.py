import os
import sys

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from common import APP, res
from docs_module import DocsModule
from news_module import NewsModule
from pdf_module import PdfModule
from slides_module import SlidesModule
from theme import apply_theme

VERSION = "1.0.0"
ROUTE = {".pdf": 1, ".pptx": 2, ".docx": 3, ".txt": 3, ".md": 3, ".html": 3, ".htm": 3}
FILTER = "Все поддерживаемые (*.pdf *.pptx *.docx *.txt *.md *.html *.htm)"


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.resize(1360, 860)
        self.setAcceptDrops(True)
        ico = res("icon.ico")
        if ico:
            self.setWindowIcon(QIcon(ico))

        self.home = NewsModule()
        self.pdf = PdfModule()
        self.slides = SlidesModule()
        self.docs = DocsModule()
        self.mods = [("🏠   Главная", self.home), ("📕   PDF", self.pdf),
                     ("📊   Презентации", self.slides), ("📝   Документы", self.docs)]

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        logo = QLabel("Nova Office")
        logo.setObjectName("logo")
        sl.addWidget(logo)
        self.stack = QStackedWidget()
        self.btns = []
        for i, (name, w) in enumerate(self.mods):
            b = QPushButton(name)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            sl.addWidget(b)
            self.btns.append(b)
            self.stack.addWidget(w)
        sl.addStretch(1)
        d = QPushButton("⚙   Программа по умолчанию")
        d.setObjectName("defbtn")
        d.setToolTip("Откроет настройки Windows: выберите Nova Office для PDF, PPTX, DOCX")
        d.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("ms-settings:defaultapps")))
        sl.addWidget(d)
        v = QLabel(f"версия {VERSION}")
        v.setObjectName("ver")
        sl.addWidget(v)

        lay.addWidget(side)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.home.act.connect(self.on_home_action)
        self.home.open_recent.connect(self.open_any)
        self.go(0)

    def go(self, i):
        self.stack.setCurrentIndex(i)
        for k, b in enumerate(self.btns):
            b.setChecked(k == i)

    def on_home_action(self, key):
        if key == "open":
            p, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", FILTER)
            if p:
                self.open_any(p)
        elif key == "pdf":
            self.go(1)
            self.pdf.open_dialog()
        elif key == "new_pres":
            self.go(2)
            self.slides.new()
        elif key == "new_doc":
            self.go(3)
            self.docs.new()

    def open_any(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".ppt", ".doc"):
            QMessageBox.information(self, APP, "Старые форматы .ppt и .doc не поддерживаются.\n"
                                    "Сохраните файл как .pptx / .docx и откройте снова.")
            return
        if ext not in ROUTE or not os.path.exists(path):
            QMessageBox.information(self, APP, "Этот формат файла не поддерживается.")
            return
        i = ROUTE[ext]
        self.go(i)
        self.mods[i][1].open_file(path)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.isLocalFile():
                self.open_any(u.toLocalFile())
                break

    def closeEvent(self, e):
        for _, m in self.mods[1:]:
            if not m.can_close():
                e.ignore()
                return
        e.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setOrganizationName("NovaOffice")
    apply_theme(app)
    w = Main()
    w.show()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args and os.path.exists(args[0]):
        QTimer.singleShot(0, lambda: w.open_any(os.path.abspath(args[0])))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
