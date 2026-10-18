#!/usr/bin/env python3
"""Animated short-video pipeline (no slideshows).

Every scene is a real AI-animated clip from HeyGen Video (heygen-video-1,
text_to_video), cut to a narration track, captioned and mixed with the
clip's own sound effects under the voice.

Usage:
  python3 make_video.py gen      <dir>   # generate missing clips/NN.mp4 from <dir>/scenes.json
  python3 make_video.py assemble <dir>   # needs <dir>/vo.mp3; writes <dir>/<slug>-hq.mp4 + preview

scenes.json: {"slug", "style", "resolution", "scenes": [{"narration", "prompt", "duration"}]}
Each scene's narration should be whole sentences; the voiceover is one take of
all narrations in order. HeyGen auth is injected by the environment proxy, or
set HEYGEN_API_KEY.
Cost (Oct 2026): 768p about $0.02/s, 1080p about $0.06/s of clip.
"""
import json, math, os, re, subprocess, sys, time, urllib.request

API = "https://api.heygen.com/v3/models/videos"
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"


def api(method, url, body=None):
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    if os.environ.get("HEYGEN_API_KEY"):
        req.add_header("x-api-key", os.environ["HEYGEN_API_KEY"])
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def gen(d):
    cfg = json.load(open(f"{d}/scenes.json"))
    os.makedirs(f"{d}/clips", exist_ok=True)
    jobs = {}
    for i, s in enumerate(cfg["scenes"]):
        out = f"{d}/clips/{i:02d}.mp4"
        if os.path.exists(out):
            continue
        body = {"model": "heygen-video-1", "mode": "text_to_video",
                "prompt": s["prompt"] + " " + cfg["style"],
                "duration": max(5, min(15, int(s.get("duration", 6)))),
                "resolution": cfg.get("resolution", "1080p"), "aspect_ratio": "9:16"}
        jobs[i] = api("POST", API, body)["data"]["video_id"]
        print(f"scene {i}: submitted {jobs[i]}", flush=True)
    while jobs:
        time.sleep(10)
        for i, vid in list(jobs.items()):
            r = api("GET", f"{API}/{vid}")["data"]
            if r["status"] == "completed":
                urllib.request.urlretrieve(r["video_url"], f"{d}/clips/{i:02d}.mp4")
                print(f"scene {i}: done", flush=True)
                del jobs[i]
            elif r["status"] in ("failed", "cancelled"):
                print(f"scene {i}: {r['status']} {r.get('error')}", flush=True)
                del jobs[i]


def run(cmd):
    subprocess.run(cmd, check=True)


def probe_dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", f]).decode())


