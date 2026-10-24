"""Small synthesized combat cues, with a silent fallback on audio-less systems."""

from array import array
from math import pi, sin
from random import Random

import pygame


def fanfare(grand=False):
    """Ascending major-triad bells, ending in a sustained victory chord."""
    rate = 22050
    beat = .32 if grand else .18
    notes = (261.63, 329.63, 392, 523.25)
    duration = 3.0 if grand else 1.35
    samples = array("h")
    for i in range(round(rate * duration)):
        t = i / rate
        wave = 0
        for index, frequency in enumerate(notes):
            age = t - index * beat
            if age < 0:
                continue
            remaining = duration - index * beat
            envelope = min(1, age / .025) * max(0, 1 - age / remaining) ** 1.5
            tone = sin(2 * pi * frequency * age) + .3 * sin(4 * pi * frequency * age)
            if grand:
                tone += .45 * sin(pi * frequency * age)
            wave += tone * envelope
        samples.append(round(wave * 2300))
    return samples


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
        pygame.mixer.set_reserved(1)
        self.victory_channel = pygame.mixer.Channel(0)
        rng = Random(8)
        settings = {
            "bolt": (1200, 450, 0.12, 0.12),
            "freeze": (1800, 850, .12, .2),
            "arrow": (750, 180, 0.14, 0.65),
            "potion_cast": (650, 1350, .18, .3),
            "phase": (450, 1050, .5, .1),
            "phase_clear": (800, 400, .4, .05),
            "hit": (160, 65, 0.10, 0.5),
            "break": (190, 35, 0.35, 0.5),
            "hurt": (125, 65, 0.18, 0.3),
            "nova": (900, 180, 0.3, 0.35),
            "patch": (330, 800, 0.4, 0.2),
            "prison": (600, 350, 0.6, 0.05),
            "shatter": (1600, 90, 0.55, 0.6),
            "frostweave_shatter": (2400, 45, 1.0, 0.85),
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
        self.sounds["miniboss_victory"] = pygame.mixer.Sound(buffer=fanfare())
        self.sounds["keeper_victory"] = pygame.mixer.Sound(buffer=fanfare(grand=True))

    def toggle(self):
        if self.available:
            self.enabled = not self.enabled
            if not self.enabled:
                pygame.mixer.stop()

    def play(self, events):
        if self.enabled:
            if "keeper_victory" in events:
                self.victory_channel.play(self.sounds["keeper_victory"])
            elif "miniboss_victory" in events:
                self.victory_channel.play(self.sounds["miniboss_victory"])
            # Limit duplicate cues when a crowd is hit in one frame.
            for name in set(events):
                if name in self.sounds and name not in ("miniboss_victory", "keeper_victory"):
                    self.sounds[name].play()
