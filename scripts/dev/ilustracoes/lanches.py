# Hambúrgueres: pães, carnes, queijos, molhos e recheios, empilhados em camadas.
import math

from .estilo import (Arte, fundo, sombra, realce, sombra_contato, suave, bolha, rng, n, CX)

PAES = {
    'classico': dict(crosta=[(0, '#f2b468'), (.45, '#d98a3a'), (1, '#99561f')],
                     miolo=[(0, '#fae6bb'), (1, '#e9c48a')],
                     topo=[(0, '#ffd894'), (.38, '#eda04b'), (.78, '#c4732b'), (1, '#8e4a17')],
                     brilho=.42, cobertura='gergelim'),
    'liso': dict(crosta=[(0, '#f2b468'), (.45, '#d98a3a'), (1, '#99561f')],
                 miolo=[(0, '#fae6bb'), (1, '#e9c48a')],
                 topo=[(0, '#ffd894'), (.38, '#eda04b'), (.78, '#c4732b'), (1, '#8e4a17')],
                 brilho=.42, cobertura=None),
    'brioche': dict(crosta=[(0, '#ea9d4c'), (.45, '#c96d24'), (1, '#7c3c11')],
                    miolo=[(0, '#fde9b4'), (1, '#f0c877')],
                    topo=[(0, '#ffd28c'), (.3, '#f09a40'), (.72, '#be5f1a'), (1, '#6f300c')],
                    brilho=.62, cobertura=None),
    'australiano': dict(crosta=[(0, '#804c2d'), (.45, '#5c321c'), (1, '#33190c')],
                        miolo=[(0, '#d2a77a'), (1, '#a97c50')],
                        topo=[(0, '#a86d43'), (.38, '#744226'), (.78, '#4b2715'), (1, '#2a1409')],
                        brilho=.3, cobertura='aveia'),
}


def C(fn, **kw):
    """Camada configurada: C(queijo, tipo='cheddar')."""
    return lambda a, y, w: fn(a, y, w, **kw)


# ---------------------------------------------------------------- pães

def pao_base(a, y, w, tipo='classico'):
    p = PAES[tipo]
    x0, x1 = CX - w / 2, CX + w / 2
    h = 30
    top = y - h
    d = (f'M{n(x0 + 2)},{n(top + 5)} C{n(x0 + 2)},{n(top + 1.5)} {n(x0 + 5)},{n(top)} {n(x0 + 10)},{n(top)} '
         f'H{n(x1 - 10)} C{n(x1 - 5)},{n(top)} {n(x1 - 2)},{n(top + 1.5)} {n(x1 - 2)},{n(top + 5)} '
         f'L{n(x1)},{n(y - 15)} C{n(x1)},{n(y - 5)} {n(x1 - 9)},{n(y)} {n(x1 - 24)},{n(y)} '
         f'H{n(x0 + 24)} C{n(x0 + 9)},{n(y)} {n(x0)},{n(y - 5)} {n(x0)},{n(y - 15)} Z')
    s = f'<path d="{d}" fill="{a.linear(p["crosta"])}" filter="{a.textura("pao")}"/>'
    s += f'<path d="{d}" fill="{a.linear([(0, "#000", 0), (.6, "#000", 0), (1, "#000", .25)])}"/>'
    s += f'<rect x="{n(x0 + 4)}" y="{n(top)}" width="{n(w - 8)}" height="7" rx="3.5" fill="{a.linear(p["miolo"])}"/>'
    s += f'<rect x="{n(x0 + 8)}" y="{n(top + 6)}" width="{n(w - 16)}" height="2" rx="1" fill="#000" opacity=".12"/>'
    s += realce(a, x0 + w * .24, top + 17, w * .15, 3.5, op=.22, blur=3)
    return s, h - 2


