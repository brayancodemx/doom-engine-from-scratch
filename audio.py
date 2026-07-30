"""Audio del juego: archivos MP3 con efectos procedurales de respaldo."""

from array import array
import math
from pathlib import Path
import random

import pygame

ROOT = Path(__file__).resolve().parent
AUDIO_ROOT = ROOT / "assets" / "audio"


def _sound_from_samples(samples):
    try:
        return pygame.mixer.Sound(buffer=array("h", samples).tobytes())
    except pygame.error:
        return None


def tone(frequency, duration, volume=0.25, slide=0.0):
    sample_rate = 22050
    total = int(sample_rate * duration)
    samples = []
    for index in range(total):
        time = index / sample_rate
        current_frequency = frequency + slide * (index / total)
        envelope = 1.0 - index / total
        value = math.sin(2 * math.pi * current_frequency * time)
        samples.append(int(32767 * volume * envelope * value))
    return _sound_from_samples(samples)


def noise(duration, volume=0.25):
    sample_rate = 22050
    total = int(sample_rate * duration)
    samples = []
    for index in range(total):
        envelope = 1.0 - index / total
        samples.append(int(32767 * volume * envelope * random.uniform(-1, 1)))
    return _sound_from_samples(samples)


class Sounds:
    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.shot = self._load_shot() if self.enabled else None
        self.shotgun = self._load_shotgun() if self.enabled else None
        self.shotgun_followup = (
            self._load_shotgun_followup() if self.enabled else None
        )
        self.hit = tone(110, 0.10, 0.30, -45) if self.enabled else None
        self.enemy_death = self._load_enemy_death() if self.enabled else None
        self.win = tone(420, 0.45, 0.20, 380) if self.enabled else None

    @staticmethod
    def _load_shot():
        """Usa disparo.mp3 y conserva el ruido procedural como respaldo."""
        shot_path = AUDIO_ROOT / "disparo.mp3"
        if shot_path.exists():
            try:
                shot = pygame.mixer.Sound(str(shot_path))
                shot.set_volume(0.72)
                return shot
            except pygame.error:
                pass
        return noise(0.11, 0.38)

    @staticmethod
    def _load_shotgun():
        """Usa escopeta.mp3 para la DOUBLE-T CANNON."""
        shotgun_path = AUDIO_ROOT / "escopeta.mp3"
        if shotgun_path.exists():
            try:
                shotgun = pygame.mixer.Sound(str(shotgun_path))
                shotgun.set_volume(0.88)
                return shotgun
            except pygame.error:
                pass
        return noise(0.34, 0.52)

    @staticmethod
    def _load_shotgun_followup():
        """Carga el golpe mecánico que acompaña la apertura de la escopeta."""
        followup_path = AUDIO_ROOT / "escopeta2.mp3"
        if followup_path.exists():
            try:
                followup = pygame.mixer.Sound(str(followup_path))
                followup.set_volume(0.50)
                return followup
            except pygame.error:
                pass
        return tone(155, 0.16, 0.28, -75)

    @staticmethod
    def _load_enemy_death():
        """Usa muerte.mp3 solamente cuando muere un enemigo."""
        death_path = AUDIO_ROOT / "muerte.mp3"
        if death_path.exists():
            try:
                death = pygame.mixer.Sound(str(death_path))
                death.set_volume(0.72)
                return death
            except pygame.error:
                pass
        return tone(92, 0.22, 0.30, -52)

    @staticmethod
    def play(sound, volume=1.0, maxtime=0):
        if sound:
            channel = sound.play(maxtime=maxtime)
            if channel:
                channel.set_volume(volume)
            return channel
        return None
