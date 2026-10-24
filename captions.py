def _t(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


def align(tokens, words):
    """Spoken words with timings. Use the engine's timings when the counts match, else spread over the audio by word length."""
    if not words: return []
    if len(tokens) == len(words): return [(w[0], w[1], t) for w, t in zip(words, tokens)]
    a, b = words[0][0], words[-1][1]; tot = sum(len(t) + 1 for t in tokens); out = []; x = a
    for t in tokens:
        d = (b - a) * (len(t) + 1) / tot; out.append((x, x + d, t)); x += d
    return out


def captions(words, path, w, h, per=3):
    """ASS file: a few words at a time, big and centred in the lower third, the word being spoken in yellow."""
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Outline,Shadow,Alignment,MarginL,MarginR,MarginV\n"
        "Style: C,DejaVu Sans,96,&H00FFFFFF,&H00000000,&H80000000,1,8,2,2,70,70,430\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Text\n"
    )
    ev = []
    for k in range(0, len(words), per):
        g = words[k:k + per]
        for j, (st, en, _) in enumerate(g):
            end = g[j + 1][0] if j + 1 < len(g) else (words[k + per][0] if k + per < len(words) else en + 0.3)
            text = " ".join(("{\\c&H00E5FF&}" + x[2].upper() + "{\\c&HFFFFFF&}") if i == j else x[2].upper() for i, x in enumerate(g))
            ev.append(f"Dialogue: 0,{_t(st)},{_t(end)},C,{text}\n")
    open(path, "w", encoding="utf-8").write(head + "".join(ev))
