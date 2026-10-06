"""구조 AI 자동 답글 (스레드).

최근 7일 안에 올린 내 스레드 글에 달린 새 댓글을 모아, Claude Code(구독)로 한 번에 답을 쓰고
각 댓글에 답글로 단다. 기록은 state/replied.json.

필요한 환경변수: THREADS_TOKEN, CLAUDE_CODE_OAUTH_TOKEN, (선택) REPLY_MODEL=opus|sonnet|haiku
사용:
  python scripts/reply.py            # 실제로 답글
  python scripts/reply.py --dry-run  # 쓸 답만 출력, 올리지 않음
"""
import json, os, subprocess, sys, time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post import api, wait_ready, TH, ROOT, KST  # noqa: E402

DRY = '--dry-run' in sys.argv
MODEL = os.environ.get('REPLY_MODEL') or 'opus'
MAX_PER_RUN = 15
MAX_PER_DAY = 80
SIGN = ' — 구조 AI'

PERSONA = open(os.path.join(ROOT, 'scripts', 'reply_persona.md'), encoding='utf-8').read()


def recent_posts(uid, tok):
    since = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())
    r = api('GET', f'{TH}/{uid}/threads', {'fields': 'id,text,timestamp', 'since': since, 'limit': 25, 'access_token': tok})
    return r.get('data', [])


def new_comments(post, tok, me, done):
    r = api('GET', f'{TH}/{post["id"]}/replies',
            {'fields': 'id,text,username,timestamp,is_reply_owned_by_me', 'reverse': 'false', 'access_token': tok})
    out = []
    for c in r.get('data', []):
        if c.get('is_reply_owned_by_me') or c.get('username') == me:
            continue
        if c['id'] in done or not (c.get('text') or '').strip():
            continue
        out.append({'id': c['id'], 'user': c.get('username', ''), 'comment': c['text'][:500], 'post': (post.get('text') or '')[:600]})
    return out


def write_replies(batch):
    prompt = (PERSONA + '\n\n## 이번에 답할 댓글 (JSON)\n' + json.dumps(batch, ensure_ascii=False, indent=1)
              + '\n\n## 출력\n다른 말 없이 JSON 배열만 출력하세요: [{"id": "댓글 id", "reply": "답글 또는 SKIP"}]')
    res = subprocess.run(['claude', '-p', prompt, '--model', MODEL, '--output-format', 'text', '--max-turns', '1'],
                         capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f'claude 실행 실패: {res.stderr[:400]}')
    out = res.stdout.strip()
    s, e = out.find('['), out.rfind(']')
    return json.loads(out[s:e + 1])


def main():
    tok = os.environ['THREADS_TOKEN']
    me = api('GET', f'{TH}/me', {'fields': 'id,username', 'access_token': tok})
    uid, uname = me['id'], me.get('username')
    state_p = os.path.join(ROOT, 'state', 'replied.json')
    state = json.load(open(state_p, encoding='utf-8')) if os.path.exists(state_p) else {}
    today = datetime.now(KST).strftime('%Y-%m-%d')
    used_today = sum(1 for v in state.values() if v.get('day') == today and v.get('reply') not in (None, 'SKIP'))
    room = min(MAX_PER_RUN, MAX_PER_DAY - used_today)
    if room <= 0:
        print('오늘 답글 한도에 닿음'); return

    batch = []
    for p in recent_posts(uid, tok):
        batch += new_comments(p, tok, uname, state)
        if len(batch) >= room:
            break
    batch = batch[:room]
    if not batch:
        print('새 댓글 없음'); return
    print(f'새 댓글 {len(batch)}개 → {MODEL}로 답 작성')

    answers = {a['id']: a['reply'].strip() for a in write_replies(batch)}
    for c in batch:
        reply = answers.get(c['id'], 'SKIP')
        if reply != 'SKIP' and not reply.endswith(SIGN.strip()):
            reply = reply.rstrip() + SIGN
        print(f'- @{c["user"]}: {c["comment"][:60]}\n  → {reply}')
        if DRY:
            continue
        entry = {'day': today, 'reply': reply}
        if reply != 'SKIP':
            try:
                cid = api('POST', f'{TH}/{uid}/threads', {'media_type': 'TEXT', 'text': reply[:500], 'reply_to_id': c['id'], 'access_token': tok})['id']
                wait_ready(TH, cid, tok, 'status')
                entry['post_id'] = api('POST', f'{TH}/{uid}/threads_publish', {'creation_id': cid, 'access_token': tok})['id']
                time.sleep(3)
            except Exception as e:
                entry = {'day': today, 'reply': None, 'error': str(e)[:300]}
                print(f'  실패: {e}')
        state[c['id']] = entry
    if not DRY:
        json.dump(state, open(state_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