def pao_topo(a, y, w, tipo='classico', semente=1):
    p = PAES[tipo]
    hd = w * .36
    x0, x1 = CX - w / 2 - 3, CX + w / 2 + 3
    ww = x1 - x0
    d = (f'M{n(x0)},{n(y - 10)} C{n(x0)},{n(y - hd * .62)} {n(x0 + ww * .16)},{n(y - hd)} {n(CX)},{n(y - hd)} '
         f'C{n(x1 - ww * .16)},{n(y - hd)} {n(x1)},{n(y - hd * .62)} {n(x1)},{n(y - 10)} '
         f'C{n(x1)},{n(y - 3)} {n(x1 - 6)},{n(y)} {n(x1 - 16)},{n(y)} H{n(x0 + 16)} '
         f'C{n(x0 + 6)},{n(y)} {n(x0)},{n(y - 3)} {n(x0)},{n(y - 10)} Z')
    s = f'<path d="{d}" fill="{a.radial(p["topo"], cx=.36, cy=.16, r=.9)}" filter="{a.textura("pao")}"/>'
    s += f'<path d="{d}" fill="{a.linear([(0, "#000", 0), (.7, "#000", 0), (1, "#000", .3)])}"/>'
    # borda de luz à direita (recortada no pão)
    s += f'<g clip-path="{a.recorte(d)}">'
    s += (f'<path d="M{n(x1 - ww * .14)},{n(y - hd * .93)} C{n(x1 - ww * .03)},{n(y - hd * .74)} {n(x1 - 1.5)},{n(y - hd * .45)} {n(x1 - 1.5)},{n(y - 13)}" '
          f'fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="4" stroke-linecap="round" filter="{a.desfoque(1.5)}"/></g>')
    # miolo aparente na base
    s += (f'<path d="M{n(x0 + 9)},{n(y - 4)} H{n(x1 - 9)} C{n(x1 - 4)},{n(y - 4)} {n(x1 - 4)},{n(y + 1)} {n(x1 - 10)},{n(y + 1)} '
          f'H{n(x0 + 10)} C{n(x0 + 4)},{n(y + 1)} {n(x0 + 4)},{n(y - 4)} {n(x0 + 9)},{n(y - 4)}Z" fill="{a.linear(p["miolo"])}"/>')
    # cobertura
    r = rng(semente * 31 + 7)
    if p['cobertura']:
        pontos = []
        alvo = 24 if p['cobertura'] == 'gergelim' else 16
        tent = 0
        while len(pontos) < alvo and tent < 2000:
            tent += 1
            u = r.uniform(-.82, .82)
            v = r.uniform(.18, .86)
            perfil = (1 - u * u) ** .55
            sx = CX + u * ww / 2 * .94
            sy = y - 10 - v * (hd - 10) * perfil
            if sy > y - 14:
                continue
            if all((sx - qx) ** 2 + ((sy - qy) * 1.4) ** 2 > 14 ** 2 for qx, qy, _ in pontos):
                pontos.append((sx, sy, u))
        if p['cobertura'] == 'gergelim':
            semg = a.linear([(0, '#fffaf0'), (1, '#e3c391')])
            for sx, sy, u in pontos:
                rx = 4.6 * (1 - .35 * abs(u))
                rot = r.uniform(-35, 35) + u * 30
                s += (f'<g transform="translate({n(sx)},{n(sy)}) rotate({n(rot)})">'
                      f'<ellipse cx=".9" cy="1.4" rx="{n(rx)}" ry="2.3" fill="#3a1a06" opacity=".3"/>'
                      f'<ellipse rx="{n(rx)}" ry="2.3" fill="{semg}"/>'
                      f'<ellipse cx="{n(-rx * .3)}" cy="-.8" rx="{n(rx * .42)}" ry=".8" fill="#fff" opacity=".85"/></g>')
        else:
            aveia = a.linear([(0, '#e2c08d'), (1, '#b48a58')])
            for sx, sy, u in pontos:
                rot = r.uniform(-50, 50)
                rx = r.uniform(3.6, 5.2) * (1 - .3 * abs(u))
                s += (f'<g transform="translate({n(sx)},{n(sy)}) rotate({n(rot)})">'
                      f'<ellipse cx=".8" cy="1.2" rx="{n(rx)}" ry="2.6" fill="#000" opacity=".3"/>'
                      f'<ellipse rx="{n(rx)}" ry="2.6" fill="{aveia}"/>'
                      f'<path d="M{n(-rx * .6)},0 H{n(rx * .6)}" stroke="#8a6238" stroke-width=".7" opacity=".6"/></g>')
    # brilho especular
    s += realce(a, CX - ww * .2, y - hd * .66, ww * .15, hd * .13, rot=-20, op=p['brilho'] * .75, blur=6)
    s += realce(a, CX - ww * .22, y - hd * .7, ww * .065, hd * .055, rot=-20, op=p['brilho'], blur=1.8)
    return s


# ---------------------------------------------------------------- carnes

CARNES = {
    'bovina': [(0, '#85532f'), (.35, '#663a1f'), (1, '#3a1f12')],
    'smash': [(0, '#73401f'), (.4, '#53301b'), (1, '#2c160b')],
    'grelhado': [(0, '#8a5232'), (.35, '#6a3a20'), (1, '#3b1d10')],
    'costela': [(0, '#7d4026'), (.4, '#5e2e1b'), (1, '#331609')],
    'picanha': [(0, '#93503a'), (.4, '#6d3421'), (1, '#3d1b0e')],
    'veggie': [(0, '#a3924f'), (.4, '#7d6e36'), (1, '#4a4120')],
}


def _contorno_disco(x0, x1, top, bot, var, semente, pontos=14):
    """Contorno de um disco visto de lado (bordas irregulares)."""
    r = rng(semente)
    h = bot - top
    rx = h * .5
    pts = []
    for i in range(pontos + 1):
        x = x0 + rx + i * (x1 - x0 - 2 * rx) / pontos
        pts.append((x, top + r.uniform(-var, var)))
    cxr = x1 - rx
    for ang in (-50, -15, 15, 50):
        t = math.radians(ang)
        pts.append((cxr + math.cos(t) * rx * 1.02, (top + bot) / 2 + math.sin(t) * h / 2))
    for i in range(pontos + 1):
        x = x1 - rx - i * (x1 - x0 - 2 * rx) / pontos
        pts.append((x, bot + r.uniform(-var * .7, var * .7)))
    cxl = x0 + rx
    for ang in (130, 165, 195, 230):
        t = math.radians(ang)
        pts.append((cxl + math.cos(t) * rx * 1.02, (top + bot) / 2 + math.sin(t) * h / 2))
    return suave(pts)


