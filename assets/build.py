"""Builds the README cards as SVGs in the style of hyowonbernabe.me.

Each card embeds only the glyphs it uses from Geist / Geist Mono, so files stay small.
Run: python assets/build.py  (needs: pip install fonttools brotli)
Bump VERSION after changing a card: GitHub caches images by URL for several minutes.
"""
import base64, io, random
from pathlib import Path
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

VERSION = "v1"
HERE = Path(__file__).parent
OUT = HERE / "cards"
W = 900
INK, RED, BONE, ASH, BLOOD = "#050505", "#ff0f0f", "#ededed", "#8a8585", "#4a0000"

FONTS = {  # css family -> (file, weight)
    "D": ("geist.woff2", 900),       # display
    "B": ("geist.woff2", 500),       # body
    "M": ("geist-mono.woff2", 700),  # labels
}
_static = {}


def static(fam):
    if fam not in _static:
        file, wght = FONTS[fam]
        _static[fam] = instancer.instantiateVariableFont(TTFont(HERE / "fonts" / file), {"wght": wght})
    return _static[fam]


def width(text, fam, size, ls=0.0):
    f = static(fam)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    adv = sum(hmtx[cmap.get(ord(c), cmap[32])][0] for c in text)
    return adv * size / upm + ls * size * max(len(text) - 1, 0)


def wrap(text, fam, size, maxw, sep=" "):
    lines, cur = [], ""
    for word in text.split(sep):
        nxt = f"{cur}{sep}{word}" if cur else word
        if cur and width(nxt, fam, size) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    return lines + [cur]


def font_css(used):
    css = []
    for fam, chars in used.items():
        f = TTFont(io.BytesIO(_dump(static(fam))))
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        s = subset.Subsetter(opts)
        s.populate(text="".join(chars) + " ")
        s.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff2"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css.append(f"@font-face{{font-family:{fam};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(css)


def _dump(font):
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


class Card:
    def __init__(self, h, seed=1, w=W):
        self.w, self.h, self.parts, self.used, self.seed = w, h, [], {}, seed

    def text(self, x, y, s, fam, size, fill=BONE, ls=0.0, anchor="start", extra=""):
        self.used.setdefault(fam, set()).update(s)
        style = f"font-family:{fam},serif;font-size:{size}px" + (f";letter-spacing:{ls}em" if ls else "")
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}" style="{style}" {extra}>{escape(s)}</text>')

    def eyebrow(self, x, y, s):
        self.parts.append(f'<rect x="{x}" y="{y - 8}" width="40" height="2.5" fill="{RED}"/>')
        self.text(x + 56, y, s, "M", 18, RED, 0.3)

    def arrow(self, x, y, size=22, color=BONE):  # the fonts have no arrow glyph, so draw one
        self.parts.append(
            f'<path d="M{x} {y + size}L{x + size} {y}M{x + size * .3} {y}H{x + size}V{y + size * .7}" '
            f'stroke="{color}" stroke-width="2.5" fill="none" stroke-linecap="square"/>')

    def svg(self, label):
        rnd = random.Random(self.seed)
        stars = "".join(
            f'<circle cx="{rnd.uniform(0, self.w):.0f}" cy="{rnd.uniform(0, self.h):.0f}" r="{rnd.choice([0.8, 1, 1.4]):.1f}" '
            f'fill="{BONE}" opacity="{rnd.uniform(.12, .5):.2f}"/>' for _ in range(int(self.w * self.h / 9000)))
        i, l = 18, 18  # HUD corner brackets: inset, arm length
        hud = "".join(
            f'<path d="M{x} {y + l * dy}V{y}H{x + l * dx}" stroke="{BONE}" stroke-opacity=".4" stroke-width="1.5" fill="none"/>'
            for x, y, dx, dy in [(i, i, 1, 1), (self.w - i, i, -1, 1), (i, self.h - i, 1, -1), (self.w - i, self.h - i, -1, -1)])
        css = font_css(self.used) + (
            "text{dominant-baseline:alphabetic}"
            ".pulse{animation:pulse 2.4s ease-in-out infinite}@keyframes pulse{50%{opacity:.35}}"
            ".spin{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}"
            "@keyframes spin{to{transform:rotate(360deg)}}"
            ".scan{animation:scan 7s linear infinite}@keyframes scan{from{transform:translateY(-20px)}to{transform:translateY(" + str(self.h + 20) + "px)}}")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(label)}">'
            f'<style>{css}</style>'
            f'<defs><pattern id="g" width="45" height="45" patternUnits="userSpaceOnUse"><path d="M45 0H0V45" fill="none" stroke="{BONE}" stroke-opacity=".05"/></pattern>'
            f'<radialGradient id="glow"><stop offset="0" stop-color="{RED}" stop-opacity=".35"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>'
            f'<filter id="bloom" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="6"/></filter>'
            f'<clipPath id="c"><rect width="{self.w}" height="{self.h}" rx="14"/></clipPath></defs>'
            f'<g clip-path="url(#c)"><rect width="{self.w}" height="{self.h}" fill="{INK}"/><rect width="{self.w}" height="{self.h}" fill="url(#g)"/>{stars}'
            + "".join(self.parts) + f'</g>{hud}'
            f'<rect x=".5" y=".5" width="{self.w - 1}" height="{self.h - 1}" rx="14" fill="none" stroke="{BONE}" stroke-opacity=".08"/></svg>')


