import os
import sys

import time

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from about_module import AboutModule
from common import APP, _s, recent, res
from docs_module import DocsModule
from news_module import NewsModule
from palette import Palette
from pdf_module import PdfModule
from settings_module import SettingsModule, flag
from slides_module import SlidesModule
from theme import apply_theme
from updater import check_updates
from version import VERSION

ROUTE = {".pdf": 1, ".pptx": 2, ".docx": 3, ".txt": 3, ".md": 3, ".html": 3, ".htm": 3}
FILTER = "Все поддерживаемые (*.pdf *.pptx *.docx *.txt *.md *.html *.htm)"


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP} {VERSION}")
        self.resize(1360, 860)
        self.setAcceptDrops(True)
        ico = res("icon.ico")
        if ico:
            self.setWindowIcon(QIcon(ico))

        self.home = NewsModule()
        self.pdf = PdfModule()
        self.slides = SlidesModule()
        self.docs = DocsModule()
        self.about = AboutModule()
        self.sett = SettingsModule()
        self.mods = [("Главная", self.home), ("PDF", self.pdf), ("Презентации", self.slides),
                     ("Документы", self.docs), ("Новости программы", self.about), ("Настройки", self.sett)]

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
        d = QPushButton("Программа по умолчанию")
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
        self.about.btn.clicked.connect(lambda: check_updates(self, silent=False))
        self.sett.changed.connect(self.on_settings)
        self.sett.feeds_clicked.connect(self.home.edit_feeds)
        self.sett.recent_cleared.connect(self.home.recent_list.clear)
        self.pal = QShortcut(QKeySequence("Ctrl+K"), self)
        self.pal.activated.connect(self.open_palette)
        self.go(int(_s.value("start_page", 0)))
        if flag("remember_geometry"):
            g = _s.value("geometry")
            if g:
                self.restoreGeometry(g)
        QShortcut(QKeySequence("F1"), self).activated.connect(self.help)
        QShortcut(QKeySequence("F11"), self).activated.connect(
            lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen())
        QTimer.singleShot(2500, self.auto_update)

    def help(self):
        QMessageBox.information(self, "Горячие клавиши", (
            "Ctrl+K — быстрые команды\nCtrl+O / Ctrl+S / Ctrl+P — открыть / сохранить / печать\n"
            "F11 — полный экран\n\nПрезентации:\nF5 — показ с первого слайда\nShift+F5 — показ с текущего\n"
            "Ctrl+D — дублировать слайд\nВ показе: стрелки/пробел — листать, Home/End — первый/последний,\n"
            "B / W — чёрный / белый экран, L — указка, T — таймер,\nцифры+Enter — перейти к слайду, Esc — выход"))

    def on_settings(self):
        apply_theme(QApplication.instance())
        self.home.apply_settings()

    def auto_update(self):
        if not flag("auto_update"):
            return
        gap = int(_s.value("update_every_h", 6)) * 3600
        if time.time() - int(_s.value("last_update_check", 0) or 0) >= gap:
            check_updates(self, silent=True)

    def open_palette(self):
        items = [("Открыть файл…", lambda: self.on_home_action("open")),
                 ("Открыть PDF", lambda: self.on_home_action("pdf")),
                 ("Новая презентация", lambda: self.on_home_action("new_pres")),
                 ("Новый документ", lambda: self.on_home_action("new_doc")),
                 ("Проверить обновления", lambda: check_updates(self, silent=False)),
                 ("Новости программы", lambda: self.go(4)),
                 ("Настройки", lambda: self.go(5)),
                 ("Переключить тему", self.toggle_theme)]
        items += [(f"Недавний: {os.path.basename(p)}", lambda p=p: self.open_any(p)) for p in recent()]
        Palette(self, items).exec()

    def toggle_theme(self):
        _s.setValue("theme", "light" if _s.value("theme", "dark") == "dark" else "dark")
        self.on_settings()

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
        for _, m in self.mods[1:4]:
            if not m.can_close():
                e.ignore()
                return
        if flag("remember_geometry"):
            _s.setValue("geometry", self.saveGeometry())
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
    elif flag("open_last", False) and recent():
        QTimer.singleShot(0, lambda: w.open_any(recent()[0]))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
