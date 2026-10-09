# Accent Coach

A free, voice-first trainer for a **British (RP)** or **General American** accent, built as an
open-source alternative to BoldVoice and Fluently. You speak, it hears which sounds you made,
compares them with a native voice, and coaches you on the words that need work.

It is tuned for a Nigerian English speaker: TH said as t/d, even syllable rhythm, full vowels
where English uses a weak "uh", long/short vowel pairs (ship/sheep), the bird/work vowel and R after vowels.

## What it does

- **Coach me** — the coach picks the sound you are weakest on, gives a one-line tip and a practice
  sentence, and plays it in the accent you chose (normal or slow). You say it back and get:
  - each word marked green or red,
  - up to three fixes with a "say it like *WAW-tuh*" spelling,
  - your pitch line against the native voice,
  - lesson videos on that sound, playing in the page.
- **Free speaking** — say anything; it coaches you on your own sentence.
- **Cold-call role-play** — a London or New York clinic receptionist answers you aloud and flags one word per turn.
- **Weak spots** — your average per sound is kept in `progress.json` and drives the next drill.

## How it works

| Part | Tool | Runs |
|------|------|------|
| Native voice (British and American) | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | on your laptop |
| Which sounds you actually made | [wav2vec2 phoneme model](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) | on your laptop |
| Which sounds you should have made | espeak-ng (via `phonemizer` and `espeakng-loader`) | on your laptop |
| Pitch line | librosa | on your laptop |
| Drills, coaching advice, role-play, transcript | OpenAI (`gpt-4.1-mini`, `whisper-1`) | API, pennies a session |
| Lesson videos | YouTube Data API (optional) | API, free allowance |

The phoneme model leans American: it hears an R and a flapped T even in the British voice. So you are
not scored against a dictionary; you are scored against **what the model hears from the native voice
saying the same sentence**. The bias is the same on both sides and cancels out.

The transcript alone would miss most mistakes: speech recognition quietly writes "think" when you
said "tink". The phoneme model is what catches them.

## Setup

Needs Python 3.12 and `ffmpeg`. No GPU needed.

```bash
python3 -m venv .venv
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in the keys
```

`.env`:

```
OPENAI_API_KEY=sk-...
YOUTUBE_API_KEY=AIza...        # optional: plays lesson videos in the page
OPENAI_MODEL=gpt-4.1-mini      # optional
OPENAI_TRANSCRIBE_MODEL=whisper-1
```

Without `YOUTUBE_API_KEY`, the video buttons open YouGlish and YouTube in a new tab instead.
To get one: Google Cloud console → enable **YouTube Data API v3** → Credentials → API key
(public data), restricted to that API.

## Run

```bash
./start.sh            # opens http://127.0.0.1:8765
pkill -f coach.py     # stop
```

The first run downloads about 1.5 GB of models. After start-up the models warm up in the
background for about 30 seconds. Allow the microphone, then hold the space bar (or the button),
speak and let go.

## Speed

On a 4-core laptop CPU, a check takes about 4–6 seconds after you stop speaking: about 2 seconds
of local sound checking, the rest is OpenAI. The native voice for a drill is built while you are
still reading and listening, and your sounds are checked while OpenAI transcribes. Free speaking
and role-play take a few seconds longer, because the sentence is only known once you have said it.

## Limits

- The phoneme model is noisy: it sometimes flags a vowel that sounded fine and occasionally misses
  a mistake. The coach is told to ignore small differences; treat the percentage as a guide.
- Rhythm and stress are only shown through the pitch line, not scored.
- One accent per target: southern British (RP) and General American, no regional accents.
- Video suggestions are YouTube's top search results; there are three to choose from.

## Files

- `coach.py` — the server: models, sound comparison, OpenAI calls, video search
- `index.html` — the page
- `start.sh` — starts the server and opens the browser
- `progress.json`, `videos.json`, `.env` — your own data and keys; not committed
