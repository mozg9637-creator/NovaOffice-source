from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout


class Palette(QDialog):
    """Ctrl+K — быстрый поиск по командам и недавним файлам."""

    def __init__(self, parent, items):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.items = items          # [(название, функция)]
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Команда или имя файла…")
        self.edit.textChanged.connect(self.filter)
        self.edit.returnPressed.connect(self.run)
        lay.addWidget(self.edit)
        self.lst = QListWidget()
        self.lst.setMinimumHeight(260)
        self.lst.itemActivated.connect(lambda _: self.run())
        lay.addWidget(self.lst)
        self.filter("")

    def filter(self, q):
        q = q.lower().strip()
        self.lst.clear()
        for name, fn in self.items:
            if q in name.lower():
                it = QListWidgetItem(name)
                it.setData(Qt.UserRole, fn)
                self.lst.addItem(it)
        if self.lst.count():
            self.lst.setCurrentRow(0)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Down, Qt.Key_Up):
            self.lst.keyPressEvent(e)
        else:
            super().keyPressEvent(e)

    def run(self):
        it = self.lst.currentItem()
        if it:
            fn = it.data(Qt.UserRole)
            self.accept()
            fn()
