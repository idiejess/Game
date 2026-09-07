#!/usr/bin/env python3
"""Procedural audio candidates for Halfway Lock (see docs/AUDIO_BIBLE.md).

Everything is synthesized from oscillators, filtered noise, envelopes and simple effects with a
fixed seed, so the output is deterministic and original. Writes 44.1 kHz 16-bit WAV (mono SFX,
stereo music) to assets/audio/ with the final filenames from assets/audio_manifest.csv, plus
reports/assets/audio_validation.json (duration, peak, RMS, clipping, silence, loop seam).

All output is a *candidate* requiring human listening review; nothing here is marked approved.

Usage: python3 tools/build_audio.py [--only sfx|music] [--seed 9]
"""
import argparse
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "audio"
SR = 44100


# ------------------------------------------------------------------------------------------ primitives
def t(seconds):
    return np.arange(int(SR * seconds)) / SR


def sine(freq, seconds, phase=0.0):
    return np.sin(2 * math.pi * freq * t(seconds) + phase)


def saw(freq, seconds):
    x = (t(seconds) * freq) % 1.0
    return 2 * x - 1


def tri(freq, seconds):
    return 2 * np.abs(saw(freq, seconds)) - 1


def noise(seconds, rng):
    return rng.uniform(-1, 1, int(SR * seconds))


def env(seconds, a=0.005, d=0.1, s=0.0, r=0.05, hold=None):
    n = int(SR * seconds)
    out = np.zeros(n)
    ia, idd, ir = int(SR * a), int(SR * d), int(SR * r)
    # Clamp segments that exceed the buffer (decay longer than the clip): decay runs to the end.
    ia = min(ia, n)
    idd = min(idd, n - ia)
    ir = min(ir, n - ia - idd)
    hold = n - ia - idd - ir if hold is None else int(SR * hold)
    hold = max(0, min(hold, n - ia - idd - ir))
    i = 0
    out[i:i + ia] = np.linspace(0, 1, ia, endpoint=False)
    i += ia
    out[i:i + idd] = np.linspace(1, s, idd, endpoint=False)
    i += idd
    out[i:i + hold] = s
    i += hold
    tail = min(ir, n - i)
    if tail > 0:
        out[i:i + tail] = np.linspace(s, 0, tail)
    return out[:n]


def _fft_filter(x, response):
    n = len(x)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    return np.fft.irfft(spec * response(freqs), n)


def lowpass_fast(x, cutoff):
    # 2-pole Butterworth magnitude response applied in the frequency domain (zero-phase).
    return _fft_filter(x, lambda f: 1.0 / np.sqrt(1.0 + (f / cutoff) ** 4))


lowpass = lowpass_fast


def highpass(x, cutoff):
    return _fft_filter(x, lambda f: (f / cutoff) ** 2 / np.sqrt(1.0 + (f / cutoff) ** 4))


def bandpass(x, lo, hi):
    return highpass(lowpass_fast(x, hi), lo)


def delay(x, seconds, feedback=0.3, mix=0.3):
    n = int(SR * seconds)
    y = x.copy()
    buf = np.zeros(len(x))
    acc = x.copy()
    for _ in range(6):
        acc = np.concatenate([np.zeros(n), acc[:-n]]) * feedback if n < len(acc) else np.zeros(len(x))
        buf += acc
    return (1 - mix) * y + mix * buf


def reverb(x, seconds=0.8, mix=0.25, rng=None):
    rng = rng or np.random.default_rng(3)
    n = int(SR * seconds)
    ir = rng.uniform(-1, 1, n) * np.exp(-np.linspace(0, 8, n))
    size = len(x) + n
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)] / (np.abs(ir).sum() ** 0.5 + 1e-9)
    wet = wet / (np.abs(wet).max() + 1e-9) * (np.abs(x).max() + 1e-9)
    return (1 - mix) * x + mix * wet


def pitch_env(f0, f1, seconds, curve=1.0):
    tt = t(seconds)
    p = (tt / seconds) ** curve
    f = f0 + (f1 - f0) * p
    phase = np.cumsum(2 * math.pi * f / SR)
    return np.sin(phase)


