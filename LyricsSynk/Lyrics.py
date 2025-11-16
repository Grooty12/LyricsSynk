import re

from PySide6.QtCore import Slot, Signal, QObject

class LyricsWord:
    def __init__(self, word, line_start_time, line_number, word_number):
        self.word = word
        self.line_start_time = line_start_time
        self.start_time = None
        self.end_time = None
        self.word_box = None
        self.line_number = line_number
        self.word_number = word_number

    @Slot(list)  # PySide6 / PyQt6
    def on_active_changed(self, active_words):
        if self.word_box and self in active_words:
            self.word_box.setChecked(True)
        elif self.word_box:
            self.word_box.setChecked(False)


class LyricsLine(LyricsWord):
    def __init__(self, line, line_number):
        self.start_time = None
        self.end_time = None
        self.hbox = None
        self.words = []
        self.words_with_time = line
        self.is_empty = False
        self.is_voice_1 = None
        self.is_voice_2 = None
        self.is_background_voice = None
        self.line_number = line_number
        self.number_of_words = 0
        if len(self.words_with_time.split("]")) > 1 :
            words_with_time_split = self.words_with_time.split("]")
            if (words_with_time_split[1] == "" or words_with_time_split[1] == " ") and words_with_time_split[0][1:4].lower() != "bg:":
                self.is_empty = True
                return
            elif words_with_time_split[0][1:4].lower() == "bg:":
                self.is_background_voice = True
                self.is_voice_2 = False
                self.words_with_time = words_with_time_split[0][4:]
            else:
                start_time_string = words_with_time_split[0][1:]
                self.start_time = ((int(start_time_string[0:1])*60)+int(start_time_string[4:5]))*1000 + int(start_time_string[6:])
                self.words_with_time = words_with_time_split[1]
        if len(self.words_with_time.split(">")) > 1:
            if self.words_with_time[:3].lower() == "v1:":
                self.is_voice_1 = True
                self.is_voice_2, self.is_background_voice = False, False
                self.words_with_time = self.words_with_time[3:]
            if self.words_with_time[:3].lower() == "v2:":
                self.is_voice_2 = True
                self.is_voice_1, self.is_background_voice = False, False
                self.words_with_time = self.words_with_time[3:]
            syllable_words = re.split(r'(<[^>]*>)', self.words_with_time)
            syllable_words = [words for words in syllable_words if words]

            if syllable_words[-1][0] == "<" and syllable_words[-2][0] == "<":
                self.end_time = self.string_time_to_ms(syllable_words[-1])
                syllable_words.pop()

            syllable_words = [[syllable_words[i-1], words, syllable_words[i+1]] for i,words in enumerate(syllable_words) if (words[0] != "<" and words[-1] != ">")]
            for i,w in enumerate(syllable_words):
                self.words.append(LyricsWord(w[1], self.start_time, line_number, i))
                self.words[i].start_time = self.string_time_to_ms(w[0])
                self.words[i].end_time = self.string_time_to_ms(w[2])

        elif self.words_with_time.strip():
            for i, w in enumerate(self.words_with_time.split()):
                if w.strip():
                    self.words.append(LyricsWord(w, self.start_time, line_number, i))
        self.end_time = None
        self.words_length = len(self.words)

    def string_time_to_ms(self, string):
        clean_string = re.sub(r'[<>[\]]+', '', string)
        return ((int(clean_string[0:2])*60)+int(clean_string[3:5]))*1000 + int(clean_string[6:])

    def toarray(self):
        return self.words


class Lyrics(QObject):
    active_words_changed = Signal(list)
    def __init__(self, lyrics):
        super().__init__()
        self.return_string = []
        self.vbox = None
        self.lines_with_time = lyrics.split("\n")
        self.lines = []
        self.lyricsPath = ""
        self.songName = ""
        self.number_of_lines = 0
        for ln in self.lines_with_time:
            if ln.strip() and not ln.split("]")[1] in [" ", ""]:
                if len(ln.split("]")) or (len(ln.split("]")) > 1 and (ln.split("]")[1] != "" and ln.split("]")[1] != " ")):
                    self.lines.append(LyricsLine(ln, self.number_of_lines))
                    self.number_of_lines += 1

    def toarray(self):
        self.return_string = []
        for ln in self.lines:
            self.return_string.append(ln.toarray())
        return self.return_string