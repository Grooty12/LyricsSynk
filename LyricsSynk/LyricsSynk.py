import vlc, sys, bisect
from PySide6.QtWidgets import (
    QApplication, QPushButton, QVBoxLayout, QWidget,
    QFileDialog, QHBoxLayout, QLabel, QSlider, QStackedWidget
)
from PySide6.QtCore import Qt
from MusicPlayer import MusicPlayer
from Widgets import format_time


class MusicPlayerWindow(MusicPlayer):
    def __init__(self):
        super().__init__()
        self.lineReached = 0
        self.wordReached = 0
        central = QWidget()
        self.setCentralWidget(central)
        self.stack = QStackedWidget()
        self.editor_widget = None
        self.lyrics_widget = None
        self.load_initial_lyrics_views()
        outer = QVBoxLayout(central)
        outer.addWidget(self.stack)
        self.words = []
        self.starts = [] # Start times

        nav = QHBoxLayout()
        self.switch_to_boxes_btn = QPushButton("Word Boxes")
        self.switch_to_editor_btn = QPushButton("Editor")
        self.switch_to_boxes_btn.clicked.connect(lambda: self.apply_lyrics_from_editor())
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
        self.save_lyrics_btn = QPushButton("Save Lyrics to File")
        self.save_lyrics_btn.clicked.connect(self.save_lyrics)
        self.save_lyrics_btn.setEnabled(False)
        lyrics_buttons = QHBoxLayout()
        lyrics_buttons.addWidget(self.load_lyrics_btn)
        lyrics_buttons.addWidget(self.save_lyrics_btn)
        outer.addLayout(lyrics_buttons)

        # Play with lyrics
        self.play_lyrics_back_btn = QPushButton("Play with lyrics")
        self.play_lyrics_back_btn.clicked.connect(self.play_with_lyrics)
        self.play_lyrics_back = False
        outer.addWidget(self.play_lyrics_back_btn)


        # Play/Pause button
        self.play_btn = QPushButton("Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_playback)
        outer.addWidget(self.play_btn)

        # Seek slider
        slider_layout = QVBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.seek)
        slider_row = QHBoxLayout()
        self.slider_position = QLabel("0")
        self.slider_song_duration = QLabel("0")
        slider_row.addWidget(self.slider_position)
        slider_row.addWidget(self.slider)
        slider_row.addWidget(self.slider_song_duration)
        slider_layout.addLayout(slider_row)
        outer.addLayout(slider_layout)

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

        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerLengthChanged, self.update_duration)
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerTimeChanged, self.update_slider)  # ➜ ADD
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerPlaying, self.play)
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerPaused, self.pause)

    def play_with_lyrics(self):
        self.play_lyrics_back = not self.play_lyrics_back
        self.words = self.lyrics.toarray()
        self.words = [w for i in self.words for w in i]
        self.starts = [w.start_time for w in self.words]
        self.lyrics_widget.set_timer(60, self.player, self.words)
        for word in self.words:  # list/iterable of WordBox
            self.lyrics_widget.active_words_changed.connect(word.on_active_changed)


    def load_song_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Song", "", "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)"
        )
        if file_path:
            self.load_song(file_path)

    def set_volume(self, value):
        self.player.audio_set_volume(value)
        self.volume_label.setText(f"Volume: {value}")

    def update_playbackSpeed(self, speed):
        self.player.set_rate(speed * 0.01)
        self.playbackspeed_label.setText(f"Playback Speed: {speed * 0.01:.1f}x")

    def toggle_playback(self):
        if self.player.get_state() == vlc.State.Playing:
            self.player.pause()
            self.lyrics_widget.stop_timer()
        else:
            self.player.play()
            self.lyrics_widget.start_timer()

    def play(self, state, userdata=None):
        self.play_btn.setText("Pause")

    def pause(self, state, userdata=None):
        self.play_btn.setText("Play")

    def update_slider(self, event, userdata=None):
        self.slider.blockSignals(True)
        self.slider.setValue(self.player.get_time())
        self.slider_position.setText(format_time(self.player.get_time()))
        self.slider.blockSignals(False)

    def update_duration(self, event, userdata=None):
        self.slider.setRange(0, self.player.get_length())
        self.slider_song_duration.setText(format_time(self.player.get_length())[:5])

    def seek(self, position):
        self.player.set_time(position)

    def keyPressEvent(self, event):
        if event.isAutoRepeat() or self.play_lyrics_back:
            return

        if event.key() == Qt.Key_W:
            self.save_start_time()
        elif event.key() == Qt.Key_E:
            self.save_end_time()
        elif event.key() == Qt.Key_J and event.modifiers() & Qt.AltModifier:
            self.seek(max(0, self.player.get_time() - 1000))
        elif event.key() == Qt.Key_K and event.modifiers() & Qt.AltModifier:
            self.seek(min(self.player.get_length(), self.player.get_time() + 1000))
        elif event.key() == Qt.Key_Left:
            self.navigate_word(-1)
        elif event.key() == Qt.Key_Right:
            self.navigate_word(1)
        elif event.key() == Qt.Key_D:
            self.save_start_time_no_skip()
        elif event.key() == Qt.Key_F:
            self.save_end_time_is_precise()
        elif event.key() == Qt.Key_J:
            self.seek(max(0, self.player.get_time() - 1000))
        elif event.key() == Qt.Key_K:
            self.seek(min(self.player.get_length(), self.player.get_time() + 1000))
        elif event.key() == Qt.Key_V:
            self.set_line_singer("v1")
        elif event.key() == Qt.Key_B:
            self.set_line_singer("v2")
        elif event.key() == Qt.Key_N:
            self.set_line_singer("bg")
        super().keyPressEvent(event)


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

    def set_line_singer(self, singer):
        if singer == "v1":
            self.lyrics.lines[self.lineReached].is_voice_1 = True
            self.lyrics.lines[self.lineReached].is_voice_2 = False
            self.lyrics.lines[self.lineReached].is_background_voice = False
        elif singer == "v2":
            self.lyrics.lines[self.lineReached].is_voice_1 = False
            self.lyrics.lines[self.lineReached].is_voice_2 = True
            self.lyrics.lines[self.lineReached].is_background_voice = False
        elif singer == "bg":
            self.lyrics.lines[self.lineReached].is_voice_1 = None
            self.lyrics.lines[self.lineReached].is_voice_2 = False
            self.lyrics.lines[self.lineReached].is_background_voice = True
        self.editor_widget.refresh_text()

    def save_start_time_no_skip(self):
        print(len(self.lyrics.lines[self.lineReached].words))
        pos = self.player.get_time()
        self.lyrics.lines[self.lineReached].words[self.wordReached].start_time = pos
        if self.wordReached == 0:
            self.lyrics.lines[self.lineReached].start_time = pos
        self.lyrics_widget.update_times()
        self.editor_widget.refresh_text()

    def save_end_time_is_precise(self):
        pos = self.player.get_time()
        self.lyrics.lines[self.lineReached].words[self.wordReached].end_time = pos
        if self.wordReached == len(self.lyrics.lines[self.lineReached].words) - 1:
            self.lyrics.lines[self.lineReached].end_time = pos
            if self.lineReached == len(self.lyrics.lines) - 1:
                self.save_lyrics()
                self.lyrics_widget.update_times()
                self.editor_widget.refresh_text()
                return
            self.wordReached = 0
            self.lineReached += 1
        else:
            self.wordReached += 1
        if self.wordReached < len(self.lyrics.lines[self.lineReached].words):
            self.lyrics.lines[self.lineReached].words[self.wordReached].word_box.setChecked(True)
        self.lyrics_widget.update_times()
        self.editor_widget.refresh_text()
        self.lyrics_widget.scroll_to_line(self.lyrics.lines[self.lineReached].words[self.wordReached].word_box)

    def save_start_time(self):
        pos = self.player.get_time()
        self.lyrics.lines[self.lineReached].words[self.wordReached].start_time = pos
        if self.wordReached == 0:
            self.lyrics.lines[self.lineReached].start_time = pos
        if self.wordReached == len(self.lyrics.lines[self.lineReached].words) - 1:
            self.wordReached = 0
            self.lineReached += 1
        else:
            self.wordReached += 1
        if self.lineReached < len(self.lyrics.lines) and self.wordReached < len(self.lyrics.lines[self.lineReached].words):
            self.lyrics.lines[self.lineReached].words[self.wordReached].word_box.setChecked(True)
            self.lyrics_widget.scroll_to_line(self.lyrics.lines[self.lineReached].words[self.wordReached].word_box)
        self.lyrics_widget.update_times()
        self.editor_widget.refresh_text()

    def save_end_time(self):
        pos = self.player.get_time()
        self.lyrics.lines[self.lineReached].words[self.wordReached].end_time = pos
        if self.wordReached == len(self.lyrics.lines[self.lineReached].words) - 1:
            self.lyrics.lines[self.lineReached].end_time = pos
            if self.lineReached == len(self.lyrics.lines) - 1:
                self.lyrics_widget.update_times()
                self.editor_widget.refresh_text()
                return
            self.wordReached = 0
            self.lineReached += 1
        else:
            if pos > self.lyrics.lines[self.lineReached].words[self.wordReached+1].start_time:
                self.lyrics.lines[self.lineReached].words[self.wordReached].end_time = max(self.lyrics.lines[self.lineReached].words[self.wordReached + 1].start_time - 10,0)
            self.wordReached += 1
        if self.wordReached < len(self.lyrics.lines[self.lineReached].words):
            self.lyrics.lines[self.lineReached].words[self.wordReached].word_box.setChecked(True)
        self.lyrics_widget.update_times()
        self.editor_widget.refresh_text()
        self.lyrics_widget.scroll_to_line(self.lyrics.lines[self.lineReached].words[self.wordReached].word_box)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicPlayerWindow()
    window.show()
    sys.exit(app.exec())