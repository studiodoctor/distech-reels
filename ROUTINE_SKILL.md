---
name: "distech-daily-social-post"
description: "Create and publish Distech Technologies' daily branded reel with hook and caption to Instagram, Facebook and LinkedIn via Buffer, using content from distech.co.za."
---

# Distech daily social post

Produce ONE new 1080x1920 animated-text reel per run, write captions, and publish through the Buffer connector to the Distech pages (Instagram Reels, Facebook Reels, LinkedIn). Runs unattended: make reasonable choices, never ask questions, and report what was posted.

**Brand rules (mandatory):** Distech brand colours are black #000000 (background) and orange #f2904b (accent), with white text. Never use blue or any other accent colour. Every reel MUST have a real audible soundtrack (never silent audio): the render script below generates one. Verify both before publishing.

## 1. Gather facts (never invent)
WebFetch https://distech.co.za and the sub-pages: /services, /services/mobile-app-development, /services/custom-business-software, /services/api-system-integrations, /services/business-automation, /services/software-modernisation, /services/maintenance-support, /crm, /erp, /our-work, /about, /blog, /contact.
Only use facts found on the site. Known facts: custom software company in Sandton, Johannesburg serving all of South Africa; tagline "Custom Software Built Around Your Business"; smaller custom projects from around R20,000 (estimate before work begins); 6-step process (Tell us your problem, Define the solution, Get a clear proposal, Build & test, Launch, Support & improve); talk directly to the people on your project; portfolio: Book Me Now SA, Nexivo, Namak Indian Restaurant, Paayal Traders; Distech CRM and Distech ERP; Android/iOS/Flutter; payment and WhatsApp integrations; small tool = few weeks, larger system = few months. Contact: WhatsApp https://wa.me/27672394281, hello@distech.co.za, +27 67 239 4281.

## 2. Pick today's topic (no repeats)
Keep a log file `post_log.json` (list of {date, topic, hook}) in the working directory; if it is missing, start it. Rotate angles so the same angle is not used within 14 days: service spotlight, portfolio case study, pain-point hook (spreadsheets, manual admin, WhatsApp chaos), process step, FAQ myth-buster, CRM/ERP feature, pricing transparency, automation tip, "who we help". Prefer a different service/project than the last post. Check new blog posts first.

## 3. Write the reel spec (spec.json)
- hook: max ~9 words, a question or bold claim aimed at South African SMEs (e.g. "Still running your business on spreadsheets?").
- 3 slides, each {title: max 5 words, body: max 14 words}, one idea each, concrete.
- cta: one short line. Handle: distech.co.za.
- No made-up stats, clients, testimonials or prices beyond what the site states.

## 4. Render the reel
The renderer lives in the GitHub repo studiodoctor/distech-reels as `render_reel.py` (source of truth; clone it, do NOT use any older inline copy). It needs ffmpeg, Pillow and numpy (`pip install pillow numpy --break-system-packages`; if `python3` can't import PIL use `/usr/bin/python3.13`). Run:
`python3 render_reel.py spec.json distech_reel_YYYY-MM-DD.mp4 --date YYYY-MM-DD` (~30-60s).
- **Different every day:** the script derives, from the date, one of 5 background styles (glow, rings, stripes, dots, bars), 4 text animations (rise, slide, wipe, fade), left/centre layout, AND a brand-new original soundtrack (scale, key, tempo 84-112 bpm, chord progression, lead instrument pluck/bell/marimba, drums soft/none/shaker, echo, soft low-pass). It prints the style + music chosen; include that in the final report. Never reuse yesterday's combination; if you add new styles/tracks, keep this rotation.
- **Music must be pleasant, not harsh:** soft melodic bed, no sirens/sweeps. If a track sounds grating, change the progression/lead list in make_audio rather than shipping it.
- **Thumbnail/cover:** frame 0 is a full cover (hook text visible, orange accents, brand chip), and the script also writes `<out>_cover.jpg`. Never ship a video whose first frame is empty/black. View the cover jpg before publishing. Keep important text in the centre band (y 450-1450) so the Instagram profile-grid crop doesn't cut it.
- Verify with ffprobe (h264 1080x1920, AAC audio, 15-20s). Audio: `ffmpeg -i reel.mp4 -af volumedetect -vn -f null -` must show mean_volume louder than -35 dB (expect about -22 dB, max about -5 dB). View the cover and one mid-reel frame: background black with only faint orange shapes, accent #f2904b, text not clipped. Brand: black, orange #f2904b, white only; never blue.
- Also commit the `_cover.jpg` to the repo next to the mp4 (same name pattern) for reference.

## 5. Write captions
- Instagram/Facebook: hook line first, 2-4 short lines of value, soft CTA ("Message us on WhatsApp: wa.me/27672394281" or "Link in bio: distech.co.za"), then 6-10 relevant hashtags (#CustomSoftware #SouthAfrica #Sandton #Johannesburg #BusinessAutomation #MobileAppDevelopment #SMESouthAfrica #CRM #ERP plus topic-specific).
- LinkedIn: more professional, 3-5 short paragraphs, business outcome focus, link https://distech.co.za, max 3 hashtags.

## 6. Publish via Buffer
1. Use the Buffer connector tools (load via ToolSearch with keyword "buffer"). List channels and select the Distech Instagram, Facebook and LinkedIn channels only.
2. Buffer needs a publicly reachable video URL. Follow the hosting instructions in the task prompt (GitHub repository studiodoctor/distech-reels, raw URL). Do not use Netlify unless the task prompt says so. Do not post to any non-Distech channel.
3. Create posts (pass the video asset with `metadata.thumbnailOffset` = 0 so the cover frame is used as thumbnail; for Instagram also keep shouldShareToFeed true): Instagram as Reel, Facebook as Reel, LinkedIn as video post, each with its own caption. Publish now if the run is within the 09:00 SAST window, otherwise schedule for 09:00 SAST (UTC+2) today.
4. Confirm Buffer returned success/queued status for each channel. On failure retry once; if it still fails, keep the mp4 and captions, and report clearly which channel failed and why. Never post duplicates.

## 7. Log and report
Append {date, topic, hook, channels, status} to post_log.json. Final message: topic, hook, captions posted, per-channel status.