import sys
from pathlib import Path
from PyQt6.QtCore import QUrl, QTimer, Qt
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QLabel)


class LyricWord:
    def __init__(self, start: float, text: str):
        self.start = start
        self.text = text


class LyricsDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lyrics Player")
        self.resize(600, 200)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_lyrics)

        self.lyrics: list[LyricWord] = []
        self.current_index = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Load an audio file and lyrics file to start")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 24px;")
        layout.addWidget(self.label)

        btn_layout = QHBoxLayout()
        self.load_audio_btn = QPushButton("Load Audio")
        self.load_audio_btn.clicked.connect(self.load_audio)
        btn_layout.addWidget(self.load_audio_btn)

        self.load_lyrics_btn = QPushButton("Load Lyrics")
        self.load_lyrics_btn.clicked.connect(self.load_lyrics_file)
        btn_layout.addWidget(self.load_lyrics_btn)

        self.play_btn = QPushButton("Play/Pause")
        self.play_btn.clicked.connect(self.toggle_playback)
        btn_layout.addWidget(self.play_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "", "Audio Files (*.mp3 *.wav *.flac)"
        )
        if not file_path:
            return
        self.player.setSource(QUrl.fromLocalFile(file_path))

    def load_lyrics_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Lyrics File", "", "LRC Files (*.lrc)"
        )
        if not file_path:
            return
        self.load_lyrics(Path(file_path))

    def load_lyrics(self, lrc_path: Path):
        self.lyrics.clear()
        self.current_index = 0
        if not lrc_path.exists():
            return
        with lrc_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("[") or "]" not in line:
                    continue
                header, body = line.split("]", 1)
                body_parts = body.split("<")
                for part in body_parts:
                    if ">" not in part:
                        continue
                    time_str, word = part.split(">", 1)
                    start = self.parse_time(time_str)
                    self.lyrics.append(LyricWord(start, word.strip()))

    def parse_time(self, s: str) -> float:
        minutes, seconds = s.split(":", 1)
        return float(minutes) * 60 + float(seconds)

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.timer.stop()
        else:
            self.player.play()
            self.timer.start()

    def update_lyrics(self):
        if not self.lyrics:
            return
        pos = self.player.position() / 1000.0
        while (self.current_index < len(self.lyrics) - 1 and
               self.lyrics[self.current_index + 1].start <= pos):
            self.current_index += 1
        if self.current_index < len(self.lyrics):
            self.label.setText(self.lyrics[self.current_index].text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LyricsDisplay()
    window.show()
    sys.exit(app.exec())
