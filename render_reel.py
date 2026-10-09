#!/usr/bin/env python3
"""Distech daily reel renderer (v2).

usage: python3 render_reel.py spec.json out.mp4 [--date YYYY-MM-DD]

Every date gets a different look AND a different original soundtrack (key, scale, tempo,
chord progression, lead instrument, rhythm), chosen deterministically from the date so the
same style/track never repeats on consecutive days. Frame 0 is a fully-formed cover (hook
text visible, brand colours) so Instagram/Facebook/LinkedIn thumbnails are never black; a
cover JPG is also written next to the mp4 (<out>_cover.jpg).
Brand: black #000000 background, orange #f2904b accent, white text. No other accent colours.
Needs: ffmpeg, Pillow, numpy.
"""
import json, subprocess, sys, math, wave, random, os, tempfile, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BG, FG, ACCENT, MUTED = (0, 0, 0), (255, 255, 255), (242, 144, 75), (170, 170, 176)

def font(names, size):
    for n in names:
        for d in ("/usr/share/fonts/truetype/google-fonts/", "/usr/share/fonts/opentype/inter/",
                  "/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/freefont/"):
            try: return ImageFont.truetype(d + n, size)
            except OSError: pass
    return ImageFont.load_default()
BOLD = ["Poppins-Bold.ttf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"]
MED = ["Poppins-Medium.ttf", "Inter-Medium.otf", "DejaVuSans.ttf", "FreeSans.ttf"]
SEMI = ["Poppins-SemiBold.ttf", "Inter-SemiBold.otf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"]
F_HOOK, F_TITLE, F_BODY, F_SM = font(BOLD, 96), font(BOLD, 78), font(MED, 52), font(SEMI, 40)

def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3

# ------------------------------------------------------------------ music
SCALES = {"major_pent": [0, 2, 4, 7, 9], "minor_pent": [0, 3, 5, 7, 10],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11]}
# chord roots as scale-degree offsets in semitones + quality (triads)
PROGS = [[(0, "M"), (5, "M"), (7, "M"), (5, "M")], [(0, "m"), (8, "M"), (3, "M"), (10, "M")],
         [(0, "M"), (7, "M"), (9, "m"), (5, "M")], [(0, "m"), (5, "m"), (10, "M"), (7, "M")],
         [(0, "M"), (9, "m"), (2, "m"), (7, "M")]]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def make_audio(path, total, starts, ordinal, sr=44100):
    rnd = random.Random(ordinal * 7919)
    scale_name = list(SCALES)[ordinal % 4]; scale = SCALES[scale_name]
    root = 48 + [0, 2, 3, 5, 7, 8, 10][(ordinal * 3) % 7]          # C3-ish roots
    bpm = rnd.choice([84, 90, 96, 102, 108, 112]); beat = 60 / bpm
    prog = PROGS[ordinal % len(PROGS)]
    lead = ["pluck", "bell", "marimba"][ordinal % 3]
    drums = ["soft", "none", "shaker", "soft"][ordinal % 4]
    n = int(total * sr); buf = np.zeros(n + sr)
    def add(t0, sig):
        a = int(t0 * sr)
        if a < n: buf[a:a + len(sig)] += sig[:max(0, len(buf) - a)]
    def tarr(d): return np.arange(int(d * sr)) / sr
    def note(f, d, kind, amp):
        t = tarr(d); att = np.minimum(1, t / 0.006)
        if kind == "pluck":
            s = np.sin(2*np.pi*f*t) + .35*np.sin(4*np.pi*f*t)*np.exp(-t*8) + .12*np.sin(6*np.pi*f*t)*np.exp(-t*12)
            e = np.exp(-t * 5.5)
        elif kind == "bell":
            s = np.sin(2*np.pi*f*t) + .5*np.sin(2*np.pi*f*2.76*t)*np.exp(-t*6) + .25*np.sin(2*np.pi*f*5.4*t)*np.exp(-t*10)
            e = np.exp(-t * 3.2)
        else:  # marimba
            s = np.sin(2*np.pi*f*t) + .45*np.sin(2*np.pi*f*4*t)*np.exp(-t*20)
            e = np.exp(-t * 7)
        return amp * s * e * att
    bars = int(total / (beat * 4)) + 1
    for b in range(bars):
        r, q = prog[b % len(prog)]
        cr = root + r; third = 4 if q == "M" else 3
        t0 = b * beat * 4; d = beat * 4 + 0.4
        t = tarr(d)
        env = np.minimum(1, t / 0.5) * np.minimum(1, (d - t) / 0.4)          # soft pad
        pad = sum(np.sin(2*np.pi*midi(cr + 12 + iv) * t * (1 + dt)) for iv in (0, third, 7) for dt in (-.0025, .0025))
        add(t0, 0.035 * pad * env)
        for k in range(4):                                                    # gentle bass on beats 1 & 3
            if k in (0, 2):
                add(t0 + k * beat, note(midi(cr - 12), beat * 1.8, "marimba", 0.22))
        for k in range(8):                                                    # lead: random-walk arpeggio
            if rnd.random() < 0.72:
                deg = rnd.choice(range(len(scale))) ; octv = rnd.choice([12, 12, 24])
                add(t0 + k * beat / 2, note(midi(root + scale[deg] + octv + 12), beat * 1.6, lead, 0.13))
        for k in range(4):
            tt = t0 + k * beat
            if drums in ("soft", "shaker"):
                kt = tarr(0.18); ke = np.exp(-kt * 22)
                if drums == "soft" and k in (0, 2):
                    add(tt, 0.28 * np.sin(2*np.pi*(46 + 60*np.exp(-kt*30))*kt) * ke)
                h = tarr(0.06); add(tt + beat / 2, 0.018 * np.random.default_rng(b*8+k).uniform(-1, 1, len(h)) * np.exp(-h*60))
    for s in starts[1:]:                                                      # soft chime at scene changes
        add(s, note(midi(root + scale[-1] + 36), 0.9, "bell", 0.10))
    buf = buf[:n]
    # echo
    for dly, g in ((beat * .75, .30), (beat * 1.5, .16)):
        k = int(dly * sr); buf[k:] += g * buf[:-k].copy()
    # soften highs (FFT low-pass ~6.5k) then fade + normalise
    sp = np.fft.rfft(buf); fr = np.fft.rfftfreq(n, 1 / sr)
    sp *= 1 / (1 + (fr / 6500.0) ** 4); buf = np.fft.irfft(sp, n)
    fade = int(0.8 * sr); g = np.ones(n); g[:fade] = np.linspace(0, 1, fade); g[-fade:] = np.linspace(1, 0, fade)
    buf *= g; buf *= 0.8 / (np.abs(buf).max() or 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())
    return f"{scale_name} root MIDI {root}, {bpm} bpm, prog#{ordinal % len(PROGS)}, lead={lead}, drums={drums}"

