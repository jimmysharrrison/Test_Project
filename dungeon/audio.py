"""Small synthesized combat cues, with a silent fallback on audio-less systems."""

from array import array
from math import pi, sin
from random import Random

import pygame


class Audio:
    def __init__(self):
        self.enabled = False
        self.available = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        except pygame.error:
            return
        self.available = self.enabled = True
        rng = Random(8)
        settings = {
            "bolt": (1200, 450, 0.12, 0.12),
            "hit": (160, 65, 0.10, 0.5),
            "break": (190, 35, 0.35, 0.5),
            "hurt": (125, 65, 0.18, 0.3),
            "nova": (900, 180, 0.3, 0.35),
            "wall": (330, 800, 0.4, 0.2),
            "prison": (600, 350, 0.6, 0.05),
            "shatter": (1600, 90, 0.55, 0.6),
            "heal": (470, 900, 0.3, 0),
            "gold": (1000, 1200, 0.07, 0),
            "loot": (650, 1400, 0.24, 0),
            "win": (450, 900, 0.65, 0),
            "dead": (200, 55, 0.6, 0.1),
        }
        for name, (start, end, duration, noise) in settings.items():
            samples = array("h")
            count = round(22050 * duration)
            for i in range(count):
                t = i / 22050
                progress = i / count
                phase = 2 * pi * (start * t + (end - start) * t * t / (2 * duration))
                wave = sin(phase) * (1 - noise) + rng.uniform(-1, 1) * noise
                envelope = min(1, progress * 30) * (1 - progress) ** 1.8
                samples.append(round(wave * envelope * 6500))
            self.sounds[name] = pygame.mixer.Sound(buffer=samples)

    def toggle(self):
        if self.available:
            self.enabled = not self.enabled
            if not self.enabled:
                pygame.mixer.stop()

    def play(self, events):
        if self.enabled:
            # Limit duplicate cues when a crowd is hit in one frame.
            for name in set(events):
                if name in self.sounds:
                    self.sounds[name].play()
