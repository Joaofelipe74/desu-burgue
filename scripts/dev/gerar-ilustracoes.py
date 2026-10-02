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

# Arte do banner da página inicial (fundo transparente)
files['hero'] = frame(shadow(rx=175) + cup(318, 252, 0.95) + fries_box(98, 256, 0.82) + mini_burger(205, 268, 0.82), title='Ilustração de hambúrguer com batata e refrigerante', bg=False)

for name, svg in files.items():
    with open(os.path.join(OUT, f'{name}.svg'), 'w') as f:
        f.write(svg)
print(len(files), 'ilustrações geradas:', ', '.join(sorted(files)))