def normalize(x, peak=0.7):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def fade(x, ms_in=3, ms_out=10):
    n_in, n_out = int(SR * ms_in / 1000), int(SR * ms_out / 1000)
    x = x.copy()
    x[:n_in] *= np.linspace(0, 1, n_in)
    x[-n_out:] *= np.linspace(1, 0, n_out)
    return x


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive) / math.tanh(drive)


def write(name, x, stereo=False, ogg=False):
    """WAV for short cues. Music is transcoded to OGG Vorbis (q5) with ffmpeg when available and the
    WAV removed, keeping the repository and exported builds small."""
    x = np.clip(x, -1, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.wav"
    pcm = (x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        if stereo:
            pcm = np.column_stack([pcm, pcm]).reshape(-1)
        w.writeframes(pcm.tobytes())
    if ogg and shutil.which("ffmpeg"):
        oggp = OUT / f"{name}.ogg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-c:a", "libvorbis", "-q:a", "5", str(oggp)], check=True)
        path.unlink()
        return oggp
    return path


# ------------------------------------------------------------------------------------------ SFX
def build_sfx(rng):
    out = {}
    # paper slide
    x = bandpass(noise(0.14, rng), 900, 5000) * env(0.14, 0.01, 0.1, 0.2, 0.03)
    out["sfx_card_drag"] = normalize(fade(x), 0.35)
    for i in range(1, 4):  # variations
        x = bandpass(noise(0.12 + i * 0.01, rng), 800 + i * 150, 4500) * env(0.12 + i * 0.01, 0.008, 0.09, 0.2, 0.03)
        out[f"sfx_card_drag_v{i}"] = normalize(fade(x), 0.33)
    # tilt tick (passing threshold): small wooden click
    x = pitch_env(1800, 900, 0.05, 2) * env(0.05, 0.001, 0.04, 0, 0.01)
    out["sfx_card_tilt"] = normalize(fade(x), 0.4)
    # snap back: short rubbery thunk
    x = pitch_env(260, 140, 0.16, 1.5) * env(0.16, 0.002, 0.12, 0.0, 0.03) + bandpass(noise(0.16, rng), 300, 1200) * env(0.16, 0.001, 0.05) * 0.4
    out["sfx_card_snap"] = normalize(fade(x), 0.5)
    # commit: paper slap + wooden gate thud + faint chain
    slap = bandpass(noise(0.3, rng), 400, 3000) * env(0.3, 0.001, 0.06, 0.0, 0.02)
    thud = pitch_env(140, 60, 0.3, 1.2) * env(0.3, 0.001, 0.22, 0.0, 0.05)
    chain = bandpass(noise(0.3, rng), 2500, 7000) * env(0.3, 0.05, 0.2, 0.1, 0.05) * 0.3
    out["sfx_card_commit"] = normalize(fade(reverb(slap * 0.6 + thud + chain, 0.4, 0.15, rng)), 0.7)
    for i in range(1, 3):
        thud = pitch_env(150 - i * 8, 62, 0.3, 1.2) * env(0.3, 0.001, 0.22, 0.0, 0.05)
        out[f"sfx_card_commit_v{i}"] = normalize(fade(reverb(slap * 0.6 + thud + chain, 0.4, 0.15, rng)), 0.68)
    # UI navigation / confirm: brass ticks
    out["sfx_ui_nav"] = normalize(fade(sine(1320, 0.05) * env(0.05, 0.001, 0.04)), 0.3)
    x = sine(880, 0.16) * env(0.16, 0.002, 0.14) + sine(1320, 0.16) * env(0.16, 0.03, 0.12) * 0.5
    out["sfx_ui_confirm"] = normalize(fade(x), 0.4)
    # resource up / down: two-note bell-ish
    up = sine(523, 0.28) * env(0.28, 0.002, 0.25) * 0.6 + np.concatenate([np.zeros(int(SR * 0.08)), sine(659, 0.2) * env(0.2, 0.002, 0.18)])[:int(SR * 0.28)]
    dn = sine(659, 0.28) * env(0.28, 0.002, 0.25) * 0.6 + np.concatenate([np.zeros(int(SR * 0.08)), sine(494, 0.2) * env(0.2, 0.002, 0.18)])[:int(SR * 0.28)]
    out["sfx_res_up"] = normalize(fade(up), 0.45)
    out["sfx_res_down"] = normalize(fade(dn), 0.45)
    # resource danger: low harmonium pulse with beating
    x = (sine(196, 0.7) + sine(198.5, 0.7) * 0.8 + sine(392, 0.7) * 0.3) * env(0.7, 0.02, 0.5, 0.3, 0.15)
    out["sfx_res_danger"] = normalize(fade(soft_clip(x, 1.2)), 0.5)
    # general warning: struck iron bar
    x = (sine(1046, 0.6) + sine(2093 * 1.01, 0.6) * 0.4 + sine(3100, 0.6) * 0.2) * env(0.6, 0.001, 0.5, 0.0, 0.08)
    out["sfx_warning"] = normalize(fade(reverb(x, 0.6, 0.2, rng)), 0.55)
    # unlock: three rising bell partials
    parts = []
    for i, f in enumerate([784, 1046, 1318]):
        seg = np.zeros(int(SR * 0.9))
        st = int(SR * 0.12 * i)
        b = (sine(f, 0.9 - 0.12 * i) + sine(f * 2.76, 0.9 - 0.12 * i) * 0.25) * env(0.9 - 0.12 * i, 0.001, 0.7, 0.0, 0.05)
        seg[st:st + len(b)] = b
        parts.append(seg)
    out["sfx_unlock"] = normalize(fade(reverb(sum(parts), 0.8, 0.25, rng)), 0.55)
    # revelation: slow swell + high shimmer
    x = (sine(220, 1.6) * 0.5 + sine(330, 1.6) * 0.3 + sine(440, 1.6) * 0.2) * env(1.6, 0.6, 0.6, 0.4, 0.4)
    x += bandpass(noise(1.6, rng), 4000, 9000) * env(1.6, 0.8, 0.5, 0.0, 0.3) * 0.15
    out["sfx_revelation"] = normalize(fade(reverb(x, 1.2, 0.3, rng), 20, 200), 0.5)
    # death: bell + descending drone
    bell = (sine(392, 1.6) + sine(392 * 2.4, 1.6) * 0.3 + sine(392 * 4.1, 1.6) * 0.1) * env(1.6, 0.001, 1.4, 0.0, 0.2)
    drone = pitch_env(98, 62, 1.6, 0.8) * env(1.6, 0.05, 1.2, 0.2, 0.3)
    out["sfx_death"] = normalize(fade(reverb(bell * 0.7 + drone, 1.5, 0.35, rng), 5, 300), 0.6)
    # success stinger: plucked bass + bell
    x = pitch_env(196, 190, 1.0, 1) * env(1.0, 0.002, 0.7, 0.0, 0.2) * 0.6 + (sine(1046, 1.0) + sine(1046 * 2.7, 1.0) * 0.2) * env(1.0, 0.001, 0.9, 0.0, 0.1) * 0.5
    out["sfx_success"] = normalize(fade(reverb(x, 0.9, 0.25, rng), 3, 200), 0.55)
    # telegram: key clicks in a rhythm
    clicks = np.zeros(int(SR * 0.5))
    for i, st in enumerate([0.0, 0.07, 0.14, 0.26, 0.33]):
        c = bandpass(noise(0.03, rng), 1500, 5000) * env(0.03, 0.001, 0.025)
        s0 = int(SR * st)
        clicks[s0:s0 + len(c)] += c
    out["sfx_telegram"] = normalize(fade(clicks), 0.4)
    # mechanical click / ratchet
    x = bandpass(noise(0.04, rng), 2000, 8000) * env(0.04, 0.001, 0.03)
    out["sfx_mech_click"] = normalize(fade(x), 0.4)
    # lock gate movement: slow groan + rumble
    x = pitch_env(70, 55, 1.4, 1) * env(1.4, 0.3, 0.6, 0.6, 0.4) * 0.6 + lowpass_fast(noise(1.4, rng), 220) * env(1.4, 0.2, 0.8, 0.5, 0.3) * 1.2
    x += bandpass(noise(1.4, rng), 600, 1400) * (0.5 + 0.5 * sine(7, 1.4)) * env(1.4, 0.2, 0.9, 0.3, 0.3) * 0.25
    out["sfx_gate_move"] = normalize(fade(soft_clip(x, 1.5), 20, 200), 0.6)
    # chain tension: metallic rattle
    rat = np.zeros(int(SR * 0.8))
    for k in range(14):
        c = (sine(2200 + rng.uniform(-300, 300), 0.06) + sine(4100, 0.06) * 0.4) * env(0.06, 0.001, 0.05)
        s0 = int(SR * (k * 0.05 + rng.uniform(0, 0.01)))
        rat[s0:s0 + len(c)] += c * (0.5 + 0.5 * rng.uniform())
    out["sfx_chain"] = normalize(fade(reverb(rat, 0.5, 0.2, rng)), 0.45)
    # water movement (loopable 3 s)
    w = lowpass_fast(noise(3.0, rng), 900) * (0.7 + 0.3 * sine(0.5, 3.0)) + bandpass(noise(3.0, rng), 1200, 3000) * 0.2 * (0.5 + 0.5 * sine(1.3, 3.0, 1.0))
    w = crossfade_loop(w, 0.25)
    out["sfx_water_loop"] = normalize(w, 0.35)
    out["sfx_water_drift"] = normalize(fade(bandpass(noise(0.25, rng), 800, 3000) * env(0.25, 0.02, 0.2), 5, 60), 0.3)
    # wood impact / metal impact
    out["sfx_wood_impact"] = normalize(fade(pitch_env(320, 120, 0.22, 1.5) * env(0.22, 0.001, 0.18) + bandpass(noise(0.22, rng), 300, 2000) * env(0.22, 0.001, 0.05) * 0.5), 0.6)
    out["sfx_metal_impact"] = normalize(fade(reverb((sine(1650, 0.7) + sine(2410, 0.7) * 0.6 + sine(3990, 0.7) * 0.3) * env(0.7, 0.001, 0.6), 0.5, 0.2, rng)), 0.55)
    # bell (single tubular)
    out["sfx_bell"] = normalize(fade(reverb((sine(587, 2.2) + sine(587 * 2.0, 2.2) * 0.5 + sine(587 * 2.9, 2.2) * 0.3 + sine(587 * 4.2, 2.2) * 0.1) * env(2.2, 0.001, 2.0, 0.0, 0.2), 1.5, 0.3, rng), 3, 300), 0.55)
    out["sfx_save"] = normalize(fade(sine(660, 0.25) * env(0.25, 0.002, 0.2) + np.concatenate([np.zeros(int(SR * 0.1)), sine(990, 0.15) * env(0.15, 0.002, 0.13)])), 0.35)
    return out


