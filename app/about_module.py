import webbrowser

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget)

import updater
from version import BUILD, REPO, VERSION


class RunsLoader(QThread):
    done = Signal(list, str)

    def run(self):
        try:
            self.done.emit(updater.fetch_runs(30), "")
        except Exception as e:
            self.done.emit([], f"Не удалось загрузить ({type(e).__name__})")


class AboutModule(QWidget):
    """Новости программы: история сборок с описаниями изменений прямо из GitHub."""

    def __init__(self):
        super().__init__()
        self.runs = []
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 20)
        root.setSpacing(10)
        t = QLabel("Новости Nova Office")
        t.setObjectName("h1")
        root.addWidget(t)
        b, _ = updater.installed_build()
        cur = QLabel(f"Установлена версия {VERSION}" + (f", сборка №{b}" if b else ", сборка из исходников"))
        cur.setObjectName("sub")
        root.addWidget(cur)

        row = QHBoxLayout()
        self.btn = QPushButton("Проверить обновления")
        self.btn.setObjectName("primary")
        row.addWidget(self.btn)
        r = QPushButton("Обновить список")
        r.clicked.connect(self.load)
        row.addWidget(r)
        g = QPushButton("Открыть на GitHub")
        g.clicked.connect(lambda: webbrowser.open(f"https://github.com/{REPO}/actions"))
        row.addWidget(g)
        row.addStretch(1)
        root.addLayout(row)

        self.status = QLabel("")
        self.status.setObjectName("status")
        root.addWidget(self.status)
        h = QHBoxLayout()
        self.lst = QListWidget()
        self.lst.setFixedWidth(240)
        self.lst.currentRowChanged.connect(self.show_run)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        h.addWidget(self.lst)
        h.addWidget(self.text, 1)
        root.addLayout(h, 1)
        self._loaded = False

    def showEvent(self, e):
        super().showEvent(e)
        if not self._loaded:
            self._loaded = True
            self.load()

    def load(self):
        if getattr(self, "w", None) is not None and self.w.isRunning():
            return
        self.status.setText("Загрузка…")
        self.w = RunsLoader()
        self.w.done.connect(self.fill)
        self.w.start()

    def fill(self, runs, err):
        self.runs = runs
        self.lst.clear()
        mine, sha = updater.installed_build()
        for r in runs:
            mark = "   · установлена" if (sha and r["sha"] == sha) or (mine and r["n"] == mine) else ""
            self.lst.addItem(QListWidgetItem(f"Сборка №{r['n']}   {r['date']}{mark}"))
        self.status.setText(err or (f"Успешных сборок: {len(runs)}" if runs else "Пока нет успешных сборок"))
        if runs:
            self.lst.setCurrentRow(0)

    def show_run(self, i):
        if 0 <= i < len(self.runs):
            r = self.runs[i]
            self.text.setPlainText(f"Сборка №{r['n']} · {r['date']}\n\n{r['msg'] or 'Без описания'}")
