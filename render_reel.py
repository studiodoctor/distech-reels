#!/usr/bin/env python3
import json, subprocess, sys, math, wave, struct, random, os, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
# Distech brand: black + orange #f2904b
BG, FG, ACCENT, MUTED = (0, 0, 0), (255, 255, 255), (242, 144, 75), (170, 170, 176)
FD = "/usr/share/fonts/truetype/google-fonts/"
def font(name, size):
    try: return ImageFont.truetype(FD + name, size)
    except OSError: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
F_HOOK, F_TITLE = font("Poppins-Bold.ttf", 96), font("Poppins-Bold.ttf", 78)
F_BODY, F_SM = font("Poppins-Medium.ttf", 52), font("Poppins-SemiBold.ttf", 40)

def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3

def wrap(draw, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

def block(img, lines, f, y, color, prog, lh, x=90):
    for i, ln in enumerate(lines):
        p = ease(prog * (len(lines) + 1) - i * 0.8)
        if p <= 0: continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((x, y + i * lh + (1 - p) * 50), ln, font=f, fill=color + (int(255 * p),))
        img.alpha_composite(layer)

def chrome(img, d, t, dur, idx, total, handle):
    d.rectangle([0, 0, W, 10], fill=(35, 35, 40))
    d.rectangle([0, 0, W * (idx + t / dur) / total, 10], fill=ACCENT)
    d.text((90, 110), "DISTECH", font=F_SM, fill=ACCENT)
    d.text((90 + d.textlength("DISTECH ", font=F_SM), 110), "TECHNOLOGIES", font=F_SM, fill=FG)
    d.text((90, H - 140), handle, font=F_SM, fill=MUTED)

def make_audio(path, total, starts, sr=44100):
    """Original upbeat synth bed (no external assets): chord pad + bass + kick/hat + a pop at each scene start."""
    n = int(total * sr); buf = [0.0] * n
    bpm = 100; beat = 60 / bpm
    chords = [(220.00, 261.63, 329.63), (174.61, 220.00, 261.63), (261.63, 329.63, 392.00), (196.00, 246.94, 293.66)]
    bass = [110.00, 87.31, 130.81, 98.00]
    rnd = random.Random(7)
    for i in range(n):
        t = i / sr
        bar = int(t / (beat * 4)) % 4
        bt = (t % beat) / beat
        v = 0.0
        for f in chords[bar]:                       # soft pad
            v += 0.05 * math.sin(2 * math.pi * f * t) + 0.025 * math.sin(2 * math.pi * f * 2.005 * t)
        v += 0.16 * math.sin(2 * math.pi * bass[bar] * t) * (0.6 + 0.4 * (1 - bt))   # bass pulse
        env = math.exp(-bt * 9)
        v += 0.30 * math.sin(2 * math.pi * (50 + 90 * env) * t) * env                # kick on every beat
        hb = ((t % (beat / 2)) / (beat / 2))
        v += 0.05 * (rnd.random() * 2 - 1) * math.exp(-hb * 18)                      # hat on 8ths
        buf[i] = v
    for s in starts:                                  # pop/whoosh at each scene change
        a = int(s * sr)
        for k in range(int(0.35 * sr)):
            if a + k < n:
                e = math.exp(-k / (0.08 * sr))
                buf[a + k] += 0.22 * e * math.sin(2 * math.pi * (400 + 1400 * (k / (0.35 * sr))) * (k / sr))
    fade = int(0.8 * sr)
    for i in range(n):                                # fade in/out, normalise
        g = min(1, i / fade, (n - i) / fade)
        buf[i] *= g
    peak = max(abs(x) for x in buf) or 1
    scale = 0.7 / peak
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x * scale)) * 32767)) for x in buf))

def render(spec, out):
    S = [("hook", spec["hook"], None, 3.2)]
    for i, s in enumerate(spec["slides"], 1): S.append(("slide", s["title"], s["body"], 3.6, i))
    S.append(("cta", spec["cta"], None, 3.4))
    total = len(S); handle = spec.get("handle", "distech.co.za")
    starts, acc = [], 0.0
    for sc in S: starts.append(acc); acc += sc[3]
    wav = os.path.join(tempfile.gettempdir(), "reel_audio.wav")
    make_audio(wav, acc, starts)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
        "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    for idx, sc in enumerate(S):
        kind, dur = sc[0], sc[3]
        for fr in range(int(dur * FPS)):
            t = fr / FPS; p = min(1, t / 1.1)
            img = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(img)
            gx = int(W * 0.5 + 300 * math.sin((idx * dur + t) / 2.5))
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse([gx - 450, 1100, gx + 450, 2000], fill=ACCENT + (45,))
            img.alpha_composite(glow)
            chrome(img, d, t, dur, idx, total, handle)
            if kind == "hook":
                block(img, wrap(probe, sc[1], F_HOOK, W - 180), F_HOOK, 560, FG, p, 120)
            elif kind == "slide":
                d.text((90, 520), f"0{sc[4]}", font=F_HOOK, fill=ACCENT)
                L = wrap(probe, sc[1], F_TITLE, W - 180)
                block(img, L, F_TITLE, 680, FG, p, 100)
                block(img, wrap(probe, sc[2], F_BODY, W - 180), F_BODY, 680 + len(L) * 100 + 50, MUTED, max(0, (t - 0.4) / 1.1), 76)
            else:
                L = wrap(probe, sc[1], F_HOOK, W - 180)
                block(img, L, F_HOOK, 600, FG, p, 120)
                by = 600 + len(L) * 120 + 70
                d.rounded_rectangle([90, by, 650, by + 120], 60, fill=ACCENT)
                d.text((130, by + 30), "distech.co.za", font=F_BODY, fill=(0, 0, 0))
            ff.stdin.write(img.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