def crossfade_loop(x, seconds):
    n = int(SR * seconds)
    head, tail = x[:n].copy(), x[-n:].copy()
    ramp = np.linspace(0, 1, n)
    x = x[:-n].copy()
    x[:n] = head * ramp + tail * (1 - ramp)
    return x


# ------------------------------------------------------------------------------------------ music
def harmonium(freqs, seconds, breath_period=6.0, detune=0.6):
    x = np.zeros(int(SR * seconds))
    for f in freqs:
        x += sine(f, seconds) + sine(f * (1 + detune / 1000), seconds) * 0.6 + sine(f * 2, seconds) * 0.15 + sine(f * 3, seconds) * 0.05
    breath = 0.65 + 0.35 * np.sin(2 * math.pi * t(seconds) / breath_period)
    return x * breath / max(1, len(freqs))


def pluck(freq, seconds, bright=0.5):
    x = tri(freq, seconds) * (1 - bright) + saw(freq, seconds) * bright
    return lowpass_fast(x, 1200) * env(seconds, 0.003, seconds * 0.8, 0.0, seconds * 0.15)


def fiddle(freq, seconds, vib=5.5, depth=0.006):
    tt = t(seconds)
    f = freq * (1 + depth * np.sin(2 * math.pi * vib * tt))
    phase = np.cumsum(2 * math.pi * f / SR)
    x = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase) + 0.12 * np.sin(4 * phase)
    return lowpass_fast(x, 2500) * env(seconds, 0.12, 0.1, 0.8, 0.25)


