"""Sync OS demo soundtrack — synthwave / cyberpunk drive (~49s, A minor, 124 BPM).

Vibe target: Tron Legacy / Kavinsky / Carpenter Brut / Perturbator.
- Punchy 4/4 kick, sidechain-pumped bass + pad.
- Detuned saw bass groove on the root.
- Bright square-wave lead playing an A pentatonic-minor hook on the drop.
- Open hat 8th notes + closed hat 16th alternation for forward motion.
- Risers, snare rolls, and a real DROP at the climax of the demo (~28s).
- All synthesized — royalty-free.
"""

import numpy as np
import wave
import sys
import os

SR = 48000
DUR = 49.0
N = int(SR * DUR)
T = np.arange(N) / SR

BPM = 124.0
BEAT = 60.0 / BPM           # 0.4839 s
SIXT = BEAT / 4.0           # 16th note
EIGHT = BEAT / 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def env_ramp(t0, t1, v0, v1):
    e = np.full(N, v0, dtype=np.float64)
    i0 = max(0, int(t0 * SR))
    i1 = min(N, int(t1 * SR))
    if i1 > i0:
        e[i0:i1] = np.linspace(v0, v1, i1 - i0)
    e[i1:] = v1
    return e


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive)


def place(buffer, t_start, samples, gain=1.0):
    i = int(t_start * SR)
    if i >= N:
        return
    end = min(N, i + len(samples))
    buffer[i:end] += samples[:end - i] * gain


def saw(freq, t):
    """Band-limited saw via summed sines (8 partials)."""
    out = np.zeros_like(t)
    for k in range(1, 9):
        out += np.sin(2 * np.pi * freq * k * t) / k
    return out * (2.0 / np.pi)


def square(freq, t, partials=10):
    out = np.zeros_like(t)
    for k in range(1, partials, 2):
        out += np.sin(2 * np.pi * freq * k * t) / k
    return out * (4.0 / np.pi) * 0.5


def smooth_lp(x, alpha=0.15):
    """One-pole lowpass (in-place style)."""
    out = np.empty_like(x)
    prev = 0.0
    for i in range(len(x)):
        prev = (1 - alpha) * prev + alpha * x[i]
        out[i] = prev
    return out


