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

VERSION = "v4"
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
        buf = io.BytesIO()
        static(fam).save(buf)
        f = TTFont(io.BytesIO(buf.getvalue()))
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        s = subset.Subsetter(opts)
        s.populate(text="".join(chars) + " ")
        s.subset(f)
        out = io.BytesIO()
        f.save(out)
        b64 = base64.b64encode(out.getvalue()).decode()
        css.append(f"@font-face{{font-family:{fam};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(css)


class Card:
    """One README panel. bg picks the colour field, like the site's ink / red / bone frames."""

    def __init__(self, h, seed=1, w=W, gap=0, bg=INK, hud=True, stars=9000):
        # gap: transparent space right of the card, for side-by-side cards. stars: px² per star, 0 for none
        self.w, self.h, self.gap, self.bg, self.hud, self.stars = w, h, gap, bg, hud, stars
        self.fg = BONE if bg == INK else INK  # line colour for HUD, grid and ghost type
        self.parts, self.used, self.seed = [], {}, seed

    def text(self, x, y, s, fam, size, fill=BONE, ls=0.0, anchor="start", extra=""):
        self.used.setdefault(fam, set()).update(s)
        style = f"font-family:{fam},serif;font-size:{size}px" + (f";letter-spacing:{ls}em" if ls else "")
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}" style="{style}" {extra}>{escape(s)}</text>')

    def chip(self, x, y, s, size=18, bg=RED, fg=BONE):
        """The site's .eyebrow b: a mono label set in a solid block. y is the text baseline."""
        tw = width(s, "M", size, 0.24)
        self.parts.append(f'<rect x="{x}" y="{y - size - 5}" width="{tw + 24:.1f}" height="{size + 14}" fill="{bg}"/>')
        self.text(x + 12, y, s, "M", size, fg, 0.24)
        return tw + 24

    def ghost(self, s, x, y, size=220, anchor="start"):
        """Huge outlined word behind the content, as on every scene of the site."""
        self.text(x, y, s, "D", size, "none", -0.05, anchor,
                  f'stroke="{self.fg}" stroke-opacity=".1" stroke-width="1.5"')

    def arrow(self, x, y, size=22, color=BONE):  # the fonts have no arrow glyph, so draw one
        self.parts.append(
            f'<path d="M{x} {y + size}L{x + size} {y}M{x + size * .3} {y}H{x + size}V{y + size * .7}" '
            f'stroke="{color}" stroke-width="3" fill="none" stroke-linecap="square"/>')

    def svg(self, label):
        w, h, fg = self.w, self.h, self.fg
        rnd = random.Random(self.seed)
        stars = "".join(
            f'<circle cx="{rnd.uniform(0, w):.0f}" cy="{rnd.uniform(0, h):.0f}" r="{rnd.choice([0.8, 1, 1.4]):.1f}" '
            f'fill="{BONE}" opacity="{rnd.uniform(.12, .5):.2f}"/>' for _ in range(int(w * h / self.stars) if self.stars else 0))
        i, l = 18, 20  # HUD corner brackets: inset, arm length
        hud = "".join(
            f'<path d="M{x} {y + l * dy}V{y}H{x + l * dx}" stroke="{fg}" stroke-opacity=".5" stroke-width="2" fill="none"/>'
            for x, y, dx, dy in [(i, i, 1, 1), (w - i, i, -1, 1), (i, h - i, 1, -1), (w - i, h - i, -1, -1)]) if self.hud else ""
        # bone frames get the site's dot screen, the others its gridlines
        pattern = (f'<pattern id="g" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="6" cy="6" r=".9" fill="{INK}" fill-opacity=".14"/></pattern>'
                   if self.bg == BONE else
                   f'<pattern id="g" width="45" height="45" patternUnits="userSpaceOnUse"><path d="M45 0H0V45" fill="none" stroke="{fg}" stroke-opacity="{.05 if self.bg == INK else .08}"/></pattern>')
        shade = (f'<rect width="{w}" height="{h}" fill="url(#edge)"/>' if self.bg == RED else "")
        css = font_css(self.used) + (
            ".pulse{animation:pulse 2.4s ease-in-out infinite}@keyframes pulse{50%{opacity:.35}}"
            ".spin{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}"
            ".grain{animation:j 1.2s steps(8) infinite}@keyframes j{50%{transform:translate(-3px,2px)}}")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + self.gap}" height="{h}" viewBox="0 0 {w + self.gap} {h}" role="img" aria-label="{escape(label)}">'
            f'<style>{css}</style><defs>{pattern}'
            f'<radialGradient id="glow"><stop offset="0" stop-color="{RED}" stop-opacity=".35"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="edge" r="80%"><stop offset=".5" stop-color="{BLOOD}" stop-opacity="0"/><stop offset="1" stop-color="{BLOOD}" stop-opacity=".55"/></radialGradient>'
            f'<filter id="bloom" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="5"/></filter>'
            f'<filter id="noise"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter>'
            f'<clipPath id="c"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>'
            f'<g clip-path="url(#c)"><rect width="{w}" height="{h}" fill="{self.bg}"/>{shade}<rect width="{w}" height="{h}" fill="url(#g)"/>{stars}'
            + "".join(self.parts) +
            f'<rect x="-10" y="-10" width="{w + 20}" height="{h + 20}" filter="url(#noise)" opacity=".07" class="grain"/></g>{hud}</svg>')


