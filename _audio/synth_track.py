"""Procedural cinematic ambient track for Sync OS demo (~49s).

Design notes:
- Key: A minor. Drone-on-tonic with builds and resolution.
- Structure follows demo chapter timeline.
- Output: 48 kHz stereo WAV.
"""

import numpy as np
import wave
import struct
import sys
import os

SR = 48000
DUR = 49.0
N = int(SR * DUR)
T = np.arange(N) / SR


def env_adsr(start, attack, hold, release, peak=1.0):
    """Generate an envelope of length N over the time axis."""
    e = np.zeros(N)
    s = int(start * SR)
    a = int(attack * SR)
    h = int(hold * SR)
    r = int(release * SR)
    if s >= N:
        return e
    e[s:s + a] = np.linspace(0, peak, a, endpoint=False) if a > 0 else 0
    e[s + a:s + a + h] = peak
    e[s + a + h:s + a + h + r] = np.linspace(peak, 0, r, endpoint=False) if r > 0 else 0
    return e[:N]


def env_ramp(t0, t1, v0, v1):
    e = np.full(N, v0, dtype=np.float64)
    i0 = max(0, int(t0 * SR))
    i1 = min(N, int(t1 * SR))
    if i1 > i0:
        e[i0:i1] = np.linspace(v0, v1, i1 - i0)
    e[i1:] = v1
    return e


def sine(freq, phase=0.0):
    return np.sin(2 * np.pi * freq * T + phase)


def saw(freq):
    # Simple band-limited approximation via summed sines (first 5 harmonics)
    out = np.zeros(N)
    for k in range(1, 6):
        out += np.sin(2 * np.pi * freq * k * T) / k
    return out * 0.6


def soft_clip(x, drive=1.5):
    return np.tanh(x * drive)


# --- Sub bass: 55 Hz (A1) drone with slow tremolo
sub_lfo = 0.06 * np.sin(2 * np.pi * 0.15 * T)
sub = sine(55.0) * (0.8 + sub_lfo)
sub_env = env_ramp(0, 5, 0.0, 0.55) * env_ramp(40, 49, 1.0, 0.0)
sub *= sub_env

# --- Sub octave click for body
sub2 = sine(110.0) * 0.3 * env_ramp(8, 12, 0, 0.4) * env_ramp(43, 49, 1.0, 0.0)

# --- Pad: Am triad (A2, C3, E3) layered with slight detune
def pad_voice(f, det=0.0):
    return 0.5 * (sine(f * (1 + det)) + sine(f * (1 - det) * 0.5)) * 0.7

pad = (pad_voice(110.0, 0.003) + pad_voice(130.81, 0.0035) + pad_voice(164.81, 0.004)) / 3.0
# soft lowpass via cumulative average (cheap)
pad = (pad + np.roll(pad, 1) + np.roll(pad, 2)) / 3.0
pad_env = env_ramp(0, 6, 0.0, 0.45) * env_ramp(28, 30, 1.0, 0.85) * env_ramp(43, 49, 1.0, 0.0)
pad *= pad_env

# --- Big climax pad (full Am with octaves) at concept reveal
big = (sine(220.0) + sine(261.63) + sine(329.63) + sine(440.0) + sine(523.25)) / 5.0
big_env = env_ramp(28, 31, 0.0, 0.55) * env_ramp(40, 43, 1.0, 0.3) * env_ramp(46, 49, 1.0, 0.0)
big *= big_env

# --- Kick: short transient at quarter notes (110 BPM), starts at 8s
bpm = 110.0
beat = 60.0 / bpm  # 0.545s
kick = np.zeros(N)
kick_start = 8.0
kick_end = 42.0
t_beat = kick_start
while t_beat < kick_end:
    i = int(t_beat * SR)
    if i < N:
        # 60Hz transient with quick decay (~0.18s)
        dec = int(0.18 * SR)
        end = min(N, i + dec)
        env = np.exp(-np.linspace(0, 5, end - i))
        freq_sweep = np.linspace(120, 50, end - i)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / SR
        kick[i:end] += np.sin(phase) * env * 0.9
    t_beat += beat
