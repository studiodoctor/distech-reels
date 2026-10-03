#!/usr/bin/env python3
import json, subprocess, sys, math
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BG, FG, ACCENT, MUTED = (8, 8, 10), (255, 255, 255), (59, 130, 246), (150, 150, 160)
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
    d.rectangle([0, 0, W, 10], fill=(30, 30, 36))
    d.rectangle([0, 0, W * (idx + t / dur) / total, 10], fill=ACCENT)
    d.text((90, 110), "DISTECH", font=F_SM, fill=FG)
    d.text((90 + d.textlength("DISTECH ", font=F_SM), 110), "TECHNOLOGIES", font=F_SM, fill=MUTED)
    d.text((90, H - 140), handle, font=F_SM, fill=MUTED)

def render(spec, out):
    S = [("hook", spec["hook"], None, 3.2)]
    for i, s in enumerate(spec["slides"], 1): S.append(("slide", s["title"], s["body"], 3.6, i))
    S.append(("cta", spec["cta"], None, 3.4))
    total = len(S); handle = spec.get("handle", "distech.co.za")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    for idx, sc in enumerate(S):
        kind, dur = sc[0], sc[3]
        for fr in range(int(dur * FPS)):
            t = fr / FPS; p = min(1, t / 1.1)
            img = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(img)
            gx = int(W * 0.5 + 300 * math.sin((idx * dur + t) / 2.5))
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse([gx - 450, 1100, gx + 450, 2000], fill=ACCENT + (38,))
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
                d.text((130, by + 30), "distech.co.za", font=F_BODY, fill=FG)
            ff.stdin.write(img.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
