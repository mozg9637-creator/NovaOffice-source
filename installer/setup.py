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
QWidget#root, QWidget#main { background: #1c1d1f; }
QWidget#bar { background: #151618; border-right: 1px solid #2b2d30; }
QLabel#step { color: #6b6e75; padding: 5px 0 5px 12px; border-left: 3px solid transparent; }
QLabel#stepon { color: #ffffff; padding: 5px 0 5px 12px; border-left: 3px solid #3b6ea5; }
QLabel#brand { font-size: 13pt; font-weight: 600; padding: 4px 0 18px 12px; }
QLabel#t { font-size: 17pt; font-weight: 600; }
QLabel#d { color: #8d9097; }
QLabel#warn { color: #d9a441; }
QLabel#err { color: #e06c5f; }
QLineEdit { background: #232426; border: 1px solid #35373b; border-radius: 3px; padding: 5px 7px; }
QPushButton { background: #2a2b2e; border: 1px solid #35373b; border-radius: 3px; padding: 6px 18px; }
QPushButton:hover { background: #2f3033; }
QPushButton:disabled { color: #5d6066; }
QPushButton#go { background: #3b6ea5; border-color: #3b6ea5; color: white; }
QPushButton#go:hover { background: #4d80b8; }
QPushButton#go:disabled { background: #2c4a6b; border-color: #2c4a6b; color: #8aa0b8; }
QProgressBar { background: #232426; border: 1px solid #35373b; border-radius: 3px; height: 14px; text-align: center; }
QProgressBar::chunk { background: #3b6ea5; }
QCheckBox { spacing: 8px; }
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


LOG = os.path.join(tempfile.gettempdir(), "NovaOffice-setup.log")


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def single_instance():
    try:
        h = ctypes.windll.kernel32.CreateMutexW(None, False, "NovaOfficeSetupMutex")
        return ctypes.windll.kernel32.GetLastError() != 183      # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def free_space(path):
    p = os.path.abspath(path)
    while p and not os.path.exists(p):
        n = os.path.dirname(p)
        if n == p:
            break
        p = n
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return 1 << 62


def payload_size():
    try:
        with zipfile.ZipFile(res("payload.zip")) as z:
            return sum(i.file_size for i in z.infolist())
    except Exception:
        return 0


def check_target(t):
    """Текст ошибки или '' если папка подходит."""
    t = os.path.abspath(t.strip())
    if not t or os.path.dirname(t) == t:
        return "Выберите папку, а не корень диска."
    if os.path.exists(t) and not os.path.isdir(t):
        return "Это файл, а не папка."
    if os.path.isdir(t) and os.listdir(t) and not os.path.exists(os.path.join(t, EXE)):
        return "Папка не пуста и в ней не установлен Nova Office. Выберите пустую или новую папку."
    need = int(payload_size() * 1.15)
    if free_space(t) < need:
        return f"Недостаточно места на диске: нужно {need // (1 << 20)} МБ."
    return ""


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
            log(f"ОШИБКА: {type(e).__name__}: {e}")
            self.done.emit(f"{type(e).__name__}: {e}")

    def install(self):
        t = os.path.abspath(self.target)
        old = t + ".old"
        had_old = False
        log(f"установка в {t}, версия {VERSION} сборка {BUILD}")
        self.progress.emit(2, "Закрываю запущенную программу…")
        kill_app()
        try:
            if os.path.exists(os.path.join(t, EXE)):
                self.progress.emit(4, "Сохраняю предыдущую версию…")
                shutil.rmtree(old, ignore_errors=True)
                os.replace(t, old)
                had_old = True
            os.makedirs(t, exist_ok=True)
            with zipfile.ZipFile(res("payload.zip")) as z:
                infos = z.infolist()
                total = sum(i.file_size for i in infos) or 1
                done = 0
                for i in infos:
                    z.extract(i, t)
                    done += i.file_size
                    self.progress.emit(6 + int(80 * done / total), "Копирую: " + os.path.basename(i.filename))
            if not os.path.exists(os.path.join(t, EXE)):
                raise RuntimeError("в установщике нет NovaOffice.exe")
        except Exception:
            self.progress.emit(0, "Ошибка, возвращаю прежнюю версию…")
            shutil.rmtree(t, ignore_errors=True)
            if had_old:
                os.replace(old, t)
            raise
        self.progress.emit(88, "Настраиваю систему…")
        exe = os.path.join(t, EXE)
        unins = os.path.join(t, "uninstall.exe")
        if getattr(sys, "frozen", False):
            shutil.copy2(sys.executable, unins)
        for lnk, on in ((os.path.join(start_menu(), NAME + ".lnk"), self.menu),
                        (os.path.join(desktop(), NAME + ".lnk"), self.desk)):
            if on:
                shortcut(lnk, exe, exe)
            elif os.path.exists(lnk):
                os.remove(lnk)
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
        size_kb = max(1, sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(t) for f in fs) // 1024)
        reg_set(KEY, "DisplayName", NAME)
        reg_set(KEY, "DisplayVersion", VERSION + (f".{BUILD}" if BUILD else ""))
        reg_set(KEY, "Publisher", "Nova")
        reg_set(KEY, "InstallLocation", t)
        reg_set(KEY, "DisplayIcon", exe)
        reg_set(KEY, "InstallDate", time.strftime("%Y%m%d"))
        reg_set(KEY, "EstimatedSize", int(size_kb), winreg.REG_DWORD)
        reg_set(KEY, "UninstallString", f'"{unins}" /UNINSTALL')
        reg_set(KEY, "QuietUninstallString", f'"{unins}" /UNINSTALL /S')
        reg_set(KEY, "NoModify", 1, winreg.REG_DWORD)
        reg_set(KEY, "NoRepair", 1, winreg.REG_DWORD)
        if had_old:
            shutil.rmtree(old, ignore_errors=True)
        refresh_shell()
        log("установка завершена")
        self.progress.emit(100, "Готово")


def uninstall(silent=False, purge=False):
    t = reg_get(KEY, "InstallLocation") or os.path.dirname(os.path.abspath(sys.executable))
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
              r"Software\NovaOffice\Capabilities", KEY):
        reg_del_tree(p)
    if purge:       # настройки приложения (QSettings) лежат в Software\NovaOffice\NovaOffice
        reg_del_tree(r"Software\NovaOffice\NovaOffice")
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\NovaOffice")     # только если пусто
    except OSError:
        pass
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, "NovaOffice")
        winreg.CloseKey(k)
    except OSError:
        pass
    refresh_shell()
    log("удалено: " + t)
    # папку, где лежит сам uninstall.exe, удаляем отдельным процессом после выхода
    subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{t}"', creationflags=NOFLAG)


class UninstallDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(f"Удаление {NAME}")
        self.setFixedSize(440, 220)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 18)
        t = QLabel(f"Удалить {NAME}?")
        t.setObjectName("t")
        lay.addWidget(t)
        d = QLabel("Будут удалены программа, ярлыки и сопоставления файлов.")
        d.setObjectName("d")
        d.setWordWrap(True)
        lay.addWidget(d)
        lay.addSpacing(8)
        self.purge = QCheckBox("Удалить также мои настройки и список недавних файлов")
        lay.addWidget(self.purge)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        c = QPushButton("Отмена")
        c.clicked.connect(self.close)
        o = QPushButton("Удалить")
        o.setObjectName("go")
        o.clicked.connect(self.go)
        row.addWidget(c)
        row.addWidget(o)
        lay.addLayout(row)

    def go(self):
        try:
            uninstall(False, self.purge.isChecked())
            QMessageBox.information(self, NAME, "Nova Office удалён.")
        except Exception as e:
            QMessageBox.critical(self, NAME, f"Не удалось удалить: {e}")
        self.close()


STEPS = ["Приветствие", "Параметры", "Установка", "Готово"]


class Wizard(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(f"Установка {NAME}")
        self.setFixedSize(660, 430)
        ico = res("icon.ico")
        if ico:
            self.setWindowIcon(QIcon(ico))
        self.prev = reg_get(KEY, "DisplayVersion")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        bar = QWidget()
        bar.setObjectName("bar")
        bar.setFixedWidth(170)
        bl = QVBoxLayout(bar)
        bl.setContentsMargins(0, 22, 0, 16)
        br = QLabel(NAME)
        br.setObjectName("brand")
        bl.addWidget(br)
        self.step_lbls = []
        for n in STEPS:
            l = QLabel(n)
            l.setObjectName("step")
            bl.addWidget(l)
            self.step_lbls.append(l)
        bl.addStretch(1)
        v = QLabel(f"v{VERSION}" + (f"  ·  №{BUILD}" if BUILD else ""))
        v.setObjectName("d")
        v.setContentsMargins(12, 0, 0, 0)
        bl.addWidget(v)
        outer.addWidget(bar)

        main = QWidget()
        main.setObjectName("main")
        lay = QVBoxLayout(main)
        lay.setContentsMargins(28, 24, 28, 18)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        outer.addWidget(main, 1)

        # 0 — приветствие
        p0 = QWidget()
        l = QVBoxLayout(p0)
        l.setContentsMargins(0, 0, 0, 0)
        t = QLabel("Установка " + NAME)
        t.setObjectName("t")
        l.addWidget(t)
        if self.prev:
            d = QLabel(f"Уже установлена версия {self.prev}.\nМастер обновит программу до {VERSION}"
                       + (f" (сборка №{BUILD})" if BUILD else "") + ". Ваши файлы и настройки сохранятся.")
        else:
            d = QLabel("PDF, презентации и документы в одном окне.\n\nПрограмма ставится для текущего "
                       "пользователя, права администратора не нужны.")
        d.setObjectName("d")
        d.setWordWrap(True)
        l.addWidget(d)
        l.addStretch(1)
        self.stack.addWidget(p0)

        # 1 — параметры
        p1 = QWidget()
        l = QVBoxLayout(p1)
        l.setContentsMargins(0, 0, 0, 0)
        t = QLabel("Параметры")
        t.setObjectName("t")
        l.addWidget(t)
        l.addSpacing(10)
        l.addWidget(QLabel("Папка установки"))
        row = QHBoxLayout()
        self.path = QLineEdit(default_dir())
        self.path.textChanged.connect(self.validate)
        b = QPushButton("Обзор…")
        b.clicked.connect(self.browse)
        row.addWidget(self.path, 1)
        row.addWidget(b)
        l.addLayout(row)
        self.info = QLabel("")
        self.info.setObjectName("d")
        l.addWidget(self.info)
        l.addSpacing(10)
        self.c_menu = QCheckBox("Ярлык в меню «Пуск»")
        self.c_menu.setChecked(True)
        self.c_desk = QCheckBox("Ярлык на рабочем столе")
        self.c_desk.setChecked(os.path.exists(os.path.join(desktop(), NAME + ".lnk")))
        self.c_assoc = QCheckBox("«Открыть с помощью»: PDF, PPTX, DOCX, TXT, MD")
        self.c_assoc.setChecked(True)
        for c in (self.c_menu, self.c_desk, self.c_assoc):
            l.addWidget(c)
        l.addStretch(1)
        self.stack.addWidget(p1)

        # 2 — установка
        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        l2.setContentsMargins(0, 0, 0, 0)
        t = QLabel("Установка")
        t.setObjectName("t")
        l2.addWidget(t)
        l2.addStretch(1)
        self.msg = QLabel("Подготовка…")
        self.msg.setObjectName("d")
        self.bar = QProgressBar()
        l2.addWidget(self.msg)
        l2.addWidget(self.bar)
        l2.addStretch(1)
        self.stack.addWidget(p2)

        # 3 — готово
        p3 = QWidget()
        l3 = QVBoxLayout(p3)
        l3.setContentsMargins(0, 0, 0, 0)
        self.fin = QLabel("")
        self.fin.setObjectName("t")
        self.fin.setWordWrap(True)
        self.fin_d = QLabel("")
        self.fin_d.setObjectName("d")
        self.fin_d.setWordWrap(True)
        self.run_cb = QCheckBox("Запустить Nova Office")
        self.run_cb.setChecked(True)
        self.def_cb = QCheckBox("Открыть настройки Windows, чтобы выбрать Nova Office по умолчанию")
        l3.addWidget(self.fin)
        l3.addWidget(self.fin_d)
        l3.addSpacing(12)
        l3.addWidget(self.run_cb)
        l3.addWidget(self.def_cb)
        l3.addStretch(1)
        self.stack.addWidget(p3)

        bt = QHBoxLayout()
        self.rm = QPushButton("Удалить программу")
        self.rm.clicked.connect(self.do_uninstall)
        self.rm.setVisible(bool(self.prev))
        bt.addWidget(self.rm)
        bt.addStretch(1)
        self.back = QPushButton("Назад")
        self.back.clicked.connect(lambda: self.show_page(self.stack.currentIndex() - 1))
        self.cancel = QPushButton("Отмена")
        self.cancel.clicked.connect(self.close)
        self.next = QPushButton("Далее")
        self.next.setObjectName("go")
        self.next.clicked.connect(self.on_next)
        for x in (self.back, self.cancel, self.next):
            bt.addWidget(x)
        lay.addLayout(bt)
        self.exe = ""
        self.show_page(0)

    def show_page(self, i):
        i = max(0, i)
        self.stack.setCurrentIndex(i)
        for k, l in enumerate(self.step_lbls):
            l.setObjectName("stepon" if k == i else "step")
            l.style().unpolish(l)
            l.style().polish(l)
        self.back.setVisible(i == 1)
        self.rm.setVisible(bool(self.prev) and i == 0)
        self.next.setText({0: "Далее", 1: "Установить" if not self.prev else "Обновить", 3: "Готово"}.get(i, ""))
        self.next.setVisible(i != 2)
        self.cancel.setVisible(i in (0, 1))
        if i == 1:
            self.validate()

    def validate(self):
        err = check_target(self.path.text())
        need = payload_size() // (1 << 20)
        if err:
            self.info.setObjectName("err")
            self.info.setText(err)
        else:
            self.info.setObjectName("d")
            self.info.setText(f"Потребуется около {need} МБ, свободно {free_space(self.path.text()) // (1 << 20)} МБ.")
        self.info.style().unpolish(self.info)
        self.info.style().polish(self.info)
        if self.stack.currentIndex() == 1:
            self.next.setEnabled(not err)

    def browse(self):
        p = QFileDialog.getExistingDirectory(self, "Папка установки", self.path.text())
        if p:
            p = os.path.normpath(p)
            self.path.setText(p if not os.listdir(p) or os.path.exists(os.path.join(p, EXE))
                              else os.path.join(p, NAME))

    def on_next(self):
        i = self.stack.currentIndex()
        if i == 0:
            self.show_page(1)
        elif i == 1:
            self.start()
        elif i == 3:
            self.finish()

    def do_uninstall(self):
        self.close()
        self.u = UninstallDialog()
        self.u.show()

    def start(self):
        self.show_page(2)
        self.w = Worker(self.path.text().strip(), self.c_desk.isChecked(), self.c_menu.isChecked(),
                        self.c_assoc.isChecked())
        self.w.progress.connect(lambda v, m: (self.bar.setValue(v), self.msg.setText(m)))
        self.w.done.connect(self.finished)
        self.w.start()

    def finished(self, err):
        self.show_page(3)
        if err:
            self.fin.setText("Не удалось установить")
            self.fin_d.setText(f"{err}\n\nПрежняя версия (если была) возвращена. Журнал: {LOG}")
            self.run_cb.hide()
            self.def_cb.hide()
            self.next.setText("Закрыть")
        else:
            self.fin.setText("Готово")
            self.fin_d.setText(f"{NAME} установлен в\n{self.path.text().strip()}")
            self.def_cb.setVisible(self.c_assoc.isChecked())
            self.exe = os.path.join(self.path.text().strip(), EXE)

    def finish(self):
        if self.exe:
            if self.def_cb.isChecked() and self.def_cb.isVisible():
                os.startfile("ms-settings:defaultapps")
            if self.run_cb.isChecked():
                subprocess.Popen([self.exe], cwd=os.path.dirname(self.exe))
        self.close()

    def closeEvent(self, e):
        w = getattr(self, "w", None)
        if w is not None and w.isRunning():
            e.ignore()          # во время копирования закрывать нельзя
            return
        e.accept()


def arg_value(args, key):
    for a in sys.argv[1:]:
        if a.upper().startswith(key + "="):
            return a.split("=", 1)[1].strip('"')
    return None


def main():
    args = [a.upper() for a in sys.argv[1:]]
    silent = "/UPDATE" in args or "/S" in args
    if "/UNINSTALL" in args:
        if "/S" not in args and getattr(sys, "frozen", False):   # запускаем копию из temp, чтобы удалить папку приложения
            tmp = os.path.join(tempfile.gettempdir(), "novaoffice_uninstall.exe")
            if os.path.abspath(sys.executable) != tmp:
                shutil.copy2(sys.executable, tmp)
                subprocess.Popen([tmp, "/UNINSTALL"])
                return
        if "/S" in args:
            uninstall(True, "/PURGE" in args)
            return
        app = QApplication(sys.argv)
        app.setStyleSheet(QSS)
        w = UninstallDialog()
        w.show()
        sys.exit(app.exec())
    if not single_instance():
        return
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    if silent:       # тихая установка: параметры берём как были, либо из ключей
        t = arg_value(args, "/DIR") or default_dir()
        w = Worker(t, "/DESKTOP" in args or os.path.exists(os.path.join(desktop(), NAME + ".lnk")),
                   True, "/NOASSOC" not in args)
        try:
            w.install()
        except Exception as e:
            log(f"тихая установка не удалась: {e}")
            return
        if "/NOLAUNCH" not in args:
            subprocess.Popen([os.path.join(t, EXE)], cwd=t)
        return
    w = Wizard()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
