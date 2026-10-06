"""GUJO Claude 계정 카드뉴스 렌더러 (1080x1350 JPEG)."""
import json, sys, pathlib, html
from playwright.sync_api import sync_playwright

KIT = pathlib.Path(__file__).resolve().parent.parent / 'GUJO_REPORT_KIT' / 'template' / 'assets'
FONTS = (KIT / 'fonts' / 'fonts.css').as_uri()
SCENES = KIT / 'scenes_cover'

CSS = """
:root{--ink:#1A1B1C;--ink-soft:#46453F;--paper:#F1F0EB;--bone:#E8E6E0;--grey:#8E8B82;--hair:#D4D1C8;--seal:#B23A2E}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px}
body{font-family:'Noto Serif KR',serif;color:var(--ink);background:var(--paper);word-break:keep-all;overflow:hidden}
.s{position:relative;width:1080px;height:1350px;padding:120px 104px}
.dark{background:var(--ink);color:var(--paper)}
.kicker{font-family:'Noto Sans KR',sans-serif;font-size:30px;letter-spacing:.18em;color:var(--grey);margin-bottom:56px}
.dark .kicker{color:#8E8B82}
.title{font-size:86px;line-height:1.32;font-weight:700;letter-spacing:-.01em}
.sub{font-size:42px;line-height:1.6;margin-top:56px;color:var(--ink-soft)}
.dark .sub{color:#CFCCC4}
.body{font-size:52px;line-height:1.62;font-weight:400}
.body b{font-weight:700}
.body .r{color:var(--seal);font-weight:700}
.small{font-family:'Noto Sans KR',sans-serif;font-size:28px;line-height:1.6;color:var(--grey)}
.foot{position:absolute;left:104px;right:104px;bottom:88px;display:flex;align-items:center;justify-content:space-between}
.seal{width:64px;height:64px;background:var(--seal);color:var(--paper);display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:700;border-radius:4px}
.brand{display:flex;align-items:center;gap:20px;font-family:'Cormorant Garamond',serif;font-size:34px;letter-spacing:.3em}
.page{font-family:'Noto Sans KR',sans-serif;font-size:26px;color:var(--grey);letter-spacing:.1em}
.center{display:flex;flex-direction:column;justify-content:center;height:100%;padding-bottom:120px}
.hr{width:72px;height:3px;background:var(--seal);margin:56px 0}
.scene{position:absolute;left:0;top:0;width:1080px;height:760px;background-size:cover;background-position:center;mix-blend-mode:multiply}
.fade{position:absolute;left:0;top:520px;width:1080px;height:241px;background:linear-gradient(to bottom,rgba(241,240,235,0),#F1F0EB)}
.stemwrap{position:absolute;left:104px;right:104px;top:700px}
.stem{display:flex;align-items:baseline;gap:28px}
.stem .ch{font-size:150px;font-weight:700;line-height:1}
.stem .nm{font-size:46px;color:var(--ink-soft)}
.stem .god{font-family:'Noto Sans KR',sans-serif;font-size:26px;color:var(--grey);margin-left:auto;letter-spacing:.05em}
.line{font-size:50px;line-height:1.55;margin-top:44px;font-weight:700}
.line2{font-size:38px;line-height:1.6;margin-top:24px;color:var(--ink-soft)}
.shot{position:absolute;left:80px;right:80px;top:200px;bottom:350px;display:flex;align-items:center;justify-content:center}
.shot img{max-width:100%;max-height:100%;box-shadow:0 18px 50px rgba(26,27,28,.22);border:1px solid var(--hair)}
.cap{position:absolute;left:104px;right:104px;bottom:190px;font-size:36px;line-height:1.55}
.qa{border-left:4px solid var(--seal);padding-left:40px}
.q{font-family:'Noto Sans KR',sans-serif;font-size:36px;color:var(--grey);margin-bottom:28px}
.a{font-size:54px;line-height:1.55;font-weight:700}
.a2{font-size:42px;line-height:1.6;margin-top:28px;color:var(--ink-soft)}
.tag{display:inline-block;font-family:'Noto Sans KR',sans-serif;font-size:24px;color:var(--grey);border:1px solid var(--hair);padding:6px 16px;margin-bottom:40px;letter-spacing:.08em}

.pair{position:absolute;left:0;right:0;top:0;bottom:200px;display:flex;flex-direction:column}
.half{flex:1;display:flex;align-items:center;gap:48px;padding:0 80px 0 0;border-bottom:1px solid var(--hair)}
.half:last-child{border-bottom:none}
.thumb{width:470px;height:100%;background-size:cover;background-position:center;mix-blend-mode:multiply;flex:none;-webkit-mask-image:linear-gradient(to right,#000 70%,transparent)}
.ht .ch{font-size:110px;font-weight:700;line-height:1}
.ht .nm{font-size:36px;color:var(--ink-soft);margin-left:16px}
.ht .god{font-family:'Noto Sans KR',sans-serif;font-size:24px;color:var(--grey);margin-top:14px}
.ht .l1{font-size:44px;font-weight:700;line-height:1.45;margin-top:26px}
.ht .l2{font-size:32px;line-height:1.55;margin-top:12px;color:var(--ink-soft)}
"""

