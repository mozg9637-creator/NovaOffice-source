"""Установщик Nova Office. Запуск: без ключей — мастер; /UPDATE или /S — тихая установка; /UNINSTALL — удаление."""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

try:
    import winreg
except ImportError:          # для проверки на не-Windows
    winreg = None

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from version import BUILD, VERSION

NAME = "Nova Office"
EXE = "NovaOffice.exe"
KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NovaOffice"
EXTS = (".pdf", ".pptx", ".docx", ".txt", ".md")
NOFLAG = 0x08000000   # CREATE_NO_WINDOW
QSS = """
* { font-family: 'Segoe UI'; font-size: 9.5pt; color: #dcdde0; }
QWidget#root { background: #1c1d1f; }
QLabel#t { font-size: 17pt; font-weight: 600; }
QLabel#d { color: #8d9097; }
QLineEdit { background: #232426; border: 1px solid #35373b; border-radius: 3px; padding: 5px 7px; }
QPushButton { background: #2a2b2e; border: 1px solid #35373b; border-radius: 3px; padding: 6px 16px; }
QPushButton:hover { background: #2f3033; }
QPushButton#go { background: #3b6ea5; border-color: #3b6ea5; color: white; }
QPushButton#go:hover { background: #4d80b8; }
QProgressBar { background: #232426; border: 1px solid #35373b; border-radius: 3px; height: 14px; text-align: center; }
QProgressBar::chunk { background: #3b6ea5; }
"""


def res(name):
    for b in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.abspath(__file__))):
        if b and os.path.exists(os.path.join(b, name)):
            return os.path.join(b, name)


def reg_set(path, name, value, kind=None):
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(k, name, 0, kind or winreg.REG_SZ, value)
    winreg.CloseKey(k)


def reg_get(path, name):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        v = winreg.QueryValueEx(k, name)[0]
        winreg.CloseKey(k)
        return v
    except OSError:
        return None


def reg_del_tree(path):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS)
        while True:
            try:
                reg_del_tree(path + "\\" + winreg.EnumKey(k, 0))
            except OSError:
                break
        winreg.CloseKey(k)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        pass


def default_dir():
    return reg_get(KEY, "InstallLocation") or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", NAME)


def shortcut(lnk, target, icon):
    os.makedirs(os.path.dirname(lnk), exist_ok=True)
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
          f"$s.TargetPath='{target}';$s.WorkingDirectory='{os.path.dirname(target)}';"
          f"$s.IconLocation='{icon}';$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=NOFLAG, check=False)


def desktop():
    return os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")


def start_menu():
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")


def kill_app():
    subprocess.run(["taskkill", "/IM", EXE, "/F"], creationflags=NOFLAG, capture_output=True)
    time.sleep(1)


def refresh_shell():
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


