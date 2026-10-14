from PySide6.QtGui import QColor, QPalette

QSS = """
* { font-family: 'Segoe UI', 'Segoe UI Emoji'; font-size: 10pt; }
QMainWindow, QDialog { background: #12141a; }
QToolTip { background: #252a3c; color: #e8eaf0; border: 1px solid #3a4160; padding: 4px; }

QFrame#side { background: #0d0f14; border-right: 1px solid #1f2331; }
QLabel#logo { font-size: 17pt; font-weight: 700; color: #ffffff; padding: 20px 16px 16px 16px; }
QLabel#ver { color: #5d647c; font-size: 8pt; padding: 4px 16px 12px 16px; }
QPushButton#nav { text-align: left; padding: 11px 16px; margin: 2px 10px; border-radius: 10px;
                  border: none; background: transparent; color: #aeb4c8; font-size: 11pt; }
QPushButton#nav:hover { background: #1b1f2c; }
QPushButton#nav:checked { background: #2a3566; color: #ffffff; }
QPushButton#defbtn { text-align: left; padding: 9px 14px; margin: 6px 10px; border-radius: 10px;
                     background: #1b1f2c; color: #aeb4c8; }
QPushButton#defbtn:hover { background: #262b3d; color: #fff; }

QPushButton { background: #252a3c; border: none; border-radius: 8px; padding: 7px 14px; }
QPushButton:hover { background: #30374f; }
QPushButton:pressed { background: #3a4466; }
QPushButton#primary { background: #5b7cff; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #7390ff; }
QPushButton#quick { background: #1a1d28; border: 1px solid #262b3d; border-radius: 14px;
                    padding: 18px; font-size: 11pt; text-align: left; }
QPushButton#quick:hover { border-color: #5b7cff; background: #1e2232; }

QToolBar { background: #171a24; border: none; spacing: 3px; padding: 5px 8px; }
QToolBar::separator { background: #2a2f44; width: 1px; margin: 4px 6px; }
QToolButton { background: transparent; border: none; border-radius: 7px; padding: 6px 9px; }
QToolButton:hover { background: #262b3d; }
QToolButton:checked { background: #3a4a9a; }
QToolButton:pressed { background: #44549f; }

QLineEdit, QSpinBox, QComboBox, QFontComboBox, QPlainTextEdit {
    background: #1a1d28; border: 1px solid #2a2f44; border-radius: 7px; padding: 5px 8px;
    selection-background-color: #5b7cff; }
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus { border-color: #5b7cff; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #1a1d28; border: 1px solid #2a2f44; selection-background-color: #3a4a9a; }

QListWidget { background: #14161e; border: none; outline: none; }
QListWidget::item { border-radius: 8px; padding: 4px; color: #aeb4c8; }
QListWidget::item:hover { background: #1b1f2c; }
QListWidget::item:selected { background: #2a3566; color: white; }

QScrollArea { border: none; background: #0f1117; }
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar::handle:vertical { background: #333a55; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4a5380; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: #333a55; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QSplitter::handle { background: #1f2331; }
QStatusBar, QLabel#status { color: #7a8099; }

QFrame#hero { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4b5cff, stop:1 #9b4dff);
              border-radius: 18px; }
QFrame#hero QLabel { color: white; background: transparent; }
QLabel#h1 { font-size: 22pt; font-weight: 700; }
QLabel#h2 { font-size: 13pt; font-weight: 600; color: #ffffff; }
QLabel#sub { color: #e3e6ff; font-size: 11pt; }

QFrame#card { background: #1a1d28; border: 1px solid #262b3d; border-radius: 12px; }
QFrame#card:hover { border-color: #5b7cff; background: #1d2130; }
QLabel#meta { color: #7d97ff; font-size: 8pt; font-weight: 600; }
QLabel#ctitle { font-size: 12pt; font-weight: 600; }
QLabel#cdesc { color: #9aa1b8; }
"""


def apply_theme(app):
    app.setStyle("Fusion")
    p = QPalette()
    c = QColor
    p.setColor(QPalette.Window, c("#12141a"))
    p.setColor(QPalette.WindowText, c("#e8eaf0"))
    p.setColor(QPalette.Base, c("#1a1d28"))
    p.setColor(QPalette.AlternateBase, c("#171a24"))
    p.setColor(QPalette.ToolTipBase, c("#252a3c"))
    p.setColor(QPalette.ToolTipText, c("#e8eaf0"))
    p.setColor(QPalette.Text, c("#e8eaf0"))
    p.setColor(QPalette.Button, c("#252a3c"))
    p.setColor(QPalette.ButtonText, c("#e8eaf0"))
    p.setColor(QPalette.BrightText, c("#ff5c5c"))
    p.setColor(QPalette.Link, c("#7d97ff"))
    p.setColor(QPalette.Highlight, c("#5b7cff"))
    p.setColor(QPalette.HighlightedText, c("#ffffff"))
    p.setColor(QPalette.PlaceholderText, c("#7a8099"))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, role, c("#6b7189"))
    app.setPalette(p)
    app.setStyleSheet(QSS)
