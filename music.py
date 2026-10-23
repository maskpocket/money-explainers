"""Generate a calm, modern background music loop (pads + soft pluck arpeggio + gentle pulse). Original, so no licensing."""
import math, random, struct, wave

SR = 22050
BPM = 84
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)


def make(path, bars=16):
    beat = 60.0 / BPM
    bar = beat * 4
    n = int(bar * bars * SR)
    buf = [0.0] * n
    rnd = random.Random(7)
    for b in range(bars):
        ch = CHORDS[b % 4]
        t0 = int(b * bar * SR)
        ln = int(bar * SR)
        for note in ch:                                   # warm pad
            f = hz(note)
            for i in range(ln):
                t = i / SR
                env = min(1, t / 0.6) * min(1, (bar - t) / 0.6)
                buf[t0 + i] += 0.07 * env * (math.sin(6.2832 * f * t) + 0.4 * math.sin(6.2832 * f * 2.003 * t))
        bf = hz(ch[0] - 12)                                # bass
        for i in range(ln):
            t = i / SR
            buf[t0 + i] += 0.12 * min(1, t / 0.2) * math.sin(6.2832 * bf * t) * min(1, (bar - t) / 0.3)
        for k in range(8):                                 # pluck arpeggio, eighth notes
            note = ch[k % 3] + 12 * (1 + (k % 4 == 3))
            f = hz(note); s0 = t0 + int(k * beat / 2 * SR)
            for i in range(int(0.5 * SR)):
                if s0 + i >= n: break
                t = i / SR
                buf[s0 + i] += 0.09 * math.exp(-6 * t) * math.sin(6.2832 * f * t)
        for k in range(4):                                 # soft kick
            s0 = t0 + int(k * beat * SR)
            for i in range(int(0.25 * SR)):
                if s0 + i >= n: break
                t = i / SR
                buf[s0 + i] += 0.22 * math.exp(-14 * t) * math.sin(6.2832 * (50 + 70 * math.exp(-30 * t)) * t)
    m = max(abs(x) for x in buf) or 1
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x / m * 0.9)) * 32767)) for x in buf))
