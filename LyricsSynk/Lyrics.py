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
        self.is_empty = False
        self.is_voice_1 = True
        self.is_voice_2 = False
        self.is_background_voice = False
        if len(self.words_with_time.split("]")) > 1 :
            words_with_time_split = self.words_with_time.split("]")
            if words_with_time_split[1] == "" or words_with_time_split[1] == " ":
                self.is_empty = True
                return
            start_time_string = words_with_time_split[0][1:]
            self.start_time = ((int(start_time_string[0:1])*60)+int(start_time_string[4:5]))*1000 + int(start_time_string[6:])
            self.words_with_time = words_with_time_split[1]
        if len(self.words_with_time.split(">")) > 1:
            syllable_words = self.words_with_time.split(" ")
            for i,w in enumerate(syllable_words):
                if i == 0:
                    word_start_time, word = w.split(">")
                else:
                    prev_end_time, word_start_time, word = w.split(">")
                    self.words[i-1].end_time = ((int(prev_end_time[1:2])*60)+int(prev_end_time[5:6]))*1000 + int(prev_end_time[7:])
                self.words.append(LyricsWord(word, self.start_time))
                self.words[i].start_time = ((int(word_start_time[1:2])*60)+int(word_start_time[5:6]))*1000 + int(word_start_time[7:])

        elif self.words_with_time.strip():
            for i, w in enumerate(self.words_with_time.split()):
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
                lyrics_line = LyricsLine(ln)
                if not lyrics_line.is_empty:
                    self.lines.append(LyricsLine(ln))

    def toarray(self):
        self.return_string = []
        for ln in self.lines:
            self.return_string.append(ln.toarray())
        return self.return_string