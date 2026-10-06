"""토큰이 어느 계정 것인지, 게시 권한이 있는지만 확인한다. 아무것도 올리지 않는다."""
import json, os, urllib.request, urllib.error


def get(url, tok):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tok})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        try:
            return {'error': json.loads(e.read()).get('error', {}).get('message', str(e))}
        except Exception:
            return {'error': str(e)}


out = {}
ig = os.environ.get('IG_TOKEN', '').strip()
if ig:
    if ig.startswith('EAA'):
        out['instagram'] = {'type': 'facebook-login', 'pages': get('https://graph.facebook.com/v21.0/me/accounts?fields=name,instagram_business_account{username}', ig)}
    else:
        me = get('https://graph.instagram.com/v21.0/me?fields=user_id,username,account_type', ig)
        r = {'type': 'instagram-login', 'me': me}
        if 'user_id' in me:
            r['publish_limit'] = get(f"https://graph.instagram.com/v21.0/{me['user_id']}/content_publishing_limit?fields=quota_usage,config", ig)
        out['instagram'] = r
th = os.environ.get('THREADS_TOKEN', '').strip()
if th:
    out['threads'] = get('https://graph.threads.net/v1.0/me?fields=id,username', th)
print(json.dumps(out, ensure_ascii=False, indent=1))
os.makedirs('state', exist_ok=True)
json.dump(out, open('state/whoami.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
