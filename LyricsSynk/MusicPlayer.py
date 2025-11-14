import vlc
from Lyrics import Lyrics
from Widgets import LyricsWidget, EditorWidget
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QFileDialog, QHBoxLayout, QStackedWidget
)

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lyrics = Lyrics("")
        self.setWindowTitle("Music Player")
        self.setBaseSize(500, 500)
        self.lineReached = 0
        self.wordReached = 0
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.player.audio_set_volume(50)
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
        self.switch_to_boxes_btn.clicked.connect(lambda: self.apply_lyrics_from_editor())
        self.switch_to_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        nav.addWidget(self.switch_to_boxes_btn)
        nav.addWidget(self.switch_to_editor_btn)
        outer.addLayout(nav)

    def load_song(self, file_path):
        if file_path:
            media = self.vlc_instance.media_new(file_path)
            self.player.set_media(media)
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
            self.editor_widget = EditorWidget(self.lyrics, self) # Todo: Make editorwidget always visible. make it update the lyrics objects when you switch back to lyrics widget.
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
            self.player.set_time(word.start_time)
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
            f.write(self.editor_widget.text.toPlainText())
