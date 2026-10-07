# Gera as ilustrações SVG dos produtos (desenhos originais, estilo flat).
import os, math

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'img', 'ilustracoes')
os.makedirs(OUT, exist_ok=True)

W, H = 400, 300

def frame(body, glow='#ffb703', title='', bg=True):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{title}">
<!-- Ilustração original Desu Burguer — não é foto do produto. -->
<defs>
  <radialGradient id="glow" cx="50%" cy="55%" r="55%">
    <stop offset="0" stop-color="{glow}" stop-opacity=".22"/>
    <stop offset="1" stop-color="{glow}" stop-opacity="0"/>
  </radialGradient>
</defs>
{('<rect width="%d" height="%d" fill="#1d1d1d"/><rect width="%d" height="%d" fill="url(#glow)"/>' % (W, H, W, H)) if bg else ''}
{body}
</svg>
'''

def shadow(cx=200, cy=262, rx=120, ry=13):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#000" opacity=".45"/>'

# ---------- camadas do hambúrguer (empilhadas de baixo para cima) ----------

def bun_bottom(y, w, color='#d98a3d'):
    x = 200 - w / 2
    return (f'<path d="M{x+6},{y} h{w-12} q6,0 6,8 v8 q0,16 -18,16 h{-(w-24)} q-18,0 -18,-16 v-8 q0,-8 6,-8z" fill="{color}"/>'
            f'<path d="M{x+10},{y+22} h{w-20}" stroke="#b86f2c" stroke-width="3" stroke-linecap="round" opacity=".5"/>'), 32

def patty(y, w, color="#5a3726", ph=26, spots="#7a4b33"):
    h = ph
    x = 200 - w / 2
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{color}"/>'
    for i in range(7):
        sx = x + 20 + i * (w - 40) / 6
        s += f'<ellipse cx="{sx:.1f}" cy="{y + h/2 + (3 if i % 2 else -3)}" rx="4" ry="2" fill="{spots}"/>'
    return s, h - 4

def crispy(y, w):
    x = 200 - w / 2
    pts = []
    n = 18
    for i in range(n + 1):
        px = x + i * w / n
        pts.append(f'{px:.1f},{y + (0 if i % 2 else 5)}')
    top = ' L'.join(pts)
    s = (f'<path d="M{x},{y+14} L{top} L{x+w},{y+14} q0,16 -16,16 H{x+16} q-16,0 -16,-16z" fill="#d6912f"/>'
         f'<path d="M{x+12},{y+16} h{w-24}" stroke="#f0b552" stroke-width="4" stroke-linecap="round" stroke-dasharray="6 10"/>')
    return s, 26

def cheese(y, w, color='#ffc533'):
    x = 200 - w / 2 - 6
    ww = w + 12
    d = f'M{x},{y} h{ww} l-6,8 '
    # gotas
    d += f'L{x+ww-30},{y+8} q-4,14 -10,0 L{x+ww/2+20},{y+8} q-5,18 -12,0 L{x+50},{y+8} q-4,12 -10,0 L{x+8},{y+8} z'
    return f'<path d="{d}" fill="{color}"/>', 6

def lettuce(y, w, color='#6cc04a'):
    x = 200 - w / 2 - 10
    ww = w + 20
    n = 10
    d = f'M{x},{y+8} '
    for i in range(n):
        x0 = x + i * ww / n
        d += f'Q{x0 + ww/n/2:.1f},{y - 6 if i % 2 else y + 20} {x0 + ww/n:.1f},{y+8} '
    d += f'L{x+ww},{y+12} L{x},{y+12}z'
    return f'<path d="{d}" fill="{color}"/>', 10

def rucula(y, w):
    s = ''
    x = 200 - w / 2 - 6
    for i in range(9):
        lx = x + i * (w + 12) / 8
        s += f'<ellipse cx="{lx:.1f}" cy="{y+6}" rx="14" ry="6" fill="#4f9a3a" transform="rotate({-20 if i % 2 else 20} {lx:.1f} {y+6})"/>'
    return s, 8

def tomato(y, w):
    x = 200 - w / 2 + 8
    ww = w - 16
    return (f'<rect x="{x}" y="{y}" width="{ww/2-4}" height="12" rx="6" fill="#e2483d"/>'
            f'<rect x="{x+ww/2+4}" y="{y}" width="{ww/2-4}" height="12" rx="6" fill="#e2483d"/>'
            f'<rect x="{x+10}" y="{y+3}" width="{ww/2-24}" height="3" rx="1.5" fill="#ff8a7a"/>'), 10

def bacon(y, w):
    x = 200 - w / 2 - 4
    ww = w + 8
    s = ''
    for k, off in enumerate((0, 9)):
        d = f'M{x},{y+off+4} '
        for i in range(6):
            x0 = x + i * ww / 6
            d += f'Q{x0 + ww/12:.1f},{y+off - 4 if i % 2 == k % 2 else y+off+12} {x0 + ww/6:.1f},{y+off+4} '
        s += f'<path d="{d}" fill="none" stroke="#a63b28" stroke-width="9" stroke-linecap="round"/>'
        s += f'<path d="{d}" fill="none" stroke="#e98f6f" stroke-width="2.5" stroke-linecap="round" opacity=".8"/>'
    return s, 18

def egg(y, w):
    return (f'<path d="M{200-w/2+4},{y+10} q20,-14 60,-10 q40,-10 70,2 q30,-6 {w-138},{8} q-10,8 -40,6 h-{w-60} q-30,2 -30,-6z" fill="#fff8ec"/>'
            f'<ellipse cx="215" cy="{y+5}" rx="20" ry="9" fill="#ffb21f"/>'
            f'<ellipse cx="209" cy="{y+2}" rx="6" ry="3" fill="#ffd36b"/>'), 12

def onion(y, w):
    s = ''
    for i in range(7):
        cx = 200 - w / 2 + 18 + i * (w - 36) / 6
        s += f'<path d="M{cx-12:.1f},{y+6} q12,-10 24,0" fill="none" stroke="#8a4d1f" stroke-width="5" stroke-linecap="round"/>'
    return s, 6

def bun_top(y, w, color='#e39a45', seeds=True, shine='#f2b467'):
    x = 200 - w / 2
    h = 62
    s = (f'<path d="M{x},{y} q0,-{h} {w/2},-{h} q{w/2},0 {w/2},{h} q0,8 -10,8 h-{w-20} q-10,0 -10,-8z" fill="{color}"/>'
         f'<path d="M{x+30},{y-30} q20,-24 60,-26" fill="none" stroke="{shine}" stroke-width="8" stroke-linecap="round" opacity=".7"/>')
    if seeds:
        for (sx, sy, r) in [(-50, -38, 20), (-20, -50, -15), (12, -44, 30), (44, -36, -25), (-34, -20, 10), (30, -18, -10), (62, -16, 25), (-62, -14, -20), (0, -26, 0)]:
            s += f'<ellipse cx="{200+sx}" cy="{y+sy}" rx="5" ry="2.6" fill="#fff1d6" transform="rotate({r} {200+sx} {y+sy})"/>'
    return s, 0

def burger(layers, base=240, w=190, top_color='#e39a45', seeds=True, bottom_color='#d98a3d'):
    """Empilha as camadas de baixo para cima; cada camada recebe o topo atual (y)."""
    out = []
    s, _ = bun_bottom(base - 30, w, bottom_color)
    out.append(s)
    y = base - 30
    for layer in layers:
        s, h = layer(y, w)
        out.append(s)
        y -= h
    st, _ = bun_top(y - 2, w, top_color, seeds)
    out.append(st)
    return ''.join(out), y

def burger_svg(name, title, layers, **kw):
    body, _ = burger(layers, **kw)
    return frame(shadow() + f'<g transform="translate(0,4)">{body}</g>', title=title)

def L(fn, h, **kw):
    """Camada de altura h: desenha a partir de (y - h) até y."""
    def f(y, w):
        s, _ = fn(y - h, w, **kw)
        return s, h
    return f

files = {}

files['hamburguer'] = burger_svg('hamburguer', 'Ilustração de hambúrguer', [
    L(patty, 26), L(cheese, 8), L(tomato, 12), L(lettuce, 12)])
files['hamburguer-bacon'] = burger_svg('hamburguer-bacon', 'Ilustração de hambúrguer com bacon', [
    L(patty, 26), L(cheese, 8), L(bacon, 22)])
files['hamburguer-salada'] = burger_svg('hamburguer-salada', 'Ilustração de hambúrguer com salada', [
    L(patty, 26), L(cheese, 8), L(tomato, 12), L(lettuce, 12), L(tomato, 12), L(lettuce, 12)])
files['hamburguer-ovo'] = burger_svg('hamburguer-ovo', 'Ilustração de hambúrguer com ovo', [
    L(patty, 26), L(cheese, 8), L(egg, 14), L(lettuce, 12)])
files['hamburguer-tudo'] = burger_svg('hamburguer-tudo', 'Ilustração de hambúrguer completo', [
    L(patty, 24), L(cheese, 8), L(patty, 24), L(cheese, 8), L(bacon, 20), L(egg, 14), L(tomato, 12), L(lettuce, 12)], base=250, w=180)
files['smash-duplo'] = burger_svg('smash-duplo', 'Ilustração de hambúrguer smash duplo', [
    L(patty, 18, ph=18), L(cheese, 8), L(patty, 18, ph=18), L(cheese, 8), L(onion, 8)], top_color='#c9772f', seeds=False, bottom_color='#c9772f')
files['frango'] = burger_svg('frango', 'Ilustração de sanduíche de frango empanado', [
    L(crispy, 28), L(tomato, 12), L(lettuce, 12)], top_color='#d98a3d', seeds=False)
files['veggie'] = burger_svg('veggie', 'Ilustração de hambúrguer vegetariano', [
    L(patty, 26, color='#8a7a3a', spots='#a59447'), L(cheese, 8, color='#ffe08a'), L(tomato, 12), L(rucula, 10)])

# ---------- acompanhamentos ----------

def fries_box(cx=200, base=250, scale=1.0, cheddar=False):
    s = f'<g transform="translate({cx},{base}) scale({scale})">'
    # batatas
    sticks = [(-40, -150, -8), (-24, -165, -3), (-8, -158, 4), (8, -170, -2), (24, -152, 6), (38, -160, 9), (-32, -138, 10), (16, -142, -9), (0, -146, 2)]
    for (x, y, r) in sticks:
        s += f'<rect x="{x-7}" y="{y}" width="14" height="110" rx="4" fill="#f6c445" transform="rotate({r} {x} {y+100})"/>'
        s += f'<rect x="{x-7}" y="{y}" width="5" height="110" rx="2" fill="#ffe08a" transform="rotate({r} {x} {y+100})"/>'
    if cheddar:
        s += '<path d="M-64,-104 q8,-26 30,-22 q14,-20 34,-12 q22,-14 36,6 q20,0 28,26 q-10,16 -14,4 q-8,22 -18,4 q-10,18 -20,0 q-12,20 -22,2 q-12,16 -20,0 q-12,14 -18,-6z" fill="#ffb21f"/>'
        s += '<path d="M-40,-118 q16,-10 34,-6" stroke="#ffd36b" stroke-width="5" fill="none" stroke-linecap="round"/>'
        for (x, y) in [(-44, -112), (-14, -122), (18, -114), (40, -106), (-28, -100), (4, -104)]:
            s += f'<rect x="{x}" y="{y}" width="10" height="7" rx="2" fill="#a63b28"/>'
    # caixa
    s += '<path d="M-62,-100 L62,-100 L50,0 L-50,0z" fill="#d63a2f"/>'
    s += '<path d="M-62,-100 q62,26 124,0 L60,-84 q-60,22 -120,0z" fill="#b52d24"/>'
    s += '<circle cx="0" cy="-42" r="18" fill="#ffb703"/><text x="0" y="-34" font-family="Arial, sans-serif" font-size="22" font-weight="900" text-anchor="middle" fill="#d63a2f">D</text>'
    s += '</g>'
    return s

files['batata'] = frame(shadow(rx=80) + fries_box(), title='Ilustração de batata frita')
files['batata-cheddar'] = frame(shadow(rx=80) + fries_box(cheddar=True), title='Ilustração de batata com cheddar e bacon')

def rings():
    s = shadow(rx=110)
    pos = [(150, 225), (250, 225), (200, 232), (175, 190), (228, 192), (200, 150)]
    for (x, y) in pos:
        s += f'<ellipse cx="{x}" cy="{y}" rx="48" ry="30" fill="none" stroke="#c9822b" stroke-width="20"/>'
        s += f'<ellipse cx="{x}" cy="{y}" rx="48" ry="30" fill="none" stroke="#e7a945" stroke-width="10" stroke-dasharray="8 6"/>'
    return s
files['onion-rings'] = frame(rings(), title='Ilustração de anéis de cebola')

def nuggets():
    s = shadow(rx=130)
    s += '<ellipse cx="200" cy="245" rx="135" ry="26" fill="#efe6d8"/><ellipse cx="200" cy="240" rx="120" ry="20" fill="#fff8ec"/>'
    blobs = [(140, 222), (185, 228), (232, 224), (160, 196), (208, 200), (184, 172)]
    for (x, y) in blobs:
        s += f'<path d="M{x-28},{y} q-4,-22 22,-24 q26,-4 32,14 q8,22 -16,28 q-34,8 -38,-18z" fill="#d6912f"/>'
        s += f'<path d="M{x-18},{y-8} q8,-10 22,-8" fill="none" stroke="#f0b552" stroke-width="4" stroke-linecap="round"/>'
    s += '<path d="M268,232 h56 l-6,26 h-44z" fill="#ffffff"/><ellipse cx="296" cy="232" rx="28" ry="8" fill="#e2483d"/>'
    return s
files['nuggets'] = frame(nuggets(), title='Ilustração de nuggets')

# ---------- combos ----------

def mini_burger(cx, base, scale):
    body, _ = burger([L(patty, 26), L(cheese, 8), L(bacon, 22)])
    return f'<g transform="translate({cx-200*scale},{base-240*scale}) scale({scale})">{body}</g>'

def cup(cx, base, scale=1.0, color='#e2483d'):
    return (f'<g transform="translate({cx},{base}) scale({scale})">'
            f'<rect x="6" y="-190" width="6" height="60" rx="3" fill="#ffffff" transform="rotate(12 9 -160)"/>'
            f'<path d="M-46,-140 h92 l-12,140 h-68z" fill="{color}"/>'
            f'<rect x="-50" y="-150" width="100" height="14" rx="5" fill="#f4f4f4"/>'
            f'<path d="M-40,-100 h80" stroke="#ffffff" stroke-width="8" opacity=".9"/>'
            f'<path d="M-36,-82 h72" stroke="#ffb703" stroke-width="5"/>'
            f'</g>')

files['combo'] = frame(shadow(rx=170) + cup(300, 252, 0.95) + fries_box(110, 256, 0.8) + mini_burger(205, 262, 0.72), title='Ilustração de combo com hambúrguer, batata e refrigerante')

def bottle(cx, base, scale=1.0, liquid='#3b1d14', label='#e2483d', cap='#d63a2f'):
    return (f'<g transform="translate({cx},{base}) scale({scale})">'
            f'<rect x="-14" y="-228" width="28" height="16" rx="3" fill="{cap}"/>'
            f'<path d="M-12,-212 h24 q0,22 22,40 q10,8 10,24 v136 q0,12 -12,12 h-64 q-12,0 -12,-12 v-136 q0,-16 10,-24 q22,-18 22,-40z" fill="{liquid}"/>'
            f'<rect x="-44" y="-120" width="88" height="46" rx="4" fill="{label}"/>'
            f'<path d="M-30,-97 h60" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>'
            f'<path d="M-30,-180 q-6,40 0,150" stroke="#ffffff" stroke-width="5" opacity=".18" fill="none"/>'
            f'</g>')

files['combo-familia'] = frame(shadow(rx=175) + bottle(318, 258, 0.85) + fries_box(232, 258, 0.75) + mini_burger(120, 250, 0.55) + mini_burger(185, 268, 0.6), title='Ilustração de combo família')

# ---------- bebidas ----------

def can():
    return (shadow(rx=60) +
            '<g transform="translate(200,258)">'
            '<path d="M-48,-190 h96 v180 q0,10 -10,10 h-76 q-10,0 -10,-10z" fill="#c62f26"/>'
            '<ellipse cx="0" cy="-190" rx="48" ry="10" fill="#cfcfcf"/><ellipse cx="0" cy="-191" rx="36" ry="6" fill="#a9a9a9"/>'
            '<rect x="-12" y="-196" width="24" height="7" rx="3" fill="#e6e6e6"/>'
            '<path d="M-48,-120 q48,30 96,0 v34 q-48,30 -96,0z" fill="#ffffff"/>'
            '<path d="M-48,-104 q48,26 96,0" stroke="#ffb703" stroke-width="5" fill="none"/>'
            '<rect x="-36" y="-180" width="10" height="160" rx="5" fill="#ffffff" opacity=".18"/>'
            '</g>')
files['refrigerante-lata'] = frame(can(), title='Ilustração de lata de refrigerante')
files['refrigerante-2l'] = frame(shadow(rx=60) + bottle(200, 262, 1.05), title='Ilustração de garrafa de refrigerante')

def glass(liquid, base=258, straw='#ffffff', extra=''):
    return (shadow(rx=70) +
            f'<g transform="translate(200,{base})">'
            f'<rect x="12" y="-232" width="9" height="120" rx="4" fill="{straw}" transform="rotate(14 16 -170)"/>'
            f'<path d="M-56,-180 h112 l-14,176 q-1,4 -5,4 h-74 q-4,0 -5,-4z" fill="#ffffff" opacity=".18"/>'
            f'<path d="M-50,-150 h100 l-11,142 q-1,4 -5,4 h-68 q-4,0 -5,-4z" fill="{liquid}"/>'
            f'<path d="M-40,-140 l8,124" stroke="#ffffff" stroke-width="6" opacity=".25" stroke-linecap="round"/>'
            f'{extra}</g>')

files['suco'] = frame(glass('#f59e1b', extra='<circle cx="48" cy="-176" r="26" fill="#f7b733"/><circle cx="48" cy="-176" r="19" fill="#ffd36b"/><path d="M48,-195 v38 M29,-176 h38 M35,-189 l26,26 M61,-189 l-26,26" stroke="#f7b733" stroke-width="2"/>'), title='Ilustração de suco natural')
files['milkshake'] = frame(glass('#e9a0b4', straw='#e2483d', extra='<path d="M-56,-178 q-6,-34 26,-36 q8,-26 34,-18 q28,-12 38,16 q30,4 14,38z" fill="#fff8ec"/><circle cx="6" cy="-232" r="11" fill="#d62839"/><path d="M6,-242 q4,-14 14,-18" stroke="#3f7d2a" stroke-width="3" fill="none"/>'), title='Ilustração de milk-shake')

def water():
    return (shadow(rx=50) + '<g transform="translate(200,262)">'
            '<rect x="-12" y="-222" width="24" height="14" rx="3" fill="#2f7fd1"/>'
            '<path d="M-10,-208 h20 q0,18 16,30 q8,6 8,18 v150 q0,10 -10,10 h-48 q-10,0 -10,-10 v-150 q0,-12 8,-18 q16,-12 16,-30z" fill="#bfe3ff" opacity=".85"/>'
            '<path d="M-34,-120 h68 v40 h-68z" fill="#2f7fd1"/><path d="M-24,-100 q12,-12 24,0 t24,0" stroke="#ffffff" stroke-width="4" fill="none"/>'
            '<path d="M-22,-170 v130" stroke="#ffffff" stroke-width="5" opacity=".5" stroke-linecap="round"/>'
            '</g>')
files['agua'] = frame(water(), glow='#7cc4ff', title='Ilustração de garrafa de água')

# ---------- sobremesas ----------

def plate(cy=248, rx=130):
    return f'<ellipse cx="200" cy="{cy}" rx="{rx}" ry="24" fill="#efe6d8"/><ellipse cx="200" cy="{cy-4}" rx="{rx-16}" ry="17" fill="#fff8ec"/>'

def scoop(cx, cy, color='#fff3d6'):
    return (f'<path d="M{cx-34},{cy} q-4,-38 34,-40 q38,2 34,40 q-8,-6 -14,0 q-8,-8 -18,0 q-10,-8 -18,0 q-10,-6 -18,0z" fill="{color}"/>'
            f'<path d="M{cx-18},{cy-24} q10,-10 22,-8" stroke="#ffffff" stroke-width="5" fill="none" stroke-linecap="round"/>')

files['brownie'] = frame(shadow(rx=135) + plate() +
    '<path d="M120,236 l20,-70 h120 l20,70z" fill="#4a2a1c"/><path d="M140,166 h120 l-10,-22 h-100z" fill="#5e3624"/>'
    '<path d="M150,190 h20 M200,206 h24 M236,184 h16" stroke="#6e4430" stroke-width="5" stroke-linecap="round"/>' +
    scoop(214, 150) + '<path d="M180,148 q10,20 4,40 M240,150 q-4,24 6,36" stroke="#3a2016" stroke-width="6" fill="none" stroke-linecap="round"/>',
    title='Ilustração de brownie com sorvete')

files['petit-gateau'] = frame(shadow(rx=135) + plate() +
    '<path d="M136,236 q-6,-80 64,-84 q70,4 64,84z" fill="#3e2217"/>'
    '<path d="M196,154 q14,30 0,52 q-8,20 14,32 l-60,0 q24,-10 20,-34 q-8,-28 26,-50z" fill="#2a160e"/>'
    '<path d="M160,236 q20,-14 40,-2 q20,10 44,0 l12,2 h-108z" fill="#2a160e"/>' +
    scoop(286, 214, '#fff3d6') + '<path d="M276,180 q4,-12 14,-14" stroke="#3f7d2a" stroke-width="4" fill="none"/>',
    title='Ilustração de petit gâteau')

files['pudim'] = frame(shadow(rx=135) + plate() +
    '<path d="M126,236 l22,-92 q52,-16 104,0 l22,92z" fill="#f2c45a"/>'
    '<path d="M148,144 q52,-16 104,0 l-4,16 q-48,-12 -96,0z" fill="#9a4b14"/>'
    '<path d="M162,160 q-4,22 2,36 M236,160 q4,18 -2,30" stroke="#9a4b14" stroke-width="7" fill="none" stroke-linecap="round"/>'
    '<ellipse cx="200" cy="144" rx="30" ry="6" fill="#7a3a0e"/>',
    title='Ilustração de pudim')

# ---------- ampliação do cardápio (06/10/2026) ----------

def calabresa(y, w):
    s = ''
    for i in range(6):
        cx = 200 - w / 2 + 22 + i * (w - 44) / 5
        s += f'<ellipse cx="{cx:.1f}" cy="{y+7}" rx="17" ry="8" fill="#b4462f"/><ellipse cx="{cx:.1f}" cy="{y+6}" rx="12" ry="5" fill="#d0654b"/>'
        s += f'<circle cx="{cx-4:.1f}" cy="{y+6}" r="1.6" fill="#f3c7a8"/><circle cx="{cx+4:.1f}" cy="{y+5}" r="1.4" fill="#f3c7a8"/>'
    for i in range(5):
        cx = 200 - w / 2 + 34 + i * (w - 68) / 4
        s += f'<path d="M{cx-10:.1f},{y+2} q10,-8 20,0" stroke="#f1e4c6" stroke-width="3" fill="none" stroke-linecap="round"/>'
    return s, 12

def shredded(y, w, color='#e0c08e', dark='#c49a5f'):
    s = f'<rect x="{200-w/2+4}" y="{y}" width="{w-8}" height="20" rx="10" fill="{color}"/>'
    for i in range(14):
        x = 200 - w / 2 + 14 + i * (w - 28) / 13
        s += f'<path d="M{x:.1f},{y+4} l{(-1)**i*6},12" stroke="{dark}" stroke-width="3" stroke-linecap="round"/>'
    return s, 18

def drip(y, w, color, big=False):
    x = 200 - w / 2 - 4
    ww = w + 8
    k = 16 if big else 10
    d = f'M{x},{y} h{ww} l-4,6 L{x+ww-26},{y+6} q-5,{k} -11,0 L{x+ww/2+18},{y+6} q-6,{k+6} -13,0 L{x+44},{y+6} q-5,{k} -11,0 L{x+6},{y+6} z'
    return f'<path d="{d}" fill="{color}"/>', 6

def corn(y, w):
    s = ''
    for i in range(10):
        x = 200 - w / 2 + 18 + i * (w - 36) / 9
        s += f'<circle cx="{x:.1f}" cy="{y + (2 if i % 2 else 6)}" r="4" fill="#f7c331"/>'
    return s, 6

def grill_patty(y, w, color='#6b3a2a', ph=30):
    s, h = patty(y, w, color=color, ph=ph, spots='#87503a')
    for i in range(4):
        x = 200 - w / 2 + 30 + i * (w - 60) / 3
        s += f'<path d="M{x:.1f},{y+6} l14,{ph-12}" stroke="#3a1d12" stroke-width="4" stroke-linecap="round" opacity=".7"/>'
    return s, h

def coalho(y, w):
    x = 200 - w / 2 + 10
    s = f'<rect x="{x}" y="{y}" width="{w-20}" height="12" rx="4" fill="#f4d79a"/>'
    for i in range(5):
        xx = x + 18 + i * (w - 56) / 4
        s += f'<path d="M{xx:.1f},{y+2} l10,8" stroke="#c98e3c" stroke-width="3" stroke-linecap="round"/>'
    return s, 10

def vinagrete(y, w):
    s = ''
    colors = ['#e2483d', '#6cc04a', '#fff1d6', '#e2483d', '#6cc04a']
    for i in range(16):
        x = 200 - w / 2 + 12 + i * (w - 24) / 15
        s += f'<rect x="{x:.1f}" y="{y + (i % 3) * 2}" width="7" height="6" rx="1.5" fill="{colors[i % 5]}"/>'
    return s, 8

def gorgonzola(y, w):
    x = 200 - w / 2 - 2
    s = f'<path d="M{x},{y} h{w+4} l-8,10 h-{w-12}z" fill="#f2efe2"/>'
    for i in range(12):
        xx = x + 14 + i * (w - 24) / 11
        s += f'<circle cx="{xx:.1f}" cy="{y + 4 + (i % 2) * 3}" r="2.2" fill="#5f8a7c"/>'
    return s, 8

def honey(y, w):
    return (f'<path d="M{200-w/2+10},{y+2} q30,10 60,0 t60,0 t50,0" stroke="#e6a417" stroke-width="5" fill="none" stroke-linecap="round"/>'
            f'<path d="M{200+20},{y+4} q2,14 -2,18" stroke="#e6a417" stroke-width="4" fill="none" stroke-linecap="round"/>'), 4

def onion_crispy(y, w):
    s = ''
    for i in range(18):
        x = 200 - w / 2 + 8 + i * (w - 16) / 17
        s += f'<path d="M{x:.1f},{y+10} q6,{-12 if i % 2 else -6} 12,0" stroke="#d99a2b" stroke-width="4" fill="none" stroke-linecap="round"/>'
    return s, 10

def pickles(y, w):
    s = ''
    for i in range(5):
        x = 200 - w / 2 + 28 + i * (w - 56) / 4
        s += f'<ellipse cx="{x:.1f}" cy="{y+5}" rx="13" ry="6" fill="#7da33a"/><ellipse cx="{x:.1f}" cy="{y+5}" rx="8" ry="3" fill="#a9c95b"/>'
    return s, 8

def jalapeno(y, w):
    s = ''
    for i in range(6):
        x = 200 - w / 2 + 24 + i * (w - 48) / 5
        s += f'<circle cx="{x:.1f}" cy="{y+5}" r="8" fill="#3f8f2e"/><circle cx="{x:.1f}" cy="{y+5}" r="4" fill="#bfe08a"/>'
    return s, 8

BRIOCHE = dict(top_color='#c9772f', seeds=False, bottom_color='#c9772f')
AUSTRALIANO = dict(top_color='#5b3220', seeds=True, bottom_color='#5b3220')

files['x-calabresa'] = burger_svg('x-calabresa', 'Ilustração de hambúrguer com calabresa', [
    L(patty, 26), L(cheese, 8), L(calabresa, 14), L(lettuce, 12)])
files['x-frango'] = burger_svg('x-frango', 'Ilustração de sanduíche de frango com catupiry', [
    L(shredded, 20), L(drip, 8, color='#fbf6ea', big=True), L(corn, 8), L(lettuce, 12)])
files['x-cheddar'] = burger_svg('x-cheddar', 'Ilustração de hambúrguer com cheddar e bacon', [
    L(patty, 26), L(drip, 8, color='#f59e0b', big=True), L(bacon, 22), L(drip, 8, color='#f59e0b')])
files['smash'] = burger_svg('smash', 'Ilustração de smash burger', [
    L(patty, 18, ph=18), L(cheese, 8), L(onion, 8)], **BRIOCHE)
files['smash-bacon'] = burger_svg('smash-bacon', 'Ilustração de smash burger com bacon', [
    L(patty, 18, ph=18), L(cheese, 8), L(patty, 18, ph=18), L(cheese, 8), L(bacon, 20)], **BRIOCHE)
files['smash-triplo'] = burger_svg('smash-triplo', 'Ilustração de smash burger triplo', [
    L(patty, 18, ph=18), L(cheese, 8), L(patty, 18, ph=18), L(cheese, 8), L(patty, 18, ph=18), L(cheese, 8)], base=250, **BRIOCHE)
files['smash-picante'] = burger_svg('smash-picante', 'Ilustração de smash burger picante', [
    L(patty, 18, ph=18), L(cheese, 8, color='#fff1d6'), L(patty, 18, ph=18), L(cheese, 8, color='#fff1d6'), L(jalapeno, 10)], **BRIOCHE)
files['premium-costela'] = burger_svg('premium-costela', 'Ilustração de hambúrguer de costela', [
    L(grill_patty, 30, color='#5a2e1f'), L(cheese, 8, color='#f6c453'), L(shredded, 20, color='#7a3b22', dark='#4f2416'), L(drip, 8, color='#7a2410', big=True)], **BRIOCHE)
files['premium-picanha'] = burger_svg('premium-picanha', 'Ilustração de hambúrguer de picanha', [
    L(grill_patty, 30, color='#7a3b2a'), L(coalho, 12), L(vinagrete, 10)], **AUSTRALIANO)
files['premium-gorgonzola'] = burger_svg('premium-gorgonzola', 'Ilustração de hambúrguer com gorgonzola e mel', [
    L(grill_patty, 30), L(gorgonzola, 10), L(honey, 6), L(rucula, 10)], **BRIOCHE)
files['premium-onion'] = burger_svg('premium-onion', 'Ilustração de hambúrguer com cebola crispy', [
    L(grill_patty, 30), L(drip, 8, color='#f59e0b', big=True), L(onion_crispy, 14)], **BRIOCHE)
files['premium-bbq'] = burger_svg('premium-bbq', 'Ilustração de hambúrguer barbecue defumado', [
    L(grill_patty, 30), L(drip, 8, color='#7a2410', big=True), L(bacon, 22), L(pickles, 10)], **AUSTRALIANO)

# hot dogs
def hotdog(variant='tradicional'):
    s = shadow(rx=150)
    s += '<g transform="rotate(-8 200 200)">'
    s += '<path d="M60,200 q0,-36 40,-36 h200 q40,0 40,36 q0,30 -40,30 h-200 q-40,0 -40,-30z" fill="#d98a3d"/>'
    sausages = [0] if variant != 'especial' else [-8, 8]
    for off in sausages:
        s += f'<rect x="58" y="{176+off}" width="284" height="26" rx="13" fill="#b5452f"/><path d="M78,{184+off} h244" stroke="#d26a50" stroke-width="4" stroke-linecap="round"/>'
    s += '<path d="M70,196 q0,-20 30,-22 h200 q30,2 30,22" fill="none" stroke="#e8a35a" stroke-width="10" stroke-linecap="round"/>'
    if variant == 'tradicional':
        s += '<path d="M90,178 l20,-10 l20,10 l20,-10 l20,10 l20,-10 l20,10 l20,-10 l20,10 l20,-10 l20,10 l20,-10 l20,10" stroke="#e2483d" stroke-width="7" fill="none" stroke-linejoin="round"/>'
    if variant == 'especial':
        s += '<path d="M96,170 q20,-26 50,-14 q20,-18 50,-4 q24,-16 50,0 q26,-10 44,10z" fill="#fbf1d8"/>'
        s += '<path d="M100,172 q100,-24 200,0" stroke="#ffc533" stroke-width="7" fill="none" stroke-linecap="round"/>'
    if variant == 'bacon':
        s += '<path d="M90,176 q30,-14 60,0 t60,0 t60,0 t40,0" stroke="#f59e0b" stroke-width="9" fill="none" stroke-linecap="round"/>'
        for x in range(104, 300, 26):
            s += f'<rect x="{x}" y="162" width="14" height="8" rx="2" fill="#a63b28"/>'
    # milho e batata palha
    for x in range(100, 300, 22):
        s += f'<circle cx="{x}" cy="{158 if variant != "bacon" else 172}" r="4" fill="#f7c331"/>'
    for i in range(16):
        x = 96 + i * 13
        s += f'<path d="M{x},{150 - (i % 3) * 3} l10,6" stroke="#f6d36b" stroke-width="3" stroke-linecap="round"/>'
    s += '</g>'
    return s

files['hotdog'] = frame(hotdog('tradicional'), title='Ilustração de cachorro-quente')
files['hotdog-especial'] = frame(hotdog('especial'), title='Ilustração de cachorro-quente especial')
files['hotdog-bacon'] = frame(hotdog('bacon'), title='Ilustração de cachorro-quente com bacon e cheddar')

# sanduíches
def toast_triangle(x, y, s=1.0, rot=0, bread='#e7b56a', crust='#b9783a', fill_layers=()):
    g = f'<g transform="translate({x},{y}) rotate({rot}) scale({s})">'
    g += f'<path d="M-90,40 L0,-80 L90,40 z" fill="{crust}"/><path d="M-76,32 L0,-66 L76,32 z" fill="{bread}"/>'
    yy = 40
    for color, h in fill_layers:
        g += f'<rect x="-94" y="{yy}" width="188" height="{h}" rx="{h/2}" fill="{color}"/>'
        yy += h - 2
    g += f'<path d="M-90,{yy} h180 l-8,14 h-164z" fill="{crust}"/>'
    g += '</g>'
    return g

files['misto-quente'] = frame(shadow(rx=140) + plate() +
    toast_triangle(168, 190, 0.85, -6, fill_layers=[('#f6c453', 10), ('#e99a9a', 10)]) +
    toast_triangle(250, 196, 0.8, 8, fill_layers=[('#f6c453', 10), ('#e99a9a', 10)]), title='Ilustração de misto quente')
files['sanduiche-natural'] = frame(shadow(rx=140) + plate() +
    toast_triangle(200, 186, 0.95, 0, bread='#b98a58', crust='#7d5530', fill_layers=[('#6cc04a', 10), ('#f08c2b', 8), ('#efdcb4', 12)]), title='Ilustração de sanduíche natural')
files['beirute'] = frame(shadow(rx=150) + plate() +
    '<path d="M70,226 q130,-150 260,0 z" fill="#e6c58f"/><path d="M84,222 q116,-128 232,0" fill="none" stroke="#c99a58" stroke-width="6"/>'
    '<path d="M96,226 q104,-40 208,0" fill="#efdcb4"/><path d="M100,222 q100,-30 200,0" stroke="#6cc04a" stroke-width="8" fill="none"/>'
    '<path d="M120,226 q80,-20 160,0" stroke="#e2483d" stroke-width="7" fill="none"/>', title='Ilustração de beirute')

# porções
def bowl(inner, cy=250, color='#2f2f2f'):
    return (f'<path d="M80,{cy-70} h240 q-10,70 -60,74 h-120 q-50,-4 -60,-74z" fill="{color}"/>'
            f'<ellipse cx="200" cy="{cy-70}" rx="120" ry="16" fill="#3a3a3a"/>' + inner)

def sticks(color, light, n=11, w=16, cy=172):
    s = ''
    for i in range(n):
        x = 100 + i * 200 / (n - 1)
        r = (-1) ** i * (8 + (i % 3) * 4)
        s += f'<rect x="{x - w/2:.1f}" y="{cy - 60 + (i % 4) * 6}" width="{w}" height="80" rx="6" fill="{color}" transform="rotate({r} {x:.1f} {cy+20})"/>'
        s += f'<rect x="{x - w/2:.1f}" y="{cy - 60 + (i % 4) * 6}" width="5" height="80" rx="2" fill="{light}" transform="rotate({r} {x:.1f} {cy+20})"/>'
    return s

files['mandioca'] = frame(shadow(rx=130) + sticks('#f1dfa8', '#fff6d8', n=9, w=22) + bowl(''), title='Ilustração de mandioca frita')
def strips():
    s = ''
    for i in range(8):
        x = 110 + i * 26
        s += f'<path d="M{x},{196 - (i % 2) * 12} q14,-40 30,-10 q8,30 -12,40 q-24,4 -18,-30z" fill="#d6912f"/>'
    return s
files['isca-frango'] = frame(shadow(rx=130) + bowl(strips()) + '<path d="M300,226 h48 l-6,26 h-36z" fill="#ffffff"/><ellipse cx="324" cy="226" rx="24" ry="7" fill="#7a2410"/>', title='Ilustração de iscas de frango')
def mixed():
    s = shadow(rx=170) + plate(250, 168)
    s += sticks('#f6c445', '#ffe08a', n=7, w=12, cy=196).replace('translate', 'translate')
    for (x, y) in [(150, 214), (196, 220)]:
        s += f'<ellipse cx="{x}" cy="{y}" rx="34" ry="20" fill="none" stroke="#c9822b" stroke-width="13"/>'
    for i in range(4):
        x = 250 + i * 22
        s += f'<path d="M{x},{224 - (i % 2) * 8} q12,-30 26,-8 q6,22 -10,30 q-20,4 -16,-22z" fill="#d6912f"/>'
    return s
files['porcao-mista'] = frame(mixed(), title='Ilustração de porção mista')
def wedges():
    s = ''
    for i in range(9):
        x = 110 + i * 22
        s += f'<path d="M{x},{190 - (i % 3) * 8} q14,-34 34,-8 l-10,30 z" fill="#e9b45c" stroke="#9b5d26" stroke-width="5" stroke-linejoin="round"/>'
    s += '<path d="M150,150 l30,-14 M170,160 l26,-18 M240,150 l28,-12" stroke="#4f8a3a" stroke-width="3" stroke-linecap="round"/>'
    return s
files['batata-rustica'] = frame(shadow(rx=130) + bowl(wedges()), title='Ilustração de batata rústica')

# kids
def juice_box(cx, base, color='#8e4fc3'):
    return (f'<g transform="translate({cx},{base})"><rect x="-26" y="-86" width="52" height="86" rx="6" fill="{color}"/>'
            f'<path d="M-26,-86 l10,-12 h32 l10,12z" fill="#b783e0"/><rect x="6" y="-122" width="5" height="34" fill="#ffffff" transform="rotate(10 8 -105)"/>'
            f'<circle cx="0" cy="-42" r="14" fill="#ffd36b"/></g>')
def star(cx, cy, r=14, color='#ffb703'):
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f'{cx + rr*math.cos(ang):.1f},{cy - rr*math.sin(ang):.1f}')
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'
files['kids'] = frame(shadow(rx=160) + juice_box(300, 258) + fries_box(108, 258, 0.6) + mini_burger(205, 262, 0.55) + star(330, 90) + star(80, 80, 10, '#e2483d'), title='Ilustração de lanche kids')
files['kids-nuggets'] = frame(shadow(rx=160) + juice_box(310, 258, '#e2483d') + fries_box(100, 258, 0.6) +
    ''.join(f'<path d="M{x-24},{y} q-4,-18 18,-20 q22,-4 28,12 q6,18 -14,24 q-28,6 -32,-16z" fill="#d6912f"/>' for (x, y) in [(190, 250), (226, 254), (208, 226)]) +
    star(340, 90) + star(70, 84, 10, '#2f7fd1'), title='Ilustração de nuggets kids')

# molhos
def ramekin(sauce, light):
    return (shadow(rx=90) + '<path d="M120,170 h160 l-14,84 h-132z" fill="#f4f1ea"/><ellipse cx="200" cy="170" rx="80" ry="18" fill="#ffffff"/>'
            f'<ellipse cx="200" cy="172" rx="68" ry="13" fill="{sauce}"/><path d="M168,168 q20,-10 44,-4" stroke="{light}" stroke-width="5" fill="none" stroke-linecap="round"/>')
files['molho-maionese'] = frame(ramekin('#f6efd6', '#fffbea'), title='Ilustração de pote de maionese')
files['molho-barbecue'] = frame(ramekin('#6e2414', '#9a3f25'), title='Ilustração de pote de barbecue')
files['molho-cheddar'] = frame(ramekin('#f59e0b', '#ffd36b'), title='Ilustração de pote de cheddar')
files['molho-verde'] = frame(ramekin('#9fc95c', '#d4ec9f'), title='Ilustração de pote de maionese verde')

# bebidas
files['refrigerante-600'] = frame(shadow(rx=50) + bottle(200, 262, 0.82, liquid='#5a2d14', label='#2f7fd1', cap='#2f7fd1'), title='Ilustração de refrigerante 600 ml')
files['limonada'] = frame(glass('#f3f6d8', straw='#6cc04a', extra='<circle cx="48" cy="-176" r="24" fill="#7dbb3c"/><circle cx="48" cy="-176" r="18" fill="#d6ee9a"/><path d="M48,-193 v34 M31,-176 h34" stroke="#7dbb3c" stroke-width="2"/>'), title='Ilustração de limonada suíça')
files['cha-gelado'] = frame(glass('#d28a2c', extra='<rect x="-30" y="-140" width="26" height="22" rx="4" fill="#ffffff" opacity=".55"/><rect x="2" y="-128" width="24" height="20" rx="4" fill="#ffffff" opacity=".5"/><path d="M30,-200 q30,-4 34,22 q-30,10 -34,-22z" fill="#f6a35f"/>'), title='Ilustração de chá gelado')

# açaí
def acai_cup(scale=1.0, cx=200, base=258):
    toppings = ('<path d="M-54,-170 q54,-26 108,0" stroke="#fff3e0" stroke-width="7" fill="none" stroke-linecap="round"/>'
                '<circle cx="-28" cy="-176" r="11" fill="#fff0b8"/><circle cx="-28" cy="-176" r="5" fill="#e8d48a"/>'
                '<circle cx="8" cy="-182" r="11" fill="#fff0b8"/><circle cx="8" cy="-182" r="5" fill="#e8d48a"/>'
                '<path d="M30,-186 q12,-14 22,0 q-4,16 -22,0z" fill="#e2483d"/>'
                + ''.join(f'<circle cx="{x}" cy="{-168 + (x % 3)}" r="3" fill="#a8743c"/>' for x in range(-44, 50, 9)))
    return (f'<g transform="translate({cx},{base}) scale({scale})">'
            '<path d="M-60,-170 h120 l-14,170 h-92z" fill="#ffffff" opacity=".2"/>'
            '<path d="M-56,-168 h112 l-13,164 h-86z" fill="#4b1f5c"/>'
            '<path d="M-44,-150 l8,140" stroke="#7c3f94" stroke-width="6" opacity=".7" stroke-linecap="round"/>'
            + toppings + '</g>')
files['acai'] = frame(shadow(rx=70) + acai_cup(0.9), glow='#a855f7', title='Ilustração de copo de açaí')
files['acai-grande'] = frame(shadow(rx=80) + acai_cup(1.08, base=262), glow='#a855f7', title='Ilustração de copo grande de açaí')
files['acai-tigela'] = frame(shadow(rx=140) + bowl(
    '<ellipse cx="200" cy="180" rx="116" ry="14" fill="#4b1f5c"/>'
    '<path d="M110,176 q90,-30 180,0" stroke="#fff3e0" stroke-width="7" fill="none" stroke-linecap="round"/>'
    + ''.join(f'<circle cx="{x}" cy="{172 + (x % 7)}" r="10" fill="#fff0b8"/><circle cx="{x}" cy="{172 + (x % 7)}" r="4" fill="#e8d48a"/>' for x in (130, 160, 250))
    + ''.join(f'<path d="M{x},{176} q10,-12 20,0 q-4,14 -20,0z" fill="#e2483d"/>' for x in (190, 270))
    + ''.join(f'<circle cx="{x}" cy="{184 + (x % 4)}" r="3" fill="#a8743c"/>' for x in range(104, 300, 8)),
    color='#7d3c98'), glow='#a855f7', title='Ilustração de tigela de açaí')

# sobremesas
def churros():
    s = shadow(rx=140) + plate()
    for i, (x, r) in enumerate([(150, -18), (190, -6), (230, 6), (270, 18)]):
        s += f'<g transform="rotate({r} {x} 230)"><rect x="{x-11}" y="120" width="22" height="116" rx="10" fill="#c27a35"/>'
        for k in range(5):
            s += f'<path d="M{x-6+k*3},{126} v104" stroke="#a5642a" stroke-width="2"/>'
        s += f'<circle cx="{x-4}" cy="150" r="2" fill="#fff8ec"/><circle cx="{x+5}" cy="190" r="2" fill="#fff8ec"/></g>'
    s += '<path d="M300,222 h52 l-6,26 h-40z" fill="#ffffff"/><ellipse cx="326" cy="222" rx="26" ry="8" fill="#a8652a"/>'
    return s
files['churros'] = frame(churros(), title='Ilustração de churros')
files['sorvete'] = frame(shadow(rx=110) + '<path d="M110,190 h180 q-10,60 -70,64 h-40 q-60,-4 -70,-64z" fill="#3b82c4"/><ellipse cx="200" cy="190" rx="90" ry="14" fill="#5b9bd5"/>' +
    scoop(168, 180, '#fff3d6') + scoop(234, 182, '#e9a0b4') + '<path d="M150,160 q30,24 50,4 q24,-18 54,2" stroke="#4a2a1c" stroke-width="7" fill="none" stroke-linecap="round"/>', title='Ilustração de sorvete')
files['mousse'] = frame(shadow(rx=80) + '<path d="M140,120 h120 l-10,120 q-50,20 -100,0z" fill="#ffffff" opacity=".2"/>'
    '<path d="M146,130 h108 l-9,106 q-45,16 -90,0z" fill="#f7d36b"/><ellipse cx="200" cy="130" rx="54" ry="10" fill="#f2b632"/>' +
    ''.join(f'<ellipse cx="{x}" cy="{129 + (x % 5)}" rx="4" ry="2.4" fill="#3a2a10"/>' for x in range(160, 244, 11)) +
    '<path d="M200,236 v18 M170,256 h60" stroke="#ffffff" stroke-width="6" opacity=".3" stroke-linecap="round"/>', title='Ilustração de mousse de maracujá')

# Arte do banner da página inicial (fundo transparente)
files['hero'] = frame(shadow(rx=175) + cup(318, 252, 0.95) + fries_box(98, 256, 0.82) + mini_burger(205, 268, 0.82), title='Ilustração de hambúrguer com batata e refrigerante', bg=False)

for name, svg in files.items():
    with open(os.path.join(OUT, f'{name}.svg'), 'w') as f:
        f.write(svg)
print(len(files), 'ilustrações geradas:', ', '.join(sorted(files)))
