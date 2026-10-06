"""띠별 오늘: 계산 → Claude가 12줄 → 수묵 릴스 → 인스타 릴스(+인스타 음악) · 스레드 타래.

환경변수: IG_TOKEN, THREADS_TOKEN, CLAUDE_CODE_OAUTH_TOKEN, (선택) DAILY_MODEL, DAILY_MUSIC_QUERIES
사용:
  python scripts/daily_run.py                 # 오늘 것 만들고 07:30에 올림 (--now: 바로 올림)
  python scripts/daily_run.py --dry-run       # 만들기만 (영상은 posts/daily/에 저장)
  python scripts/daily_run.py --date 2026-10-07 --dry-run
"""
import json, os, re, subprocess, sys, glob, time
from datetime import datetime, date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'reels'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import daily  # noqa: E402
from daily_reel import render  # noqa: E402
from post import KST, post_instagram, post_threads, find_music  # noqa: E402

DRY = '--dry-run' in sys.argv
MODEL = os.environ.get('DAILY_MODEL') or 'opus'
QUERIES = [q.strip() for q in (os.environ.get('DAILY_MUSIC_QUERIES') or
           'meditation,zen,gayageum,guzheng,koto,asian ambient,bamboo flute,calm piano,ambient,peaceful morning').split(',') if q.strip()]
MOOD = ('한지 위 먹으로 그린 수묵화 영상(산, 붓글씨, 띠 동물), 아침 7시 30분에 보는 30초 띠별 운세. '
        '고요하고 단정한 동양적 분위기. 가사 없는 연주곡, 느리거나 중간 빠르기, 피아노·가야금·대금·고토·앰비언트 계열이 맞고 '
        '댄스·록·힙합·파티·생일·코믹·효과음은 맞지 않는다.')
