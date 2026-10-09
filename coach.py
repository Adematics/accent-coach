"""Accent Coach: speak, compare your sounds with a British or American model, get coached.

Open-source parts run locally: Kokoro (voice), wav2vec2 phoneme model (what you said),
espeak-ng via phonemizer (what you should have said), librosa (pitch).
OpenAI writes the lessons, transcribes, and turns the comparison into advice.
"""
import datetime
import difflib
import io
import json
import os
import subprocess
import tempfile
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from openai import OpenAI

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
PROGRESS = HERE / "progress.json"
VIDEO_CACHE = HERE / "videos.json"  # YouTube searches are saved so the free daily allowance lasts

ACCENTS = {
    "british": {"lang": "b", "espeak": "en-gb", "voices": {"female": "bf_emma", "male": "bm_george"},
                "name": "British (Received Pronunciation)"},
    "american": {"lang": "a", "espeak": "en-us", "voices": {"female": "af_heart", "male": "am_michael"},
                 "name": "General American"},
}

SOUNDS = [
    "TH as in think (not t)", "TH as in this (not d)", "R after vowels", "long EE vs short I (sheep/ship)",
    "long OO vs short U (fool/full)", "A in cat vs U in cut", "ER as in bird/work", "weak vowel schwa (a-BOUT)",
    "word stress", "sentence rhythm (stress-timed)", "final consonant clusters (asked, months)",
    "L at the end of words (feel, call)", "T between vowels (water, better)",
]

LEARNER = ("The learner is a Nigerian English speaker. Typical gaps: TH said as t/d, every syllable given "
           "equal weight (syllable-timed rhythm), full vowels where English uses schwa, long/short vowel "
           "pairs merged, the bird/work vowel said as a or e, R pronounced after vowels.")

app = FastAPI()


@app.exception_handler(Exception)
async def friendly_error(request, exc):
    msg = str(exc) if isinstance(exc, RuntimeError) else f"{type(exc).__name__}: {exc}"
    return JSONResponse({"error": msg[:300]}, status_code=500)


_lock = threading.Lock()
_infer = threading.Lock()  # one model run at a time; parallel runs on 4 cores only slow each other
_models = {}
_pool = ThreadPoolExecutor(4)
_native = OrderedDict()  # (text, accent, gender) -> future of native voice, its sounds and its pitch


def client():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Put OPENAI_API_KEY in ~/accent-coach/.env and restart.")
    return OpenAI()


# ---------- local models (loaded once, on first use) ----------

def tts_pipeline(lang):
    with _lock:
        key = "tts_" + lang
        if key not in _models:
            from kokoro import KPipeline
            _models[key] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
        return _models[key]


def phoneme_model():
    with _lock:
        if "ph" not in _models:
            from transformers import AutoModelForCTC, AutoProcessor
            name = "facebook/wav2vec2-lv-60-espeak-cv-ft"
            _models["ph"] = (AutoProcessor.from_pretrained(name), AutoModelForCTC.from_pretrained(name).eval())
        return _models["ph"]


def espeak_backend(code):
    with _lock:
        key = "es_" + code
        if key not in _models:
            import espeakng_loader
            from phonemizer.backend import EspeakBackend
            from phonemizer.backend.espeak.wrapper import EspeakWrapper
            EspeakWrapper.set_library(espeakng_loader.get_library_path())
            EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
            _models[key] = EspeakBackend(code, preserve_punctuation=False, with_stress=False)
        return _models[key]


# ---------- audio helpers ----------

def speak(text, accent, gender="female", speed=1.0):
    a = ACCENTS[accent]
    pipe = tts_pipeline(a["lang"])
    with _infer:
        chunks = [audio for _, _, audio in pipe(text, voice=a["voices"][gender], speed=speed)]
    return np.concatenate([np.asarray(c) for c in chunks]) if chunks else np.zeros(2400), 24000


def wav_bytes(audio, sr):
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