def bell(freq, seconds):
    return (sine(freq, seconds) + sine(freq * 2.0, seconds) * 0.5 + sine(freq * 2.9, seconds) * 0.3 + sine(freq * 4.2, seconds) * 0.1) * env(seconds, 0.001, seconds * 0.9, 0.0, seconds * 0.05)


def place(canvas, x, at):
    s0 = max(0, int(SR * at))
    n = min(len(x), len(canvas) - s0)
    if n > 0:
        canvas[s0:s0 + n] += x[:n]


# D minor with raised sixth (Dorian): "The River" motif. Tonal centre D (146.83 Hz).
D, E, F, G, A, B, C = 146.83, 164.81, 174.61, 196.0, 220.0, 246.94, 261.63
RIVER = [(D, 1.5), (F, 0.5), (G, 1.0), (A, 1.5), (B, 0.5), (A, 1.0), (G, 1.0), (F, 1.0), (D, 2.0)]


def music_title(rng):
    seconds = 48.0  # loop
    x = harmonium([D / 2, A / 2, D], seconds, 6.0) * 0.5
    x += harmonium([F, A], seconds, 9.0) * 0.18
    drips = np.zeros(len(x))
    for k in range(18):
        at = rng.uniform(0.5, seconds - 1)
        place(drips, pitch_env(rng.uniform(1800, 2600), 900, 0.18, 2) * env(0.18, 0.001, 0.15) * 0.25, at)
    x += drips
    # fragment of The River on fiddle, once, quietly
    at = 20.0
    for f, d in RIVER[:5]:
        place(x, fiddle(f * 2, d * 1.2) * 0.12, at)
        at += d * 1.2
    x = reverb(x, 1.6, 0.35, rng)
    x = crossfade_loop(x, 3.0)
    return normalize(x, 0.5)