def carne(a, y, w, h=32, tipo='bovina', semente=3):
    r = rng(semente)
    smash = tipo == 'smash'
    pw = w * (1.0 if smash else .97)
    x0, x1 = CX - pw / 2, CX + pw / 2
    top = y - h
    s = ''
    if smash:
        # bordas rendadas e crocantes, típicas do smash
        renda = bolha(CX, top + h / 2 + 1, pw / 2 + 9, h / 2 + 2.5, pontos=34, var=.07, semente=semente + 50)
        s += f'<path d="{renda}" fill="{a.linear([(0, "#7a421d"), (1, "#3a1b0b")])}" filter="{a.textura("frito")}"/>'
        rr = rng(semente + 70)
        for lado in (-1, 1):
            for i in range(7):
                bx = CX + lado * (pw / 2 + rr.uniform(1, 9))
                by = top + rr.uniform(2, h)
                s += f'<ellipse cx="{n(bx)}" cy="{n(by)}" rx="{n(rr.uniform(1.5, 3))}" ry="{n(rr.uniform(1, 2))}" fill="#9a5a26" opacity=".9"/>'
    d = _contorno_disco(x0, x1, top, y, 1.4 if not smash else 1.9, semente)
    s += f'<path d="{d}" fill="{a.linear(CARNES[tipo])}" filter="{a.textura("carne")}"/>'
    clip = a.recorte(d)
    s += f'<g clip-path="{clip}">'
    s += f'<rect x="{n(x0)}" y="{n(top - 2)}" width="{n(pw)}" height="{n(h * .4)}" fill="{a.linear([(0, "#1e0d05", .55), (1, "#1e0d05", 0)])}"/>'
    s += f'<rect x="{n(x0)}" y="{n(y - h * .35)}" width="{n(pw)}" height="{n(h * .4)}" fill="{a.linear([(0, "#000", 0), (1, "#000", .4)])}"/>'
    if tipo in ('grelhado', 'costela', 'picanha'):
        for i in range(6):
            gx = x0 + 22 + i * (pw - 44) / 5
            s += (f'<path d="M{n(gx)},{n(top - 2)} l{n(h * .42)},{n(h + 4)}" stroke="#170803" stroke-width="5" '
                  f'stroke-linecap="round" opacity=".55" filter="{a.desfoque(.7)}"/>')
    if tipo == 'veggie':
        for i in range(16):
            vx = x0 + 12 + r.uniform(0, pw - 24)
            vy = top + r.uniform(h * .3, h * .8)
            cor = r.choice(['#6aa63a', '#c8452f', '#e8c046', '#6aa63a'])
            s += f'<ellipse cx="{n(vx)}" cy="{n(vy)}" rx="{n(r.uniform(1.8, 3))}" ry="{n(r.uniform(1.3, 2))}" fill="{cor}" opacity=".9"/>'
    s += '</g>'
    # pedacinhos tostados na borda de cima e brilho de suco
    for i in range(11 if not smash else 15):
        bx = x0 + 10 + r.uniform(0, pw - 20)
        s += f'<ellipse cx="{n(bx)}" cy="{n(top + r.uniform(0, 2.5))}" rx="{n(r.uniform(2.5, 5))}" ry="{n(r.uniform(1.1, 2))}" fill="#1f0e06" opacity=".75"/>'
    for i in range(5):
        gx = x0 + 18 + r.uniform(0, pw - 36)
        s += realce(a, gx, top + h * r.uniform(.3, .55), r.uniform(3, 6), r.uniform(.9, 1.5), op=.32, blur=.8)
    return s, h


def frango_empanado(a, y, w, h=32, semente=8):
    r = rng(semente)
    pw = w * 1.02
    x0, x1 = CX - pw / 2, CX + pw / 2
    top = y - h
    d = _contorno_disco(x0, x1, top, y, 3.2, semente, pontos=24)
    s = f'<path d="{d}" fill="{a.linear([(0, "#f6bf63"), (.45, "#dd9232"), (1, "#995716")])}" filter="{a.textura("frito")}"/>'
    s += f'<g clip-path="{a.recorte(d)}"><rect x="{n(x0)}" y="{n(y - h * .35)}" width="{n(pw)}" height="{n(h * .4)}" fill="{a.linear([(0, "#000", 0), (1, "#3a1a00", .4)])}"/></g>'
    for i in range(26):
        cx = x0 + 8 + r.uniform(0, pw - 16)
        cy = top + r.uniform(2, h * .75)
        s += bolha_mini(cx, cy, r.uniform(1.6, 3.2), r, '#ffd98a' if i % 3 else '#a8661c', .9)
    for i in range(5):
        s += realce(a, x0 + 20 + r.uniform(0, pw - 40), top + h * r.uniform(.25, .45), r.uniform(4, 7), 1.4, op=.35, blur=1)
    return s, h


def bolha_mini(cx, cy, raio, r, cor, op=1):
    return f'<path d="{bolha(cx, cy, raio, raio * .75, pontos=6, var=.3, semente=r.randint(1, 9999))}" fill="{cor}" opacity="{n(op)}"/>'


# ---------------------------------------------------------------- queijos e molhos

QUEIJOS = {
    'prato': ([(0, '#ffdc66'), (1, '#f2aa1f')], False),
    'cheddar': ([(0, '#ffb841'), (1, '#e07405')], True),
    'branco': ([(0, '#fffaf0'), (1, '#e8dcc2')], False),
    'catupiry': ([(0, '#fffdf6'), (1, '#e9dfc8')], True),
    'barbecue': ([(0, '#93311a'), (1, '#4a1206')], True),
}


def queijo(a, y, w, tipo='prato', pingos=None, semente=4):
    cores, molho = QUEIJOS[tipo]
    r = rng(semente)
    t = 6 if molho else 5
    x0, x1 = CX - w / 2 - 6, CX + w / 2 + 6
    if pingos is None:
        pingos = ([(.16, 15), (.4, 10), (.58, 20), (.8, 12)] if molho else [(.3, 9), (.62, 13)])
    largura = 7 if molho else 6
    topo = [(x0, y - t + 1), (x0 + 6, y - t), (CX, y - t - .5), (x1 - 6, y - t), (x1, y - t + 1)]
    base = [(x1 + 1, y + 1)]
    if not molho:
        base += [(x1 - 1, y + 9), (x1 - 8, y + 2)]   # canto da fatia caindo
    for fx, comp in sorted(pingos, key=lambda p: -p[0]):
        dx = x0 + (x1 - x0) * fx
        base += [(dx + largura + 2, y + 1.5), (dx + largura * .55, y + comp * .7), (dx, y + comp),
                 (dx - largura * .55, y + comp * .7), (dx - largura - 2, y + 1.5)]
    if not molho:
        base += [(x0 + 8, y + 2), (x0 + 1, y + 11)]
    base += [(x0 - 1, y + 1)]
    d = suave(topo + base, t=.85)
    s = f'<path d="{d}" fill="{a.linear(cores)}"/>'
    if tipo in ('cheddar', 'barbecue', 'catupiry'):
        s += f'<path d="{d}" fill="none" stroke="#000" stroke-opacity=".12" stroke-width="1"/>'
    s += f'<path d="M{n(x0 + 4)},{n(y - t + 1.3)} H{n(x1 - 4)}" stroke="#fff" stroke-opacity="{".55" if molho else ".45"}" stroke-width="1.4" stroke-linecap="round"/>'
    for fx, comp in pingos:
        dx = x0 + (x1 - x0) * fx
        s += realce(a, dx - 1.6, y + comp * .5, 1.3, comp * .22, op=.6, blur=.4)
    return s, t


