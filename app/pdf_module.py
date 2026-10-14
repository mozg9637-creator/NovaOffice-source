import os
import time

import pymupdf as fitz
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (QAction, QActionGroup, QColor, QIcon, QKeySequence, QPainter,
                           QPen, QPixmap, QShortcut)
from PySide6.QtWidgets import (QApplication, QMenu, QToolButton, QColorDialog, QFileDialog, QInputDialog, QLabel, QLineEdit,
                               QListView, QListWidget, QListWidgetItem, QMessageBox,
                               QScrollArea, QSpinBox, QSplitter, QToolBar, QVBoxLayout,
                               QWidget)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter

from common import add_recent, maybe_save, pix_to_qimage

FONT = r"C:\Windows\Fonts\arial.ttf"


class PageLabel(QLabel):
    pressed = Signal(QPoint)
    moved = Signal(QPoint)
    released = Signal(QPoint)

    def __init__(self):
        super().__init__()
        self.sel = None
        self.stroke = []
        self.ink_color = QColor("#e53935")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.pressed.emit(e.position().toPoint())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.moved.emit(e.position().toPoint())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.released.emit(e.position().toPoint())

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.sel or len(self.stroke) > 1:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            if self.sel:
                p.fillRect(self.sel, QColor(91, 124, 255, 70))
                p.setPen(QPen(QColor(91, 124, 255), 1))
                p.drawRect(self.sel)
            if len(self.stroke) > 1:
                p.setPen(QPen(self.ink_color, 2))
                p.drawPolyline(self.stroke)
            p.end()


class Scroll(QScrollArea):
    zoomed = Signal(int)
    edge = Signal(int)

    def __init__(self):
        super().__init__()
        self._t = 0

    def wheelEvent(self, e):
        d = e.angleDelta().y()
        if e.modifiers() & Qt.ControlModifier:
            self.zoomed.emit(1 if d > 0 else -1)
            e.accept()
            return
        sb = self.verticalScrollBar()
        now = time.monotonic()
        if now - self._t > 0.25:
            if d < 0 and sb.value() >= sb.maximum():
                self._t = now
                self.edge.emit(1)
                e.accept()
                return
            if d > 0 and sb.value() <= sb.minimum():
                self._t = now
                self.edge.emit(-1)
                e.accept()
                return
        super().wheelEvent(e)


