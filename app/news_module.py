import html
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from PySide6.QtCore import QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
                               QListWidget, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from common import get_list, recent, set_list

DEFAULT_FEEDS = [
    "Lenta.ru|https://lenta.ru/rss/news",
    "Habr|https://habr.com/ru/rss/articles/",
    "BBC Русская служба|https://feeds.bbci.co.uk/russian/rss.xml",
    "Hacker News|https://hnrss.org/frontpage",
    "The Verge|https://www.theverge.com/rss/index.xml",
]
ATOM = "{http://www.w3.org/2005/Atom}"


def txt(el, tag):
    e = el.find(tag)
    return (e.text or "").strip() if e is not None and e.text else ""


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:240] + ("…" if len(s) > 240 else "")


def parse_date(s):
    if s:
        try:
            dt = parsedate_to_datetime(s)
        except Exception:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                dt = None
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone()
    return datetime.now().astimezone()


def mk(src, title, link, desc, date):
    dt = parse_date(date)
    return {"src": src, "title": clean(title), "link": link, "desc": clean(desc),
            "ts": dt.timestamp(), "when": dt.strftime("%d.%m %H:%M")}


def parse_feed(data, src):
    root = ET.fromstring(data)
    out = []
    for it in list(root.iter("item"))[:25]:
        out.append(mk(src, txt(it, "title"), txt(it, "link"), txt(it, "description"), txt(it, "pubDate")))
    for en in list(root.iter(ATOM + "entry"))[:25]:
        ln = en.find(ATOM + "link")
        href = ln.get("href") if ln is not None else ""
        out.append(mk(src, txt(en, ATOM + "title"), href,
                      txt(en, ATOM + "summary") or txt(en, ATOM + "content"),
                      txt(en, ATOM + "updated") or txt(en, ATOM + "published")))
    return [i for i in out if i["title"] and i["link"]]


class Fetcher(QThread):
    feed_done = Signal(list)

    def __init__(self, feeds):
        super().__init__()
        self.feeds = feeds

    def run(self):
        for line in self.feeds:
            if "|" not in line:
                continue
            name, url = [x.strip() for x in line.split("|", 1)]
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "NovaOffice/1.1"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    self.feed_done.emit(parse_feed(r.read(), name))
            except Exception:
                continue


class Card(QFrame):
    def __init__(self, it):
        super().__init__()
        self.setObjectName("card")
        self.url = it["link"]
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(5)
        meta = QLabel(f"{it['src'].upper()}   ·   {it['when']}")
        meta.setObjectName("meta")
        title = QLabel(it["title"])
        title.setObjectName("ctitle")
        title.setWordWrap(True)
        lay.addWidget(meta)
        lay.addWidget(title)
        if it["desc"]:
            d = QLabel(it["desc"])
            d.setObjectName("cdesc")
            d.setWordWrap(True)
            lay.addWidget(d)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl(self.url))


class NewsModule(QWidget):
    act = Signal(str)
    open_recent = Signal(str)

    def __init__(self):
        super().__init__()
        self.items = []
        self.worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 18)
        root.setSpacing(16)

        h1 = QLabel("Главная")
        h1.setObjectName("h1")
        root.addWidget(h1)

        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (text, key) in enumerate((("Открыть файл…", "open"),
                                         ("Открыть PDF", "pdf"),
                                         ("Новая презентация", "new_pres"),
                                         ("Новый документ", "new_doc"))):
            b = QPushButton(text)
            b.setObjectName("quick")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.act.emit(k))
            grid.addWidget(b, 0, i)
        root.addLayout(grid)

        body = QHBoxLayout()
        body.setSpacing(18)
        root.addLayout(body, 1)

        self.recent_box = QWidget()
        left = QVBoxLayout(self.recent_box)
        left.setContentsMargins(0, 0, 0, 0)
        lt = QLabel("Недавние файлы")
        lt.setObjectName("h2")
        left.addWidget(lt)
        self.recent_list = QListWidget()
        self.recent_list.setFixedWidth(280)
        self.recent_list.itemClicked.connect(lambda it: self.open_recent.emit(it.toolTip()))
        left.addWidget(self.recent_list, 1)
        body.addWidget(self.recent_box)

        right = QVBoxLayout()
        top = QHBoxLayout()
        nt = QLabel("Лента новостей")
        nt.setObjectName("h2")
        top.addWidget(nt)
        top.addStretch(1)
        self.filter = QComboBox()
        self.filter.addItem("Все источники")
        self.filter.currentIndexChanged.connect(self.render)
        top.addWidget(self.filter)
        b1 = QPushButton("Обновить")
        b1.clicked.connect(self.refresh)
        top.addWidget(b1)
        b2 = QPushButton("Источники…")
        b2.clicked.connect(self.edit_feeds)
        top.addWidget(b2)
        right.addLayout(top)
        self.status = QLabel("")
        self.status.setObjectName("status")
        right.addWidget(self.status)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.holder = QWidget()
        self.vbox = QVBoxLayout(self.holder)
        self.vbox.setSpacing(10)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.holder)
        right.addWidget(self.scroll, 1)
        body.addLayout(right, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.apply_settings()
        QTimer.singleShot(300, self.refresh)

    def apply_settings(self):
        from common import _s
        self.timer.start(int(_s.value("news_min", 10)) * 60 * 1000)
        show = _s.value("show_recent", True) in (True, "true", "1", 1)
        self.recent_box.setVisible(show)

    def feeds(self):
        f = get_list("feeds")
        return f or DEFAULT_FEEDS

    def showEvent(self, e):
        super().showEvent(e)
        self.recent_list.clear()
        from PySide6.QtWidgets import QListWidgetItem
        for p in recent():
            it = QListWidgetItem(os.path.basename(p))
            it.setToolTip(p)
            self.recent_list.addItem(it)

    def refresh(self):
        if self.worker and self.worker.isRunning():
            return
        self.items = []
        self.status.setText("Загрузка новостей…")
        self.worker = Fetcher(self.feeds())
        self.worker.feed_done.connect(self.on_feed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_feed(self, items):
        self.items.extend(items)
        self.render()

    def on_finished(self):
        if not self.items:
            self.status.setText("Не удалось загрузить новости. Проверьте интернет или список источников.")
        else:
            self.status.setText(f"Обновлено: {datetime.now().strftime('%H:%M')} · материалов: {len(self.items)}")

    def render(self):
        names = sorted({i["src"] for i in self.items})
        cur = self.filter.currentText()
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItem("Все источники")
        self.filter.addItems(names)
        idx = self.filter.findText(cur)
        self.filter.setCurrentIndex(max(0, idx))
        self.filter.blockSignals(False)
        sel = self.filter.currentText()
        data = [i for i in self.items if sel == "Все источники" or i["src"] == sel]
        data.sort(key=lambda i: i["ts"], reverse=True)
        while self.vbox.count() > 1:
            w = self.vbox.takeAt(0).widget()
            if w:
                w.deleteLater()
        for it in data[:80]:
            self.vbox.insertWidget(self.vbox.count() - 1, Card(it))

    def edit_feeds(self):
        cur = "\n".join(self.feeds())
        text, ok = QInputDialog.getMultiLineText(
            self, "Источники новостей", "Один источник на строку:  Название | адрес RSS/Atom", cur)
        if ok:
            lines = [l.strip() for l in text.splitlines() if "|" in l]
            set_list("feeds", lines or DEFAULT_FEEDS)
            self.refresh()