# ---------------------------------------------------------------- folhas e legumes

def alface(a, y, w, semente=5):
    r = rng(semente)
    x0, x1 = CX - w / 2 - 18, CX + w / 2 + 18
    s = ''
    camadas = [
        ([(0, '#4f9a2c'), (1, '#24581a')], 0, 0, 8),
        ([(0, '#8fd052'), (.6, '#5aa835'), (1, '#357a22')], 7, 5, 6),
        ([(0, '#d3f28e'), (.5, '#97d453'), (1, '#5aa834')], 3, 12, 4),
    ]
    for k, (cores, desloc, enc, amp) in enumerate(camadas):
        topo = []
        for i in range(9):
            topo.append((x0 + enc + i * (x1 - x0 - 2 * enc) / 8, y - 11 + k + math.sin(i * 1.7 + k) * 1.3))
        babado = []
        m = 16 - k * 2
        for i in range(m + 1):
            xx = x1 - enc - i * (x1 - x0 - 2 * enc) / m + (desloc if 0 < i < m else 0)
            yy = y + (amp if i % 2 else -1) + r.uniform(-1.5, 1.5) - k
            babado.append((xx, yy))
        d = suave(topo + babado, t=.9)
        s += f'<path d="{d}" fill="{a.linear(cores)}"/>'
        if k == 2:
            s += f'<g clip-path="{a.recorte(d)}">'
            for j in range(9):
                vx = x0 + enc + 14 + j * (x1 - x0 - 2 * enc - 28) / 8 + r.uniform(-4, 4)
                s += (f'<path d="M{n(vx)},{n(y - 9)} q{n(r.uniform(-3, 3))},5 {n(r.uniform(-5, 5))},{n(r.uniform(9, 13))}" '
                      f'fill="none" stroke="#f3ffd8" stroke-opacity=".6" stroke-width="1.2" stroke-linecap="round"/>')
            s += '</g>'
    s += f'<path d="M{n(x0 + 16)},{n(y - 9.2)} H{n(x1 - 16)}" stroke="#fff" stroke-opacity=".3" stroke-width="1.2"/>'
    return s, 11


def tomate(a, y, w, semente=6):
    r = rng(semente)
    x0, x1 = CX - w / 2 - 6, CX + w / 2 + 6
    largura = (x1 - x0) / 3 + 8
    s = ''
    grad = a.linear([(0, '#ff6b56'), (.5, '#e2382b'), (1, '#a01b14')])
    for i in range(3):
        sx = x0 + i * (x1 - x0 - largura) / 2
        yy = y - 13 + (1.5 if i == 1 else 0)
        s += f'<rect x="{n(sx)}" y="{n(yy)}" width="{n(largura)}" height="13" rx="6.5" fill="{grad}"/>'
        s += f'<rect x="{n(sx + 5)}" y="{n(yy + 4)}" width="{n(largura - 10)}" height="5" rx="2.5" fill="#ff9682" opacity=".65"/>'
        for k in range(4):
            px = sx + 10 + k * (largura - 20) / 3
            s += f'<ellipse cx="{n(px)}" cy="{n(yy + 6.5)}" rx="3.2" ry="2" fill="#ffd9a3"/><circle cx="{n(px)}" cy="{n(yy + 6.5)}" r=".9" fill="#c47a2c"/>'
        s += f'<path d="M{n(sx + 6)},{n(yy + 1.5)} H{n(sx + largura - 6)}" stroke="#fff" stroke-opacity=".45" stroke-width="1.2" stroke-linecap="round"/>'
    return s, 12


def bacon(a, y, w, semente=7):
    x0, x1 = CX - w / 2 - 14, CX + w / 2 + 14
    s = ''
    for k, (base_y, fase, ini, fim) in enumerate([(y - 13, 0, x0, x1), (y - 6, 2.4, x0 + 8, x1 - 4)]):
        def linha(dy):
            pts = []
            x = ini
            while x <= fim + .1:
                pts.append((x, base_y + dy + 4.5 * math.sin((x - x0) / 15 + fase)))
                x += 6
            return suave(pts, fechado=False)
        s += f'<path d="{linha(.6)}" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="13" stroke-linecap="round" filter="{a.desfoque(1.5)}"/>'
        s += f'<path d="{linha(0)}" fill="none" stroke="#4a1407" stroke-width="12" stroke-linecap="round"/>'
        s += f'<path d="{linha(0)}" fill="none" stroke="#a3361f" stroke-width="10" stroke-linecap="round"/>'
        s += f'<path d="{linha(-2.2)}" fill="none" stroke="#d1653f" stroke-width="3.6" stroke-linecap="round"/>'
        s += f'<path d="{linha(1.4)}" fill="none" stroke="#f5bd9b" stroke-width="2.2" stroke-linecap="round"/>'
        s += f'<path d="{linha(3.6)}" fill="none" stroke="#6e2210" stroke-width="1.6" stroke-linecap="round"/>'
        s += f'<path d="{linha(-3.8)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1" stroke-linecap="round"/>'
    return s, 16