kick *= env_ramp(8, 9, 0, 1) * env_ramp(20, 22, 1, 0.4) * env_ramp(28, 30, 0.4, 1.0) * env_ramp(40, 42, 1, 0)

# --- Arp shimmer (16th notes) cycling A5 C6 E6 A5
arp_notes = [880.0, 1046.5, 1318.5, 1760.0]
arp = np.zeros(N)
arp_start = 10.0
arp_end = 42.0
step = beat / 4.0  # 16th
i_step = 0
t_step = arp_start
while t_step < arp_end:
    f = arp_notes[i_step % len(arp_notes)]
    i = int(t_step * SR)
    dec = int(0.22 * SR)
    end = min(N, i + dec)
    env = np.exp(-np.linspace(0, 6, end - i))
    arp[i:end] += np.sin(2 * np.pi * f * (np.arange(end - i) / SR)) * env * 0.18
    i_step += 1
    t_step += step
arp *= env_ramp(10, 12, 0, 1) * env_ramp(20, 24, 1, 0.5) * env_ramp(28, 30, 0.5, 1.0) * env_ramp(40, 42, 1, 0)

# --- Filtered noise sweep (riser) at 23-29s and 40-43s
def noise_riser(t0, t1, level=0.25):
    n = np.zeros(N)
    i0 = int(t0 * SR); i1 = int(t1 * SR)
    if i1 > i0:
        white = np.random.normal(0, 1, i1 - i0)
        # cheap "lowpass that opens" via accumulated exponential smoothing
        # ramp the smoothing so it gets brighter
        ramp = np.linspace(0.95, 0.5, i1 - i0)
        out = np.zeros_like(white)
        prev = 0.0
        for k in range(len(white)):
            out[k] = ramp[k] * prev + (1 - ramp[k]) * white[k]
            prev = out[k]
        amp = np.linspace(0, level, i1 - i0)
        n[i0:i1] = out * amp
    return n

riser = noise_riser(23, 29, 0.30) + noise_riser(40, 43, 0.18)

# --- Soft white-noise air bed throughout
air = np.random.normal(0, 1, N)
# smooth
prev = 0.0
for k in range(0, N, 1):
    air[k] = 0.97 * prev + 0.03 * air[k]
    prev = air[k]
air *= 0.04 * env_ramp(0, 5, 0, 1) * env_ramp(45, 49, 1, 0)

# --- Mix
mix = sub + sub2 + pad + big + kick + arp + riser + air
# soft saturation
mix = soft_clip(mix, drive=0.9)

# --- Cheap stereo widen via Haas effect (different short delays per channel)
def stereo_widen(mono, delay_ms_l=0.0, delay_ms_r=12.0):
    dl = int(delay_ms_l * SR / 1000)
    dr = int(delay_ms_r * SR / 1000)
    L = np.zeros(N)
    R = np.zeros(N)
    L[dl:] = mono[:N - dl] if dl > 0 else mono
    R[dr:] = mono[:N - dr] if dr > 0 else mono
    return L, R

L_pad, R_pad = stereo_widen(pad + big + arp, 0, 14)
L_low, R_low = stereo_widen(sub + sub2 + kick, 0, 0)
L_air, R_air = stereo_widen(air + riser, 6, 0)

L = L_pad + L_low + L_air
R = R_pad + R_low + R_air

# --- Send to a simple plate-reverb-like delay tail (multi-tap echo)
def reverb(x, taps=((0.027, 0.5), (0.041, 0.4), (0.063, 0.35), (0.087, 0.28), (0.131, 0.22))):
    out = x.copy()
    for delay_s, gain in taps:
        d = int(delay_s * SR)
        tail = np.zeros(N)
        tail[d:] = x[:N - d] * gain
        out += tail
    return out * 0.55 + x * 0.7

L = reverb(L)
R = reverb(R)

# --- Normalize
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
if peak > 0:
    L = L / peak * 0.92
    R = R / peak * 0.92

# Final fade-out failsafe
fade = env_ramp(0, 0.05, 0, 1) * env_ramp(48.5, 49, 1, 0)
L *= fade
R *= fade

# --- Write WAV
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
