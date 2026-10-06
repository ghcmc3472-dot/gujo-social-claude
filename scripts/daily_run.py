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
           'calm piano,korean traditional,gayageum,ambient morning,lofi chill,acoustic morning').split(',') if q.strip()]
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
        print('\n[캡션]\n' + cap); return

    # 영상이 공개 주소에 올라가야 인스타·스레드가 가져갈 수 있으므로 먼저 커밋·푸시
    subprocess.run(['git', 'add', 'posts/daily', 'state/daily_history.json'], cwd=ROOT, check=True)
    subprocess.run(['git', '-c', 'user.name=gujo-bot', '-c', 'user.email=gujo-bot@users.noreply.github.com',
                    'commit', '-m', f'띠별 오늘 {d}'], cwd=ROOT, check=False)
    subprocess.run(['git', 'pull', '--rebase'], cwd=ROOT, check=False)
    subprocess.run(['git', 'push'], cwd=ROOT, check=True)

    used = [h.get('audio', {}).get('audio_id') for h in hist.values() if h.get('audio')]
    music = find_music(os.environ['IG_TOKEN'], QUERIES[d.toordinal() % len(QUERIES):] + QUERIES, avoid=used[-14:])
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
