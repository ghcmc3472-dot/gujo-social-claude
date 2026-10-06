"""GUJO Claude 계정 예약 게시.

posts/schedule.json에서 approved=true이고 시각이 지난 항목을 인스타그램·스레드에 올리고,
state/posted.json에 기록한다. 토큰은 환경변수 IG_TOKEN, THREADS_TOKEN에서만 읽는다.

사용:
  python scripts/post.py            # 실제 게시
  python scripts/post.py --dry-run  # 무엇이 올라갈지만 출력
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = timezone(timedelta(hours=9))
IG = 'https://graph.instagram.com/v23.0'
TH = 'https://graph.threads.net/v1.0'
DRY = '--dry-run' in sys.argv
MAX_PER_RUN = 3  # 한 번 실행에 최대 3건 (밀린 게 몰려 올라가지 않게)


def api(method, url, params):
    data = urllib.parse.urlencode(params).encode()
    if method == 'GET':
        req = urllib.request.Request(url + '?' + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        raise RuntimeError(f'{e.code} {body[:500]}') from None


def image_url(rel):
    repo = os.environ.get('GITHUB_REPOSITORY', 'OWNER/REPO')
    branch = os.environ.get('GITHUB_REF_NAME', 'main')
    return f'https://raw.githubusercontent.com/{repo}/{branch}/posts/{rel}'


def wait_ready(base, cid, token, field, tries=30):
    for _ in range(tries):
        st = api('GET', f'{base}/{cid}', {'fields': field, 'access_token': token}).get(field, '')
        if st in ('FINISHED', 'PUBLISHED'):
            return
        if st in ('ERROR', 'EXPIRED'):
            raise RuntimeError(f'컨테이너 {cid} 상태 {st}')
        time.sleep(5)
    raise RuntimeError(f'컨테이너 {cid} 준비 시간 초과')


FB = 'https://graph.facebook.com/v23.0'


def ig_ctx(tok):
    """토큰 종류에 따라 (API 주소, 인스타 계정 id). EAA… = 페이스북 로그인(음악 가능), IGAA… = 인스타 로그인."""
    if tok.startswith('EAA'):
        pages = api('GET', f'{FB}/me/accounts', {'fields': 'instagram_business_account', 'access_token': tok}).get('data', [])
        ids = [p['instagram_business_account']['id'] for p in pages if p.get('instagram_business_account')]
        if not ids:
            raise RuntimeError('페이스북 페이지에 연결된 인스타 계정을 찾지 못했습니다')
        return FB, ids[0]
    return IG, api('GET', f'{IG}/me', {'fields': 'user_id,username', 'access_token': tok})['user_id']


def find_music(tok, queries, avoid=(), min_ms=25000):
    """인스타 음악 검색(페이스북 로그인 토큰일 때만). 최근에 쓴 곡은 피한다."""
    if not tok.startswith('EAA'):
        return None
    base, uid = ig_ctx(tok)
    for q in queries:
        try:
            params = {'audio_type': 'music', 'user_id': uid, 'access_token': tok}
            if q:  # 검색어가 비어 있으면 지금 인기 음악
                params['search_query'] = q
            res = api('GET', 'https://graph.facebook.com/v26.0/ig_audio', params)
            rows = res.get('audio') or res.get('data') or []
        except Exception as e:
            print(f'  음악 검색 실패({q}): {e}')
            continue
        for r in rows:
            if r.get('audio_id') and r['audio_id'] not in avoid and int(r.get('duration_in_ms') or 0) >= min_ms:
                return {'audio_id': r['audio_id'], 'title': r.get('title'), 'artist': r.get('display_artist'), 'query': q}
    return None


def post_instagram(item):
    tok = os.environ['IG_TOKEN']
    base, uid = ig_ctx(tok)
    if item.get('video'):
        params = {'media_type': 'REELS', 'video_url': image_url(item['video']), 'caption': item['text'],
                  'share_to_feed': 'true', 'access_token': tok}
        if item.get('audio_id') and base == FB:
            params['audio_configuration'] = json.dumps({'audio_id': item['audio_id'], 'audio_volume': 100, 'video_volume': 0})
        cid = api('POST', f'{base}/{uid}/media', params)['id']
        wait_ready(base, cid, tok, 'status_code', tries=60)
        return api('POST', f'{base}/{uid}/media_publish', {'creation_id': cid, 'access_token': tok})['id']
    imgs = item['images']
    if not imgs:
        raise RuntimeError('인스타그램은 이미지가 필요합니다')
    if len(imgs) == 1:
        cid = api('POST', f'{base}/{uid}/media', {'image_url': image_url(imgs[0]), 'caption': item['text'], 'access_token': tok})['id']
    else:
        if len(imgs) > 10:
            raise RuntimeError('캐러셀은 10장까지입니다')
        kids = []
        for im in imgs:
            k = api('POST', f'{base}/{uid}/media', {'image_url': image_url(im), 'is_carousel_item': 'true', 'access_token': tok})['id']
            wait_ready(base, k, tok, 'status_code'); kids.append(k)
        cid = api('POST', f'{base}/{uid}/media', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'caption': item['text'], 'access_token': tok})['id']
    wait_ready(base, cid, tok, 'status_code')
    return api('POST', f'{base}/{uid}/media_publish', {'creation_id': cid, 'access_token': tok})['id']


def th_publish_one(uid, tok, text, imgs, topic=None, reply_to=None, video=None):
    if len(text) > 500:
        raise RuntimeError('스레드 글은 500자까지입니다')
    extra = {'access_token': tok}
    if topic:
        extra['topic_tag'] = topic
    if reply_to:
        extra['reply_to_id'] = reply_to
    if video:
        cid = api('POST', f'{TH}/{uid}/threads', {'media_type': 'VIDEO', 'video_url': image_url(video), 'text': text, **extra})['id']
        wait_ready(TH, cid, tok, 'status', tries=60)
        return api('POST', f'{TH}/{uid}/threads_publish', {'creation_id': cid, 'access_token': tok})['id']
    if not imgs:
        cid = api('POST', f'{TH}/{uid}/threads', {'media_type': 'TEXT', 'text': text, **extra})['id']
    elif len(imgs) == 1:
        cid = api('POST', f'{TH}/{uid}/threads', {'media_type': 'IMAGE', 'image_url': image_url(imgs[0]), 'text': text, **extra})['id']
    else:
        kids = []
        for im in imgs:
            kids.append(api('POST', f'{TH}/{uid}/threads', {'media_type': 'IMAGE', 'image_url': image_url(im), 'is_carousel_item': 'true', 'access_token': tok})['id'])
        for k in kids:
            wait_ready(TH, k, tok, 'status')
        cid = api('POST', f'{TH}/{uid}/threads', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'text': text, **extra})['id']
    wait_ready(TH, cid, tok, 'status')
    return api('POST', f'{TH}/{uid}/threads_publish', {'creation_id': cid, 'access_token': tok})['id']


def post_threads(item):
    """본문을 올리고, replies가 있으면 내 글에 이어 다는 타래로 올린다."""
    tok = os.environ['THREADS_TOKEN']
    uid = api('GET', f'{TH}/me', {'fields': 'id,username', 'access_token': tok})['id']
    root = th_publish_one(uid, tok, item['text'], item.get('images', []), item.get('topic'), video=item.get('video'))
    prev = root
    for n, r in enumerate(item.get('replies', []), 1):
        time.sleep(5)
        try:
            prev = th_publish_one(uid, tok, r['text'], r.get('images', []), reply_to=prev)
        except Exception as e:  # 본문은 이미 올라갔으니 다시 올리지 않는다
            print(f'  타래 {n}번째에서 멈춤: {e}')
            break
    return root


def main():
    sched = json.load(open(os.path.join(ROOT, 'posts', 'schedule.json'), encoding='utf-8'))
    state_p = os.path.join(ROOT, 'state', 'posted.json')
    state = json.load(open(state_p, encoding='utf-8')) if os.path.exists(state_p) else {}
    now = datetime.now(KST)
    done = 0
    new_fail = []
    for it in sorted(sched['items'], key=lambda x: x['at']):
        if done >= MAX_PER_RUN:
            break
        prev = state.get(it['id'], {})
        if prev.get('ok') or prev.get('fails', 0) >= 3:
            continue
        if not it.get('approved'):
            continue
        at = datetime.strptime(it['at'], '%Y-%m-%d %H:%M').replace(tzinfo=KST)
        if at > now:
            continue
        if now - at > timedelta(days=2):
            print(f'건너뜀(이틀 넘게 지남): {it["id"]}')
            continue
        print(f'게시: {it["id"]} ({it["channel"]}, {it["at"]}, 이미지 {len(it.get("images", []))}장, 타래 {len(it.get("replies", []))}개)')
        if DRY:
            continue
        try:
            pid = post_instagram(it) if it['channel'] == 'instagram' else post_threads(it)
            state[it['id']] = {'ok': True, 'post_id': pid, 'at': now.isoformat(timespec='minutes')}
            print(f'  완료: {pid}')
        except Exception as e:
            fails = state.get(it['id'], {}).get('fails', 0) + 1
            state[it['id']] = {'ok': False, 'error': str(e)[:300], 'fails': fails, 'at': now.isoformat(timespec='minutes')}
            print(f'  실패: {e}')
            new_fail.append(it['id'])
        done += 1
    if not DRY:
        json.dump(state, open(state_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if new_fail:
        print('이번 실행 실패:', ', '.join(new_fail), '(3번 실패하면 더 시도하지 않음)')
        sys.exit(1)


if __name__ == '__main__':
    main()