def music_ambient(rng):
    seconds = 96.0
    x = harmonium([D / 2, A / 2], seconds, 6.0) * 0.4
    x += harmonium([D, F], seconds, 7.5) * 0.12
    water = lowpass_fast(noise(seconds, rng), 500) * (0.6 + 0.4 * sine(0.17, seconds)) * 0.12
    x += water
    gear = np.zeros(len(x))
    beat = 60 / 52.0  # slow mechanical pulse
    for k in range(int(seconds / beat)):
        if rng.uniform() < 0.55:
            place(gear, bandpass(noise(0.03, rng), 1800, 6000) * env(0.03, 0.001, 0.025) * 0.18, k * beat + rng.uniform(-0.01, 0.01))
    x += gear
    for k in range(10):
        place(x, pitch_env(rng.uniform(1600, 2400), 800, 0.2, 2) * env(0.2, 0.001, 0.17) * 0.18, rng.uniform(1, seconds - 1))
    x = reverb(x, 1.8, 0.3, rng)
    x = crossfade_loop(x, 4.0)
    return normalize(x, 0.45)


def music_crisis(rng):
    bpm = 120
    beat = 60 / bpm
    bars = 16
    seconds = bars * 4 * beat
    x = np.zeros(int(SR * seconds))
    for k in range(bars * 4):
        at = k * beat
        f = [D, D, F, D][k % 4]
        place(x, harmonium([f, f * 1.5], beat * 0.9, 100.0) * env(beat * 0.9, 0.01, beat * 0.5, 0.3, beat * 0.2) * 0.5, at)
        if k % 2 == 0:
            place(x, pluck(D / 2, beat * 0.8, 0.6) * 0.5, at)
        if k % 16 == 0:
            place(x, bell(A * 2, 3.0) * 0.5, at)
        place(x, bandpass(noise(0.05, rng), 1200, 5000) * env(0.05, 0.001, 0.04) * 0.3, at + beat * 0.5)
    x = reverb(x, 0.9, 0.2, rng)
    x = crossfade_loop(x, beat)
    return normalize(soft_clip(x, 1.1), 0.55)


def music_ending_fail(rng):
    seconds = 12.0
    x = np.zeros(int(SR * seconds))
    place(x, bell(D * 2, 6.0) * 0.6, 0.0)
    place(x, bell(A, 7.0) * 0.4, 1.5)
    drone = harmonium([D / 2, F / 2], 10.0, 5.0) * env(10.0, 0.5, 6.0, 0.2, 3.0) * 0.5
    place(x, drone, 0.5)
    x = reverb(x, 2.5, 0.4, rng)
    return normalize(fade(x, 5, 1500), 0.5)


