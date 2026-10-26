#!/usr/bin/env python3
"""Desenul lui Lio (SVG) — sursa unică pentru mascota site-ului.

Rulează `python3 scripts/lio_svg.py` ca să regenerezi:
  public/assets/img/lio.svg      Lio întreg, face cu mâna și clipește
  public/assets/img/lio-cap.svg  doar capul (butonul de citire)
  public/favicon.svg             iconița site-ului

Funcția `lio()` poate fi folosită și pentru ilustrații (fără animații).
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FUR = "#FBCB5C"
FUR_SHADE = "#F0B140"
CREAM = "#FFEBC2"
MANE = "#EC8A35"
MANE_LIGHT = "#F6A64A"
MANE_DARK = "#D2701F"
EYE = "#3B2214"
BLUSH = "#F79C9C"
PINK = "#F7A9A8"
SCARF = "#2EC4B6"
SCARF_DARK = "#1E9C91"
STAR = "#FFE066"
NOSE = "#6B3A22"
MOUTH = "#7A2E25"
TONGUE = "#F28B82"


def star_path(cx, cy, r, inner=0.45, points=5, rot=-90):
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 180 / points)
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return "M" + " L".join(pts) + " Z"


def ring(cx, cy, radius, count, r, color, offset=0.0):
    out = []
    for i in range(count):
        a = 2 * math.pi * i / count + offset
        out.append(f'<circle cx="{cx + radius * math.cos(a):.1f}" cy="{cy + radius * math.sin(a):.1f}" r="{r}" fill="{color}"/>')
    return "".join(out)


def arm(path):
    return (f'<path d="{path}" stroke="{FUR_SHADE}" stroke-width="26" fill="none" stroke-linecap="round"/>')


def paw(x, y):
    return f'<circle cx="{x}" cy="{y}" r="15" fill="{FUR}"/><circle cx="{x}" cy="{y + 3}" r="6" fill="{PINK}" opacity=".7"/>'


def arms_svg(pose, animated):
    if pose == "up":
        return arm("M-42,-100 Q-100,-128 -106,-196") + paw(-106, -200) + arm("M42,-100 Q100,-128 106,-196") + paw(106, -200)
    if pose == "hold":
        return arm("M-42,-100 Q-40,-62 -12,-70") + paw(-12, -70) + arm("M42,-100 Q40,-62 12,-70") + paw(12, -70)
    left = arm("M-42,-100 Q-60,-66 -52,-42") + paw(-52, -40)
    if pose == "wave":
        right = arm("M42,-100 Q104,-112 110,-172") + paw(110, -176)
        if animated:
            right = (f'<g>{right}<animateTransform attributeName="transform" type="rotate" '
                     f'values="0 42 -100;-14 42 -100;6 42 -100;-14 42 -100;0 42 -100;0 42 -100" '
                     f'keyTimes="0;.15;.3;.45;.6;1" dur="3s" repeatCount="indefinite"/></g>')
        return left + right
    return left + arm("M42,-100 Q60,-66 52,-42") + paw(52, -40)


def eyes_svg(state, animated):
    if state == "closed":
        return "".join(f'<path d="M{x - 13},-184 q13,11 26,0" stroke="{EYE}" stroke-width="5" fill="none" stroke-linecap="round"/>' for x in (-23, 23))
    blink_ry = ('<animate attributeName="ry" values="17;17;2;17" keyTimes="0;.94;.97;1" dur="4.5s" repeatCount="indefinite"/>'
                if animated else "")
    blink_op = ('<animate attributeName="opacity" values="1;1;0;1" keyTimes="0;.94;.97;1" dur="4.5s" repeatCount="indefinite"/>'
                if animated else "")
    out = []
    for x in (-23, 23):
        out.append(f'<ellipse cx="{x}" cy="-184" rx="14" ry="17" fill="{EYE}">{blink_ry}</ellipse>')
        out.append(f'<g>{blink_op}<circle cx="{x + 5}" cy="-191" r="6" fill="#fff"/><circle cx="{x - 5}" cy="-177" r="2.6" fill="#fff"/></g>')
    return "".join(out)


def mouth_svg(state, talking_ready):
    smile = (f'<path d="M0,-158 v5 M-13,-151 q6.5,8 13,0 q6.5,8 13,0" stroke="{NOSE}" stroke-width="4" fill="none" '
             f'stroke-linecap="round" stroke-linejoin="round"/>')
    open_mouth = (f'<path d="M0,-158 v4" stroke="{NOSE}" stroke-width="4" stroke-linecap="round"/>'
                  f'<path d="M-11,-152 Q0,-150 11,-152 Q10,-134 0,-134 Q-10,-134 -11,-152 Z" fill="{MOUTH}"/>'
                  f'<ellipse cx="0" cy="-139" rx="6" ry="4" fill="{TONGUE}"/>')
    if talking_ready:
        return f'<g class="lio-mouth-smile">{smile}</g><g class="lio-mouth-open">{open_mouth}</g>'
    return open_mouth if state == "open" else smile


def head_svg(eyes="open", mouth="smile", animated=False, talking_ready=False):
    cx, cy = 0, -180
    return f'''
  {ring(cx, cy, 64, 16, 26, MANE)}
  {ring(cx, cy, 54, 14, 20, MANE_LIGHT, 0.2)}
  <path d="M-4,-250 q2,-26 24,-22 q-14,6 -10,22 z" fill="{MANE_DARK}"/>
  <circle cx="-52" cy="-238" r="21" fill="{FUR}"/><circle cx="52" cy="-238" r="21" fill="{FUR}"/>
  <circle cx="-52" cy="-238" r="11" fill="{PINK}"/><circle cx="52" cy="-238" r="11" fill="{PINK}"/>
  <circle cx="{cx}" cy="{cy}" r="62" fill="{FUR}"/>
  <ellipse cx="0" cy="-150" rx="31" ry="22" fill="{CREAM}"/>
  <ellipse cx="-41" cy="-160" rx="12" ry="8" fill="{BLUSH}" opacity=".75"/>
  <ellipse cx="41" cy="-160" rx="12" ry="8" fill="{BLUSH}" opacity=".75"/>
  <path d="M-31,-211 q8,-6 16,0 M15,-211 q8,-6 16,0" stroke="{MANE_DARK}" stroke-width="4" fill="none" stroke-linecap="round"/>
  {eyes_svg(eyes, animated)}
  <circle cx="-17" cy="-148" r="2" fill="#E2AE62"/><circle cx="-22" cy="-142" r="2" fill="#E2AE62"/>
  <circle cx="17" cy="-148" r="2" fill="#E2AE62"/><circle cx="22" cy="-142" r="2" fill="#E2AE62"/>
  <path d="M0,-157 C-9,-163 -13,-170 -8,-173 C-4,-175 -1,-172 0,-170 C1,-172 4,-175 8,-173 C13,-170 9,-163 0,-157 Z" fill="{NOSE}"/>
  <ellipse cx="-3" cy="-169" rx="2.5" ry="1.5" fill="#fff" opacity=".6"/>
  {mouth_svg(mouth, talking_ready)}'''


def lio(x=0, y=0, s=1.0, flip=False, arms="down", eyes="open", mouth="smile", animated=False, talking_ready=False):
    """Lio cu picioarele la (x, y). Înălțime ≈ 290·s."""
    front_arms = arms in ("up", "wave")
    arms_markup = arms_svg(arms, animated)
    return f'''<g transform="translate({x},{y}) scale({-s if flip else s},{s})">
  <ellipse cx="0" cy="4" rx="66" ry="11" fill="#000" opacity=".13"/>
  <path d="M44,-36 C96,-30 112,-74 96,-104" stroke="{FUR_SHADE}" stroke-width="11" fill="none" stroke-linecap="round"/>
  {ring(96, -112, 6, 5, 9, MANE)}
  <ellipse cx="-26" cy="-12" rx="25" ry="17" fill="{FUR_SHADE}"/><ellipse cx="26" cy="-12" rx="25" ry="17" fill="{FUR_SHADE}"/>
  <path d="M-34,-6 v-8 M-26,-4 v-9 M-18,-6 v-8 M18,-6 v-8 M26,-4 v-9 M34,-6 v-8" stroke="{MANE_DARK}" stroke-width="2.5" stroke-linecap="round" opacity=".5"/>
  <ellipse cx="0" cy="-62" rx="52" ry="56" fill="{FUR}"/>
  <ellipse cx="0" cy="-50" rx="32" ry="36" fill="{CREAM}"/>
  {"" if front_arms else arms_markup}
  {head_svg(eyes, mouth, animated, talking_ready)}
  <path d="M-46,-106 Q0,-86 46,-106 L44,-89 Q0,-68 -44,-89 Z" fill="{SCARF}"/>
  <path d="M16,-86 L36,-44 L20,-42 L10,-82 Z" fill="{SCARF_DARK}"/>
  <path d="M20,-43 l-2,8 M28,-43 l1,8" stroke="{SCARF_DARK}" stroke-width="3" stroke-linecap="round"/>
  <circle cx="14" cy="-85" r="8" fill="{SCARF_DARK}"/>
  <path d="{star_path(-26, -94, 6)}" fill="{STAR}"/><path d="{star_path(-3, -88, 6)}" fill="{STAR}"/><path d="{star_path(32, -97, 5)}" fill="{STAR}"/>
  {arms_markup if front_arms else ""}
</g>'''


TALK_STYLE = """<style>
  .lio-mouth-open { opacity: 0; }
  .is-talking .lio-mouth-open { animation: lio-talk .32s steps(1) infinite; }
  .is-talking .lio-mouth-smile { animation: lio-talk .32s steps(1) infinite reverse; }
  @keyframes lio-talk { 0% { opacity: 1; } 50% { opacity: 0; } }