class PdfModule(QWidget):
    def __init__(self):
        super().__init__()
        self.doc = None
        self.path = None
        self.page = 0
        self.zoom = 1.25
        self.tool = "view"
        self.undo_stack = []
        self.dirty = False
        self.hits = {}
        self.last_q = ""
        self.p0 = None
        self.color = (0.9, 0.1, 0.1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- верхняя панель
        bar = QToolBar()
        bar.setMovable(False)
        root.addWidget(bar)
        self.act(bar, "Открыть", "Открыть PDF", self.open_dialog, "Ctrl+O")
        self.act(bar, "Сохранить", "Сохранить", self.save, "Ctrl+S")
        self.act(bar, "Сохранить как…", "Сохранить как…", self.save_as, "Ctrl+Shift+S")
        self.act(bar, "Печать", "Печать на любую бумагу", self.print_doc, "Ctrl+P")
        bar.addSeparator()
        grp = QActionGroup(self)
        for name, text, tip in (("view", "Просмотр", "Просмотр"),
                                ("hl", "Выделить", "Выделить текст маркером"),
                                ("text", "🅣 Текст", "Добавить текст — клик по странице"),
                                ("ink", "Рисовать", "Рисовать от руки")):
            a = self.act(bar, text, tip, lambda *_, n=name: self.set_tool(n), checkable=True)
            grp.addAction(a)
            if name == "view":
                a.setChecked(True)
        a = self.act(bar, "Цвет", "Цвет текста и рисунка", self.pick_color)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 96)
        self.size_spin.setValue(14)
        self.size_spin.setToolTip("Размер шрифта для текста")
        bar.addWidget(self.size_spin)
        bar.addSeparator()
        self.act(bar, "Отменить", "Отменить", self.undo, "Ctrl+Z")
        self.act(bar, "Повернуть", "Повернуть страницу", self.rotate_page)
        self.act(bar, "Пустая", "Вставить пустую страницу после текущей", self.add_blank)
        self.act(bar, "Добавить PDF", "Вставить страницы из другого PDF", self.insert_pdf)
        self.act(bar, "Удалить страницу", "Удалить страницу", self.delete_page)
        more = QToolButton()
        more.setText("Ещё")
        more.setPopupMode(QToolButton.InstantPopup)
        mm = QMenu(more)
        for t, fn in (("Извлечь страницы в новый PDF…", self.extract_pages),
                      ("Текущая страница в PNG…", self.page_to_png),
                      ("Скопировать текст страницы", self.copy_page_text),
                      ("Пронумеровать страницы", self.number_pages)):
            mm.addAction(t, fn)
        more.setMenu(mm)
        bar.addWidget(more)

        # ---- навигация
        nav = QToolBar()
        nav.setMovable(False)
        root.addWidget(nav)
        self.act(nav, "Назад", "Предыдущая страница", lambda *_: self.goto(self.page - 1))
        self.spin = QSpinBox()
        self.spin.setRange(1, 1)
        self.spin.editingFinished.connect(lambda: self.goto(self.spin.value() - 1))
        nav.addWidget(self.spin)
        self.total = QLabel(" / 0 ")
        nav.addWidget(self.total)
        self.act(nav, "Вперёд", "Следующая страница", lambda *_: self.goto(self.page + 1))
        nav.addSeparator()
        self.act(nav, "Меньше", "Уменьшить", lambda *_: self.change_zoom(-1))
        self.zoom_lbl = QLabel(" 125% ")
        nav.addWidget(self.zoom_lbl)
        self.act(nav, "Больше", "Увеличить", lambda *_: self.change_zoom(1))
        self.act(nav, "По ширине", "Вписать по ширине", self.fit_width)
        nav.addSeparator()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по документу…")
        self.search.setFixedWidth(230)
        self.search.returnPressed.connect(self.find)
        nav.addWidget(self.search)

        # ---- центр
        self.thumbs = QListWidget()
        self.thumbs.setFixedWidth(150)
        self.thumbs.setIconSize(QSize(100, 140))
        self.thumbs.setSpacing(6)
        self.thumbs.setMovement(QListView.Static)
        self.thumbs.currentRowChanged.connect(self.goto)

        self.view = PageLabel()
        self.view.setAlignment(Qt.AlignCenter)
        self.view.pressed.connect(self.on_press)
        self.view.moved.connect(self.on_move)
        self.view.released.connect(self.on_release)
        self.scroll = Scroll()
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.view)
        self.scroll.zoomed.connect(self.change_zoom)
        self.scroll.edge.connect(self.on_edge)

        split = QSplitter()
        split.addWidget(self.thumbs)
        split.addWidget(self.scroll)
        split.setStretchFactor(1, 1)
        split.setSizes([150, 900])
        root.addWidget(split, 1)

        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setContentsMargins(12, 4, 12, 4)
        root.addWidget(self.status)

        QShortcut(QKeySequence("PgDown"), self, activated=lambda: self.goto(self.page + 1))
        QShortcut(QKeySequence("PgUp"), self, activated=lambda: self.goto(self.page - 1))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search.setFocus())
        self.show_page()

    # ------------------------------------------------------------ helpers
    def act(self, bar, text, tip, slot, key=None, checkable=False):
        a = QAction(text, self)
        a.setToolTip(tip + (f" ({key})" if key else ""))
        if key:
            a.setShortcut(QKeySequence(key))
        a.setCheckable(checkable)
        a.triggered.connect(lambda *_: slot())
        bar.addAction(a)
        return a

    def pg(self):
        return self.doc[self.page]

    def set_tool(self, name):
        self.tool = name
        self.view.setCursor({"view": Qt.ArrowCursor, "text": Qt.IBeamCursor}.get(name, Qt.CrossCursor))

    def pick_color(self):
        c = QColorDialog.getColor(QColor.fromRgbF(*self.color), self, "Цвет")
        if c.isValid():
            self.color = (c.redF(), c.greenF(), c.blueF())
            self.view.ink_color = c

    # ------------------------------------------------------------ open / save
    def open_dialog(self):
        p, _ = QFileDialog.getOpenFileName(self, "Открыть PDF", "", "PDF (*.pdf)")
        if p:
            self.open_file(p)

    def can_close(self):
        return maybe_save(self, self.dirty and self.doc is not None,
                          os.path.basename(self.path or "документ.pdf"), self.save)

    def open_file(self, path):
        if not self.can_close():
            return
        try:
            d = fitz.open(path)
            if d.needs_pass:
                pw, ok = QInputDialog.getText(self, "Пароль", "Документ защищён паролем:",
                                              QLineEdit.Password)
                if not ok or not d.authenticate(pw):
                    QMessageBox.warning(self, "PDF", "Неверный пароль.")
                    return
        except Exception as e:
            QMessageBox.warning(self, "PDF", f"Не удалось открыть файл:\n{e}")
            return
        if self.doc:
            self.doc.close()
        self.doc, self.path = d, path
        self.page, self.dirty, self.hits, self.last_q = 0, False, {}, ""
        self.undo_stack.clear()
        add_recent(path)
        self.build_thumbs()
        self.fit_width()

    def save(self):
        if not self.doc:
            return True
        if not self.path:
            return self.save_as()
        return self._write(self.path)

    def save_as(self):
        if not self.doc:
            return False
        p, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", self.path or "", "PDF (*.pdf)")
        return self._write(p) if p else False

    def _write(self, path):
        try:
            data = self.doc.tobytes(garbage=3, deflate=True)
        except Exception as e:
            QMessageBox.critical(self, "PDF", f"Ошибка сохранения:\n{e}")
            return False
        try:
            self.doc.close()
            with open(path, "wb") as f:
                f.write(data)
            self.doc = fitz.open(path)
        except Exception as e:
            self.doc = fitz.open("pdf", data)
            QMessageBox.critical(self, "PDF", f"Не удалось записать файл:\n{e}")
            return False
        self.path = path
        self.dirty = False
        add_recent(path)
        self.status.setText("Сохранено: " + path)
        return True

    # ------------------------------------------------------------ undo
    def push_undo(self):
        self.undo_stack.append(self.doc.tobytes())
        del self.undo_stack[:-10]
        self.dirty = True

    def undo(self):
        if not self.undo_stack or not self.doc:
            return
        data = self.undo_stack.pop()
        self.doc.close()
        self.doc = fitz.open("pdf", data)
        self.page = min(self.page, len(self.doc) - 1)
        self.build_thumbs()
        self.show_page()

    # ------------------------------------------------------------ view
    def build_thumbs(self):
        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        for i in range(len(self.doc)):
            it = QListWidgetItem(str(i + 1))
            it.setTextAlignment(Qt.AlignHCenter)
            if i < 80:
                it.setIcon(self.thumb_icon(i))
            self.thumbs.addItem(it)
        self.thumbs.blockSignals(False)

    def thumb_icon(self, i):
        pix = self.doc[i].get_pixmap(matrix=fitz.Matrix(0.2, 0.2), alpha=False)
        return QIcon(QPixmap.fromImage(pix_to_qimage(pix)))

    def update_thumb(self):
        it = self.thumbs.item(self.page)
        if it is not None and self.page < 80:
            it.setIcon(self.thumb_icon(self.page))

    def show_page(self):
        if not self.doc:
            self.view.setPixmap(QPixmap())
            self.view.setFixedSize(520, 300)
            self.view.setText("Откройте PDF или перетащите файл в окно")
            self.total.setText(" / 0 ")
            return
        self.page = max(0, min(self.page, len(self.doc) - 1))
        page = self.pg()
        dpr = self.devicePixelRatioF()
        s = self.zoom * dpr
        pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
        img = pix_to_qimage(pix)
        if self.page in self.hits:
            p = QPainter(img)
            for r in self.hits[self.page]:
                r = r * page.rotation_matrix
                p.fillRect(int(r.x0 * s), int(r.y0 * s), int(r.width * s), int(r.height * s),
                           QColor(255, 200, 0, 110))
            p.end()
        img.setDevicePixelRatio(dpr)
        self.view.setText("")
        self.view.setPixmap(QPixmap.fromImage(img))
        self.view.setFixedSize(int(pix.width / dpr), int(pix.height / dpr))
        self.spin.blockSignals(True)
        self.spin.setRange(1, len(self.doc))
        self.spin.setValue(self.page + 1)
        self.spin.blockSignals(False)
        self.total.setText(f" / {len(self.doc)} ")
        self.zoom_lbl.setText(f" {int(self.zoom * 100)}% ")
        self.thumbs.blockSignals(True)
        self.thumbs.setCurrentRow(self.page)
        self.thumbs.blockSignals(False)

    def goto(self, n):
        if not self.doc or n < 0 or n >= len(self.doc):
            return
        self.page = n
        self.show_page()
        self.scroll.verticalScrollBar().setValue(0)

    def on_edge(self, d):
        if not self.doc:
            return
        n = self.page + d
        if 0 <= n < len(self.doc):
            self.goto(n)
            if d < 0:
                sb = self.scroll.verticalScrollBar()
                sb.setValue(sb.maximum())

    def change_zoom(self, d):
        self.zoom = max(0.2, min(6.0, self.zoom * (1.15 if d > 0 else 1 / 1.15)))
        self.show_page()

    def fit_width(self):
        if self.doc:
            w = self.scroll.viewport().width() - 30
            self.zoom = max(0.2, min(6.0, w / self.pg().rect.width))
        self.show_page()

    # ------------------------------------------------------------ search
    def find(self):
        q = self.search.text().strip()
        if not q or not self.doc:
            return
        if q != self.last_q:
            self.last_q = q
            self.hits = {}
            for i in range(len(self.doc)):
                r = self.doc[i].search_for(q)
                if r:
                    self.hits[i] = r
        if not self.hits:
            self.status.setText("Ничего не найдено")
            self.show_page()
            return
        pages = sorted(self.hits)
        nxt = next((p for p in pages if p > self.page), pages[0])
        total = sum(len(v) for v in self.hits.values())
        self.status.setText(f"Найдено совпадений: {total}")
        self.goto(nxt)

    # ------------------------------------------------------------ editing
    def to_pdf(self, pt):
        p = fitz.Point(pt.x() / self.zoom, pt.y() / self.zoom)
        return p * self.pg().derotation_matrix

    def on_press(self, pos):
        if not self.doc or self.tool == "view":
            return
        self.p0 = pos
        if self.tool == "ink":
            self.view.stroke = [pos]
        elif self.tool == "hl":
            self.view.sel = QRect(pos, pos)

    def on_move(self, pos):
        if not self.doc or self.p0 is None:
            return
        if self.tool == "ink":
            self.view.stroke.append(pos)
        elif self.tool == "hl":
            self.view.sel = QRect(self.p0, pos).normalized()
        self.view.update()

    def on_release(self, pos):
        if not self.doc or self.p0 is None:
            return
        p0, self.p0 = self.p0, None
        sel, stroke = self.view.sel, self.view.stroke
        self.view.sel, self.view.stroke = None, []
        self.view.update()
        try:
            if self.tool == "hl" and sel is not None and sel.width() > 3:
                self.do_highlight(p0, pos)
            elif self.tool == "ink" and len(stroke) > 2:
                self.do_ink(stroke)
            elif self.tool == "text":
                self.do_text(p0)
        except Exception as e:
            QMessageBox.warning(self, "PDF", f"Не удалось применить: {e}")
        self.show_page()
        self.update_thumb()

    def pdf_rect(self, a, b):
        pa, pb = self.to_pdf(a), self.to_pdf(b)
        return fitz.Rect(min(pa.x, pb.x), min(pa.y, pb.y), max(pa.x, pb.x), max(pa.y, pb.y))

    def do_highlight(self, a, b):
        r = self.pdf_rect(a, b)
        self.push_undo()
        page = self.pg()
        words = [fitz.Rect(w[:4]) for w in page.get_text("words") if fitz.Rect(w[:4]).intersects(r)]
        if words:
            page.add_highlight_annot(quads=[w.quad for w in words])
        else:
            an = page.add_rect_annot(r)
            an.set_colors(fill=(1, 0.9, 0), stroke=(1, 0.9, 0))
            an.set_opacity(0.4)
            an.update()

    def do_ink(self, stroke):
        pts = [self.to_pdf(p) for p in stroke[::2]]
        self.push_undo()
        an = self.pg().add_ink_annot([pts])
        an.set_border(width=2)
        an.set_colors(stroke=self.color)
        an.update()

    def do_text(self, pos):
        text, ok = QInputDialog.getMultiLineText(self, "Текст", "Введите текст:")
        if not ok or not text.strip():
            return
        size = self.size_spin.value()
        p = self.to_pdf(QPoint(pos.x(), pos.y() + int(size * self.zoom)))
        self.push_undo()
        kw = {"fontname": "arial", "fontfile": FONT} if os.path.exists(FONT) else {"fontname": "helv"}
        self.pg().insert_text(p, text, fontsize=size, color=self.color, **kw)

    def rotate_page(self):
        if not self.doc:
            return
        self.push_undo()
        pg = self.pg()
        pg.set_rotation((pg.rotation + 90) % 360)
        self.show_page()
        self.update_thumb()

    def add_blank(self):
        if not self.doc:
            return
        self.push_undo()
        r = self.pg().rect
        self.doc.new_page(self.page + 1, width=r.width, height=r.height)
        self.build_thumbs()
        self.goto(self.page + 1)

    def delete_page(self):
        if not self.doc or len(self.doc) < 2:
            return
        if QMessageBox.question(self, "Удалить", f"Удалить страницу {self.page + 1}?") != QMessageBox.Yes:
            return
        self.push_undo()
        self.doc.delete_page(self.page)
        self.page = min(self.page, len(self.doc) - 1)
        self.build_thumbs()
        self.show_page()

    def insert_pdf(self):
        if not self.doc:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Добавить страницы из PDF", "", "PDF (*.pdf)")
        if not p:
            return
        try:
            src = fitz.open(p)
            self.push_undo()
            self.doc.insert_pdf(src, start_at=self.page + 1)
            src.close()
        except Exception as e:
            QMessageBox.warning(self, "PDF", f"Не удалось добавить: {e}")
            return
        self.build_thumbs()
        self.goto(self.page + 1)

    # ------------------------------------------------------------ дополнительно
    def parse_range(self, text):
        out = []
        for part in text.replace(" ", "").split(","):
            if not part:
                continue
            a, _, b = part.partition("-")
            a, b = int(a), int(b or a)
            out += [i - 1 for i in range(min(a, b), max(a, b) + 1) if 1 <= i <= len(self.doc)]
        return list(dict.fromkeys(out))

    def extract_pages(self):
        if not self.doc:
            return
        text, ok = QInputDialog.getText(self, "Извлечь страницы", f"Номера страниц (всего {len(self.doc)}), например 1-3,5:",
                                        text=str(self.page + 1))
        if not ok:
            return
        try:
            idx = self.parse_range(text)
            if not idx:
                raise ValueError("нет таких страниц")
        except ValueError as e:
            QMessageBox.warning(self, "PDF", f"Неверный диапазон: {e}")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить страницы", "", "PDF (*.pdf)")
        if not path:
            return
        out = fitz.open()
        for i in idx:
            out.insert_pdf(self.doc, from_page=i, to_page=i)
        out.save(path, garbage=3, deflate=True)
        out.close()
        self.status.setText(f"Сохранено страниц: {len(idx)} → {path}")

    def page_to_png(self):
        if not self.doc:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить страницу", f"страница-{self.page + 1}.png",
                                              "PNG (*.png)")
        if path:
            self.pg().get_pixmap(dpi=200).save(path)
            self.status.setText("Сохранено: " + path)

    def copy_page_text(self):
        if not self.doc:
            return
        txt = self.pg().get_text().strip()
        QApplication.clipboard().setText(txt)
        self.status.setText(f"Скопировано символов: {len(txt)}" if txt else
                            "На странице нет текстового слоя (скан) — копировать нечего")

    def number_pages(self):
        if not self.doc:
            return
        self.push_undo()
        n = len(self.doc)
        for i, pg in enumerate(self.doc):
            r = pg.rect
            pg.insert_textbox(fitz.Rect(0, r.height - 34, r.width, r.height - 12), f"{i + 1} / {n}",
                              fontsize=10, fontname="helv", align=1, color=(0.3, 0.3, 0.3))
        self.show_page()
        self.build_thumbs()
        self.status.setText("Номера страниц добавлены (Ctrl+Z — отменить)")

    # ------------------------------------------------------------ print
    def print_doc(self):
        if not self.doc:
            return
        pr = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(pr, self)
        dlg.setMinMax(1, len(self.doc))
        dlg.setOption(QPrintDialog.PrintPageRange, True)
        dlg.setOption(QPrintDialog.PrintCurrentPage, True)
        if dlg.exec() != QPrintDialog.Accepted:
            return
        n = len(self.doc)
        if pr.printRange() == QPrinter.PageRange:
            a, b = max(0, pr.fromPage() - 1), min(n - 1, pr.toPage() - 1)
        elif pr.printRange() == QPrinter.CurrentPage:
            a = b = self.page
        else:
            a, b = 0, n - 1
        painter = QPainter(pr)
        scale = pr.resolution() / 72.0
        r = pr.pageRect(QPrinter.DevicePixel)
        for i in range(a, b + 1):
            if i > a:
                pr.newPage()
            pix = self.doc[i].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            img = pix_to_qimage(pix).scaled(int(r.width()), int(r.height()),
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawImage(QPoint(int((r.width() - img.width()) / 2), 0), img)
        painter.end()