class Worker(QThread):
    progress = Signal(int, str)
    done = Signal(str)

    def __init__(self, target, desk, menu, assoc):
        super().__init__()
        self.target, self.desk, self.menu, self.assoc = target, desk, menu, assoc

    def run(self):
        try:
            self.install()
            self.done.emit("")
        except Exception as e:
            self.done.emit(f"{type(e).__name__}: {e}")

    def install(self):
        t = self.target
        self.progress.emit(2, "Закрываю запущенную программу…")
        kill_app()
        os.makedirs(t, exist_ok=True)
        with zipfile.ZipFile(res("payload.zip")) as z:
            names = z.namelist()
            for i, n in enumerate(names):
                self.progress.emit(5 + int(80 * i / len(names)), "Копирую файлы…")
                z.extract(n, t)
        self.progress.emit(88, "Настраиваю систему…")
        exe = os.path.join(t, EXE)
        unins = os.path.join(t, "uninstall.exe")
        if getattr(sys, "frozen", False):
            shutil.copy2(sys.executable, unins)
        if self.menu:
            shortcut(os.path.join(start_menu(), NAME + ".lnk"), exe, exe)
        if self.desk:
            shortcut(os.path.join(desktop(), NAME + ".lnk"), exe, exe)
        if self.assoc:
            cls = r"Software\Classes"
            reg_set(cls + r"\NovaOffice.File", "", "Документ Nova Office")
            reg_set(cls + r"\NovaOffice.File\DefaultIcon", "", f"{exe},0")
            reg_set(cls + r"\NovaOffice.File\shell\open\command", "", f'"{exe}" "%1"')
            reg_set(cls + r"\Applications\NovaOffice.exe\shell\open\command", "", f'"{exe}" "%1"')
            cap = r"Software\NovaOffice\Capabilities"
            reg_set(cap, "ApplicationName", NAME)
            reg_set(cap, "ApplicationDescription", "PDF, презентации и документы")
            for e in EXTS:
                reg_set(cls + f"\\{e}\\OpenWithProgids", "NovaOffice.File", "")
                reg_set(cap + r"\FileAssociations", e, "NovaOffice.File")
            reg_set(r"Software\RegisteredApplications", "NovaOffice", cap)
        reg_set(KEY, "DisplayName", NAME)
        reg_set(KEY, "DisplayVersion", VERSION + (f".{BUILD}" if BUILD else ""))
        reg_set(KEY, "Publisher", "Nova")
        reg_set(KEY, "InstallLocation", t)
        reg_set(KEY, "DisplayIcon", exe)
        reg_set(KEY, "UninstallString", f'"{unins}" /UNINSTALL')
        reg_set(KEY, "NoModify", 1, winreg.REG_DWORD)
        reg_set(KEY, "NoRepair", 1, winreg.REG_DWORD)
        reg_set(r"Software\NovaOffice", "installed_build", str(BUILD))
        refresh_shell()
        self.progress.emit(100, "Готово")


def uninstall(silent=False):
    t = reg_get(KEY, "InstallLocation") or os.path.dirname(os.path.abspath(sys.executable))
    if not silent:
        a = QApplication.instance() or QApplication(sys.argv)
        if QMessageBox.question(None, NAME, f"Удалить {NAME} с этого компьютера?") != QMessageBox.Yes:
            return
    kill_app()
    for p in (os.path.join(start_menu(), NAME + ".lnk"), os.path.join(desktop(), NAME + ".lnk")):
        if os.path.exists(p):
            os.remove(p)
    for e in EXTS:
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{e}\\OpenWithProgids", 0,
                               winreg.KEY_SET_VALUE)
            winreg.DeleteValue(k, "NovaOffice.File")
            winreg.CloseKey(k)
        except OSError:
            pass
    for p in (r"Software\Classes\NovaOffice.File", r"Software\Classes\Applications\NovaOffice.exe",
              r"Software\NovaOffice", KEY):
        reg_del_tree(p)
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, "NovaOffice")
        winreg.CloseKey(k)
    except OSError:
        pass
    refresh_shell()
    # папку с самим uninstall.exe удаляем отдельным процессом после выхода
    subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{t}"', creationflags=NOFLAG)
    if not silent:
        QMessageBox.information(None, NAME, "Nova Office удалён.")


