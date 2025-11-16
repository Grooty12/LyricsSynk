from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QHBoxLayout, QScrollArea,
    QButtonGroup, QPlainTextEdit, QPushButton
)
from PySide6.QtCore import Qt, QPoint, QObject, QTimer, Signal
from PySide6.QtGui import QPainter, QFontMetrics
from bisect import bisect_right
import time

current_time = 0
last_event_clock = 0.0

def get_current_time():
    return current_time

def set_current_time(new_time):
    global current_time, last_event_clock
    current_time = new_time
    last_event_clock = time.perf_counter()

def format_time(ms):
    if ms is None:
        return "00:00.000"
    milliseconds = str(ms % 1000).zfill(3)
    seconds = str((ms // 1000) % 60).zfill(2)
    minutes = str((ms // 1000) // 60).zfill(2)
    return f"{minutes}:{seconds}.{milliseconds}"


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
            txt = format_time(self.start_time)
            right = self.rect().topRight() - QPoint(fm.horizontalAdvance(txt) + 2, -12)
            p.drawText(right, txt)
        if self.end_time is not None:
            txt = format_time(self.end_time)
            right = self.rect().bottomRight() - QPoint(fm.horizontalAdvance(txt) + 2, 0)
            p.drawText(right, txt)

class LyricsWidget(QWidget):
    active_words_changed = Signal(list)
    def __init__(self, lyrics, parent=None):
        super().__init__(parent)
        global current_time, last_event_clock
        self.lyrics = lyrics
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.current_line = 0
        self.current_word = 0
        self.parent = parent
        self.scroll_area = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000 // 240)
        self._timer.timeout.connect(self.on_frame)
        self.player = None
        self.words = []
        self.init_ui()
        self.active = []

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
            if ln.is_voice_2 is None or ln.is_voice_2 is True:
                ln.hbox.addStretch()
            ln.hbox.setSpacing(10)
            for j, w in enumerate(ln.words):
                w.word_box = WordBox(w.word)
                w.word_box.start_time = w.start_time
                w.word_box.end_time = w.end_time
                ln.hbox.addWidget(w.word_box)
                self.group.addButton(w.word_box)
                w.word_box.clicked.connect(self._make_jump_cb(w))
            if ln.is_voice_1 is None or ln.is_voice_1 is True:
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

    def set_timer(self, current_time, player, words):
        self.player = player
        self.words = words

    def start_timer(self):
        self._timer.start()
        self.group.setExclusive(False)

    def stop_timer(self):
        self._timer.stop()
        self.group.setExclusive(True)

    def on_frame(self):
        elapsed = time.perf_counter() - last_event_clock
        interpolated = current_time + (elapsed*1000)
        active = []
        for word in self.active:
            if word.end_time > interpolated:
                active.append(word)
            else:
                word.word_box.setChecked(False)
        idx = bisect_right([w.start_time for w in self.words], interpolated) - 1
        while idx < len(self.words) and \
                self.words[idx].start_time <= interpolated < self.words[idx].end_time:
            active.append(self.words[idx])
            idx += 1
        if active:
            self.scroll_to_line(active[-1 if len(active) > 1 else 0].word_box)
        self.active_words_changed.emit(active)
        self.active = active


class EditorWidget(QWidget):
    def __init__(self, lyrics, parent=None):
        super().__init__(parent)
        self.lyrics = lyrics
        self.text = QPlainTextEdit()
        self.init_ui()

    def init_ui(self):
        v = QVBoxLayout(self)
        self.refresh_text()
        v.addWidget(self.text)

    def refresh_text(self):
        out = []
        if self.lyrics is None:
            return
        for ln in self.lyrics.lines:
            line_txt = ""
            if ln.start_time is not None and not ln.is_background_voice:
                line_txt += f"[{format_time(ln.start_time)}]"
                line_txt += "v1:" if ln.is_voice_1 else ""
                line_txt += "v2:" if ln.is_voice_2 else ""
            line_txt += "[bg:" if ln.is_background_voice else ""
            for x,w in enumerate(ln.words):
                if w.start_time is not None and w.end_time is not None:
                    line_txt += f"<{format_time(w.start_time)}>{w.word} <{format_time(w.end_time)}>"
                    if x == len(ln.words) - 1 and not ln.is_background_voice:
                        line_txt += f"<{format_time(w.end_time)}>"
                else:
                    line_txt += f"{w.word} "
            line_txt += "]" if ln.is_background_voice else ""
            out.append(line_txt.strip())
        self.text.setPlainText("\n".join(out))