def dot(card, cx, cy, r):
    card.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r * 2.2}" fill="{RED}" opacity=".6" filter="url(#bloom)" class="pulse"/>'
                      f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{RED}"/>')


def hero():
    c = Card(440, seed=7)
    # muzzle ring with a slow-turning rifling ring, from the site's about scene
    c.parts.append(f'<circle cx="740" cy="210" r="230" fill="url(#glow)"/>'
                   f'<circle cx="740" cy="210" r="150" fill="none" stroke="{BONE}" stroke-opacity=".18" stroke-width="5"/>'
                   f'<circle cx="740" cy="210" r="190" fill="none" stroke="{BONE}" stroke-opacity=".08" stroke-width="22" stroke-dasharray="6 26" class="spin"/>'
                   f'<rect x="0" y="0" width="{W}" height="1.5" fill="{RED}" opacity=".35" class="scan"/>')
    c.eyebrow(48, 86, "FULL STACK + AI ENGINEER")
    c.text(44, 202, "HYOWON", "D", 112, BONE, -0.05)
    c.text(44, 302, "BERNABE", "D", 112, "none", -0.05, extra=f'stroke="{RED}" stroke-width="2.5"')
    dot(c, 44 + width("BERNABE", "D", 112, -0.05) + 22, 292, 11)
    c.parts.append(f'<rect x="48" y="346" width="{W - 96}" height="1.5" fill="{BONE}" opacity=".2"/>')
    c.text(48, 384, "AI ENGINEER @ MULTIPLY OS", "M", 17, BONE, 0.14)
    c.text(W - 48, 384, "CTO @ ZURALOG + FLH MEDIA", "M", 17, BONE, 0.14, "end")
    dot(c, 56, 410, 4)
    c.text(70, 415, "BAGUIO CITY, PH  /  GMT+8", "M", 15, ASH, 0.2)
    return c.svg("Hyowon Bernabe. Full stack and AI engineer. AI Engineer at Multiply OS, CTO at ZuraLog and FLH Media. Baguio City, Philippines.")


def header(title, count):
    c = Card(84, seed=len(title))
    c.eyebrow(48, 50, title)
    c.text(W - 48, 50, count, "M", 18, ASH, 0.3, "end")
    return c.svg(title)


def project(i, name, tech, desc):
    lines = wrap(desc, "B", 22, W - 150)
    c = Card(128 + 30 * len(lines), seed=i)
    c.text(48, 62, f"{i:02d}", "M", 16, RED, 0.2)
    c.text(92, 70, name.upper(), "D", 44, BONE, -0.04)
    tw = width(tech.upper(), "M", 14, 0.2) + 28
    c.parts.append(f'<rect x="{W - 92 - tw}" y="44" width="{tw}" height="30" rx="15" fill="none" stroke="{RED}" stroke-opacity=".6"/>')
    c.text(W - 92 - tw / 2, 64, tech.upper(), "M", 14, RED, 0.2, "middle")
    c.arrow(W - 70, 48)
    for n, line in enumerate(lines):
        c.text(92, 112 + 30 * n, line, "B", 22, ASH)
    return c.svg(f"{name} ({tech}): {desc}")


def arsenal():
    rows = [("AI / ML", "RAG · Fine-tuning (Unsloth, LoRA) · Whisper · Hugging Face"),
            ("LANGUAGES", "Python · TypeScript · Rust · Kotlin · C# · Java · C++"),
            ("FRAMEWORKS", "React · Next.js · Tailwind · Three.js · WPF"),
            ("BACKEND", "Node.js · PostgreSQL · Prisma · Firebase · Docker"),
            ("CREDENTIALS", "BS CS, Saint Louis University · Harvard CS50 AI · Databricks · Hugging Face")]
    y, body = 128, []
    for label, val in rows:
        lines = wrap(val, "B", 21, W - 300, " · ")
        body.append((y, label, lines))
        y += 34 * len(lines) + 22
    c = Card(y + 14, seed=99)
    c.eyebrow(48, 70, "ARSENAL")
    for y0, label, lines in body:
        c.parts.append(f'<rect x="48" y="{y0 - 30}" width="{W - 96}" height="1" fill="{BONE}" opacity=".12"/>')
        c.text(48, y0, label, "M", 15, RED, 0.24)
        for n, line in enumerate(lines):
            c.text(252, y0 + 34 * n, line, "B", 21, BONE)
    return c.svg("Arsenal. " + " ".join(f"{a}: {b}." for a, b in rows))


def contact():
    c = Card(250, seed=3)
    c.parts.append(f'<circle cx="{W - 120}" cy="240" r="260" fill="url(#glow)"/>')
    c.eyebrow(48, 76, "CONTACT")
    c.text(44, 166, "LET'S BUILD", "D", 84, BONE, -0.05)
    dot(c, 44 + width("LET'S BUILD", "D", 84, -0.05) + 18, 158, 9)
    c.text(48, 212, "CONTACT@HYOWONBERNABE.ME", "M", 18, ASH, 0.2)
    c.arrow(W - 76, 136, 30, RED)
    return c.svg("Let's build. contact@hyowonbernabe.me")


def button(label):
    c = Card(76, seed=len(label) * 5, w=440)
    c.text(40, 46, label, "M", 18, BONE, 0.3)
    c.arrow(c.w - 64, 28, 20, RED)
    return c.svg(label)


PROJECTS = [
    ("Messenger-Z", "Kotlin", "Non-root Android privacy mod for Messenger. Featured on XDA."),
    ("Globit AI", "RAG", "AI chatbot and booking platform for a live rental business. Handles ~70% of guest inquiries."),
    ("TOS Risk", "Llama 3", "Fine-tuned model that flags risky clauses in Terms of Service."),
    ("TAGriculture", "Kotlin", "RFID livestock tracking app. 2nd place, PCCI 2025."),
    ("ShadowPrompt", "Rust", "Hotkey-driven AI exam assistant for Windows. One executable, no taskbar entry."),
    ("Kuroko", "C#", "AI assistant invisible to screen share, with local Whisper and SQLite vector RAG."),
    ("i-Tril", "Next.js", "Lab reservation system with QR check-in for Saint Louis University."),
]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    cards = {"hero": hero(), "work": header("SELECTED WORK", f"{len(PROJECTS):02d}"),
             "arsenal": arsenal(), "contact": contact(),
             "website": button("WEBSITE"), "linkedin": button("LINKEDIN")}
    for n, p in enumerate(PROJECTS, 1):
        cards[f"p{n}"] = project(n, *p)
    for name, svg in cards.items():
        (OUT / f"{name}-{VERSION}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}-{VERSION}.svg {len(svg) // 1024}KB")
