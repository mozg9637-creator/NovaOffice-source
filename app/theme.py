from PySide6.QtGui import QColor, QPalette

from common import _s

ACCENTS = {
    "Синий": "#3b6ea5",
    "Зелёный": "#3f7d5c",
    "Кирпичный": "#b5533c",
    "Графит": "#6b7280",
}

DARK = dict(bg="#1c1d1f", bg2="#232426", side="#17181a", panel="#2a2b2e", line="#35373b",
            text="#dcdde0", dim="#8d9097", hover="#2f3033")
LIGHT = dict(bg="#f4f3f1", bg2="#ffffff", side="#e9e8e5", panel="#e3e2df", line="#cfcdc9",
             text="#222326", dim="#6b6d72", hover="#dddcd8")

QSS = """
* { font-family: 'Segoe UI'; font-size: 9.5pt; }
QMainWindow, QDialog { background: %(bg)s; }
QToolTip { background: %(bg2)s; color: %(text)s; border: 1px solid %(line)s; padding: 3px 5px; }

QFrame#side { background: %(side)s; border-right: 1px solid %(line)s; }
QLabel#logo { font-size: 13pt; font-weight: 600; color: %(text)s; padding: 16px 16px 12px 16px; }
QLabel#ver { color: %(dim)s; font-size: 8pt; padding: 4px 16px 10px 16px; }
QPushButton#nav { text-align: left; padding: 8px 16px; margin: 0; border-radius: 0;
                  border: none; border-left: 3px solid transparent; background: transparent; color: %(dim)s; }
QPushButton#nav:hover { background: %(hover)s; color: %(text)s; }
QPushButton#nav:checked { background: %(bg)s; color: %(text)s; border-left: 3px solid %(acc)s; }
QPushButton#defbtn { text-align: left; padding: 7px 16px; margin: 0; border-radius: 0;
                     background: transparent; color: %(dim)s; }
QPushButton#defbtn:hover { background: %(hover)s; color: %(text)s; }

QPushButton { background: %(panel)s; border: 1px solid %(line)s; border-radius: 3px; padding: 5px 12px; color: %(text)s; }
QPushButton:hover { background: %(hover)s; }
QPushButton:pressed { background: %(line)s; }
QPushButton#primary { background: %(acc)s; border-color: %(acc)s; color: white; }
QPushButton#primary:hover { background: %(acc2)s; }
QPushButton#quick { background: transparent; border: 1px solid %(line)s; border-radius: 3px;
                    padding: 10px 14px; text-align: left; }
QPushButton#quick:hover { border-color: %(acc)s; }

QToolBar { background: %(bg2)s; border: none; border-bottom: 1px solid %(line)s; spacing: 2px; padding: 3px 6px; }
QToolBar::separator { background: %(line)s; width: 1px; margin: 4px 5px; }
QToolButton { background: transparent; border: none; border-radius: 3px; padding: 5px 8px; color: %(text)s; }
QToolButton:hover { background: %(hover)s; }
QToolButton:checked { background: %(line)s; }
QToolButton:pressed { background: %(line)s; }

QLineEdit, QSpinBox, QComboBox, QFontComboBox, QPlainTextEdit, QTextEdit {
    background: %(bg2)s; border: 1px solid %(line)s; border-radius: 3px; padding: 4px 6px;
    selection-background-color: %(acc)s; selection-color: white; }
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: %(acc)s; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: %(bg2)s; border: 1px solid %(line)s; selection-background-color: %(acc)s; }
QCheckBox { spacing: 7px; }

QListWidget { background: %(bg2)s; border: 1px solid %(line)s; outline: none; }
QListWidget::item { padding: 5px 6px; color: %(text)s; }
QListWidget::item:hover { background: %(hover)s; }
QListWidget::item:selected { background: %(acc)s; color: white; }

QScrollArea { border: none; background: %(bg)s; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: %(line)s; border-radius: 3px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(dim)s; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: %(line)s; border-radius: 3px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QSplitter::handle { background: %(line)s; }
QTabWidget::pane { border: 1px solid %(line)s; }
QTabBar::tab { background: transparent; padding: 6px 14px; color: %(dim)s; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(text)s; border-bottom: 2px solid %(acc)s; }
QStatusBar, QLabel#status { color: %(dim)s; }
QProgressBar { background: %(bg2)s; border: 1px solid %(line)s; border-radius: 3px; text-align: center; height: 14px; }
QProgressBar::chunk { background: %(acc)s; }

QLabel#h1 { font-size: 17pt; font-weight: 600; color: %(text)s; }
QLabel#h2 { font-size: 11pt; font-weight: 600; color: %(text)s; }
QLabel#sub { color: %(dim)s; }
QLabel#meta { color: %(acc)s; font-size: 8pt; }
QLabel#ctitle { font-size: 10.5pt; font-weight: 600; }
QLabel#cdesc { color: %(dim)s; }
QFrame#card { background: transparent; border: none; border-bottom: 1px solid %(line)s; }
QFrame#card:hover { background: %(hover)s; }
QLabel#canvas, QWidget#wrap { background: %(side)s; }
QFrame#sep { background: %(line)s; max-height: 1px; }
"""


def current():
    return _s.value("theme", "dark")


def accent():
    return ACCENTS.get(_s.value("accent", "Синий"), ACCENTS["Синий"])


def apply_theme(app):
    c = QColor
    t = DARK if current() == "dark" else LIGHT
    acc = accent()
    acc2 = c(acc).lighter(118).name()
    app.setStyle("Fusion")
    p = QPalette()
    for role, col in ((QPalette.Window, t["bg"]), (QPalette.WindowText, t["text"]),
                      (QPalette.Base, t["bg2"]), (QPalette.AlternateBase, t["bg"]),
                      (QPalette.ToolTipBase, t["bg2"]), (QPalette.ToolTipText, t["text"]),
                      (QPalette.Text, t["text"]), (QPalette.Button, t["panel"]),
                      (QPalette.ButtonText, t["text"]), (QPalette.BrightText, "#ff5c5c"),
                      (QPalette.Link, acc2), (QPalette.Highlight, acc),
                      (QPalette.HighlightedText, "#ffffff"), (QPalette.PlaceholderText, t["dim"])):
        p.setColor(role, c(col))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, role, c(t["dim"]))
    app.setPalette(p)
    app.setStyleSheet(QSS % dict(t, acc=acc, acc2=acc2))