def ovo(a, y, w, semente=9):
    r = rng(semente)
    x0, x1 = CX - w / 2 - 16, CX + w / 2 + 16
    pts = []
    for i in range(10):
        pts.append((x0 + 10 + i * (x1 - x0 - 20) / 9, y - 10 + r.uniform(-1.8, 1.8)))
    pts += [(x1, y - 4), (x1 - 2, y + 5), (x1 - 12, y + 2)]
    for i in range(6):
        pts.append((x1 - 20 - i * (x1 - x0 - 40) / 5, y + r.uniform(0, 4)))
    pts += [(x0 + 12, y + 3), (x0 + 3, y + 7), (x0, y - 3)]
    d = suave(pts, t=.9)
    s = f'<path d="{d}" fill="{a.linear([(0, "#ffffff"), (1, "#ece0cb")])}" stroke="#d6c7ab" stroke-width=".8"/>'
    gx = CX + 10
    gema = f'M{n(gx - 25)},{n(y - 9)} C{n(gx - 24)},{n(y - 25)} {n(gx + 24)},{n(y - 25)} {n(gx + 25)},{n(y - 9)} Z'
    s += f'<path d="{gema}" fill="{a.radial([(0, "#ffe682"), (.45, "#fbb321"), (1, "#dd7404")], cx=.4, cy=.35, r=.75)}"/>'
    s += realce(a, gx - 8, y - 18, 6, 2.6, rot=-15, op=.75, blur=1)
    return s, 12


def cebola(a, y, w, semente=10):
    r = rng(semente)
    s = ''
    for i in range(16):
        x = CX - w / 2 + 8 + r.uniform(0, w - 16)
        yy = y - r.uniform(1, 6)
        c = (f'M{n(x)},{n(yy)} q{n(r.uniform(4, 8))},{n(r.uniform(-5, -2))} {n(r.uniform(10, 16))},{n(r.uniform(-1, 2))} '
             f't{n(r.uniform(8, 12))},{n(r.uniform(-2, 2))}')
        s += f'<path d="{c}" fill="none" stroke="#6b3110" stroke-width="4.4" stroke-linecap="round"/>'
        s += f'<path d="{c}" fill="none" stroke="#c4803b" stroke-width="2" stroke-linecap="round"/>'
        s += f'<path d="{c}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width=".7" stroke-linecap="round" transform="translate(0,-.8)"/>'
    return s, 6


def calabresa(a, y, w, semente=11):
    r = rng(semente)
    s = ''
    interior = a.radial([(0, '#e98a72'), (1, '#b4432d')], cx=.4, cy=.4)
    for linha, (yy, qtd, d0) in enumerate([(y - 8, 6, 0), (y - 4, 5, 18)]):
        for i in range(qtd):
            cx = CX - w / 2 + 22 + d0 + i * (w - 44 - d0) / max(qtd - 1, 1) + r.uniform(-3, 3)
            s += f'<ellipse cx="{n(cx)}" cy="{n(yy)}" rx="17" ry="7.5" fill="#7d2412"/>'
            s += f'<ellipse cx="{n(cx)}" cy="{n(yy - .8)}" rx="14.5" ry="5.6" fill="{interior}"/>'
            for k in range(5):
                s += f'<circle cx="{n(cx + r.uniform(-10, 10))}" cy="{n(yy - .8 + r.uniform(-3, 3))}" r="{n(r.uniform(.8, 1.4))}" fill="#f7d6c4"/>'
            s += realce(a, cx - 5, yy - 3.5, 5, 1.2, op=.45, blur=.6)
    return s, 12


def desfiado(a, y, w, cores=('#efd3a0', '#cfa465', '#9b6c35'), fibra='#8a5a28', semente=12):
    r = rng(semente)
    x0, x1 = CX - w / 2 + 2, CX + w / 2 - 2
    pts = []
    for i in range(12):
        pts.append((x0 + 6 + i * (x1 - x0 - 12) / 11, y - 18 + r.uniform(-2.5, 2.5)))
    pts += [(x1 + 2, y - 9), (x1 - 2, y + 1)]
    pts += [(x0 + 2, y + 1), (x0 - 2, y - 9)]
    d = suave(pts, t=.9)
    s = f'<path d="{d}" fill="{a.linear(list(zip((0, .5, 1), cores)))}"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    for i in range(46):
        fx = x0 + r.uniform(0, x1 - x0)
        fy = y - r.uniform(2, 18)
        ang = r.uniform(-.6, .6)
        L = r.uniform(6, 13)
        cor = fibra if i % 3 else '#ffffff'
        op = .55 if i % 3 else .35
        s += (f'<path d="M{n(fx)},{n(fy)} l{n(L * math.cos(ang))},{n(L * math.sin(ang))}" stroke="{cor}" stroke-opacity="{op}" '
              f'stroke-width="{n(r.uniform(1, 1.8))}" stroke-linecap="round"/>')
    s += '</g>'
    return s, 18


def milho(a, y, w, semente=13):
    r = rng(semente)
    grao = a.radial([(0, '#fff3a6'), (.6, '#f7c42f'), (1, '#d39412')], cx=.4, cy=.35)
    s = ''
    for i in range(16):
        gx = CX - w / 2 + 16 + i * (w - 32) / 15 + r.uniform(-2, 2)
        gy = y - (6 if i % 2 else 3) + r.uniform(-1, 1)
        s += f'<rect x="{n(gx - 3.4)}" y="{n(gy - 3)}" width="6.8" height="6" rx="2.6" fill="{grao}"/>'
        s += f'<circle cx="{n(gx - 1.2)}" cy="{n(gy - 1.4)}" r=".9" fill="#fff" opacity=".8"/>'
    return s, 6