# ------------------------------------------------------------------ visuals
STYLES = ["glow", "rings", "stripes", "dots", "bars"]
ANIMS = ["rise", "slide", "wipe", "fade"]

def wrap(draw, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

def background(img, style, t, idx, dur):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L); tg = idx * dur + t
    if style == "glow":
        gx = int(W * .5 + 300 * math.sin(tg / 2.5)); d.ellipse([gx-450, 1100, gx+450, 2000], fill=ACCENT + (45,))
    elif style == "rings":
        for k in range(5):
            r = int(((tg * 90 + k * 170) % 850)) + 40
            d.ellipse([W//2 - r, 1350 - r, W//2 + r, 1350 + r], outline=ACCENT + (int(70 * (1 - r / 900)),), width=5)
    elif style == "stripes":
        off = int(tg * 60) % 140
        for x in range(-H, W + H, 140):
            d.line([(x + off, H), (x + off + H, 0)], fill=ACCENT + (26,), width=36)
    elif style == "dots":
        for gx in range(60, W, 90):
            for gy in range(1000, H - 60, 90):
                a = int(25 + 45 * (0.5 + 0.5 * math.sin(tg * 2 + gx / 140 + gy / 170)))
                d.ellipse([gx-6, gy-6, gx+6, gy+6], fill=ACCENT + (a,))
    else:  # bars
        for k in range(12):
            h = int(120 + 220 * (0.5 + 0.5 * math.sin(tg * 1.6 + k * .7)))
            d.rectangle([60 + k * 82, H - 60 - h, 60 + k * 82 + 56, H - 60], fill=ACCENT + (38,))
    img.alpha_composite(L)

def block(img, lines, f, y, color, prog, lh, anim, align, x=90):
    probe = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        p = ease(prog * (len(lines) + 1) - i * 0.8)
        if p <= 0: continue
        tw = probe.textlength(ln, font=f)
        bx = x if align == "left" else (W - tw) / 2
        dx = dy = 0; alpha = int(255 * p)
        if anim == "rise": dy = (1 - p) * 50
        elif anim == "slide": dx = -(1 - p) * 160
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((bx + dx, y + i * lh + dy), ln, font=f, fill=color + (alpha if anim != "wipe" else 255,))
        if anim == "wipe":
            m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle([0, 0, int(bx + tw * p + 10), H], fill=255)
            layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", (W, H), 0), m))
        img.alpha_composite(layer)

def chrome(img, d, t, dur, idx, total, handle):
    d.rectangle([0, 0, W, 10], fill=(35, 35, 40))
    d.rectangle([0, 0, W * (idx + t / dur) / total, 10], fill=ACCENT)
    d.text((90, 110), "DISTECH", font=F_SM, fill=ACCENT)
    d.text((90 + d.textlength("DISTECH ", font=F_SM), 110), "TECHNOLOGIES", font=F_SM, fill=FG)
    d.text((90, H - 140), handle, font=F_SM, fill=MUTED)

def render(spec, out, date):
    ordinal = date.toordinal()
    style, anim, align = STYLES[ordinal % 5], ANIMS[ordinal % 4], ("left", "center")[(ordinal // 2) % 2]
    S = [("hook", spec["hook"], None, 3.4)]
    for i, s in enumerate(spec["slides"], 1): S.append(("slide", s["title"], s["body"], 3.6, i))
    S.append(("cta", spec["cta"], None, 3.4))
    total = len(S); handle = spec.get("handle", "distech.co.za")
    starts, acc = [], 0.0
    for sc in S: starts.append(acc); acc += sc[3]
    wav = os.path.join(tempfile.gettempdir(), "reel_audio.wav")
    music = make_audio(wav, acc, starts, ordinal)
    print(f"style={style} anim={anim} align={align} | music: {music}")
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
            background(img, style, t, idx, dur)
            chrome(img, d, t, dur, idx, total, handle)
            cx = (lambda s, f: 90 if align == "left" else (W - d.textlength(s, font=f)) / 2)
            if kind == "hook":
                # cover: hook fully visible from frame 0 so the thumbnail is never black/empty
                L = wrap(probe, sc[1], F_HOOK, W - 180); y0 = 640 - (len(L) - 3) * 60
                d.rounded_rectangle([90 if align == "left" else (W - 160) / 2, y0 - 70, (90 if align == "left" else (W - 160) / 2) + 160, y0 - 56], 7, fill=ACCENT)
                block(img, L, F_HOOK, y0, FG, 1.0, 120, "fade", align)
                by = y0 + len(L) * 120 + 40
                bar = 300
                d.rectangle([90 if align == "left" else (W - bar) / 2, by, (90 if align == "left" else (W - bar) / 2) + bar, by + 10], fill=ACCENT)
                cw = 460; cxx = 90 if align == "left" else (W - cw) / 2   # brand chip: keeps the cover recognisable in the grid
                d.rounded_rectangle([cxx, by + 60, cxx + cw, by + 150], 45, fill=ACCENT)
                d.text((cxx + 40, by + 83), "distech.co.za", font=F_SM, fill=(0, 0, 0))
            elif kind == "slide":
                num = f"0{sc[4]}"; d.text((cx(num, F_HOOK), 520), num, font=F_HOOK, fill=ACCENT)
                L = wrap(probe, sc[1], F_TITLE, W - 180)
                block(img, L, F_TITLE, 680, FG, p, 100, anim, align)
                block(img, wrap(probe, sc[2], F_BODY, W - 180), F_BODY, 680 + len(L) * 100 + 50, MUTED, max(0, (t - 0.4) / 1.1), 76, anim, align)
            else:
                L = wrap(probe, sc[1], F_HOOK, W - 180)
                block(img, L, F_HOOK, 600, FG, p, 120, anim, align)
                by = 600 + len(L) * 120 + 70
                bw = 560; bx = 90 if align == "left" else (W - bw) / 2
                d.rounded_rectangle([bx, by, bx + bw, by + 120], 60, fill=ACCENT)
                d.text((bx + 40, by + 30), "distech.co.za", font=F_BODY, fill=(0, 0, 0))
            rgb = img.convert("RGB")
            if idx == 0 and fr == 0:
                rgb.save(os.path.splitext(out)[0] + "_cover.jpg", quality=92)
            ff.stdin.write(rgb.tobytes())
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    a = sys.argv[1:]
    date = datetime.date.fromisoformat(a[a.index("--date") + 1]) if "--date" in a else datetime.date.today()
    render(json.load(open(a[0])), a[1], date)
