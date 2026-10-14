import os
import sys

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox

APP = "Nova Office"
_s = QSettings("NovaOffice", "NovaOffice")


def res(name):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (getattr(sys, "_MEIPASS", None), here, os.path.join(here, "..")):
        if base:
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
    return None


def get_list(key):
    v = _s.value(key, [])
    if isinstance(v, str):
        v = [v]
    return list(v or [])


def set_list(key, value):
    _s.setValue(key, value)


def add_recent(path):
    path = os.path.abspath(path)
    r = [p for p in get_list("recent") if p != path]
    r.insert(0, path)
    _s.setValue("recent", r[:12])


def recent():
    return [p for p in get_list("recent") if os.path.exists(p)]


def pix_to_qimage(pix):
    fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
    return QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()


def maybe_save(parent, dirty, name, save_fn):
    """True — можно продолжать (сохранили или отказались от сохранения)."""
    if not dirty:
        return True
    r = QMessageBox.question(
        parent, "Несохранённые изменения", f"Сохранить изменения в «{name}»?",
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    if r == QMessageBox.Cancel:
        return False
    if r == QMessageBox.Yes:
        return bool(save_fn())
    return True
