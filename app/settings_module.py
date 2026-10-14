from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from common import _s
from theme import ACCENTS


def flag(key, default=True):
    v = _s.value(key, default)
    return v in (True, "true", "1", 1)


class SettingsModule(QWidget):
    changed = Signal()
    feeds_clicked = Signal()
    recent_cleared = Signal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 20)
        root.setSpacing(14)
        t = QLabel("Настройки")
        t.setObjectName("h1")
        root.addWidget(t)

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        form.setVerticalSpacing(11)
        form.setHorizontalSpacing(24)

        self.theme = QComboBox()
        self.theme.addItems(["Тёмная", "Светлая"])
        self.theme.setCurrentIndex(0 if _s.value("theme", "dark") == "dark" else 1)
        form.addRow("Тема", self.theme)

        self.accent = QComboBox()
        self.accent.addItems(list(ACCENTS))
        self.accent.setCurrentText(_s.value("accent", "Синий"))
        form.addRow("Цвет выделения", self.accent)

        self.start = QComboBox()
        self.start.addItems(["Главная", "PDF", "Презентации", "Документы"])
        self.start.setCurrentIndex(int(_s.value("start_page", 0)))
        form.addRow("Открывать при запуске", self.start)

        self.news_min = QSpinBox()
        self.news_min.setRange(2, 240)
        self.news_min.setSuffix(" мин")
        self.news_min.setValue(int(_s.value("news_min", 10)))
        form.addRow("Обновлять ленту новостей", self.news_min)

        self.restore = QCheckBox("Показывать недавние файлы на главной")
        self.restore.setChecked(flag("show_recent"))
        form.addRow("", self.restore)

        self.auto = QCheckBox("Проверять обновления при запуске")
        self.auto.setChecked(flag("auto_update"))
        form.addRow("Обновления", self.auto)

        self.every = QSpinBox()
        self.every.setRange(1, 168)
        self.every.setSuffix(" ч")
        self.every.setValue(int(_s.value("update_every_h", 6)))
        form.addRow("Не чаще чем раз в", self.every)

        self.token = QLineEdit(_s.value("gh_token", ""))
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText("необязательно — нужен для скачивания артефактов Actions")
        form.addRow("Токен GitHub", self.token)
        root.addLayout(form)

        sep = QFrame()
        sep.setObjectName("sep")
        root.addWidget(sep)

        row = QHBoxLayout()
        b1 = QPushButton("Источники новостей…")
        b1.clicked.connect(self.feeds_clicked)
        b2 = QPushButton("Очистить недавние файлы")
        b2.clicked.connect(self.clear_recent)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        root.addLayout(row)
        root.addStretch(1)

        for w in (self.theme, self.accent, self.start):
            w.currentIndexChanged.connect(self.save)
        for w in (self.news_min, self.every):
            w.valueChanged.connect(self.save)
        for w in (self.restore, self.auto):
            w.toggled.connect(self.save)
        self.token.editingFinished.connect(self.save)

    def clear_recent(self):
        _s.setValue("recent", [])
        self.recent_cleared.emit()

    def save(self):
        _s.setValue("theme", "dark" if self.theme.currentIndex() == 0 else "light")
        _s.setValue("accent", self.accent.currentText())
        _s.setValue("start_page", self.start.currentIndex())
        _s.setValue("news_min", self.news_min.value())
        _s.setValue("show_recent", self.restore.isChecked())
        _s.setValue("auto_update", self.auto.isChecked())
        _s.setValue("update_every_h", self.every.value())
        _s.setValue("gh_token", self.token.text().strip())
        self.changed.emit()
