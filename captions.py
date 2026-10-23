def _t(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


def captions(words, path, w, h, per=3):
    """ASS file: a few words at a time, big and centred in the lower third, shown while they are spoken."""
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Outline,Shadow,Alignment,MarginL,MarginR,MarginV\n"
        "Style: C,DejaVu Sans,84,&H00FFFFFF,&H00000000,&H80000000,1,6,2,2,80,80,420\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Text\n"
    )
    ev = []
    for k in range(0, len(words), per):
        g = words[k:k + per]
        end = words[k + per][0] if k + per < len(words) else g[-1][1] + 0.3
        text = " ".join(x[2] for x in g).upper()
        ev.append(f"Dialogue: 0,{_t(g[0][0])},{_t(end)},C,{text}\n")
    open(path, "w", encoding="utf-8").write(head + "".join(ev))
