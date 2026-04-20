"""Sync OS demo soundtrack — "Ghost in the Shell" inspired (~49s, A minor).

Design principles
- Eastern modal flavor: A pentatonic-minor (A C D E G) melodic motif.
- Suspended, mystical pads (Am9: A C E G B).
- Taiko-like low pulse instead of an EDM kick.
- Bell / kalimba-like tones for the ostinato (clean sines + harmonic taps).
- NO white-noise riser, NO airy noise bed (was previously perceived as "ザー").
- Brighter octave shimmer + breath-like pulse at climax for an uplifting lift.
- All synthesized; royalty-free.
"""

import numpy as np
import wave
import sys
import os

SR = 48000
DUR = 49.0
N = int(SR * DUR)
T = np.arange(N) / SR


def env_ramp(t0, t1, v0, v1):
    """Hold v0, ramp to v1 over [t0,t1], then hold v1."""
    e = np.full(N, v0, dtype=np.float64)
    i0 = max(0, int(t0 * SR))
    i1 = min(N, int(t1 * SR))
    if i1 > i0:
        e[i0:i1] = np.linspace(v0, v1, i1 - i0)
    e[i1:] = v1
    return e


def sine(freq, phase=0.0):
    return np.sin(2 * np.pi * freq * T + phase)


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive)


def place(buffer, t_start, samples):
    """Add `samples` into buffer starting at time t_start (s). Truncates if needed."""
    i = int(t_start * SR)
    if i >= N:
        return
    end = min(N, i + len(samples))
    buffer[i:end] += samples[:end - i]


# ---------------------------------------------------------------------------
# 1. Sub bass — A1 (55 Hz) drone with very slow tremolo
# ---------------------------------------------------------------------------
sub_lfo = 0.05 * np.sin(2 * np.pi * 0.12 * T)
sub = sine(55.0) * (0.85 + sub_lfo)
sub_env = env_ramp(0, 5, 0.0, 0.45) * env_ramp(43, 49, 1.0, 0.0)
sub *= sub_env

# ---------------------------------------------------------------------------
# 2. Pad — Am9 (A2 C3 E3 G3 B3) with subtle detune chorus.
#     This is the cinematic, suspended chord that gives the GitS aura.
# ---------------------------------------------------------------------------
def pad_voice(f, det=0.004):
    a = sine(f * (1 + det))
    b = sine(f * (1 - det))
    c = sine(f * 0.5)  # sub-octave reinforcement
    return (a + b + 0.5 * c) / 2.5


pad_freqs = [110.0, 130.81, 164.81, 196.0, 246.94]   # A2 C3 E3 G3 B3 (Am9)
pad = sum(pad_voice(f, 0.003 + 0.001 * i) for i, f in enumerate(pad_freqs)) / len(pad_freqs)
# slight low-pass via 3-point moving avg
pad = (pad + np.roll(pad, 1) + np.roll(pad, 2)) / 3.0
pad_env = env_ramp(0, 7, 0.0, 0.40) * env_ramp(28, 31, 1.0, 0.85) * env_ramp(45, 49, 1.0, 0.0)
pad *= pad_env

# ---------------------------------------------------------------------------
# 3. Climax pad — open-fifth + octaves stack (A2 E3 A3 E4 A4 E5)
#     Big, uplifting reveal at the concept scene (~29-42s).
# ---------------------------------------------------------------------------
big_freqs = [110.0, 164.81, 220.0, 329.63, 440.0, 659.25]
big = sum(sine(f) for f in big_freqs) / len(big_freqs)
big = soft_clip(big, drive=1.1)
big_env = env_ramp(28, 32, 0.0, 0.50) * env_ramp(40, 43, 1.0, 0.30) * env_ramp(46, 49, 1.0, 0.0)
big *= big_env

# ---------------------------------------------------------------------------
# 4. Taiko-like low pulse — slow half-note hits, replaces the EDM kick
# ---------------------------------------------------------------------------
bpm = 96.0
beat = 60.0 / bpm  # 0.625s
half = beat * 2.0

