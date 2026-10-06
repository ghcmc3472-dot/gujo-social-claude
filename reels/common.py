"""수묵 릴스 공통: 한지, 먹산, 인장 질감, 글꼴, 글자 외곽선."""
import base64, json, math, os, pathlib, random

HERE = pathlib.Path(__file__).resolve().parent
A = HERE / 'assets'


def data_uri(p, mime):
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()


PAPER = data_uri(A / 'paper.jpg', 'image/jpeg')
WEAR = data_uri(A / 'wear.png', 'image/png')
GLYPHS = json.load(open(A / 'glyphs.json', encoding='utf-8'))
STROKES = json.load(open(A / 'strokes.json', encoding='utf-8'))  # 획순 자료 (STROKES_SOURCE.md)
ANIMALS = A / 'animals'
ANIMAL_FILE = dict(zip('子丑寅卯辰巳午未申酉戌亥',
                       ['rat', 'ox', 'tiger', 'rabbit', 'dragon', 'snake', 'horse', 'sheep', 'monkey', 'rooster', 'dog', 'pig']))

# 웹 글꼴(로컬 시험용 GUJO_FONTS_CSS)이 없으면 시스템 글꼴(fonts-noto-cjk, fonts-nanum)을 쓴다.
_extra = os.environ.get('GUJO_FONTS_CSS')
FONT_LINK = f'<link rel="stylesheet" href="{_extra}">' if _extra else ''
FONT_FACE = ("@font-face{font-family:'Cormorant Garamond';font-weight:600;src:url(" +
             data_uri(A / 'cormorant-garamond-latin-600-normal.woff2', 'font/woff2') + ") format('woff2')}")
SERIF = "'Noto Serif KR','Noto Serif CJK KR',serif"
SANS = "'Noto Sans KR','Noto Sans CJK KR',sans-serif"
BRUSH = "'Nanum Myeongjo','NanumMyeongjo','NanumMyeongjo ExtraBold','Noto Serif CJK KR',serif"


def animal_uri(branch):
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        p = ANIMALS / f'{ANIMAL_FILE[branch]}.{ext}'
        if p.exists():
            return data_uri(p, 'image/png' if ext == 'png' else f'image/{"jpeg" if ext in ("jpg", "jpeg") else ext}')
    return None


def glyph_svg(ch, size, cls='gl'):
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 -880 1000 1000">'
            f'<path d="{GLYPHS[ch]["d"]}" transform="scale(1,-1)"/></svg>')


def _ridge(seed, base_y, amp, rough, w=1600):
    random.seed(seed)
    ph = [random.random() * 6.28 for _ in range(3)]
    pts = []
    for x in range(-200, w, 20):
        y = base_y - amp * (0.55 * math.sin(x / 260 + ph[0]) + 0.3 * math.sin(x / 120 + ph[1])
                            + 0.15 * math.sin(x / 47 + ph[2])) - rough * random.random()
        pts.append(f'{x},{y:.1f}')
    return 'M-200,2000 L' + ' L'.join(pts) + f' L{w},2000 Z'


MOUNT = [(3, 1180, 220, 10, .18, 6), (5, 1300, 170, 14, .30, 3), (9, 1430, 120, 18, .55, 1.5)]


def mountains_svg(idp):
    layers = ''.join(
        f'<g class="ml" data-k="{k}"><path d="{_ridge(sd, by, am, ro)}" fill="url(#{idp}g{k})" filter="url(#{idp}b{k})" opacity="{op}"/></g>'
        for k, (sd, by, am, ro, op, bl) in enumerate(MOUNT))
    defs = ''.join(
        f'<linearGradient id="{idp}g{k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1A1B1C"/>'
        f'<stop offset=".35" stop-color="#1A1B1C" stop-opacity=".55"/><stop offset=".8" stop-color="#1A1B1C" stop-opacity="0"/></linearGradient>'
        f'<filter id="{idp}b{k}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="3" seed="{k+2}"/>'
        f'<feDisplacementMap in="SourceGraphic" scale="{18+k*6}"/><feGaussianBlur stdDeviation="{bl}"/></filter>'
        for k, (sd, by, am, ro, op, bl) in enumerate(MOUNT))
    return f'<svg class="mount" viewBox="0 0 1080 1920" width="1080" height="1920"><defs>{defs}</defs>{layers}</svg>'


_uid = [0]


def brush_svg(ch, size, cls='gl'):
    """획순대로 붓이 지나가며 써지는 글자. 각 획 모양으로 잘라 낸 굵은 붓길(median)을 차례로 그린다."""
    d = STROKES[ch]
    _uid[0] += 1
    u = f'b{_uid[0]}'
    clips, paths = '', ''
    for i, (st, med) in enumerate(zip(d['strokes'], d['medians'])):
        clips += f'<clipPath id="{u}c{i}"><path d="{st}"/></clipPath>'
        pts = ' L'.join(f'{x},{y}' for x, y in med)
        paths += (f'<path class="ink" d="M{pts}" clip-path="url(#{u}c{i})" fill="none" stroke="#1A1B1C" '
                  f'stroke-width="150" stroke-linecap="round" stroke-linejoin="round"/>')
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 1024 1024"><defs>{clips}</defs>'
            f'<g transform="scale(1,-1) translate(0,-900)">{paths}</g></svg>')