class Wizard(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(f"Установка {NAME}")
        self.setFixedSize(520, 360)
        ico = res("icon.ico")
        if ico:
            self.setWindowIcon(QIcon(ico))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        p1 = QWidget()
        l = QVBoxLayout(p1)
        l.setContentsMargins(0, 0, 0, 0)
        t = QLabel(NAME)
        t.setObjectName("t")
        d = QLabel(f"Версия {VERSION}" + (f", сборка №{BUILD}" if BUILD else "") + "\nPDF, презентации и документы.")
        d.setObjectName("d")
        l.addWidget(t)
        l.addWidget(d)
        l.addSpacing(14)
        l.addWidget(QLabel("Папка установки"))
        row = QHBoxLayout()
        self.path = QLineEdit(default_dir())
        b = QPushButton("Обзор…")
        b.clicked.connect(self.browse)
        row.addWidget(self.path, 1)
        row.addWidget(b)
        l.addLayout(row)
        l.addSpacing(8)
        self.c_menu = QCheckBox("Ярлык в меню «Пуск»")
        self.c_menu.setChecked(True)
        self.c_desk = QCheckBox("Ярлык на рабочем столе")
        self.c_assoc = QCheckBox("Добавить в «Открыть с помощью» (PDF, PPTX, DOCX, TXT, MD)")
        self.c_assoc.setChecked(True)
        for c in (self.c_menu, self.c_desk, self.c_assoc):
            l.addWidget(c)
        l.addStretch(1)
        self.stack.addWidget(p1)

        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        l2.addStretch(1)
        self.msg = QLabel("Установка…")
        self.bar = QProgressBar()
        l2.addWidget(self.msg)
        l2.addWidget(self.bar)
        l2.addStretch(1)
        self.stack.addWidget(p2)

        p3 = QWidget()
        l3 = QVBoxLayout(p3)
        l3.addStretch(1)
        self.fin = QLabel("")
        self.fin.setObjectName("t")
        self.fin.setWordWrap(True)
        self.run_cb = QCheckBox("Запустить Nova Office")
        self.run_cb.setChecked(True)
        l3.addWidget(self.fin)
        l3.addWidget(self.run_cb)
        l3.addStretch(1)
        self.stack.addWidget(p3)

        bt = QHBoxLayout()
        bt.addStretch(1)
        self.cancel = QPushButton("Отмена")
        self.cancel.clicked.connect(self.close)
        self.next = QPushButton("Установить")
        self.next.setObjectName("go")
        self.next.clicked.connect(self.start)
        bt.addWidget(self.cancel)
        bt.addWidget(self.next)
        lay.addLayout(bt)

    def browse(self):
        p = QFileDialog.getExistingDirectory(self, "Папка установки", self.path.text())
        if p:
            self.path.setText(os.path.join(p, NAME) if os.listdir(p) else p)

    def start(self):
        self.stack.setCurrentIndex(1)
        self.next.setEnabled(False)
        self.cancel.setEnabled(False)
        self.w = Worker(self.path.text().strip(), self.c_desk.isChecked(), self.c_menu.isChecked(),
                        self.c_assoc.isChecked())
        self.w.progress.connect(lambda v, m: (self.bar.setValue(v), self.msg.setText(m)))
        self.w.done.connect(self.finished)
        self.w.start()

    def finished(self, err):
        self.stack.setCurrentIndex(2)
        self.cancel.hide()
        self.next.setEnabled(True)
        self.next.setText("Закрыть")
        self.next.clicked.disconnect()
        if err:
            self.fin.setText("Ошибка установки:\n" + err)
            self.run_cb.hide()
            self.next.clicked.connect(self.close)
        else:
            self.fin.setText("Готово")
            self.exe = os.path.join(self.path.text().strip(), EXE)
            self.next.clicked.connect(self.close_and_run)

    def close_and_run(self):
        if self.run_cb.isChecked():
            subprocess.Popen([self.exe], cwd=os.path.dirname(self.exe))
        self.close()


def main():
    args = [a.upper() for a in sys.argv[1:]]
    if "/UNINSTALL" in args:
        if "/S" not in args and getattr(sys, "frozen", False):      # копия во временную папку, чтобы удалить папку приложения
            tmp = os.path.join(tempfile.gettempdir(), "novaoffice_uninstall.exe")
            if os.path.abspath(sys.executable) != tmp:
                shutil.copy2(sys.executable, tmp)
                subprocess.Popen([tmp, "/UNINSTALL"])
                return
        uninstall("/S" in args)
        return
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    if "/UPDATE" in args or "/S" in args:       # тихая установка поверх, с теми же параметрами
        t = default_dir()
        w = Worker(t, os.path.exists(os.path.join(desktop(), NAME + ".lnk")), True, True)
        w.install()
        subprocess.Popen([os.path.join(t, EXE)], cwd=t)
        return
    w = Wizard()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