def taiko_hit(amp=1.0, decay_s=0.45):
    n = int(decay_s * SR)
    env = np.exp(-np.linspace(0, 4, n))
    # Pitch sweep: 90 → 45 Hz (gives the punchy, hand-played taiko feel)
    sweep = np.linspace(90, 45, n)
    phase = 2 * np.pi * np.cumsum(sweep) / SR
    body = np.sin(phase)
    # subtle attack click
    click_n = int(0.012 * SR)
    click = np.random.normal(0, 1, click_n) * np.exp(-np.linspace(0, 8, click_n)) * 0.3
    out = body * env * amp
    out[:click_n] += click * amp
    return out

taiko = np.zeros(N)
# Half-note pulse from 6s → 42s
t_hit = 6.0
while t_hit < 42.0:
    # Vary intensity: louder at downbeats every 4 hits
    idx = int(round((t_hit - 6.0) / half))
    amp = 0.95 if idx % 4 == 0 else 0.55
    place(taiko, t_hit, taiko_hit(amp=amp))
    t_hit += half
# Final accent at 42s
place(taiko, 41.5, taiko_hit(amp=1.0, decay_s=1.5))
taiko *= env_ramp(6, 8, 0, 1) * env_ramp(40, 43, 1, 0)

# ---------------------------------------------------------------------------
# 5. Ostinato motif — A pentatonic minor melody on bell-like FM-ish synth
#     Repeats with slight variation for forward motion.
# ---------------------------------------------------------------------------
# Pattern in 8th notes (12 notes covering 6 beats at 96 BPM):
# A4 - C5 - D5 - E5 - D5 - C5 - E5 - G5 - A5 - G5 - E5 - C5
A4 = 440.0; C5 = 523.25; D5 = 587.33; E5 = 659.25; G5 = 783.99; A5 = 880.0
melody = [A4, C5, D5, E5, D5, C5, E5, G5, A5, G5, E5, C5]


def bell_note(freq, dur=0.55, amp=0.22):
    n = int(dur * SR)
    t = np.arange(n) / SR
    # FM-ish: carrier + small modulator gives metallic shimmer
    mod = np.sin(2 * np.pi * freq * 2.0 * t) * 0.5
    car = np.sin(2 * np.pi * freq * t + mod)
    # subtle 3rd partial
    car += 0.25 * np.sin(2 * np.pi * freq * 3 * t)
    env = np.exp(-np.linspace(0, 6, n))
    # add soft attack pluck
    attack = np.exp(-np.linspace(0, 80, n)) * 0.4
    return car * (env + attack) * amp


bell = np.zeros(N)
ostinato_start = 9.0
ostinato_end = 42.0
step = beat / 2.0  # 8th notes
t_step = ostinato_start
i = 0
while t_step < ostinato_end:
    f = melody[i % len(melody)]
    # Drop volume on the off-beats for groove
    amp = 0.22 if i % 2 == 0 else 0.16
    place(bell, t_step, bell_note(f, dur=0.6, amp=amp))
    i += 1
    t_step += step

bell *= env_ramp(9, 11, 0, 1) * env_ramp(20, 24, 1, 0.55) * env_ramp(28, 30, 0.55, 1.0) * env_ramp(40, 42, 1, 0)