def dot(card, cx, cy, r, color=RED):
    glow = f'<circle cx="{cx}" cy="{cy}" r="{r * 2.2}" fill="{color}" opacity=".6" filter="url(#bloom)" class="pulse"/>' if color == RED else ""
    card.parts.append(f'{glow}<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')


def ammo(card, x, y, loaded, total):
    """The site's ammo counter: loaded rounds glow red, the last one drops in."""
    for n in range(total):
        bx = x + n * 16
        path = f'M{bx} {y + 4}a5 5 0 0 1 10 0V{y + 26}H{bx}Z'  # round-nosed cartridge, 10x26
        if n < loaded:
            cls = ' class="pulse"' if n == loaded - 1 else ""
            card.parts.append(f'<g{cls}><path d="{path}" fill="{RED}" opacity=".7" filter="url(#bloom)"/><path d="{path}" fill="{RED}"/></g>')
        else:
            card.parts.append(f'<path d="{path}" fill="none" stroke="{card.fg}" stroke-opacity=".35" stroke-width="1.5"/>')


def hero():
    c = Card(460, seed=7, bg=RED, stars=0)
    c.ghost("PORTFOLIO 2026", -20, 175)
    c.parts.append(f'<circle cx="760" cy="230" r="190" fill="none" stroke="{INK}" stroke-opacity=".14" stroke-width="22" stroke-dasharray="6 26" class="spin"/>'
                   f'<circle cx="760" cy="230" r="150" fill="none" stroke="{INK}" stroke-opacity=".18" stroke-width="5"/>')
    c.chip(48, 82, "FULL STACK + AI ENGINEER", 19, INK, RED)
    c.text(42, 212, "HYOWON", "D", 120, INK, -0.05)
    c.text(42, 318, "BERNABE", "D", 120, "none", -0.05, extra=f'stroke="{INK}" stroke-width="3"')
    dot(c, 42 + width("BERNABE", "D", 120, -0.05) + 18, 304, 14, INK)
    c.parts.append(f'<rect x="48" y="358" width="{W - 96}" height="2" fill="{INK}" opacity=".35"/>')
    c.text(48, 398, "AI ENGINEER @ MULTIPLY OS", "M", 20, INK, 0.12)
    c.text(W - 48, 398, "CTO @ ZURALOG + FLH MEDIA", "M", 20, INK, 0.12, "end")
    c.parts.append(f'<circle cx="56" cy="425" r="5" fill="{INK}" class="pulse"/>')
    c.text(72, 431, "BAGUIO CITY, PH  /  GMT+8", "M", 18, INK, 0.2, extra='fill-opacity=".7"')
    return c.svg("Hyowon Bernabe. Full stack and AI engineer. AI Engineer at Multiply OS, CTO at ZuraLog and FLH Media. Baguio City, Philippines.")


def header(title, total):
    c = Card(96, seed=len(title), hud=False, stars=18000)
    c.chip(48, 60, title, 20)
    ammo(c, W - 48 - total * 16 + 6, 34, total, total)
    return c.svg(title)


