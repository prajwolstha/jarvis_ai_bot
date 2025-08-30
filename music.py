from __future__ import annotations
import os
from typing import List
import pygame
from pygame import mixer
from dataclasses import dataclass
from pathlib import Path

SUPPORTED = (".mp3", ".wav", ".ogg", ".flac")

@dataclass
class Track:
    path: Path
    title: str

class MusicPlayer:
    def __init__(self, music_folder: str):
        self.music_folder = Path(music_folder)
        self.playlist: List[Track] = []
        self.index = 0
        pygame.init()
        mixer.init()

    def scan(self) -> int:
        self.playlist.clear()
        if not self.music_folder.exists():
            self.music_folder.mkdir(parents=True, exist_ok=True)

        for p in sorted(self.music_folder.rglob("*")):
            if p.suffix.lower() in SUPPORTED and p.is_file():
                self.playlist.append(Track(p, p.stem))
        return len(self.playlist)

    def _load_current(self) -> None:
        if not self.playlist:
            raise RuntimeError("Playlist is empty. Put some audio files in your music folder.")
        track = self.playlist[self.index]
        mixer.music.load(track.path.as_posix())

    def play(self) -> str:
        self._load_current()
        mixer.music.play()
        return self.current_title()

    def pause(self) -> None:
        mixer.music.pause()

    def resume(self) -> None:
        mixer.music.unpause()

    def stop(self) -> None:
        mixer.music.stop()

    def next(self) -> str:
        if not self.playlist:
            return "No tracks"
        self.index = (self.index + 1) % len(self.playlist)
        return self.play()

    def prev(self) -> str:
        if not self.playlist:
            return "No tracks"
        self.index = (self.index - 1) % len(self.playlist)
        return self.play()

    def current_title(self) -> str:
        if not self.playlist:
            return "No track"
        return self.playlist[self.index].title