# ---------------------------------------------------------------------------
# 6. Choir-like vowel pad — sine stack tuned to evoke ethereal female "ahh"
#     Comes in at the climax (~28-42s).
# ---------------------------------------------------------------------------
def choir(freq, dur=14.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    # Three slightly detuned voices + 2nd partial
    a = np.sin(2 * np.pi * freq * t)
    b = np.sin(2 * np.pi * freq * 1.005 * t)
    c = np.sin(2 * np.pi * freq * 0.995 * t)
    d = np.sin(2 * np.pi * freq * 2 * t) * 0.25
    voice = (a + b + c + d) / 3.5
    # gentle vibrato
    vib = 1 + 0.005 * np.sin(2 * np.pi * 5.5 * t)
    voice *= vib
    # ahh-shaped envelope
    env_attack = np.linspace(0, 1, int(2.0 * SR))
    env_release = np.linspace(1, 0, int(3.0 * SR))
    sustain_n = n - len(env_attack) - len(env_release)
    if sustain_n < 0:
        sustain_n = 0
    env = np.concatenate([env_attack, np.ones(sustain_n), env_release])[:n]
    return voice * env


choir_buf = np.zeros(N)
# Choir voices at A4, E5, G5 (top of Am9 cluster)
for f, amp in [(440.0, 0.18), (659.25, 0.13), (783.99, 0.10)]:
    voice = choir(f, dur=14.0) * amp
    place(choir_buf, 28.5, voice)
choir_buf *= env_ramp(28.5, 30, 0, 1) * env_ramp(42, 44, 1, 0)

# ---------------------------------------------------------------------------
# 7. Subtle breath swell at transitions (filtered, not noisy)
#     Use a slow LFO modulated tone instead of white noise.
# ---------------------------------------------------------------------------
def breath_pulse(freq=220.0, dur=2.5, amp=0.06):
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = 0.5 * (np.sin(2 * np.pi * freq * t) + np.sin(2 * np.pi * freq * 1.5 * t))
    # bell-like decay
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return tone * env * amp


breath_buf = np.zeros(N)
place(breath_buf, 4.5, breath_pulse(330.0, dur=2.0, amp=0.05))
place(breath_buf, 27.5, breath_pulse(440.0, dur=2.5, amp=0.07))
place(breath_buf, 41.0, breath_pulse(660.0, dur=3.0, amp=0.05))

# ---------------------------------------------------------------------------
# 8. Gentle tonic chime at intro and outro (single soft bell hits)
# ---------------------------------------------------------------------------
chime_buf = np.zeros(N)
place(chime_buf, 0.5, bell_note(440.0, dur=2.5, amp=0.30))
place(chime_buf, 1.4, bell_note(659.25, dur=2.5, amp=0.22))
place(chime_buf, 43.0, bell_note(440.0, dur=4.0, amp=0.30))
place(chime_buf, 44.0, bell_note(659.25, dur=4.0, amp=0.22))
place(chime_buf, 45.0, bell_note(880.0, dur=4.0, amp=0.18))

# ---------------------------------------------------------------------------
# Mix
# ---------------------------------------------------------------------------
mix = sub + pad + big + taiko + bell + choir_buf + breath_buf + chime_buf
mix = soft_clip(mix, drive=0.85)


# ---------------------------------------------------------------------------
# Stereo widen via Haas + light rotation per source
# ---------------------------------------------------------------------------
def shift(x, ms):
    d = int(ms * SR / 1000)
    out = np.zeros(N)
    if d == 0:
        return x.copy()
    if d > 0:
        out[d:] = x[:N - d]
    else:
        out[:N + d] = x[-d:]
    return out


# pad/choir slightly wider, bass center, bell slightly right
L = (sub
     + 0.95 * pad
     + 0.95 * big
     + taiko
     + shift(bell, -8) * 0.95
     + shift(choir_buf, -10) * 1.05
     + breath_buf
     + chime_buf)
R = (sub
     + 1.05 * shift(pad, 7) + 0.05 * pad
     + 1.05 * shift(big, 6)
     + taiko
     + shift(bell, 0) * 1.05
     + shift(choir_buf, 8) * 1.0
     + shift(breath_buf, 6)
     + chime_buf)


# ---------------------------------------------------------------------------
# Multi-tap "plate reverb" tail
# ---------------------------------------------------------------------------
def reverb(x, taps=((0.029, 0.45), (0.043, 0.36), (0.067, 0.30), (0.091, 0.24), (0.137, 0.18))):
    out = x.copy()
    for delay_s, gain in taps:
        d = int(delay_s * SR)
        tail = np.zeros(N)
        tail[d:] = x[:N - d] * gain
        out += tail
    return out * 0.55 + x * 0.7


L = reverb(L)
R = reverb(R)


# ---------------------------------------------------------------------------
# Final envelope, normalize, write WAV
# ---------------------------------------------------------------------------
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
if peak > 0:
    L = L / peak * 0.92
    R = R / peak * 0.92

fade = env_ramp(0, 0.05, 0, 1) * env_ramp(48.6, 49, 1, 0)
L *= fade
R *= fade

out_path = sys.argv[1] if len(sys.argv) > 1 else "track.wav"
with wave.open(out_path, "wb") as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    interleaved = np.empty(N * 2, dtype=np.int16)
    interleaved[0::2] = (L * 32767).astype(np.int16)
    interleaved[1::2] = (R * 32767).astype(np.int16)
    f.writeframes(interleaved.tobytes())

print(f"wrote {out_path} ({DUR:.1f}s, {os.path.getsize(out_path) // 1024} KB)")
