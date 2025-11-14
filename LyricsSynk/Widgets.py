from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QHBoxLayout, QScrollArea,
    QButtonGroup, QPlainTextEdit, QPushButton
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QFontMetrics

class WordBox(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setFixedSize(90, 50)
        self.setCheckable(True)
        self.start_time = None
        self.end_time = None
        self.setStyleSheet("""
            WordBox {
                border: 2px solid #555;
                border-radius: 10px;
                background: #222;
                color: #fff;
                font-size: 14px;
            }
            WordBox:checked {
                border: 3px solid #1e90ff;
                background: #333;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setPen(Qt.white)
        fm = QFontMetrics(p.font())
        if self.start_time is not None:
            txt = self._format_time(self.start_time)
            right = self.rect().topRight() - QPoint(fm.horizontalAdvance(txt) + 2, -12)
            p.drawText(right, txt)
        if self.end_time is not None:
            txt = self._format_time(self.end_time)
            right = self.rect().bottomRight() - QPoint(fm.horizontalAdvance(txt) + 2, 0)
            p.drawText(right, txt)

    def _format_time(self, ms):
        if ms is None:
            return ""

        s = (ms // 1000) % 60
        m = (ms // 1000) // 60
        ms1 = ms % 1000
        return f"{m:02d}:{s:02d}.{ms1:03d}"

class LyricsWidget(QWidget):
    def __init__(self, lyrics, parent=None):
        super().__init__(parent)
        self.lyrics = lyrics
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.current_line = 0
        self.current_word = 0
        self.parent = parent
        self.scroll_area = None
        self.init_ui()

    def init_ui(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        container = QWidget()
        self.lyrics.vbox = QVBoxLayout(container)
        self.lyrics.vbox.setSpacing(10)
        self.lyrics.vbox.setAlignment(Qt.AlignTop)

        for i, ln in enumerate(self.lyrics.lines):
            line_widget = QWidget()
            ln.hbox = QHBoxLayout(line_widget)
            ln.hbox.addStretch()
            ln.hbox.setSpacing(10)
            for j, w in enumerate(ln.words):
                w.word_box = WordBox(w.word)
                w.word_box.start_time = w.start_time
                w.word_box.end_time = w.end_time
                ln.hbox.addWidget(w.word_box)
                self.group.addButton(w.word_box)
                w.word_box.clicked.connect(self._make_jump_cb(w))
                w.word_box.setProperty("line_idx", i)
                w.word_box.setProperty("word_idx", j)
            ln.hbox.addStretch()
            self.lyrics.vbox.addLayout(ln.hbox)
            self.lyrics.vbox.addWidget(line_widget)
        self.scroll_area.setWidget(container)
        outer = QVBoxLayout(self)
        outer.addWidget(self.scroll_area)

    def _make_jump_cb(self, w):
        return lambda: self.parent.jump_to_word(w)

    def update_times(self):
        for ln in self.lyrics.lines:
            for w in ln.words:
                if w.word_box:
                    w.word_box.start_time = w.start_time
                    w.word_box.end_time = w.end_time
                    w.word_box.update()

    def select_word(self, line_idx, word_idx):
        if 0 <= line_idx < len(self.lyrics.lines):
            if 0 <= word_idx < len(self.lyrics.lines[line_idx].words):
                word = self.lyrics.lines[line_idx].words[word_idx]
                if word.word_box:
                    word.word_box.setChecked(True)
                    self.current_line = line_idx
                    self.current_word = word_idx
                    self.scroll_to_line(word.word_box)

    def scroll_to_line(self, wordbox):
        self.scroll_area.ensureWidgetVisible(wordbox)



class EditorWidget(QWidget):
    def __init__(self, lyrics, parent=None):
        super().__init__(parent)
        self.lyrics = lyrics
        self.init_ui()

    def init_ui(self):
        v = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.refresh_text()
        v.addWidget(self.text)

    def refresh_text(self):
        out = []
        if self.lyrics is None:
            self.text.setPlainText("Enter lyrics or import them...")
            return
        for ln in self.lyrics.lines:
            line_txt = ""
            if ln.start_time is not None:
                line_txt += f"[{self._format_time(ln.start_time)}]"
            for w in ln.words:
                if w.start_time is not None and w.end_time is not None:
                    line_txt += f"<{self._format_time(w.start_time)}>{w.word} <{self._format_time(w.end_time)}>"
                else:
                    line_txt += f"{w.word} "
            out.append(line_txt.strip())
        self.text.setPlainText("\n".join(out))

    def _format_time(self, ms):
        if ms is None:
            return "00:00.000"
        milliseconds = str(ms % 1000).zfill(3)
        seconds = str((ms // 1000) % 60).zfill(2)
        minutes = str((ms // 1000) // 60).zfill(2)
        return f"{minutes}:{seconds}.{milliseconds}"