</style>"""


def standalone(content, view_box, label, style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" role="img" aria-label="{label}">'
            f'<title>{label}</title>{style}{content}</svg>\n')


def head_only(animated=False, talking_ready=False):
    return f'<g>{head_svg(animated=animated, talking_ready=talking_ready)}</g>'


def main():
    img = ROOT / "public" / "assets" / "img"
    img.mkdir(parents=True, exist_ok=True)
    (img / "lio.svg").write_text(
        standalone(lio(arms="wave", animated=True, talking_ready=True), "-135 -290 270 300", "Lio", TALK_STYLE), encoding="utf-8")
    (img / "lio-static.svg").write_text(
        standalone(lio(arms="wave"), "-135 -290 270 300", "Lio"), encoding="utf-8")
    # Lio bucuros (răspuns corect): brațele sus, gura deschisă, sare de bucurie
    hop = ('<animateTransform attributeName="transform" type="translate" values="0 0;0 -14;0 0;0 0" '
           'keyTimes="0;.2;.4;1" dur="1.2s" repeatCount="indefinite"/>')
    (img / "lio-bravo.svg").write_text(
        standalone(f'<g>{lio(arms="up", mouth="open")}{hop}</g>', "-135 -300 270 310", "Lio se bucură"), encoding="utf-8")
    (img / "lio-bravo-static.svg").write_text(
        standalone(lio(arms="up", mouth="open"), "-135 -300 270 310", "Lio se bucură"), encoding="utf-8")
    # Lio somnoros (modul de culcare): ochii închiși, lăbuțele ținute la piept
    (img / "lio-somnoros.svg").write_text(
        standalone(lio(arms="hold", eyes="closed"), "-135 -290 270 300", "Lio somnoros"), encoding="utf-8")
    (img / "lio-cap.svg").write_text(
        standalone(head_only(animated=True, talking_ready=True), "-92 -272 184 184", "Lio", TALK_STYLE), encoding="utf-8")
    (ROOT / "public" / "favicon.svg").write_text(
        standalone(head_only(), "-92 -272 184 184", "Lio"), encoding="utf-8")
    print("Lio regenerat.")


if __name__ == "__main__":
    main()