def esc(t):
    return html.escape(t).replace('\n', '<br>').replace('[[', '<span class="r">').replace(']]', '</span>').replace('{{', '<b>').replace('}}', '</b>')

def foot(i, n, dark=False):
    return (f'<div class="foot"><div class="brand"><div class="seal">構</div>GUJO</div>'
            f'<div class="page">{i} / {n}</div></div>')

def slide_html(s, i, n):
    t = s['type']
    if t == 'cover':
        inner = (f'<div class="s dark"><div class="center"><div class="kicker">{esc(s.get("kicker",""))}</div>'
                 f'<div class="title">{esc(s["title"])}</div>'
                 + (f'<div class="sub">{esc(s["sub"])}</div>' if s.get('sub') else '') + '</div>' + foot(i, n, True) + '</div>')
    elif t == 'text':
        inner = (f'<div class="s"><div class="center">'
                 + (f'<div class="kicker">{esc(s["kicker"])}</div>' if s.get('kicker') else '')
                 + f'<div class="body">{esc(s["body"])}</div>'
                 + (f'<div class="hr"></div><div class="small">{esc(s["note"])}</div>' if s.get('note') else '')
                 + '</div>' + foot(i, n) + '</div>')
    elif t == 'qa':
        inner = (f'<div class="s"><div class="center"><div><span class="tag">{esc(s.get("tag","예시"))}</span></div><div class="qa">'
                 f'<div class="q">{esc(s["q"])}</div><div class="a">{esc(s["a"])}</div>'
                 + (f'<div class="a2">{esc(s["a2"])}</div>' if s.get('a2') else '') + '</div>'
                 + (f'<div class="hr"></div><div class="small">{esc(s["note"])}</div>' if s.get('note') else '')
                 + '</div>' + foot(i, n) + '</div>')
    elif t == 'stem':
        img = (SCENES / f'{s["scene"]}.jpg').as_uri()
        inner = (f'<div class="s"><div class="scene" style="background-image:url({img})"></div><div class="fade"></div>'
                 f'<div class="stemwrap"><div class="stem"><span class="ch">{s["ch"]}</span><span class="nm">{esc(s["name"])}</span>'
                 + (f'<span class="god">{esc(s["god"])}</span>' if s.get('god') else '') + '</div>'
                 f'<div class="line">{esc(s["line"])}</div>'
                 + (f'<div class="line2">{esc(s["line2"])}</div>' if s.get('line2') else '')
                 + '</div>' + foot(i, n) + '</div>')
    elif t == 'stem2':
        halves = ''
        for h in s['items']:
            img = (SCENES / f'{h["scene"]}.jpg').as_uri()
            halves += (f'<div class="half"><div class="thumb" style="background-image:url({img})"></div><div class="ht">'
                       f'<div><span class="ch">{h["ch"]}</span><span class="nm">{esc(h["name"])}</span></div>'
                       f'<div class="god">{esc(h["god"])}</div><div class="l1">{esc(h["line"])}</div><div class="l2">{esc(h["line2"])}</div></div></div>')
        inner = f'<div class="s"><div class="pair">{halves}</div>' + foot(i, n) + '</div>'
    elif t == 'shot':
        img = pathlib.Path(s['img']).resolve().as_uri()
        inner = (f'<div class="s"><div class="kicker">{esc(s.get("kicker",""))}</div>'
                 f'<div class="shot"><img src="{img}"></div><div class="cap">{esc(s["cap"])}</div>' + foot(i, n) + '</div>')
    elif t == 'end':
        inner = (f'<div class="s dark"><div class="center" style="align-items:flex-start">'
                 f'<div class="seal" style="width:120px;height:120px;font-size:80px">構</div>'
                 f'<div class="title" style="font-size:64px;margin-top:64px">{esc(s["title"])}</div>'
                 f'<div class="sub">{esc(s.get("sub",""))}</div>'
                 f'<div class="kicker" style="margin-top:72px;font-size:36px;color:#E8E6E0">gujo.kr</div></div>'
                 + foot(i, n, True) + '</div>')
    else:
        raise ValueError(t)
    return f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}"><style>{CSS}</style></head><body>{inner}</body></html>'

def render(spec_path, out_dir):
    spec = json.load(open(spec_path, encoding='utf-8'))
    out = pathlib.Path(out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1080, 'height': 1350})
        for post in spec:
            d = out / post['id']; d.mkdir(exist_ok=True)
            n = len(post['slides'])
            for i, s in enumerate(post['slides'], 1):
                tmp = d / f'_s{i}.html'
                tmp.write_text(slide_html(s, i, n), encoding='utf-8')
                pg.goto(tmp.as_uri()); pg.wait_for_timeout(250)
                pg.evaluate('document.fonts.ready')
                pg.screenshot(path=str(d / f'{i:02d}.jpg'), type='jpeg', quality=90)
                tmp.unlink()
        b.close()

if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2])
