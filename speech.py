"""Turn numbers, money and percentages into words so the voice reads them the way a person would."""
import re

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
BIG = [(10**9, "billion"), (10**6, "million"), (1000, "thousand")]
CUR = {"$": ("dollar", "cent"), "£": ("pound", "pence"), "€": ("euro", "cent"), "₵": ("cedi", "pesewa")}
SCALE = {"k": 1000, "m": 10**6, "bn": 10**9, "b": 10**9}

def int_words(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000: return ONES[n // 100] + " hundred" + (" " + int_words(n % 100) if n % 100 else "")
    for v, name in BIG:
        if n >= v: return int_words(n // v) + " " + name + (" " + int_words(n % v) if n % v else "")

def year_words(n):
    a, b = divmod(n, 100)
    return int_words(a) + " " + ("oh " + ONES[b] if 0 < b < 10 else int_words(b) if b else "hundred")

def _num(s, suffix=None):
    s = s.replace(",", "")
    if suffix:
        v = float(s) * SCALE[suffix.lower()]
        return int_words(int(round(v))) if v == int(v) else _num(s) + " " + {"k": "thousand", "m": "million", "b": "billion", "bn": "billion"}[suffix.lower()]
    if "." in s:
        a, b = s.split(".")
        return int_words(int(a or 0)) + " point " + " ".join(ONES[int(c)] for c in b)
    return int_words(int(s))

def _money(m):
    sym, n, suf = m.group(1), m.group(2), m.group(3)
    unit = CUR[sym][0]
    if suf:
        words = _num(n, suf)
        return words + " " + unit + "s"
    if "." in n:
        a, b = n.replace(",", "").split(".")
        a, b = int(a or 0), int((b + "0")[:2])
        out = int_words(a) + " " + unit + ("" if a == 1 else "s")
        return out + (" and " + int_words(b) + " " + CUR[sym][1] + ("" if b == 1 or CUR[sym][1] == "pence" else "s") if b else "")
    v = int(n.replace(",", ""))
    return int_words(v) + " " + unit + ("" if v == 1 else "s")

def speakable(t):
    t = re.sub(r"([$£€₵])\s?(\d[\d,]*(?:\.\d+)?)\s?(bn|[kKmMbB])?\b", lambda m: _money(m), t)
    t = re.sub(r"(\d[\d,]*(?:\.\d+)?)\s?%", lambda m: _num(m.group(1)) + " percent", t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{1,2})\b", lambda m: " ".join(int_words(int(x)) for x in m.groups()), t)
    t = re.sub(r"\b(1[5-9]\d\d|20\d\d)\b", lambda m: year_words(int(m.group(1))), t)
    t = re.sub(r"\b(\d[\d,]*)(?:\.(\d+))?\b", lambda m: _num(m.group(0)), t)
    return t.replace("&", " and ")