# ---------------------------------------------------------------------------
# Drum hits
# ---------------------------------------------------------------------------
def kick(amp=1.0, dur=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    # Pitch sweep 160 → 50 Hz
    sweep = np.linspace(160, 50, n)
    phase = 2 * np.pi * np.cumsum(sweep) / SR
    body = np.sin(phase)
    env = np.exp(-np.linspace(0, 7, n))
    # transient click
    cl = int(0.005 * SR)
    click = np.random.normal(0, 1, cl) * np.exp(-np.linspace(0, 12, cl)) * 0.4
    out = body * env
    out[:cl] += click
    return soft_clip(out * amp, 1.4)


def snare(amp=1.0, dur=0.22):
    n = int(dur * SR)
    noise = np.random.normal(0, 1, n)
    # bandpass-ish: mix noise with one-pole hipass via subtraction
    smoothed = smooth_lp(noise, alpha=0.5)
    body = noise - smoothed * 0.7
    # tonal layer for snap
    t = np.arange(n) / SR
    snap = np.sin(2 * np.pi * 200 * t) * np.exp(-np.linspace(0, 30, n)) * 0.3
    env = np.exp(-np.linspace(0, 12, n))
    return (body * env + snap) * amp


def hat(amp=1.0, dur=0.06, open_hat=False):
    n = int(dur * SR)
    noise = np.random.normal(0, 1, n)
    smoothed = smooth_lp(noise, alpha=0.7)
    body = noise - smoothed * 0.85   # bright
    decay = 6 if not open_hat else 1.5
    env = np.exp(-np.linspace(0, decay, n))
    return body * env * amp


def clap(amp=1.0):
    """Stacked snare-like hits to mimic a clap."""
    out = np.zeros(int(0.18 * SR))
    for off_ms, g in [(0, 0.7), (12, 1.0), (26, 0.85)]:
        s = snare(amp=g, dur=0.12)
        i = int(off_ms / 1000 * SR)
        if i + len(s) <= len(out):
            out[i:i + len(s)] += s
    return out * amp


def riser(dur=4.0, amp=0.4):
    """Filtered noise sweep for build-ups (less harsh than v1)."""
    n = int(dur * SR)
    noise = np.random.normal(0, 1, n)
    # gradually opening filter
    out = np.zeros(n)
    prev = 0.0
    alphas = np.linspace(0.05, 0.6, n)
    for i in range(n):
        prev = (1 - alphas[i]) * prev + alphas[i] * noise[i]
        out[i] = prev
    # rising amplitude
    env = np.linspace(0, 1, n) ** 2
    return out * env * amp


# ---------------------------------------------------------------------------
# Drum buffer
# ---------------------------------------------------------------------------
drums = np.zeros(N)

KICK_START = 4.0
KICK_END = 42.0
SNARE_START = 8.0
SNARE_END = 42.0
HAT_START = 6.0
HAT_END = 42.0


# Pre-build sidechain envelope (1.0 normally, dips to 0.25 at each kick)
def make_sidechain(kick_times, attack=0.005, release=0.18):
    env = np.ones(N)
    rel_n = int(release * SR)
    for kt in kick_times:
        i = int(kt * SR)
        end = min(N, i + rel_n)
        # exponential rise from 0.25 to 1.0
        ramp = 0.25 + (1.0 - 0.25) * (1 - np.exp(-np.linspace(0, 5, end - i)))
        env[i:end] = np.minimum(env[i:end], ramp)
    return env


# Build kick hits
kick_times = []
t = KICK_START
while t < KICK_END:
    kick_times.append(t)
    t += BEAT
# DROP boost: extra kicks 28-40s already covered by 4/4 above

for i, kt in enumerate(kick_times):
    # Heavier on 1s during the drop
    after_drop = kt >= 28.0
    amp = 1.0 if not after_drop else 1.15
    place(drums, kt, kick(amp=amp))

# Snare on beats 2 & 4
for i, kt in enumerate(kick_times):
    if kt < SNARE_START:
        continue
    beat_idx = int(round((kt - KICK_START) / BEAT))
    if beat_idx % 2 == 1:  # off-beats
        place(drums, kt, snare(amp=0.55))

# Clap layered on beats 2 & 4 from drop
for kt in kick_times:
    if kt < 28.0 or kt >= 40.0:
        continue
    beat_idx = int(round((kt - KICK_START) / BEAT))
    if beat_idx % 2 == 1:
        place(drums, kt, clap(amp=0.5))

# Hi-hats: closed on every 16th, open on every 4th 16th, from 6s
t = HAT_START
i = 0
while t < HAT_END:
    is_open = (i % 4 == 2)  # syncopated open
    place(drums, t, hat(amp=0.18 if not is_open else 0.22, dur=0.08 if not is_open else 0.18, open_hat=is_open))
    t += SIXT
    i += 1

# Snare roll into the drop (24-28s)
roll_dur = 4.0
roll_steps = 32
for s in range(roll_steps):
    t_s = 24.0 + s * (roll_dur / roll_steps)
    amp = 0.15 + 0.55 * (s / roll_steps)
    place(drums, t_s, snare(amp=amp, dur=0.08))


# ---------------------------------------------------------------------------
# Bass: detuned saws, 16th-note groove on the root with octave jumps
# ---------------------------------------------------------------------------
def bass_note(freq, dur, amp=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    a = saw(freq * 1.003, t)
    b = saw(freq * 0.997, t)
    sub = np.sin(2 * np.pi * freq * 0.5 * t) * 0.6
    sig = (a + b) * 0.5 + sub
    # quick attack, short decay envelope per 16th
    env = np.exp(-np.linspace(0, 4.5, n))
    env[:int(0.005 * SR)] = np.linspace(0, 1, int(0.005 * SR))
    return soft_clip(sig * env * amp, 1.5)


# Pattern (16ths): root R + jumps to 8va & 5th for groove
# 16 steps per bar (4 beats × 4 sixteenths)
A1 = 55.0; A2 = 110.0; E2 = 82.41; G2 = 98.0
bass_pattern = [
    A1, A1, A2, A1,  E2, A1, A1, A2,
    A1, A1, A2, G2,  A1, E2, A1, A2,
]

bass = np.zeros(N)
BASS_START = 4.0
BASS_END = 42.0
t = BASS_START
i = 0
while t < BASS_END:
    f = bass_pattern[i % len(bass_pattern)]
    place(bass, t, bass_note(f, dur=SIXT * 1.3, amp=0.55))
    t += SIXT
    i += 1


# ---------------------------------------------------------------------------
# Pad: lush detuned saws on Am7 (A C E G)
# ---------------------------------------------------------------------------
def pad_voice_chord(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        out += saw(f * 1.004, t) * 0.5 + saw(f * 0.996, t) * 0.5
    out /= len(freqs)
    return out


pad_freqs = [220.0, 261.63, 329.63, 392.0]   # A3 C4 E4 G4
pad_long = pad_voice_chord(pad_freqs, DUR)
# soft-lowpass to tame
pad_long = smooth_lp(pad_long, alpha=0.18) * 1.5
pad_env = (env_ramp(0, 4, 0.0, 0.35) *
           env_ramp(28, 30, 1.0, 1.15) *
           env_ramp(40, 43, 1.0, 0.4) *
           env_ramp(46, 49, 1.0, 0.0))
pad = pad_long * pad_env


# ---------------------------------------------------------------------------
# Lead: square wave melody on A pentatonic-minor (drop section, 28-40s)
# Pattern: A4-E5-A5-G5-E5-A5-C5-A4 (...) repeated with variation
# ---------------------------------------------------------------------------
def lead_note(freq, dur, amp=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = square(freq, t, partials=12)
    # add a slight sub for body
    sig += np.sin(2 * np.pi * freq * 0.5 * t) * 0.2
    # quick AD envelope
    env = np.exp(-np.linspace(0, 5, n))
    a = int(0.008 * SR)
    env[:a] = np.linspace(0, 1, a)
    return soft_clip(sig * env * amp, 1.3)


A4 = 440.0; C5 = 523.25; D5 = 587.33; E5 = 659.25; G5 = 783.99; A5 = 880.0
lead_pattern_8 = [
    A4, E5, A5, G5,  E5, A5, C5, A4,
    A4, E5, A5, G5,  E5, G5, E5, C5,
]

lead = np.zeros(N)
LEAD_START = 28.0
LEAD_END = 40.0
t = LEAD_START
i = 0
while t < LEAD_END:
    f = lead_pattern_8[i % len(lead_pattern_8)]
    place(lead, t, lead_note(f, dur=EIGHT * 1.1, amp=0.30))
    t += EIGHT
    i += 1


# ---------------------------------------------------------------------------
# Pre-chorus arp (16th plucks) 12-24s
# ---------------------------------------------------------------------------
def pluck(freq, dur=0.18, amp=0.18):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.exp(-np.linspace(0, 8, n))
    return sig * env * amp


arp_seq = [A4, C5, E5, G5, A5, G5, E5, C5]
arp = np.zeros(N)
t = 12.0
i = 0
while t < 28.0:
    f = arp_seq[i % len(arp_seq)]
    place(arp, t, pluck(f, dur=0.20, amp=0.12))
    t += SIXT
    i += 1
arp_env = env_ramp(12, 14, 0, 1) * env_ramp(26, 28, 1, 0)
arp *= arp_env


# ---------------------------------------------------------------------------
# Risers / FX
# ---------------------------------------------------------------------------
fx = np.zeros(N)
place(fx, 24.0, riser(dur=4.0, amp=0.18))
# downward sweep at end of drop
def downsweep(dur=2.5, amp=0.15):
    n = int(dur * SR)
    t = np.arange(n) / SR
    freqs = np.linspace(2000, 200, n)
    phase = 2 * np.pi * np.cumsum(freqs) / SR
    sig = np.sin(phase) * np.linspace(1, 0, n) ** 2
    return sig * amp
place(fx, 39.5, downsweep(dur=2.5, amp=0.10))


# ---------------------------------------------------------------------------
# Sidechain ducking on pad and bass driven by kicks
# ---------------------------------------------------------------------------
sc_env = make_sidechain(kick_times, release=0.16)
sc_env_pad = 0.55 + 0.45 * sc_env   # pad ducks by ~45%
sc_env_bass = 0.70 + 0.30 * sc_env  # bass ducks lightly

pad_sc = pad * sc_env_pad
bass_sc = bass * sc_env_bass


# ---------------------------------------------------------------------------
# Energy gating per section
# ---------------------------------------------------------------------------
drum_gain = (env_ramp(0, 4, 0.0, 1.0)
             * env_ramp(28, 30, 1.0, 1.25)
             * env_ramp(40, 42, 1.0, 0.0))
drums *= drum_gain

bass_gain = (env_ramp(0, 4, 0, 1)
             * env_ramp(24, 27.5, 1, 0.4)   # drop the bass before the drop
             * env_ramp(27.5, 28.5, 0.4, 1.3)
             * env_ramp(40, 42, 1, 0))
bass_sc *= bass_gain

lead_gain = env_ramp(28, 28.3, 0, 1) * env_ramp(40, 41, 1, 0)
lead *= lead_gain


# ---------------------------------------------------------------------------
# Mix
# ---------------------------------------------------------------------------
mix = drums * 1.20 + bass_sc * 1.10 + pad_sc * 0.55 + lead * 1.10 + arp * 1.0 + fx * 1.0
# Light pre-saturation
mix = soft_clip(mix * 0.85, drive=1.0)


# ---------------------------------------------------------------------------
# Stereo widen
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


L = (drums * 1.0
     + bass_sc * 1.0
     + shift(pad_sc, -10) * 1.05
     + shift(lead, -6) * 1.0
     + shift(arp, -8) * 1.0
     + shift(fx, -4) * 1.0)
R = (drums * 1.0
     + bass_sc * 1.0
     + shift(pad_sc, 10) * 1.05
     + shift(lead, 6) * 1.0
     + shift(arp, 8) * 1.0
     + shift(fx, 4) * 1.0)


# ---------------------------------------------------------------------------
# Plate-style multi-tap reverb (subtle)
# ---------------------------------------------------------------------------
def reverb(x, taps=((0.027, 0.30), (0.041, 0.24), (0.063, 0.20), (0.097, 0.15))):
    out = x.copy()
    for delay_s, gain in taps:
        d = int(delay_s * SR)
        tail = np.zeros(N)
        tail[d:] = x[:N - d] * gain
        out += tail
    return out * 0.55 + x * 0.75


L = reverb(L)
R = reverb(R)


# ---------------------------------------------------------------------------
# Finalize — soft brick-wall limiter for perceived loudness
# ---------------------------------------------------------------------------
def limit(x, ceiling=0.94, threshold=0.78, knee=0.06):
    """Soft compressor + final ceiling for loudness without harsh clipping."""
    abs_x = np.abs(x)
    over = abs_x - threshold
    over = np.where(over > 0, over, 0)
    # smooth knee compression
    gain_red = 1 - np.tanh(over / knee) * 0.6
    y = x * gain_red
    # final hard limit
    y = np.clip(y, -ceiling, ceiling)
    return y


L = limit(L)
R = limit(R)

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