def to_16k(raw: bytes):
    with tempfile.NamedTemporaryFile(suffix=".webm") as src:
        src.write(raw)
        src.flush()
        out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src.name, "-ac", "1", "-ar", "16000",
                              "-f", "wav", "-"], capture_output=True, check=True).stdout
    audio, sr = sf.read(io.BytesIO(out), dtype="float32")
    return audio, sr


def resample16(audio, sr):
    import librosa
    return librosa.resample(np.asarray(audio, dtype=np.float32), orig_sr=sr, target_sr=16000)


def heard_phones(audio16):
    import torch
    torch.set_num_threads(os.cpu_count() or 4)
    proc, model = phoneme_model()
    inputs = proc(audio16, sampling_rate=16000, return_tensors="pt")
    with _infer, torch.no_grad():
        ids = model(inputs.input_values).logits.argmax(-1)
    return proc.batch_decode(ids)[0].split()


def norm(p):
    return p.replace("ˈ", "").replace("ˌ", "").replace("͡", "").replace("ᵻ", "ɪ").replace("ɐ", "ə")


def split_phones(ipa):
    """Split an espeak IPA word into phones (keep length marks and diphthongs that wav2vec2 uses)."""
    out, i = [], 0
    multi = ["aɪ", "eɪ", "ɔɪ", "aʊ", "oʊ", "əʊ", "ɪə", "eə", "ʊə", "tʃ", "dʒ", "ɜː", "iː", "uː", "ɑː", "ɔː"]
    ipa = norm(ipa)
    while i < len(ipa):
        two = ipa[i:i + 2]
        if two in multi:
            out.append(two); i += 2
        elif i + 1 < len(ipa) and ipa[i + 1] == "ː":
            out.append(ipa[i:i + 2]); i += 2
        else:
            out.append(ipa[i]); i += 1
    return [p for p in out if p.strip()]


def expected_phones(text, accent):
    words = [w.strip(".,!?;:\"()") for w in text.split()]
    words = [w for w in words if w]
    ipas = espeak_backend(ACCENTS[accent]["espeak"]).phonemize(words, strip=True)
    return [(w, ipa, split_phones(ipa)) for w, ipa in zip(words, ipas)]


def calibrate(expected, native_heard):
    """Replace each word's dictionary phones with what the recogniser hears from the native voice.

    The recogniser leans American (it hears r and flapped t even in the British voice), so the
    learner is compared with the native voice as the recogniser hears it: the same bias on both sides.
    """
    words, _ = compare(expected, native_heard)
    out = []
    for (w, ipa, phones), r in zip(expected, words):
        got = r["heard_list"]
        out.append((w, ipa, got if got else phones))
    return out


