"""Обновление из GitHub Actions: берём последний успешный билд, качаем установщик, сравниваем с установленным."""
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton,
                               QTextEdit, QVBoxLayout)

from common import APP, _s
from version import ARTIFACT, BUILD, REPO, SHA, VERSION, WORKFLOW_NAME

API = f"https://api.github.com/repos/{REPO}"
UA = {"User-Agent": "NovaOffice-Updater", "Accept": "application/vnd.github+json"}


def installed_build():
    """(номер сборки, sha) — то, что реально стоит у пользователя."""
    b = BUILD or int(_s.value("installed_build", 0) or 0)
    s = SHA or _s.value("installed_sha", "")
    return int(b), str(s)


def _get(url, token="", raw=False, timeout=15):
    h = dict(UA)
    if token:
        h["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        data = r.read()
    return data if raw else json.loads(data.decode("utf-8"))


def fetch_runs(limit=15):
    """Успешные билды ветки main нашего workflow, новые первыми."""
    d = _get(f"{API}/actions/runs?status=success&branch=main&per_page={limit}",
             _s.value("gh_token", ""))
    out = []
    for r in d.get("workflow_runs", []):
        if r.get("name") != WORKFLOW_NAME or r.get("conclusion") != "success":
            continue
        out.append({"id": r["id"], "n": r["run_number"], "sha": r["head_sha"],
                    "msg": (r.get("head_commit") or {}).get("message", "").strip(),
                    "date": r.get("updated_at", "")[:10], "url": r.get("html_url", "")})
    return out


def is_newer(run):
    b, s = installed_build()
    if s and run["sha"] == s:
        return False          # тот же коммит — это уже установленная версия
    if b and run["n"] <= b:
        return False          # билд не новее установленного
    return True


class Checker(QThread):
    done = Signal(object, str)    # run | None, ошибка

    def run(self):
        try:
            runs = fetch_runs()
            self.done.emit(next((r for r in runs if is_newer(r)), None), "")
        except urllib.error.HTTPError as e:
            self.done.emit(None, "GitHub ограничил запросы, попробуйте позже" if e.code in (403, 429)
                           else f"Ошибка GitHub: {e.code}")
        except Exception as e:
            self.done.emit(None, f"Нет связи с GitHub ({type(e).__name__})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _candidate_urls(run):
    """Откуда можно скачать zip с установщиком. Артефакты Actions без токена GitHub не отдаёт."""
    token = _s.value("gh_token", "")
    urls = []
    if token:
        try:
            arts = _get(f"{API}/actions/runs/{run['id']}/artifacts", token)["artifacts"]
            for a in arts:
                if a["name"] == ARTIFACT and not a.get("expired"):
                    urls.append((a["archive_download_url"], token))
        except Exception:
            pass
    urls.append((f"https://github.com/{REPO}/releases/download/build-{run['n']}/NovaOffice-Setup.exe", ""))
    urls.append((f"https://nightly.link/{REPO}/actions/runs/{run['id']}/{ARTIFACT}.zip", ""))
    return urls


class Downloader(QThread):
    progress = Signal(int)
    done = Signal(str, str)    # путь к exe, ошибка

    def __init__(self, run):
        super().__init__()
        self.run_info = run

    def _fetch(self, url, token, dst):
        h = dict(UA, Accept="application/octet-stream")
        if token:
            h["Authorization"] = f"Bearer {token}"
        opener = urllib.request.build_opener(_NoRedirect) if token else urllib.request.build_opener()
        try:
            r = opener.open(urllib.request.Request(url, headers=h), timeout=30)
        except urllib.error.HTTPError as e:       # редирект на blob — идём уже без токена
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                r = urllib.request.urlopen(urllib.request.Request(
                    e.headers["Location"], headers={"User-Agent": UA["User-Agent"]}), timeout=30)
            else:
                raise
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        with open(dst, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    self.progress.emit(int(got * 100 / total))
        r.close()

    def run(self):
        tmp = tempfile.mkdtemp(prefix="novaoffice_upd_")
        last = "не удалось скачать"
        for url, token in _candidate_urls(self.run_info):
            dst = os.path.join(tmp, "dl.bin")
            try:
                self._fetch(url, token, dst)
                if zipfile.is_zipfile(dst):
                    with zipfile.ZipFile(dst) as z:
                        name = next((n for n in z.namelist() if n.lower().endswith(".exe")), None)
                        if not name:
                            raise RuntimeError("в архиве нет exe")
                        z.extract(name, tmp)
                        exe = os.path.join(tmp, name)
                else:
                    exe = os.path.join(tmp, "NovaOffice-Setup.exe")
                    os.replace(dst, exe)
                if os.path.getsize(exe) < 1_000_000:
                    raise RuntimeError("файл слишком маленький")
                self.done.emit(exe, "")
                return
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
        hint = "" if _s.value("gh_token", "") else \
            "\nАртефакты Actions GitHub отдаёт только с токеном — добавьте его в Настройках."
        self.done.emit("", last + hint)


class UpdateDialog(QDialog):
    def __init__(self, parent, run):
        super().__init__(parent)
        self.run_info = run
        self.setWindowTitle("Обновление")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        b, _ = installed_build()
        head = QLabel(f"Доступна новая сборка №{run['n']} от {run['date']}")
        head.setObjectName("h2")
        lay.addWidget(head)
        lay.addWidget(QLabel(f"Сейчас установлено: {VERSION}" + (f" (сборка №{b})" if b else "")))
        note = QTextEdit(run["msg"] or "Описание не указано")
        note.setReadOnly(True)
        note.setFixedHeight(90)
        lay.addWidget(note)
        self.bar = QProgressBar()
        self.bar.hide()
        lay.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        row = QHBoxLayout()
        row.addStretch(1)
        self.skip = QPushButton("Пропустить эту сборку")
        self.skip.clicked.connect(self.on_skip)
        self.go = QPushButton("Скачать и установить")
        self.go.setObjectName("primary")
        self.go.clicked.connect(self.start)
        row.addWidget(self.skip)
        row.addWidget(self.go)
        lay.addLayout(row)

    def reject(self):
        if getattr(self, "dl", None) is not None and self.dl.isRunning():
            return            # во время скачивания закрыть нельзя
        super().reject()

    def on_skip(self):
        _s.setValue("skip_build", self.run_info["n"])
        self.reject()

    def start(self):
        self.go.setEnabled(False)
        self.skip.setEnabled(False)
        self.bar.show()
        self.status.setText("Скачиваю…")
        self.dl = Downloader(self.run_info)
        self.dl.progress.connect(self.bar.setValue)
        self.dl.done.connect(self.finished_dl)
        self.dl.start()

    def finished_dl(self, exe, err):
        if err:
            self.status.setText("Ошибка: " + err)
            self.go.setEnabled(True)
            self.skip.setEnabled(True)
            return
        _s.setValue("installed_build", self.run_info["n"])
        _s.setValue("installed_sha", self.run_info["sha"])
        _s.sync()
        flags = 0x00000008 | 0x00000200 if sys.platform == "win32" else 0   # DETACHED | NEW_GROUP
        subprocess.Popen([exe, "/UPDATE"], creationflags=flags, close_fds=True)
        self.accept()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()


def check_updates(parent, silent):
    """silent=True — автопроверка на старте: молчим, если нечего показывать."""
    old = getattr(parent, "_chk", None)
    if old is not None and old.isRunning():
        return
    chk = Checker()
    parent._chk = chk

    def done(run, err):
        _s.setValue("last_update_check", int(__import__("time").time()))
        if err:
            if not silent:
                QMessageBox.warning(parent, APP, err)
        elif run is None:
            if not silent:
                QMessageBox.information(parent, APP, "У вас уже установлена последняя версия.")
        elif silent and int(_s.value("skip_build", 0) or 0) == run["n"]:
            return
        else:
            UpdateDialog(parent, run).exec()
    chk.done.connect(done)
    chk.start()
