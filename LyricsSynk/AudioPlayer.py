import numpy as np
import pydub
import pyrubberband as pyrb
import sounddevice as sd
import threading
import time
import pyaudio


class AudioPlayer:
    def __init__(self):
        # Initialize without audio
        self.audio = None
        self.sample_rate = 44100
        self.channels = 2
        self.samples = None

        # Playback state
        self.playback_speed = 1.0
        self.current_position = 0  # in samples
        self.is_playing = False
        self.volume = 50

        # Events
        self.duration_callbacks = []
        self.time_callbacks = []
        self.state_callbacks = []

        # Playback thread
        self.playback_thread = None

    def load_audio(self, file_path):
        """Load audio file after initialization"""
        self.audio = pydub.AudioSegment.from_file(file_path, format="flac")
        self.sample_rate = self.audio.frame_rate
        self.channels = self.audio.channels

        # Convert to numpy array
        self.samples = np.array(self.audio.get_array_of_samples())
        if self.channels == 2:
            self.samples = self.samples.reshape((-1, 2))

        # Reset position
        self.current_position = 0

        # Notify duration callbacks
        for callback in self.duration_callbacks:
            callback(self.get_length())

    def update_duration(self, duration):
        for callback in self.duration_callbacks:
            callback(duration)

    def update_slider(self, position):
        for callback in self.time_callbacks:
            callback(position)

    def play(self):
        if not self.is_playing and self.audio is not None:
            self.is_playing = True
            for callback in self.state_callbacks:
                callback('playing')
            self._start_playback()

    def pause(self):
        self.is_playing = False
        for callback in self.state_callbacks:
            callback('paused')

    def _start_playback(self):
        if self.audio is None:
            return

        def playback_worker():
            # Apply time stretching (keep your existing code)
            stretch_rate = 1.0 / self.playback_speed
            start_sample = self.current_position
            audio_segment = self.samples[start_sample:]

            if len(audio_segment) == 0:
                return

            stretched_samples = pyrb.time_stretch(
                audio_segment,
                self.sample_rate,
                stretch_rate
            )

            # Apply volume (keep your existing code)
            audio_data = (stretched_samples * (self.volume / 100.0)).astype(np.float32)

            # Replace sounddevice with PyAudio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                output=True
            )

            chunk_size = 1024
            for i in range(0, len(audio_data), chunk_size):
                if not self.is_playing:
                    break

                end_idx = min(i + chunk_size, len(audio_data))
                stream.write(audio_data[i:end_idx].tobytes())

                # Update position (keep your existing code)
                samples_played = int(i * stretch_rate)
                self.current_position = min(
                    start_sample + samples_played,
                    len(self.samples) - 1
                )

                time_ms = int((self.current_position / self.sample_rate) * 1000)
                self.update_slider(time_ms)

            stream.stop_stream()
            stream.close()
            p.terminate()

        self.playback_thread = threading.Thread(target=playback_worker)
        self.playback_thread.start()

    def set_playback_speed(self, speed_percent):
        self.playback_speed = speed_percent / 100.0

    def set_volume(self, volume_percent):
        self.volume = volume_percent

    def get_time(self):
        if self.audio is None:
            return 0
        return int((self.current_position / self.sample_rate) * 1000)

    def set_time(self, position_ms):
        if self.audio is None:
            return
        # Set position in milliseconds
        self.current_position = int((position_ms / 1000.0) * self.sample_rate)
        self.current_position = min(self.current_position, len(self.samples) - 1)

    def get_length(self):
        if self.audio is None:
            return 0
        return len(self.audio)

    def get_state(self):
        return 'playing' if self.is_playing else 'paused'

    # Event attachment methods
    def event_attach(self, event_type, callback):
        if event_type == 'duration':
            self.duration_callbacks.append(callback)
            if self.audio is not None:
                callback(self.get_length())
        elif event_type == 'time':
            self.time_callbacks.append(callback)
        elif event_type == 'state':
            self.state_callbacks.append(callback)