def compare(expected, heard):
    """Align expected phones to heard phones; return per-word results."""
    flat, owner = [], []
    for wi, (_, _, phones) in enumerate(expected):
        flat += phones
        owner += [wi] * len(phones)
    heard = [norm(p) for p in heard]
    words = [{"word": w, "expected": ipa, "heard": [], "issues": []} for w, ipa, _ in expected]
    sm = difflib.SequenceMatcher(a=flat, b=heard, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                words[owner[i1 + k]]["heard"].append(heard[j1 + k])
            continue
        if i1 == i2:  # extra sounds: attach to the neighbouring word
            wi = owner[i1 - 1] if i1 > 0 else 0
            if words:
                words[wi]["heard"] += heard[j1:j2]
                words[wi]["issues"].append({"expected": "", "said": "".join(heard[j1:j2])})
            continue
        wi = owner[i1]
        words[wi]["heard"] += heard[j1:j2]
        words[wi]["issues"].append({"expected": "".join(flat[i1:i2]), "said": "".join(heard[j1:j2]) or "(nothing)"})
    for w in words:
        w["heard_list"] = w["heard"]
        w["heard"] = "".join(w["heard"])
        w["ok"] = not w["issues"]
    total = len(flat) or 1
    matched = sum(b.size for b in sm.get_matching_blocks())
    return words, round(100 * matched / total)


def pitch(audio, sr, points=120):
    import librosa
    audio = audio.astype(np.float32)
    f0 = librosa.yin(audio, fmin=65, fmax=420, sr=sr, frame_length=1024, hop_length=256)
    rms = librosa.feature.rms(y=audio, frame_length=1024, hop_length=256)[0][:len(f0)]
    f0 = f0[:len(rms)]
    loud = rms > 0.25 * np.median(rms) if rms.size else rms
    f0 = np.where(loud, f0, 0)  # drop silence and breath
    voiced = np.nonzero(f0)[0]
    if len(voiced) < 2:
        return []
    f0 = f0[voiced[0]:voiced[-1] + 1]
    idx = np.linspace(0, len(f0) - 1, points).astype(int)
    vals = f0[idx]
    med = np.median(vals[vals > 0]) if np.any(vals > 0) else 1
    return [round(float(12 * np.log2(v / med)), 2) if v > 0 else None for v in vals]  # semitones vs median


def _build_native(text, accent, gender):
    audio, sr = speak(text, accent, gender)
    expected = calibrate(expected_phones(text, accent), heard_phones(resample16(audio, sr)))
    return {"audio": audio, "sr": sr, "expected": expected, "pitch": pitch(audio, sr), "wav": wav_bytes(audio, sr)}


def native(text, accent, gender, speed=1.0):
    """Start (or reuse) the native version of a sentence; returns a future."""
    key = (text.strip(), accent, gender, speed)
    with _lock:
        if key not in _native:
            if speed == 1.0:
                _native[key] = _pool.submit(_build_native, key[0], accent, gender)
            else:  # slow version is only listened to, never compared
                _native[key] = _pool.submit(lambda: {"wav": wav_bytes(*speak(key[0], accent, gender, speed))})
            while len(_native) > 30:
                _native.popitem(last=False)
        return _native[key]


def warm_up():
    try:
        for acc in ACCENTS:
            native("Hello there.", acc, "female").result()
    except Exception as e:  # the app still works; first request will just be slower
        print("warm-up failed:", e)


@app.on_event("startup")
def _start_warm_up():
    threading.Thread(target=warm_up, daemon=True).start()


# ---------- progress ----------

MASTERED_AFTER = 3  # right this many times in a row


def load_progress():
    try:
        p = json.loads(PROGRESS.read_text())
    except Exception:
        p = {}
    p.setdefault("sounds", {})
    p.setdefault("sessions", 0)
    p.setdefault("words", {"british": {}, "american": {}})  # accent -> word -> stats
    p.setdefault("history", [])  # one entry per attempt: day, score, mode
    return p


def clean_word(w):
    return w.strip(".,!?;:\"()“”‘’").lower().replace("’", "'")


def record(focus, score, accent, target="", missed=()):
    """Save one attempt: sound average, daily history and per-word results.

    A word counts as missed only when the coach chose to fix it (the raw sound flags are too noisy);
    a word already on the list counts as right when it was said and not fixed.
    """
    with _lock:
        p = load_progress()
        s = p["sounds"].setdefault(focus, {"tries": 0, "avg": 0})
        s["avg"] = round((s["avg"] * s["tries"] + score) / (s["tries"] + 1), 1)
        s["tries"] += 1
        p["sessions"] += 1
        today = datetime.date.today().isoformat()
        p["history"].append({"day": today, "score": score, "mode": focus})
        p["history"] = p["history"][-2000:]
        words = p["words"].setdefault(accent, {})
        missed = {clean_word(m["word"]): m for m in missed if m.get("word")}
        for w, fix in missed.items():
            e = words.setdefault(w, {"tries": 0, "misses": 0, "streak": 0, "mastered": False})
            e.update(tries=e["tries"] + 1, misses=e["misses"] + 1, streak=0, mastered=False, last=today,
                     problem=fix.get("problem", ""), how=fix.get("how", ""), say_it_like=fix.get("say_it_like", ""))
        for w in {clean_word(x) for x in target.split()} - set(missed):
            e = words.get(w)
            if e:
                e.update(tries=e["tries"] + 1, streak=e["streak"] + 1, last=today)
                e["mastered"] = e["streak"] >= MASTERED_AFTER
        PROGRESS.write_text(json.dumps(p, indent=2))


def weak_words(accent, n=8):
    words = load_progress()["words"].get(accent, {})
    todo = [(w, e) for w, e in words.items() if not e["mastered"]]
    return [w for w, _ in sorted(todo, key=lambda x: (-x[1]["misses"] + x[1]["streak"], x[0]))][:n]


def ask_json(system, user):
    r = client().chat.completions.create(model=MODEL, response_format={"type": "json_object"},
                                         messages=[{"role": "system", "content": system},
                                                   {"role": "user", "content": user}])
    return json.loads(r.choices[0].message.content)


def transcribe(raw):
    f = ("speech.webm", raw, "audio/webm")
    return client().audio.transcriptions.create(model=TRANSCRIBE_MODEL, file=f, language="en").text.strip()


# ---------- routes ----------

@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


@app.get("/api/videos")
def videos(q: str):
    """Top embeddable YouTube lessons for a search; empty list when no YOUTUBE_API_KEY is set."""
    import urllib.parse
    import urllib.request
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return {"videos": [], "enabled": False}
    q = q.strip().lower()
    try:
        cache = json.loads(VIDEO_CACHE.read_text())
    except Exception:
        cache = {}
    if q not in cache:
        url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode({
            "part": "snippet", "q": q, "type": "video", "videoEmbeddable": "true", "maxResults": 3,
            "relevanceLanguage": "en", "safeSearch": "strict", "key": key})
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                items = json.load(r).get("items", [])
        except Exception as e:
            return JSONResponse({"error": f"YouTube search failed: {e}"}, 502)
        from html import unescape
        cache[q] = [{"id": i["id"]["videoId"], "title": unescape(i["snippet"]["title"]),
                     "channel": unescape(i["snippet"]["channelTitle"])} for i in items]
        VIDEO_CACHE.write_text(json.dumps(cache, indent=1))
    return {"videos": cache[q], "enabled": True}


@app.get("/api/progress")
def progress():
    return load_progress()


@app.post("/api/word")
def word_status(accent: str = Form(...), word: str = Form(...), action: str = Form(...)):
    """Mark a word mastered by hand, or remove it from the list."""
    with _lock:
        p = load_progress()
        words = p["words"].setdefault(accent, {})
        w = clean_word(word)
        if action == "remove":
            words.pop(w, None)
        elif action == "mastered" and w in words:
            words[w]["mastered"] = True
        PROGRESS.write_text(json.dumps(p, indent=2))
    return {"ok": True}


@app.post("/api/lesson")
def lesson(accent: str = Form(...), focus: str = Form(""), gender: str = Form("female")):
    p = load_progress()["sounds"]
    weak = weak_words(accent)
    system = ("You are a friendly accent coach. " + LEARNER + " Reply in JSON with keys: focus (one item from the "
              "list), tip (one or two short sentences: what to do with tongue/lips/rhythm, with an example word), "
              "sentence (8-14 everyday words, natural, packed with the focus sound; business or daily-life "
              "topics), words (2-4 key words from the sentence that carry the sound).")
    user = (f"Target accent: {ACCENTS[accent]['name']}.\nSounds list: {SOUNDS}\n"
            f"Learner's history (avg score per sound, lower = weaker): {json.dumps(p)}\n"
            + (f"Words the learner keeps getting wrong: {weak}. Where it fits naturally, put one or two of "
               "them in the sentence.\n" if weak else "")
            + (f"Use this focus: {focus}" if focus else
               "Pick the weakest sound, or one not tried yet. Avoid repeating the same sentence as before."))
    out = ask_json(system, user)
    native(out.get("sentence", ""), accent, gender)  # built while they read and listen
    return out


@app.post("/api/tts")
def tts(text: str = Form(...), accent: str = Form(...), gender: str = Form("female"), speed: float = Form(1.0)):
    return Response(native(text, accent, gender, speed).result()["wav"], media_type="audio/wav")


@app.post("/api/attempt")
async def attempt(audio: UploadFile = File(...), accent: str = Form(...), target: str = Form(""),
                  focus: str = Form(""), gender: str = Form("female")):
    raw = await audio.read()
    a16, _ = to_16k(raw)
    if target.strip():
        native(target, accent, gender)  # usually already built while they listened
    you = _pool.submit(lambda: (heard_phones(a16), pitch(a16, 16000)))  # runs while OpenAI transcribes
    said = transcribe(raw)
    target = target.strip() or said  # free-speaking mode: coach what you said
    if not target:
        return JSONResponse({"error": "I didn't catch anything. Try again, a bit closer to the mic."}, 400)
    nat = native(target, accent, gender).result()
    heard, pitch_you = you.result()
    words, score = compare(nat["expected"], heard)
    system = ("You are a warm, precise accent coach. " + LEARNER + " You get the target sentence, what speech "
              "recognition wrote down, and a phoneme comparison (IPA) per word between the target accent and what "
              "the learner said. The phoneme recogniser is noisy: ignore tiny vowel-quality differences and "
              "anything that would not be noticed by a listener. Reply JSON: summary (one encouraging sentence), "
              "fixes (list of at most 3 objects: word, problem in plain words, how (mouth/tongue/stress "
              "instruction), say_it_like (respelling a non-linguist can read, e.g. 'WAW-tuh')), "
              "next (what to do on the next try, one sentence). No IPA in your answer.")
    user = json.dumps({"accent": ACCENTS[accent]["name"], "focus": focus, "target": target,
                       "recognised_text": said, "score": score,
                       "words": [{k: w[k] for k in ("word", "expected", "heard", "issues")} for w in words]})
    feedback = ask_json(system, user)
    record(focus or "free speaking", score, accent, target, feedback.get("fixes") or [])
    for w in words:
        w.pop("heard_list", None)
    import base64
    return {"said": said, "target": target, "score": score, "words": words, "feedback": feedback,
            "model_wav": base64.b64encode(nat["wav"]).decode(),
            "pitch_you": pitch_you, "pitch_model": nat["pitch"]}


@app.post("/api/roleplay")
async def roleplay(audio: UploadFile = File(...), accent: str = Form(...), history: str = Form("[]"),
                   gender: str = Form("female")):
    raw = await audio.read()
    a16, _ = to_16k(raw)
    you = _pool.submit(heard_phones, a16)  # runs while OpenAI transcribes
    said = transcribe(raw)
    if not said:
        return JSONResponse({"error": "I didn't catch anything. Try again."}, 400)
    words, score = compare(native(said, accent, gender).result()["expected"], you.result())
    weak = [{"word": w["word"], "issues": w["issues"]} for w in words if not w["ok"]][:6]
    hist = json.loads(history)
    system = ("You are role-playing the receptionist or owner of a busy aesthetics clinic in "
              + ("London" if accent == "british" else "New York") + ", answering a cold call from someone "
              "offering a booking website and AI front desk. Be realistic: a bit busy, ask natural questions, "
              "raise mild objections. Keep replies to 1-3 short spoken sentences. You are also an accent coach: "
              + LEARNER + " Given noisy phoneme issues for the caller's last line, pick at most ONE word worth "
              "fixing (ignore trivia; pick none if fine). Reply JSON: reply (your spoken line), tip (null or "
              "{word, how, say_it_like}).")
    msgs = [{"role": "system", "content": system}] + hist + [
        {"role": "user", "content": json.dumps({"caller_said": said, "phoneme_issues": weak})}]
    r = client().chat.completions.create(model=MODEL, response_format={"type": "json_object"}, messages=msgs)
    out = json.loads(r.choices[0].message.content)
    tip = out.get("tip")
    record("role-play", score, accent, said, [tip] if isinstance(tip, dict) else [])
    return {"said": said, "score": score, "reply": out.get("reply", ""), "tip": out.get("tip")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