HIST_P = os.path.join(ROOT, 'state', 'daily_history.json')
JARGON = ['육합', '반합', '삼합', '원진', '형살', '비겁', '식상', '재성', '관성', '인성', '일진', '지지', '천간', '십성']
TAGS = '#오늘의운세 #띠별운세 #사주 #명리 #일진 #운세 #GUJO'


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def write_lines(facts, hist):
    recent = [it['line'] for d in sorted(hist)[-7:] for it in hist[d].get('items', [])]
    prompt = (open(os.path.join(ROOT, 'scripts', 'daily_prompt.md'), encoding='utf-8').read()
              + '\n\n## 오늘의 계산\n' + json.dumps(facts, ensure_ascii=False, indent=1)
              + '\n\n## 최근에 쓴 문장 (반복 금지)\n' + '\n'.join(recent[-84:]))
    last_err = None
    for _ in range(2):
        r = subprocess.run(['claude', '-p', prompt, '--model', MODEL, '--output-format', 'text', '--max-turns', '1'],
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            last_err = r.stderr[:400]; continue
        out = r.stdout; s, e = out.find('{'), out.rfind('}')
        try:
            items = json.loads(out[s:e + 1])['items']
            check(items, recent)
            return items
        except Exception as ex:
            last_err = str(ex); prompt += f'\n\n## 지난 출력의 문제\n{last_err}\n다시 지침대로만 쓰세요.'
    raise RuntimeError(f'문장 작성 실패: {last_err}')


def pick_music(tok, avoid):
    """분위기 검색어로 후보를 모으고, 영상 분위기에 가장 맞는 곡을 Claude가 고른다."""
    from post import ig_ctx, api
    if not tok.startswith('EAA'):
        return None
    _, uid = ig_ctx(tok)
    cands, seen = [], set()
    for q in QUERIES:
        try:
            res = api('GET', 'https://graph.facebook.com/v26.0/ig_audio',
                      {'audio_type': 'music', 'user_id': uid, 'search_query': q, 'access_token': tok})
        except Exception as e:
            print(f'  음악 검색 실패({q}): {e}'); continue
        for r in (res.get('audio') or res.get('data') or [])[:8]:
            a = r.get('audio_id')
            if a and a not in seen and a not in avoid and int(r.get('duration_in_ms') or 0) >= 30000:
                seen.add(a)
                cands.append({'audio_id': a, 'title': r.get('title'), 'artist': r.get('display_artist'),
                              'sec': int(r.get('duration_in_ms') or 0) // 1000, 'query': q})
    if not cands:
        return None
    listing = '\n'.join(f"{i}. {c['title']} — {c['artist']} ({c['sec']}초, 검색어: {c['query']})" for i, c in enumerate(cands))
    prompt = (f'영상 분위기: {MOOD}\n\n후보 곡 목록:\n{listing}\n\n'
              '제목·아티스트·검색어로 판단해 이 영상에 가장 어울리는 곡 하나의 번호만 JSON으로 답하세요. 예: {"pick": 3, "why": "한 줄 이유"}')
    try:
        r = subprocess.run(['claude', '-p', prompt, '--model', MODEL, '--output-format', 'text', '--max-turns', '1'],
                           capture_output=True, text=True, timeout=300)
        o = r.stdout; j = json.loads(o[o.find('{'):o.rfind('}') + 1])
        c = cands[int(j['pick'])]; c['why'] = j.get('why')
        return c
    except Exception as e:
        print(f'  곡 고르기 실패, 첫 후보 사용: {e}')
        return cands[0]


def check(items, recent):
    if [it['b'] for it in items] != list(daily.Z):
        raise ValueError('12띠가 子부터 亥 순서로 다 있어야 합니다')
    seconds = set()
    for it in items:
        if len(it['tag']) > 14: raise ValueError(f'tag가 깁니다: {it["tag"]}')
        if re.search(r'[\u4e00-\u9fff]', it['tag'] + it['line']): raise ValueError(f'한자가 들어갔습니다: {it["tag"]} / {it["line"]}')
        for w in JARGON:
            if w in it['tag'] or w in it['line']: raise ValueError(f'어려운 말({w}): {it["tag"]} / {it["line"]}')
        if len(it['line']) > 38: raise ValueError(f'line이 깁니다({len(it["line"])}자): {it["line"]}')
        if it['line'] in recent: raise ValueError(f'최근 문장 반복: {it["line"]}')
        sec = it['line'].split('.')[1].strip() if '.' in it['line'] else it['line']
        if sec in seconds: raise ValueError(f'같은 할 일 반복: {sec}')
        seconds.add(sec)


def caption(facts, items):
    d = date.fromisoformat(facts['날짜'])
    tags = ' '.join(f'#{daily.ANIMAL[b]}띠' for b in daily.Z)
    return (f'오늘 내 띠는 뭘 하면 될까? 👆 영상에서 확인하세요\n'
            f'{d.month}월 {d.day}일 {facts["요일"]}요일, {facts["일진 읽기"]}\n\n'
            '띠 하나로는 부족합니다.\n\n'
            'GUJO. 현실의 나와 사주의 운명을 함께 계산합니다.\n'
            '궁금한 운명, GUJO가 답합니다.\n'
            '평생 한 번, GUJO. → gujo.kr (프로필 링크)\n\n'
            '(띠는 설날이 아니라 입춘, 2월 4일 무렵에 바뀝니다.)\n\n'
            f'#오늘의운세 #띠별운세 {tags} #사주 #GUJO')


def main():
    d = date.fromisoformat(arg('--date')) if arg('--date') else datetime.now(KST).date()
    hist = json.load(open(HIST_P, encoding='utf-8')) if os.path.exists(HIST_P) else {}
    if hist.get(d.isoformat(), {}).get('ig') and not DRY:
        print('오늘 것은 이미 올렸습니다'); return
    facts = daily.facts(d)
    print('일진', facts['일진'])
    items = hist.get(d.isoformat(), {}).get('items') or write_lines(facts, hist)
    for it in items: print(f'  {daily.ANIMAL[it["b"]]}띠 | {it["tag"]} | {it["line"]}')
    rec = hist.setdefault(d.isoformat(), {}); rec['items'] = items

    rel = f'daily/{d.isoformat()}.mp4'
    out = os.path.join(ROOT, 'posts', rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    render({'date': d.isoformat(), 'items': items}, out, work=os.path.join(ROOT, '.work'))
    # 2주 넘은 영상은 지움(저장소가 커지지 않게)
    for f in glob.glob(os.path.join(ROOT, 'posts', 'daily', '*.mp4')):
        if os.path.basename(f) < (d - timedelta(days=14)).isoformat(): os.remove(f)
    cap = caption(facts, items)
    json.dump(hist, open(HIST_P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if DRY:
        used = [h.get('audio', {}).get('audio_id') for h in hist.values() if h.get('audio')]
        music = pick_music(os.environ.get('IG_TOKEN', ''), used[-14:])
        print('\n[캡션]\n' + cap + '\n\n[음악] ' + json.dumps(music, ensure_ascii=False))
        od = os.path.join(ROOT, 'dryrun', 'out'); os.makedirs(od, exist_ok=True)
        open(os.path.join(od, 'caption.txt'), 'w', encoding='utf-8').write(cap)
        json.dump({'music': music, 'items': items}, open(os.path.join(od, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return

    # 영상이 공개 주소에 올라가야 인스타·스레드가 가져갈 수 있으므로 먼저 커밋·푸시
    subprocess.run(['git', 'add', 'posts/daily', 'state/daily_history.json'], cwd=ROOT, check=True)
    subprocess.run(['git', '-c', 'user.name=gujo-bot', '-c', 'user.email=gujo-bot@users.noreply.github.com',
                    'commit', '-m', f'띠별 오늘 {d}'], cwd=ROOT, check=False)
    subprocess.run(['git', 'pull', '--rebase'], cwd=ROOT, check=False)
    subprocess.run(['git', 'push'], cwd=ROOT, check=True)

    used = [h.get('audio', {}).get('audio_id') for h in hist.values() if h.get('audio')]
    music = pick_music(os.environ['IG_TOKEN'], used[-14:])
    if music: print(f'음악: {music["title"]} — {music["artist"]}'); rec['audio'] = music
    else: print('음악 없이 올림(페이스북 로그인 토큰이 아니거나 검색 결과 없음)')

    # 게시 시각(기본 07:30)까지 기다렸다가 올린다. 수동 실행은 --now로 바로 올림.
    if '--now' not in sys.argv:
        hh, mm = (os.environ.get('DAILY_POST_AT') or '07:30').split(':')
        target = datetime.now(KST).replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        wait = (target - datetime.now(KST)).total_seconds()
        if 0 < wait < 3 * 3600:
            print(f'{hh}:{mm}까지 {int(wait // 60)}분 기다림'); time.sleep(wait)

    errors = []
    try:
        rec['ig'] = post_instagram({'video': rel, 'text': cap, 'audio_id': music and music['audio_id']}); print('인스타 완료', rec['ig'])
    except Exception as e:
        errors.append(f'인스타: {e}')
    try:
        dd = date.fromisoformat(facts['날짜'])
        root_text = (f'{dd.month}월 {dd.day}일 {facts["요일"]}요일, 오늘은 {facts["일진 읽기"]}.\n'
                     f'내 띠 오늘의 운, 아래 타래에서 찾아보세요. 👇')
        replies = [{'text': f'{daily.ANIMAL[it["b"]]}띠 · {it["tag"]}\n{it["line"]}'} for it in items]
        replies.append({'text': '띠 하나로는 부족해요.\nGUJO는 현실의 나와 사주의 운명을 함께 계산해요. 궁금한 운명, GUJO가 답합니다.\n평생 한 번, GUJO → gujo.kr'})
        rec['threads'] = post_threads({'text': root_text, 'video': rel, 'topic': '오늘의운세', 'replies': replies}); print('스레드 완료', rec['threads'])
    except Exception as e:
        errors.append(f'스레드: {e}')
    json.dump(hist, open(HIST_P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if errors:
        print('\n'.join(errors)); sys.exit(1)


if __name__ == '__main__':
    main()