def music_ending_true(rng):
    seconds = 40.0
    x = np.zeros(int(SR * seconds))
    at = 1.0
    for rep in range(2):
        for f, d in RIVER:
            place(x, fiddle(f * 2, d * 1.4) * 0.5, at)
            at += d * 1.4
        at += 1.0
    pad = harmonium([D / 2, A / 2, D], seconds, 8.0) * env(seconds, 4.0, 10.0, 0.6, 10.0) * 0.25
    x += pad
    place(x, bell(D * 2, 8.0) * 0.4, seconds - 9.0)
    x = reverb(x, 2.2, 0.35, rng)
    return normalize(fade(x, 20, 3000), 0.5)


def music_ending_ordinary(rng):
    seconds = 20.0
    x = np.zeros(int(SR * seconds))
    for i, f in enumerate([D, F, A, D * 2, A, F, D]):
        place(x, pluck(f, 2.2, 0.35) * 0.5, 0.5 + i * 1.6)
    pad = harmonium([D / 2, A / 2], seconds, 6.0) * env(seconds, 2.0, 6.0, 0.5, 6.0) * 0.3
    x += pad
    place(x, bell(A * 2, 6.0) * 0.35, 13.0)
    x = reverb(x, 2.0, 0.3, rng)
    return normalize(fade(x, 10, 2000), 0.5)


# ------------------------------------------------------------------------------------------ validation
def analyse(path):
    if path.suffix == ".ogg":
        tmp = path.with_suffix(".check.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), str(tmp)], check=True)
        rep = analyse(tmp)
        tmp.unlink()
        rep["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        rep["container"] = "ogg"
        return rep
    with wave.open(str(path), "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32768
    if ch == 2:
        data = data.reshape(-1, 2).mean(axis=1)
    peak = float(np.abs(data).max()) if len(data) else 0.0
    rms = float(np.sqrt(np.mean(data ** 2))) if len(data) else 0.0
    clipped = int((np.abs(data) >= 0.999).sum())
    silent = bool(peak < 0.001)
    seam = None
    if n > SR:
        # Loop seam: RMS mismatch between the last and first 100 ms; small means a clean loop.
        a, b = data[-int(SR * 0.1):], data[:int(SR * 0.1)]
        seam = float(abs(np.sqrt(np.mean(a ** 2)) - np.sqrt(np.mean(b ** 2))))
    return {"channels": ch, "sample_rate": sr, "bits": sw * 8, "duration_s": round(n / sr, 3), "peak": round(peak, 3),
            "rms_db": round(20 * math.log10(rms + 1e-9), 1), "clipped_samples": clipped, "silent": silent,
            "loop_seam_delta": None if seam is None else round(seam, 4),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--seed", type=int, default=9)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    written = []
    if args.only in (None, "sfx"):
        for name, x in build_sfx(rng).items():
            written.append(write(name, x))
        print("sfx:", len(written))
    if args.only in (None, "music"):
        for name, fn in {"mus_title": music_title, "mus_ambient": music_ambient, "mus_crisis": music_crisis,
                         "mus_ending_fail": music_ending_fail, "mus_ending_true": music_ending_true,
                         "mus_ending_ordinary": music_ending_ordinary}.items():
            written.append(write(name, fn(rng), stereo=True, ogg=True))
            print("music:", name)
    report = {str(p.relative_to(ROOT)): analyse(p) for p in sorted(list(OUT.glob("*.wav")) + list(OUT.glob("*.ogg")))}
    problems = [k for k, v in report.items() if v["clipped_samples"] > 0 or v["silent"] or v["peak"] > 0.95]
    dup = {}
    for k, v in report.items():
        dup.setdefault(v["sha256"], []).append(k)
    duplicates = [v for v in dup.values() if len(v) > 1]
    out = ROOT / "reports" / "assets" / "audio_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"files": report, "problems": problems, "duplicates": duplicates, "note": "All files are procedural candidates requiring human listening review."}, indent=1) + "\n")
    print(f"validated {len(report)} files; problems: {problems}; duplicate groups: {len(duplicates)}")


if __name__ == "__main__":
    main()