def coalho(a, y, w, semente=14):
    x0, x1 = CX - w / 2 + 6, CX + w / 2 - 6
    d = f'M{n(x0 + 5)},{n(y - 12)} H{n(x1 - 5)} Q{n(x1)},{n(y - 12)} {n(x1)},{n(y - 7)} V{n(y - 4)} Q{n(x1)},{n(y + 1)} {n(x1 - 5)},{n(y + 1)} H{n(x0 + 5)} Q{n(x0)},{n(y + 1)} {n(x0)},{n(y - 4)} V{n(y - 7)} Q{n(x0)},{n(y - 12)} {n(x0 + 5)},{n(y - 12)}Z'
    s = f'<path d="{d}" fill="{a.linear([(0, "#fbe9bd"), (.6, "#efcf8a"), (1, "#c99242")])}" filter="{a.textura("fino")}"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    for i in range(6):
        gx = x0 + 14 + i * (x1 - x0 - 28) / 5
        s += f'<path d="M{n(gx)},{n(y - 14)} l7,16" stroke="#8a4a14" stroke-width="3.6" stroke-linecap="round" opacity=".75" filter="{a.desfoque(.5)}"/>'
    s += '</g>'
    s += f'<path d="M{n(x0 + 5)},{n(y - 11)} H{n(x1 - 5)}" stroke="#fff" stroke-opacity=".5" stroke-width="1.1"/>'
    return s, 11


def vinagrete(a, y, w, semente=15):
    r = rng(semente)
    cores = ['#e2483d', '#f5efe0', '#5fa83a', '#e2483d', '#9fd05a', '#c93226']
    s = ''
    for i in range(30):
        vx = CX - w / 2 + 8 + r.uniform(0, w - 16)
        vy = y - r.uniform(2, 8)
        lado = r.uniform(4, 6.5)
        rot = r.uniform(-30, 30)
        cor = cores[i % len(cores)]
        s += (f'<rect x="{n(vx - lado / 2)}" y="{n(vy - lado / 2)}" width="{n(lado)}" height="{n(lado * .85)}" rx="1.5" fill="{cor}" '
              f'transform="rotate({n(rot)} {n(vx)} {n(vy)})"/>')
        s += f'<circle cx="{n(vx - 1)}" cy="{n(vy - 1.2)}" r=".8" fill="#fff" opacity=".7"/>'
    return s, 8


def gorgonzola(a, y, w, semente=16):
    r = rng(semente)
    s = ''
    grad = a.linear([(0, '#fdfbf2'), (1, '#ddd6bd')])
    for i in range(10):
        gx = CX - w / 2 + 14 + i * (w - 28) / 9 + r.uniform(-3, 3)
        gy = y - 5 + r.uniform(-1.5, 1.5)
        s += f'<path d="{bolha(gx, gy, r.uniform(10, 13), r.uniform(5, 6.5), pontos=8, var=.22, semente=i + 3)}" fill="{grad}"/>'
        for k in range(3):
            s += f'<path d="M{n(gx + r.uniform(-7, 5))},{n(gy + r.uniform(-3, 2))} l{n(r.uniform(2, 4))},{n(r.uniform(-1, 1.5))}" stroke="#3f6f68" stroke-width="1.6" stroke-linecap="round" opacity=".85"/>'
        s += realce(a, gx - 3, gy - 3, 4, 1.2, op=.6, blur=.5)
    return s, 9


def mel(a, y, w, semente=17):
    x0, x1 = CX - w / 2 + 8, CX + w / 2 - 8
    pts = []
    for i in range(14):
        pts.append((x0 + i * (x1 - x0) / 13, y - 2 + (3 if i % 2 else -2)))
    c = suave(pts, fechado=False)
    s = f'<path d="{c}" fill="none" stroke="#b8650a" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
    s += f'<path d="{c}" fill="none" stroke="#f5b62c" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
    s += f'<path d="{c}" fill="none" stroke="#fff3c4" stroke-width="1" stroke-linecap="round" transform="translate(0,-1)" opacity=".8"/>'
    for gx, L in ((CX - 38, 14), (CX + 46, 10)):
        s += f'<path d="M{n(gx)},{n(y - 1)} q1,{n(L * .6)} 0,{n(L)}" stroke="#d98a10" stroke-width="3.4" stroke-linecap="round" fill="none"/>'
        s += f'<circle cx="{n(gx)}" cy="{n(y - 1 + L)}" r="2.6" fill="#e99b14"/>'
    return s, 3


def cebola_crispy(a, y, w, semente=18):
    r = rng(semente)
    s = ''
    for i in range(34):
        x = CX - w / 2 + 4 + r.uniform(0, w - 8)
        yy = y - r.uniform(1, 11)
        c = (f'M{n(x)},{n(yy)} q{n(r.uniform(3, 6))},{n(r.uniform(-6, -2))} {n(r.uniform(8, 12))},{n(r.uniform(-2, 2))} '
             f't{n(r.uniform(5, 9))},{n(r.uniform(-3, 3))}')
        s += f'<path d="{c}" fill="none" stroke="#8a4a10" stroke-width="3.6" stroke-linecap="round"/>'
        s += f'<path d="{c}" fill="none" stroke="#eaa83f" stroke-width="2" stroke-linecap="round"/>'
        if i % 3 == 0:
            s += f'<path d="{c}" fill="none" stroke="#fff4c8" stroke-width=".7" stroke-linecap="round" transform="translate(0,-.7)"/>'
    return s, 11