def project(i, total, name, tech, desc):
    lines = wrap(desc, "B", 26, W - 140)
    last = 124 + 36 * (len(lines) - 1)
    c = Card(last + 78, seed=i, hud=False, stars=18000)
    c.ghost(f"{i:02d}", W - 24, c.h + 30, 200, "end")
    c.text(48, 70, f"{i:02d}", "M", 20, RED, 0.1)
    c.text(96, 80, name.upper(), "D", 52, BONE, -0.04)
    tw = width(tech.upper(), "M", 18, 0.2) + 32
    c.parts.append(f'<rect x="{W - 100 - tw:.1f}" y="44" width="{tw:.1f}" height="38" rx="19" fill="none" stroke="{RED}" stroke-width="1.5"/>')
    c.text(W - 100 - tw / 2, 69, tech.upper(), "M", 18, RED, 0.2, "middle")
    c.arrow(W - 76, 48, 26)
    for n, line in enumerate(lines):
        c.text(96, 124 + 36 * n, line, "B", 26, ASH)
    ammo(c, 96, last + 24, i, total)
    return c.svg(f"{name} ({tech}): {desc}")


def arsenal():
    rows = [("AI / ML", "RAG · Fine-tuning (Unsloth, LoRA) · Whisper · Hugging Face"),
            ("LANGUAGES", "Python · TypeScript · Rust · Kotlin · C# · Java · C++"),
            ("FRAMEWORKS", "React · Next.js · Tailwind · Three.js · WPF"),
            ("BACKEND", "Node.js · PostgreSQL · Prisma · Firebase · Docker"),
            ("CREDENTIALS", "BS CS, Saint Louis University · Harvard CS50 AI · Databricks · Hugging Face")]
    y, body = 140, []
    for label, val in rows:
        lines = wrap(val, "B", 25, W - 136, " · ")
        body.append((y, label, lines))
        y += 40 + 36 * len(lines) + 26
    c = Card(y + 10, seed=99, bg=BONE, stars=0)
    c.ghost("ARSENAL", W + 20, y + 40, 200, "end")
    c.chip(48, 82, "ARSENAL", 20)
    for n, (y0, label, lines) in enumerate(body):
        c.text(48, y0, label, "M", 18, RED, 0.2)
        c.parts.append(f'<rect x="{48 + width(label, "M", 18, 0.2) + 18:.1f}" y="{y0 - 6}" width="{W - 114 - width(label, "M", 18, 0.2):.1f}" height="1.5" fill="{INK}" opacity=".15"/>')
        # skill marker from the site's arsenal list: red for the primary row
        mark = f'fill="{RED}"' if n == 0 else f'fill="none" stroke="{INK}" stroke-width="1.5"'
        c.parts.append(f'<rect x="48" y="{y0 + 20}" width="9" height="23" rx="2" {mark}/>')
        for k, line in enumerate(lines):
            c.text(74, y0 + 40 + 36 * k, line, "B", 25, INK)
    return c.svg("Arsenal. " + " ".join(f"{a}: {b}." for a, b in rows))


def contact():
    c = Card(280, seed=3, bg=RED, stars=0)
    c.ghost("CONTACT", W + 20, 300, 220, "end")
    c.chip(48, 82, "CONTACT", 20, INK, RED)
    c.text(42, 186, "LET'S BUILD", "D", 92, INK, -0.05)
    dot(c, 42 + width("LET'S BUILD", "D", 92, -0.05) + 16, 176, 11, INK)
    c.text(48, 236, "CONTACT@HYOWONBERNABE.ME", "M", 21, INK, 0.16, extra='fill-opacity=".75"')
    c.arrow(W - 90, 150, 40, INK)
    return c.svg("Let's build. contact@hyowonbernabe.me")


def button(label, gap=0):
    c = Card(104, seed=len(label) * 5, w=440, gap=gap, hud=False, stars=18000)
    c.parts.append(f'<rect width="440" height="4" fill="{RED}"/>')
    c.text(36, 66, label, "D", 34, BONE, -0.02)
    c.arrow(440 - 66, 40, 26, RED)
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
    cards = {"hero": hero(), "work": header("SELECTED WORK", len(PROJECTS)),
             "arsenal": arsenal(), "contact": contact(),
             "website": button("WEBSITE", gap=12), "linkedin": button("LINKEDIN")}
    for n, p in enumerate(PROJECTS, 1):
        cards[f"p{n}"] = project(n, len(PROJECTS), *p)
    for name, svg in cards.items():
        (OUT / f"{name}-{VERSION}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}-{VERSION}.svg {len(svg) // 1024}KB")
