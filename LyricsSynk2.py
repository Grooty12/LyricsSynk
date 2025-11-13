import sys, os, re, math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QFileDialog, QHBoxLayout, QLabel, QSlider, QTextEdit, QScrollArea,
    QButtonGroup, QStackedWidget, QPlainTextEdit
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, Qt, QTimer, QPoint
from PySide6.QtGui import QKeySequence, QShortcut, QPainter, QFontMetrics


class LyricsWord:
    def __init__(self, word, line_start_time):
        self.word = word
        self.line_start_time = line_start_time
        self.start_time = None
        self.end_time = None
        self.word_box = None


class LyricsLine:
    def __init__(self, line):
        self.start_time = None
        self.hbox = None
        self.words = []
        self.words_with_time = line
        if self.words_with_time.strip():
            for w in self.words_with_time.split():
                if w.strip():
                    self.words.append(LyricsWord(w, self.start_time))
        self.end_time = None
        self.words_length = len(self.words)

    def toarray(self):
        return self.words


class Lyrics:
    def __init__(self, lyrics):
        self.return_string = []
        self.vbox = None
        self.lines_with_time = lyrics.split("\n")
        self.lines = []
        self.lyricsPath = ""
        self.songName = ""
        for ln in self.lines_with_time:
            if ln.strip():
                self.lines.append(LyricsLine(ln))

    def toarray(self):
        self.return_string = []
        for ln in self.lines:
            self.return_string.append(ln.toarray())
        return self.return_string


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
        base = self.rect().bottomLeft()
        if self.start_time is not None:
            txt = self._format_time(self.start_time)
            p.drawText(base - QPoint(fm.horizontalAdvance(txt), 0), txt)
        if self.end_time is not None:
            txt = self._format_time(self.end_time)
            right = self.rect().bottomRight() - QPoint(fm.horizontalAdvance(txt) + 2, 0)
            p.drawText(right, txt)

    def _format_time(self, ms):
        if ms is None:
            return ""
        s = (ms // 1000) % 60
        m = (ms // 1000) // 60
        return f"{m:02d}:{s:02d}"


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
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        container = QWidget()
        self.lyrics.vbox = QVBoxLayout(container)
        self.lyrics.vbox.setSpacing(10)
        self.lyrics.vbox.setAlignment(Qt.AlignTop)

        for i, ln in enumerate(self.lyrics.lines):
            ln.hbox = QHBoxLayout()
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
                    self.scroll_to_line(line_idx)

    def scroll_to_line(self, line_idx):
        if not self.scroll_area or line_idx >= len(self.lyrics.lines):
            return

        container = self.scroll_area.widget()
        if not container:
            return

        line_layout = self.lyrics.lines[line_idx].hbox
        if not line_layout:
            return

        line_widget = None
        for i in range(line_layout.count()):
            item = line_layout.itemAt(i)
            if item and item.widget():
                line_widget = item.widget().parent()
                break

        if not line_widget:
            return

        viewport_height = self.scroll_area.viewport().height()
        widget_height = line_widget.height()

        vertical_bar = self.scroll_area.verticalScrollBar()
        if vertical_bar:
            center_position = line_widget.y() - (viewport_height // 2) + (widget_height // 2)
            vertical_bar.setValue(max(0, center_position))


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
        for ln in self.lyrics.lines:
            line_txt = ""
            if ln.start_time is not None:
                line_txt += f"[{self._format_time(ln.start_time)}]"
            for w in ln.words:
                if w.start_time is not None and w.end_time is not None:
                    line_txt += f"<{self._format_time(w.start_time)}>{w.word}<{self._format_time(w.end_time)}> "
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


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lyrics = Lyrics("")
        self.setWindowTitle("Music Player")
        self.setBaseSize(500, 500)
        self.lineReached = 0
        self.wordReached = 0
        self.timingWord = False
        self.pressedKey = ""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        central = QWidget()
        self.setCentralWidget(central)
        self.stack = QStackedWidget()
        self.lyrics_widget = None
        self.editor_widget = None
        outer = QVBoxLayout(central)
        outer.addWidget(self.stack)

        nav = QHBoxLayout()
        self.switch_to_boxes_btn = QPushButton("Word Boxes")
        self.switch_to_editor_btn = QPushButton("Editor")
        self.switch_to_boxes_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.switch_to_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        nav.addWidget(self.switch_to_boxes_btn)
        nav.addWidget(self.switch_to_editor_btn)
        outer.addLayout(nav)

        self.player.durationChanged.connect(self.duration_changed)
        self.player.positionChanged.connect(self.update_slider)
        self.player.playbackStateChanged.connect(self.on_state_changed)

    def load_song(self, file_path):
        if file_path:
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.label.setText(file_path.split("/")[-1])
            self.play_btn.setEnabled(True)
            self.play_btn.setText("Play")

    def load_lyrics_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Lyrics", "", "Text Files (*.txt *.lrc)"
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.lyrics = Lyrics(f.read())
                self.lyrics.songName = file_path.split("/")[-1]
            self.lyrics_string = self.lyrics.toarray()
            self.lyrics_widget = LyricsWidget(self.lyrics, self)
            self.editor_widget = EditorWidget(self.lyrics, self)
            self.stack.addWidget(self.lyrics_widget)
            self.stack.addWidget(self.editor_widget)
            self.stack.setCurrentIndex(0)

    def apply_lyrics_from_editor(self):
        text = self.editor_widget.text.toPlainText()
        self.lyrics = Lyrics(text)
        self.lyrics_string = self.lyrics.toarray()

        # Store current position
        current_line = self.lineReached
        current_word = self.wordReached

        # Remove old widgets
        if self.lyrics_widget:
            self.stack.removeWidget(self.lyrics_widget)
            self.lyrics_widget.deleteLater()
        if self.editor_widget:
            self.stack.removeWidget(self.editor_widget)
            self.editor_widget.deleteLater()

        # Create new widgets
        self.lyrics_widget = LyricsWidget(self.lyrics, self)
        self.editor_widget = EditorWidget(self.lyrics, self)

        # Add to stack
        self.stack.insertWidget(0, self.lyrics_widget)
        self.stack.insertWidget(1, self.editor_widget)

        # Restore position (within bounds)
        if current_line >= len(self.lyrics.lines):
            current_line = len(self.lyrics.lines) - 1
        if current_line >= 0:
            if current_word >= len(self.lyrics.lines[current_line].words):
                current_word = len(self.lyrics.lines[current_line].words) - 1
            if current_word >= 0:
                self.lyrics_widget.select_word(current_line, current_word)

        self.lineReached = current_line
        self.wordReached = current_word
        self.stack.setCurrentIndex(0)

    def jump_to_word(self, word):
        if word.start_time is not None:
            self.player.setPosition(max(0, word.start_time - 2000))
            for ln in self.lyrics.lines:
                for w in ln.words:
                    if w.word_box and w.word_box.isChecked():
                        w.word_box.setChecked(False)
            word.word_box.setChecked(True)
            for i, ln in enumerate(self.lyrics.lines):
                for j, w in enumerate(ln.words):
                    if w == word:
                        self.lineReached = i
                        self.wordReached = j
                        if self.lyrics_widget:
                            self.lyrics_widget.current_line = i
                            self.lyrics_widget.current_word = j
                        return

    def save_lyrics(self):
        saved_lyrics = self.lyrics.songName + ".elrc"
        with open(saved_lyrics, "w", encoding="utf-8") as f:
            out = ""
            for x, ln in enumerate(self.lyrics.lines):
                out += "\n" if x > 0 else ""
                out += f"[{self._format_time(ln.start_time)}]"
                for w in ln.words:
                    out += f"<{self._format_time(w.start_time)}>{w.word}<{self._format_time(w.end_time)}>"
            f.write(out)

    def _format_time(self, ms):
        if ms is None:
            return "00:00.000"
        milliseconds = str(ms % 1000).zfill(3)
        seconds = str((ms // 1000) % 60).zfill(2)
        minutes = str((ms // 1000) // 60).zfill(2)
        return f"{minutes}:{seconds}.{milliseconds}"


class MusicPlayerWindow(MusicPlayer):
    def __init__(self):
        super().__init__()
        self.lineReached = 0
        self.wordReached = 0
        self.timingWord = False
        self.pressedKey = ""
        central = QWidget()
        self.setCentralWidget(central)
        self.stack = QStackedWidget()
        self.lyrics_widget = None
        self.editor_widget = None
        outer = QVBoxLayout(central)
        outer.addWidget(self.stack)

        nav = QHBoxLayout()
        self.switch_to_boxes_btn = QPushButton("Word Boxes")
        self.switch_to_editor_btn = QPushButton("Editor")
        self.switch_to_boxes_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.switch_to_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        nav.addWidget(self.switch_to_boxes_btn)
        nav.addWidget(self.switch_to_editor_btn)
        outer.addLayout(nav)

        # File label
        self.label = QLabel("No file loaded")
        self.label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.label)

        # Load button
        self.load_btn = QPushButton("Load Song")
        self.load_btn.clicked.connect(self.load_song_dialog)
        outer.addWidget(self.load_btn)

        # Load Lyrics button
        self.load_lyrics_btn = QPushButton("Load Lyrics File")
        self.load_lyrics_btn.clicked.connect(self.load_lyrics_from_file)
        outer.addWidget(self.load_lyrics_btn)

        # Apply Lyrics button
        self.apply_lyrics_btn = QPushButton("Apply Lyrics from Editor")
        self.apply_lyrics_btn.clicked.connect(self.apply_lyrics_from_editor)
        outer.addWidget(self.apply_lyrics_btn)

        # Play/Pause button
        self.play_btn = QPushButton("Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_playback)
        outer.addWidget(self.play_btn)

        # Seek slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.seek)
        outer.addWidget(self.slider)

        # Timer for updating slider
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_slider)

        # Volume slider with label
        vol_layout = QVBoxLayout()
        self.volume_label = QLabel("Volume: 50")
        vol_layout.addWidget(self.volume_label)
        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("0"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        vol_row.addWidget(self.volume_slider)
        vol_row.addWidget(QLabel("100"))
        vol_layout.addLayout(vol_row)
        outer.addLayout(vol_layout)

        # Playback speed slider with label
        self.playbackspeed_label = QLabel("Playback Speed: 1.0x")
        outer.addWidget(self.playbackspeed_label)
        self.playbackspeed_slider = QSlider(Qt.Orientation.Horizontal)
        self.playbackspeed_slider.setRange(0, 200)
        self.playbackspeed_slider.setMaximumWidth(250)
        self.playbackspeed_slider.setValue(100)
        self.playbackspeed_slider.valueChanged.connect(self.update_playbackSpeed)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.playbackspeed_slider)
        h.addStretch()
        outer.addLayout(h)

        self.player.durationChanged.connect(self.duration_changed)
        self.player.positionChanged.connect(self.update_slider)
        self.player.playbackStateChanged.connect(self.on_state_changed)

    def load_song_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Song", "", "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)"
        )
        if file_path:
            self.load_song(file_path)

    def set_volume(self, value):
        self.audio_output.setVolume(value * 0.01)
        self.volume_label.setText(f"Volume: {value}")

    def update_playbackSpeed(self, speed):
        self.player.setPlaybackRate(speed * 0.01)
        self.playbackspeed_label.setText(f"Playback Speed: {speed * 0.01:.1f}x")

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("Pause")
            self.timer.start()
        else:
            self.play_btn.setText("Play")
            self.timer.stop()

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def update_slider(self):
        self.slider.blockSignals(True)
        self.slider.setValue(self.player.position())
        self.slider.blockSignals(False)

    def seek(self, position):
        self.player.setPosition(position)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return

        if event.key() == Qt.Key_L and event.modifiers() & Qt.AltModifier:
            self.on_alt_l_pressed()
        elif event.key() == Qt.Key_J and event.modifiers() & Qt.AltModifier:
            self.seek(max(0, self.player.position() - 1000))
        elif event.key() == Qt.Key_K and event.modifiers() & Qt.AltModifier:
            self.seek(min(self.player.duration(), self.player.position() + 1000))
        elif event.key() == Qt.Key_Left:
            self.navigate_word(-1)
        elif event.key() == Qt.Key_Right:
            self.navigate_word(1)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_L and event.modifiers() & Qt.AltModifier:
            self.on_alt_l_released()
        super().keyReleaseEvent(event)

    def navigate_word(self, direction):
        if not self.lyrics_widget or not self.lyrics.lines:
            return

        current_line = self.lyrics_widget.current_line
        current_word = self.lyrics_widget.current_word

        if direction == -1:  # Left arrow
            if current_word > 0:
                current_word -= 1
            elif current_line > 0:
                current_line -= 1
                current_word = len(self.lyrics.lines[current_line].words) - 1
        else:  # Right arrow
            if current_word < len(self.lyrics.lines[current_line].words) - 1:
                current_word += 1
            elif current_line < len(self.lyrics.lines) - 1:
                current_line += 1
                current_word = 0

        self.lyrics_widget.select_word(current_line, current_word)
        self.lineReached = current_line
        self.wordReached = current_word

    def on_alt_l_pressed(self):
        pos = self.player.position()
        self.lyrics.lines[self.lineReached].words[self.wordReached].start_time = pos
        if self.wordReached == 0:
            self.lyrics.lines[self.lineReached].start_time = pos
        self.lyrics_widget.update_times()

    def on_alt_l_released(self):
        pos = self.player.position()
        self.lyrics.lines[self.lineReached].words[self.wordReached].end_time = pos
        if self.wordReached == len(self.lyrics.lines[self.lineReached].words) - 1:
            if self.lineReached == len(self.lyrics.lines) - 1:
                self.save_lyrics()
                return
            self.lyrics.lines[self.lineReached].end_time = pos
            self.wordReached = 0
            self.lineReached += 1
        else:
            self.wordReached += 1
        if self.wordReached < len(self.lyrics.lines[self.lineReached].words):
            self.lyrics.lines[self.lineReached].words[self.wordReached].word_box.setChecked(True)
        self.lyrics_widget.update_times()
        self.editor_widget.refresh_text()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicPlayerWindow()
    window.show()
    sys.exit(app.exec())