def picles(a, y, w, semente=19):
    s = ''
    interior = a.radial([(0, '#d6e88f'), (.7, '#a8c75a'), (1, '#7ea33a')])
    for i in range(5):
        px = CX - w / 2 + 26 + i * (w - 52) / 4
        py = y - 4.5
        s += f'<ellipse cx="{n(px)}" cy="{n(py)}" rx="14" ry="6" fill="#3f6b1b"/>'
        s += f'<ellipse cx="{n(px)}" cy="{n(py - .6)}" rx="11.5" ry="4.4" fill="{interior}"/>'
        for k in range(6):
            ang = k * math.pi / 3
            s += f'<ellipse cx="{n(px + math.cos(ang) * 5.5)}" cy="{n(py - .6 + math.sin(ang) * 2)}" rx="1.2" ry=".8" fill="#f2f5d6"/>'
        s += realce(a, px - 5, py - 3.2, 4, 1, op=.5, blur=.5)
    return s, 7


def jalapeno(a, y, w, semente=20):
    s = ''
    for i in range(7):
        px = CX - w / 2 + 20 + i * (w - 40) / 6
        py = y - 4.5 - (1.2 if i % 2 else 0)
        s += f'<ellipse cx="{n(px)}" cy="{n(py)}" rx="10" ry="6" fill="#2d7420"/>'
        s += f'<ellipse cx="{n(px)}" cy="{n(py - .5)}" rx="7.2" ry="4" fill="#cfe69a"/>'
        s += f'<ellipse cx="{n(px)}" cy="{n(py - .5)}" rx="3.2" ry="1.8" fill="#f4f0cf"/>'
        s += f'<circle cx="{n(px - 1.5)}" cy="{n(py - .8)}" r=".8" fill="#e9d88c"/><circle cx="{n(px + 1.5)}" cy="{n(py)}" r=".8" fill="#e9d88c"/>'
        s += realce(a, px - 4, py - 3.5, 3.5, 1, op=.55, blur=.4)
    return s, 8


def rucula(a, y, w, semente=21):
    r = rng(semente)
    s = ''
    grad = a.linear([(0, '#7cc04f'), (1, '#2e6a1e')])
    for i in range(13):
        lx = CX - w / 2 - 10 + i * (w + 20) / 12 + r.uniform(-3, 3)
        ly = y - 4 + r.uniform(-1.5, 1.5)
        rot = r.uniform(-28, 28)
        folha = bolha(0, 0, 15, 5, pontos=12, var=.25, semente=i + 40)
        s += (f'<g transform="translate({n(lx)},{n(ly)}) rotate({n(rot)})"><path d="{folha}" fill="{grad}"/>'
              f'<path d="M-12,0 H12" stroke="#c8eaa0" stroke-width=".9" opacity=".7"/></g>')
    return s, 8


# ---------------------------------------------------------------- montagem

def hamburguer(a, camadas, w=216, base=252, pao='classico', semente=1):
    """Monta o lanche de baixo para cima. Devolve (svg, y do topo)."""
    s, h = pao_base(a, base, w, pao)
    out = [s]
    y = base - h
    for camada in camadas:
        cs, ch = camada(a, y, w)
        out.append(sombra_contato(a, CX - w * .47, CX + w * .47, y - 1, op=.38))
        out.append(cs)
        y -= ch
    out.append(sombra_contato(a, CX - w * .48, CX + w * .48, y, alt=7, op=.45))
    out.append(pao_topo(a, y + 2, w, pao, semente))
    return ''.join(out), y + 2 - w * .36


def tabua(a, base, largura=300):
    """Tábua de madeira (linha premium). O lanche fica apoiado em `base`."""
    x0, x1 = CX - largura / 2, CX + largura / 2
    topo = f'M{n(x0 + 16)},{n(base - 7)} H{n(x1 - 16)} Q{n(x1)},{n(base - 7)} {n(x1)},{n(base)} H{n(x0)} Q{n(x0)},{n(base - 7)} {n(x0 + 16)},{n(base - 7)}Z'
    frente = f'M{n(x0)},{n(base)} H{n(x1)} V{n(base + 6)} Q{n(x1)},{n(base + 12)} {n(x1 - 10)},{n(base + 12)} H{n(x0 + 10)} Q{n(x0)},{n(base + 12)} {n(x0)},{n(base + 6)}Z'
    s = f'<path d="{topo}" fill="{a.linear([(0, "#a9743f"), (1, "#c99359")])}" filter="{a.textura("fino")}"/>'
    s += f'<g clip-path="{a.recorte(topo)}">'
    for i, yy in enumerate((base - 5.5, base - 3, base - 1)):
        s += f'<path d="M{n(x0 + 10 + i * 24)},{n(yy)} q70,-1.2 140,0 t130,0" stroke="#7a4a1e" stroke-opacity=".35" stroke-width=".8" fill="none"/>'
    s += '</g>'
    s += f'<path d="{frente}" fill="{a.linear([(0, "#8a5a2e"), (1, "#4e2f14")])}" filter="{a.textura("fino")}"/>'
    s += f'<path d="M{n(x0 + 2)},{n(base + .6)} H{n(x1 - 2)}" stroke="#f0cc95" stroke-opacity=".55" stroke-width="1"/>'
    return s


def lanche_svg(titulo, camadas, pao='classico', w=216, base=252, premium=False, semente=1):
    a = Arte(titulo)
    if premium:
        corpo, _ = hamburguer(a, camadas, w=w, base=base - 12, pao=pao, semente=semente)
        return a.svg(fundo(a) + sombra(a, cy=base + 1, rx=160, ry=8) + tabua(a, base - 11) + sombra(a, cy=base - 13, rx=w * .52, ry=4, forca=.8) + corpo)
    corpo, _ = hamburguer(a, camadas, w=w, base=base, pao=pao, semente=semente)
    return a.svg(fundo(a) + sombra(a, cy=base, rx=w * .56, ry=10) + corpo)