def sentence_times(vo, sents):
    """Start/end of each sentence: walk the VO, snapping each expected sentence
    end (from character counts) to the nearest real pause, longer pauses preferred."""
    log = subprocess.run(["ffmpeg", "-i", vo, "-af", "silencedetect=n=-35dB:d=0.12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    total = probe_dur(vo)
    lead = ends[0] if starts and starts[0] < 0.05 else 0.0
    tail = starts[-1] if starts and len(starts) > len(ends) else total
    gaps = [(s, e) for s, e in zip(starts, ends) if lead < s and e < tail]
    # Global alignment (DP): pick len(sents)-1 pauses in order, rewarding long
    # pauses and penalising sentences spoken unusually fast or slow.
    chars = [len(x) for x in sents]
    rate = (tail - lead) / sum(chars)
    n, m = len(sents), len(gaps)
    pts = [(lead, lead)] + gaps + [(tail, tail)]  # (speech end, next speech start)

    def cost(i, a, b):  # sentence i spoken from pts[a] start to pts[b] end
        dur = pts[b][0] - pts[a][1]
        if dur <= 0.2:
            return 1e9
        return 0.15 * chars[i] * math.log(dur / (chars[i] * rate)) ** 2 - 4.0 * (pts[b][1] - pts[b][0])

    INF = float("inf")
    best = [[INF] * (m + 2) for _ in range(n + 1)]
    back = [[None] * (m + 2) for _ in range(n + 1)]
    best[0][0] = 0.0
    for i in range(n):
        for a in range(m + 1):
            if best[i][a] == INF:
                continue
            targets = [m + 1] if i == n - 1 else range(a + 1, m + 1)
            for b in targets:
                c = best[i][a] + cost(i, a, b)
                if c < best[i + 1][b]:
                    best[i + 1][b], back[i + 1][b] = c, a
    if best[n][m + 1] == INF:
        sys.exit("not enough pauses to place every sentence; lower silencedetect d=")
    idx, b = [m + 1], m + 1
    for i in range(n, 0, -1):
        b = back[i][b]
        idx.append(b)
    idx.reverse()
    bounds = [(pts[idx[i]][1], pts[idx[i + 1]][0]) for i in range(n)]
    return bounds, total


def chunks(sentence, max_chars=20):
    """Caption lines short enough to fit the frame at the caption font size."""
    out, cur = [], ""
    for w in sentence.split():
        if cur and len(cur) + 1 + len(w) > max_chars:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + [cur]


def assemble(d):
    cfg = json.load(open(f"{d}/scenes.json"))
    vo = f"{d}/vo.mp3"
    sents = [[x.strip() for x in re.findall(r"[^.!?]+[.!?]", s["narration"])] for s in cfg["scenes"]]
    flat = [x for ss in sents for x in ss]
    bounds, total = sentence_times(vo, flat)
    for (a, b), s in zip(bounds, flat):
        print(f"{a:6.2f}-{b:6.2f}  {s}")
    tmp = f"{d}/build"
    os.makedirs(tmp, exist_ok=True)

    # Scene windows: from its first sentence start to the next scene's first sentence start.
    k, win = 0, []
    for ss in sents:
        win.append(bounds[k][0])
        k += len(ss)
    win[0] = 0.0
    win.append(total + 0.8)

    parts = []
    for i in range(len(sents)):
        need = win[i + 1] - win[i]
        clip = f"{d}/clips/{i:02d}.mp4"
        have = probe_dur(clip)
        speed = min(1.0, have / need) if need > have else 1.0  # slow slightly if short
        vf = (f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"fps={FPS},tpad=stop_mode=clone:stop_duration=2")
        af = f"atempo={max(0.5, speed)},apad"
        out = f"{tmp}/p{i:02d}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-vf", vf, "-af", af, "-t", f"{need:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "2", out])
        parts.append(out)
    with open(f"{tmp}/list.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt", "-c", "copy",
         f"{tmp}/joined.mp4"])

    # Captions: short chunks timed across each sentence by character count.
    draws, n = [], 0
    for (s0, s1), sent in zip(bounds, flat):
        cs = chunks(sent)
        span, tot = s1 - s0, sum(len(c) for c in cs)
        t = s0
        for c in cs:
            dt = span * len(c) / tot
            tf = f"{tmp}/cap{n:03d}.txt"
            open(tf, "w").write(c)
            draws.append(f"drawtext=fontfile={FONT}:textfile={tf}:fontsize=74:fontcolor=white:"
                         f"borderw=7:bordercolor=black@0.85:x=(w-text_w)/2:y=h*0.70:"
                         f"enable='between(t,{t:.2f},{t + dt:.2f})'")
            t += dt
            n += 1
    vf = ",".join(draws)
    slug = cfg["slug"]
    hq = f"{d}/{slug}-hq.mp4"
    # Clip sound effects ducked under the voice.
    fc = (f"[0:v]{vf}[v];[0:a]volume=0.22[sfx];[1:a]volume=1.0,apad[vo];"
          f"[sfx][vo]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{tmp}/joined.mp4", "-i", vo, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", hq])
    run(["ffmpeg", "-v", "error", "-y", "-i", hq, "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "26",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", f"{d}/{slug}-preview.mp4"])
    print("wrote", hq, f"{probe_dur(hq):.1f}s")


if __name__ == "__main__":
    {"gen": gen, "assemble": assemble}[sys.argv[1]](sys.argv[2].rstrip("/"))
