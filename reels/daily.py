"""띠별 오늘: 날짜 → 일진과 12띠 관계(계산), 그리고 글쓰기용 사실 묶음."""
import json, sys
from datetime import date

G = '甲乙丙丁戊己庚辛壬癸'
Z = '子丑寅卯辰巳午未申酉戌亥'
ANIMAL = dict(zip(Z, ['쥐', '소', '호랑이', '토끼', '용', '뱀', '말', '양', '원숭이', '닭', '개', '돼지']))
READ = dict(zip(Z, ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']))
GREAD = dict(zip(G, ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']))
MAIN = dict(zip(Z, '癸己甲乙戊丙丁己庚辛戊壬'))  # 지지 본기
EL = dict(zip(G, '木木火火土土金金水水'))
YUKHAP = {frozenset(p) for p in ['子丑', '寅亥', '卯戌', '辰酉', '巳申', '午未']}
CHUNG = {frozenset(p) for p in ['子午', '丑未', '寅申', '卯酉', '辰戌', '巳亥']}
WONJIN = {frozenset(p) for p in ['子未', '丑午', '寅酉', '卯申', '辰亥', '巳戌']}
SAMHAP = ['申子辰', '亥卯未', '寅午戌', '巳酉丑']
HYUNG = ['寅巳申', '丑戌未']
SELF_HYUNG = '辰午酉亥'
GROUP = {'木': 0, '火': 1, '土': 2, '金': 3, '水': 4}
GOD = ['비겁(같은 편)', '식상(표현·솜씨)', '재성(돈·결실)', '관성(규칙·책임)', '인성(도움·문서)']


def day_pillar(d):
    i = (40 + (d - date(1988, 8, 17)).days) % 60  # 1988-08-17 = 甲辰
    return G[i % 10] + Z[i % 12]


def relation(b, day_b):
    s = frozenset(b + day_b)
    out = []
    if b == day_b:
        out.append('같은 글자' + (' · 자형' if b in SELF_HYUNG else ''))
    if s in YUKHAP: out.append('육합')
    if s in CHUNG: out.append('충')
    if s in WONJIN: out.append('원진')
    if s == frozenset('子卯'): out.append('형')
    for g in HYUNG:
        if b != day_b and b in g and day_b in g: out.append('형')
    for g in SAMHAP:
        if b != day_b and b in g and day_b in g and g[1] in (b, day_b): out.append('반합')
    return out


def god(me_b, other_b):
    a, o = GROUP[EL[MAIN[me_b]]], GROUP[EL[MAIN[other_b]]]
    return GOD[(o - a) % 5]


def facts(d):
    dp = day_pillar(d)
    rows = []
    for b in Z:
        rows.append({'띠': ANIMAL[b] + '띠', '지지': b, '오늘과의 관계': relation(b, dp[1]) or ['특별한 합·충 없음'],
                     '오늘 지지가 이 띠에게': god(b, dp[1])})
    return {'날짜': d.isoformat(), '요일': '월화수목금토일'[d.weekday()], '일진': dp,
            '일진 읽기': GREAD[dp[0]] + READ[dp[1]] + '일', '띠별': rows}


if __name__ == '__main__':
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(json.dumps(facts(d), ensure_ascii=False, indent=1))
