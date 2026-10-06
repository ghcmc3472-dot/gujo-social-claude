"""띠별 오늘 수묵 릴스. 입력: lines.json ({"date":..., "intro":..., "items":[{"b":"子","tag":..,"line":..}]})"""
import json, pathlib, subprocess, sys, shutil
from datetime import date
from playwright.sync_api import sync_playwright
from common import mountains_svg, PAPER, WEAR, FONT_LINK, FONT_FACE, SERIF, SANS, BRUSH, GLYPHS as GL, animal_uri, glyph_svg, brush_svg
import daily

HERE = pathlib.Path(__file__).resolve().parent
FPS = 30
INTRO, PER, OUTRO = 3.2, 2.0, 3.2


gsvg = brush_svg


def build(spec):
    d = date.fromisoformat(spec['date'])
    f = daily.facts(d)
    dp = f['일진']
    head = f'{d.month}월 {d.day}일 {f["요일"]}요일 · {f["일진 읽기"]}'
    secs = ''
    for i, it in enumerate(spec['items']):
        b = it['b']
        au = animal_uri(b)
        pic = (f'<div class="pic" style="background-image:url({au})"></div>{gsvg(b, 300, "gl sm")}' if au else gsvg(b, 380))
        secs += (f'<section class="z{" has" if au else ""}" id="z{i}">{pic}'
                 f'<div class="an">{daily.ANIMAL[b]}띠</div><div class="rd">{daily.READ[b]} {b}</div>'
                 f'<div class="tag"><i></i>{it["tag"]}</div><div class="ln">{it["line"]}</div>'
                 f'<div class="ix">{i+1} / 12</div></section>')
    dur = INTRO + PER * len(spec['items']) + OUTRO
    html = f'''<!doctype html><html><head><meta charset="utf-8">{FONT_LINK}<style>{FONT_FACE}
:root{{--ink:#1A1B1C;--paper:#F1F0EB;--seal:#B23A2E}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:url({PAPER});word-break:keep-all}}
.mwrap{{position:absolute;inset:0;opacity:.7;transform:translateY(330px)}}
.brand{{position:absolute;left:110px;top:130px;display:flex;align-items:center;gap:22px;font-family:'Cormorant Garamond',serif;font-size:40px;letter-spacing:.3em;color:var(--ink);z-index:50}}
.brand .s{{width:72px;height:72px;background:var(--seal);color:var(--paper);display:flex;align-items:center;justify-content:center;font-family:{SERIF};font-weight:600;font-size:48px;border-radius:5px;-webkit-mask-image:url({WEAR});-webkit-mask-size:100% 100%}}
.head{{position:absolute;left:110px;top:250px;font-family:{SANS};font-size:34px;letter-spacing:.12em;color:#6B6860;z-index:50}}
section{{position:absolute;inset:0;opacity:0}}
.gl path.ink{{fill:none}}
.z .gl{{position:absolute;left:90px;top:420px;filter:url(#rough)}}
.pic{{position:absolute;left:380px;top:300px;width:640px;height:640px;background-size:contain;background-repeat:no-repeat;background-position:center;
     -webkit-mask-image:linear-gradient(110deg,#000 0%,#000 var(--p),transparent calc(var(--p) + 18%))}}
.z.has .gl{{left:80px;top:400px}}
.z.has .an{{left:110px;top:700px;font-size:84px}}
.z.has .rd{{left:116px;top:820px}}
.an{{position:absolute;left:540px;top:520px;font-family:{BRUSH};font-weight:800;font-size:96px;color:var(--ink)}}
.rd{{position:absolute;left:546px;top:660px;font-family:{SANS};font-size:34px;letter-spacing:.2em;color:#8E8B82}}
.tag{{position:absolute;left:110px;top:900px;font-family:{SANS};font-size:42px;color:var(--seal);display:flex;align-items:center;gap:16px;font-weight:500}}
.tag i{{width:16px;height:16px;background:var(--seal);display:inline-block}}
.ln{{position:absolute;left:110px;top:980px;width:860px;font-family:{BRUSH};font-weight:800;font-size:70px;line-height:1.38;color:var(--ink);
     -webkit-mask-image:linear-gradient(to right,#000 0%,#000 var(--p),transparent calc(var(--p) + 12%))}}
.ix{{position:absolute;right:110px;top:150px;font-family:{SANS};font-size:30px;color:#8E8B82;letter-spacing:.1em}}
#intro .k{{position:absolute;left:110px;top:420px;font-family:{SANS};font-size:54px;letter-spacing:.06em;color:#46453F}}
#intro .gl{{position:absolute;left:250px;top:520px;filter:url(#rough)}}
#intro .ip{{left:200px;top:440px;width:680px;height:680px}}
#intro .t{{position:absolute;left:110px;top:1060px;font-family:{BRUSH};font-weight:800;font-size:100px;line-height:1.3;color:var(--ink);
     -webkit-mask-image:linear-gradient(to right,#000 0%,#000 var(--p),transparent calc(var(--p) + 12%))}}
#outro .seal{{position:absolute;left:390px;top:470px;width:300px;height:300px;background:var(--seal);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--paper);font-family:{SERIF};font-weight:600;font-size:210px;-webkit-mask-image:url({WEAR});-webkit-mask-size:100% 100%;filter:url(#rough)}}
#outro .a{{position:absolute;left:0;right:0;top:850px;text-align:center;font-family:{BRUSH};font-weight:800;font-size:62px;line-height:1.45;color:var(--ink)}}
#outro .b{{position:absolute;left:0;right:0;top:1110px;text-align:center;font-family:{SERIF};font-size:40px;line-height:1.6;color:#46453F}}
#outro .c{{position:absolute;left:0;right:0;top:1280px;text-align:center;font-family:{SANS};font-size:40px;letter-spacing:.16em;color:#6B6860}}
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs><filter id="rough"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="4"/></filter></defs></svg>
<div class="mwrap" id="mw">{mountains_svg("d")}</div>
<div class="brand" id="brand"><div class="s">構</div>GUJO</div>
<div class="head" id="head">{head}</div>
<section id="intro"><div class="k">오늘은 {daily.ANIMAL[dp[1]]}의 날, {f["일진 읽기"]}</div>{(f'<div class="pic ip" style="background-image:url({animal_uri(dp[1])})"></div>' if animal_uri(dp[1]) else gsvg(dp[1], 580))}
<div class="t">오늘 운세,<br>띠별로 한 줄</div></section>
{secs}
<section id="outro"><div class="seal" id="seal">構</div>
<div class="a">현실의 나와 사주의 운명을<br>함께 계산합니다.</div>
<div class="b">궁금한 운명, GUJO가 답합니다.<br>평생 한 번, GUJO</div>
<div class="c">gujo.kr</div></section>
<script>
const INTRO={INTRO},PER={PER},N={len(spec["items"])};
const C=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),E=x=>1-Math.pow(1-C(x),3);
const $=id=>document.getElementById(id);
document.querySelectorAll('svg.gl').forEach(svg=>{{let tot=0;const ps=[...svg.querySelectorAll('path.ink')];
  ps.forEach(p=>{{const L=p.getTotalLength()+150;p.dataset.L=L;p.dataset.s=tot;tot+=L+120;p.style.strokeDasharray=L+' '+(L+10);p.style.strokeDashoffset=L;}});svg.dataset.T=tot;}});
function draw(svg,p){{ // 붓이 획순대로: 전체 길이 중 p만큼 진행
  if(!svg) return; const T=+svg.dataset.T, at=C(p)*T;
  svg.querySelectorAll('path.ink').forEach(el=>{{const L=+el.dataset.L,s0=+el.dataset.s;el.style.strokeDashoffset=L*(1-C((at-s0)/L));}});
}}
function brush(el,p){{el.style.setProperty('--p',(E(p)*112-12)+'%');}}
function setT(t){{
  $('mw').querySelectorAll('.ml').forEach(g=>{{const k=+g.dataset.k;g.setAttribute('transform',`translate(${{-t*(5+k*8)}},${{(1-E(t/2))*120}})`);}});
  $('head').style.opacity=E((t-.2)/.6);
  const it=$('intro'); it.style.opacity = t<INTRO?1:C(1-(t-INTRO)/.2);
  const isv=it.querySelector('svg.gl'); if(isv) draw(isv,t/1.5);
  const ip=it.querySelector('.ip'); if(ip) ip.style.setProperty('--p',(E(t/1.2)*118-18)+'%'); it.querySelector('.k').style.opacity=E((t-.2)/.5); brush(it.querySelector('.t'),(t-1.2)/1.0);
  for(let i=0;i<N;i++){{const s=$('z'+i),lt=t-(INTRO+i*PER),on=lt>-.1&&lt<PER+.1;
    s.style.opacity=on?C(Math.min((lt+.1)/.15,(PER+.1-lt)/.15)):0; if(!on) continue;
    draw(s.querySelector('svg.gl'),lt/.95); s.querySelector('.an').style.opacity=E((lt-.1)/.3);
    s.querySelector('.rd').style.opacity=E((lt-.2)/.3); s.querySelector('.tag').style.opacity=E((lt-.25)/.3);
    brush(s.querySelector('.ln'),(lt-.3)/.6);
    const pic=s.querySelector('.pic'); if(pic){{pic.style.setProperty('--p',(E(lt/.7)*118-18)+'%');pic.style.transform=`scale(${{1.04-.04*E(lt/1.2)}})`;}}}}
  const ot=t-(INTRO+N*PER),o=$('outro'); o.style.opacity=C((ot+.1)/.25);
  const seal=$('seal'); if(ot<.2) seal.style.opacity=0; else {{const st=ot-.2,p=C(st/.22);
    seal.style.opacity=Math.min(1,p*1.4); seal.style.transform=`scale(${{1.55-.55*p+(st>.22?.035*Math.sin((st-.22)*28)*Math.exp(-(st-.22)*9):0)}}) rotate(${{-6+4*p}}deg)`;}}
  o.querySelector('.a').style.opacity=E((ot-.8)/.5); o.querySelector('.b').style.opacity=E((ot-1.3)/.5); o.querySelector('.c').style.opacity=E((ot-1.8)/.5);
  $('brand').style.opacity = ot>0?C(1-ot/.2):1; $('head').style.opacity = ot>0?C(1-ot/.2):E((t-.2)/.6);
}}
window.setT=setT;
</script></body></html>'''
    return html, dur


def render(spec, out_mp4, only=None, work=None):
    html, dur = build(spec)
    work = pathlib.Path(work or HERE / '_work'); work.mkdir(exist_ok=True)
    frames = work / 'frames'; shutil.rmtree(frames, ignore_errors=True); frames.mkdir()
    hp = work / 'daily.html'; hp.write_text(html, encoding='utf-8')
    n = int(dur * FPS)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        pg.goto(hp.as_uri()); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(800)
        for k in (only or range(n)):
            pg.evaluate(f'setT({k / FPS})'); pg.screenshot(path=str(frames / f'{k:05d}.jpg'), type='jpeg', quality=92)
        b.close()
    if only: return
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(frames / '%05d.jpg'),
                    '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-shortest',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-crf', '20', '-preset', 'medium',
                    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(out_mp4)], check=True)
    print(out_mp4, f'{dur:.1f}s')


if __name__ == '__main__':
    only = [int(x) for x in sys.argv[3:]] or None
    render(json.load(open(sys.argv[1], encoding='utf-8')), sys.argv[2], only)