def mini_hamburguer(a, cx, base, escala, camadas=None, pao='classico'):
    """Hambúrguer pequeno para combos: centro `cx`, apoiado em `base`."""
    camadas = camadas or [C(carne), C(queijo), C(bacon), C(alface)]
    corpo, _ = hamburguer(a, camadas, base=252, pao=pao)
    return f'<g transform="translate({n(cx - CX * escala)},{n(base - 252 * escala)}) scale({n(escala)})">{corpo}</g>'


GRELHADO = dict(tipo='grelhado', h=30)


def gerar():
    A = {}
    A['hamburguer'] = lanche_svg('Ilustração de hambúrguer', [C(carne), C(queijo), C(tomate), C(alface)])
    A['hamburguer-bacon'] = lanche_svg('Ilustração de hambúrguer com bacon', [C(carne), C(queijo), C(bacon)], semente=2)
    A['hamburguer-salada'] = lanche_svg('Ilustração de hambúrguer com salada', [
        C(carne), C(queijo), C(tomate), C(alface), C(tomate, semente=16), C(alface, semente=25)], semente=3)
    A['hamburguer-ovo'] = lanche_svg('Ilustração de hambúrguer com ovo', [C(carne), C(queijo), C(ovo), C(alface)], semente=4)
    A['hamburguer-tudo'] = lanche_svg('Ilustração de hambúrguer completo', [
        C(carne, h=24), C(queijo), C(carne, h=24, semente=30), C(queijo, semente=8), C(bacon), C(ovo), C(tomate), C(alface)],
        w=200, base=256, semente=5)
    A['smash-duplo'] = lanche_svg('Ilustração de hambúrguer smash duplo', [
        C(carne, tipo='smash', h=17), C(queijo), C(carne, tipo='smash', h=17, semente=31), C(queijo, semente=9), C(cebola)], pao='brioche')
    A['frango'] = lanche_svg('Ilustração de sanduíche de frango empanado', [C(frango_empanado), C(tomate), C(alface)], pao='liso')
    A['veggie'] = lanche_svg('Ilustração de hambúrguer vegetariano', [
        C(carne, tipo='veggie'), C(queijo, tipo='branco'), C(tomate), C(rucula)], semente=6)
    A['x-calabresa'] = lanche_svg('Ilustração de hambúrguer com calabresa', [C(carne), C(queijo), C(calabresa), C(alface)], semente=7)
    A['x-frango'] = lanche_svg('Ilustração de sanduíche de frango com catupiry', [
        C(desfiado), C(queijo, tipo='catupiry'), C(milho), C(alface)], pao='liso')
    A['x-cheddar'] = lanche_svg('Ilustração de hambúrguer com cheddar e bacon', [
        C(carne), C(queijo, tipo='cheddar'), C(bacon), C(queijo, tipo='cheddar', pingos=[(.25, 9), (.7, 13)], semente=12)], semente=8)
    A['smash'] = lanche_svg('Ilustração de smash burger', [C(carne, tipo='smash', h=17), C(queijo), C(cebola)], pao='brioche', semente=2)
    A['smash-bacon'] = lanche_svg('Ilustração de smash burger com bacon', [
        C(carne, tipo='smash', h=17), C(queijo), C(carne, tipo='smash', h=17, semente=32), C(queijo, semente=10), C(bacon)], pao='brioche', semente=3)
    A['smash-triplo'] = lanche_svg('Ilustração de smash burger triplo', [
        C(carne, tipo='smash', h=17), C(queijo), C(carne, tipo='smash', h=17, semente=33), C(queijo, semente=11),
        C(carne, tipo='smash', h=17, semente=34), C(queijo, semente=13)], pao='brioche', base=256, semente=4)
    A['smash-picante'] = lanche_svg('Ilustração de smash burger picante', [
        C(carne, tipo='smash', h=17), C(queijo, tipo='branco'), C(carne, tipo='smash', h=17, semente=35),
        C(queijo, tipo='branco', semente=14), C(jalapeno)], pao='brioche', semente=5)
    A['premium-costela'] = lanche_svg('Ilustração de hambúrguer de costela', [
        C(carne, tipo='costela', h=30), C(queijo), C(desfiado, cores=('#9a5432', '#7a3b22', '#4f2416'), fibra='#3a1508'),
        C(queijo, tipo='barbecue', pingos=[(.2, 12), (.55, 16), (.82, 10)])], pao='brioche', premium=True, semente=6)
    A['premium-picanha'] = lanche_svg('Ilustração de hambúrguer de picanha', [
        C(carne, tipo='picanha', h=30), C(coalho), C(vinagrete)], pao='australiano', premium=True, semente=7)
    A['premium-gorgonzola'] = lanche_svg('Ilustração de hambúrguer com gorgonzola e mel', [
        C(carne, **GRELHADO), C(gorgonzola), C(mel), C(rucula)], pao='brioche', premium=True, semente=8)
    A['premium-onion'] = lanche_svg('Ilustração de hambúrguer com cebola crispy', [
        C(carne, **GRELHADO), C(queijo, tipo='cheddar'), C(cebola_crispy)], pao='brioche', premium=True, semente=9)
    A['premium-bbq'] = lanche_svg('Ilustração de hambúrguer barbecue defumado', [
        C(carne, **GRELHADO), C(queijo, tipo='barbecue'), C(bacon), C(picles)], pao='australiano', premium=True, semente=10)
    return A
