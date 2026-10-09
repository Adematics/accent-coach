# Accent Coach

**Practise a British or American English accent by speaking — free, on your own computer.**

You say a sentence out loud. Accent Coach listens, shows which words and sounds were off, tells you
how to fix them, and plays how a native speaker would say it. It remembers the words you struggle
with and keeps bringing them back until you get them right.

It is a free alternative to paid apps like BoldVoice and Fluently. It is tuned for Nigerian English
speakers, but works for anyone.

---

## What you can do

| Mode | What happens |
|------|--------------|
| **Coach me** | The coach picks a sound you need (for example the "th" in *think*), gives you a tip and a sentence, and plays it. You say it back and see what to fix. |
| **Free speaking** | Say anything you like. It coaches you on your own words. |
| **Cold-call role-play** | Practise a phone call. A receptionist in London or New York talks back to you out loud, and you get one pronunciation tip per turn. |

After every try you see:

- 🟢 🔴 **each word in green or red**
- **up to 3 fixes**, each with a "say it like *WAW-tuh*" spelling you can read without phonetics
- **two pitch lines**, yours and the native speaker's, so you can see where your voice should go up and down
- **▶ You** and **▶ Native** buttons to compare the two recordings
- **lesson videos** on that sound or word

It also keeps your **progress**: tries today, your average score, your day streak, and a list of
**words to work on**. Say a word right 3 times in a row and it moves to *Mastered*.

---

## Before you start

You need:

- **A computer with Linux or macOS.** It has been tested on Ubuntu Linux; macOS should work the same way. (Windows: see [Windows](#windows) at the bottom.)
- **About 3 GB of free disk space** and **4 GB of free memory**. No graphics card needed.
- **A microphone** (the laptop's built-in one is fine; a headset is better).
- **An OpenAI account with a little credit** (a few dollars lasts a long time; a practice session costs pennies).
- *(Optional)* **A free YouTube key**, to play lesson videos inside the app.

---

## Setup (about 15 minutes, once)

### Step 1 — Install Python and ffmpeg

Open the **Terminal** app and paste the line for your computer.

**Ubuntu / Linux Mint / Debian:**

```bash
sudo apt update && sudo apt install -y python3 python3-venv ffmpeg git
```

**macOS:** first install [Homebrew](https://brew.sh) if you don't have it (paste the command from its
home page), then:

```bash
brew install python@3.12 ffmpeg git
```

> Accent Coach needs **Python 3.10, 3.11 or 3.12**. Check with `python3 --version`.
> If yours is 3.13 or newer, install 3.12 as shown above (macOS) or with `sudo apt install python3.12 python3.12-venv` (Linux).

### Step 2 — Download Accent Coach

```bash
git clone https://github.com/Adematics/accent-coach.git
cd accent-coach
```

### Step 3 — Install it

```bash
./setup.sh
```

This takes a few minutes. When it finishes you will see **"Done. Start the app with: ./start.sh"**.

### Step 4 — Add your OpenAI key

1. Go to <https://platform.openai.com/api-keys> and sign in.
2. Click **Create new secret key**, give it a name like `accent-coach`, and **copy** the key (it starts with `sk-`).
3. Make sure your account has credit: <https://platform.openai.com/settings/organization/billing>.
4. Open the settings file:

   ```bash
   nano .env
   ```

5. Paste your key after `OPENAI_API_KEY=` so the line looks like:

   ```
   OPENAI_API_KEY=sk-abc123...
   ```

6. Save and close: press **Ctrl+O**, **Enter**, then **Ctrl+X**.

> 🔒 Keep your keys secret. Put them only in the `.env` file — never in a chat, an email or a screenshot.
> The `.env` file is never uploaded to GitHub.

### Step 5 (optional) — Add a YouTube key for videos in the app

Without this, the video buttons simply open YouTube in a new tab. With it, videos play inside the app.

1. Go to <https://console.cloud.google.com> and sign in with any Google account.
2. At the top, pick a project (or click **New project**, name it `accent-coach`, and select it).
3. Open <https://console.cloud.google.com/apis/library/youtube.googleapis.com> and click **Enable**.
4. In the left menu go to **APIs & Services → Credentials → + Create credentials → API key**.
   If asked, choose **YouTube Data API v3** and **Public data**.
5. Copy the key (it starts with `AIza`).
6. Recommended: click the key, choose **Restrict key → YouTube Data API v3**, and **Save**.
7. Run `nano .env` again and paste it after `YOUTUBE_API_KEY=`. Save and close as before.

It is free and needs no card.

---

## Using it

### Start

```bash
cd accent-coach
./start.sh
```

Your browser opens **http://127.0.0.1:8765**. If it doesn't, open that address yourself.

- **The very first start downloads the voice and listening models (about 1.5 GB).** That can take
  several minutes. After that, each start takes about 30 seconds to warm up.
- When the browser asks to use your **microphone**, click **Allow**.

### Practise

1. Pick **British** or **American** at the top, and a **female** or **male** voice.
2. Read the tip and the sentence. Press **▶ Listen** (or **▶ Slow**).
3. **Hold the space bar** (or the big blue button), say the sentence, then **let go**.
   While it listens, the button turns red with a pulsing dot and a timer, and a **green bar moves with
   your voice**. If the bar doesn't move, the microphone isn't hearing you.
4. Wait a few seconds for your result. Read the fixes, press **▶ Native** to hear it again, and try once more.
5. Press **Next drill →** for a new sentence.

Scroll down to see **Your progress** and **Words to work on**. Press **▶ Practise** next to a word to
drill just that word.

### Stop

Go back to the Terminal window and press **Ctrl+C**.

### Tips for better results

- Speak at a normal volume, about 20–30 cm from the microphone, in a quiet room.
- Hold the button for the whole sentence; don't let go too early.
- Treat the score as a guide, not an exam. Focus on the red words and the fixes.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `./setup.sh: Permission denied` | Run `chmod +x setup.sh start.sh`, then try again. |
| "Python 3.10, 3.11 or 3.12 is needed" | Install Python 3.12 (see Step 1). |
| "ffmpeg is missing" | Install it (see Step 1). |
| "Put OPENAI_API_KEY in … .env" | Do Step 4, then stop the app (Ctrl+C) and run `./start.sh` again. |
| An error mentioning *quota*, *billing* or *401* | Your OpenAI key is wrong or the account has no credit. Check Step 4. |
| "Microphone blocked" | Click the lock or mic icon in the browser's address bar, allow the microphone, and reload the page. |
| "Too short" / "I didn't catch anything" | Hold the button the whole time you speak, and speak a bit louder. |
| The first try is very slow | Normal: the models are still loading. Wait about 30 seconds after starting. |
| No videos inside the app | Normal without a YouTube key (Step 5). The buttons still open YouTube. |
| "address already in use" | The app is already running. Use the open browser tab, or stop the other one first. |

To start completely fresh, delete `progress.json` (your scores and word list).

---

## How it works

Most of the work happens on your own computer, using free, open-source tools:

| Job | Tool | Where it runs | Cost |
|-----|------|---------------|------|
| The native British / American voice | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | your computer | free |
| Hearing which sounds *you* made | [wav2vec2 phoneme model](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) | your computer | free |
| Knowing which sounds you *should* make | espeak-ng | your computer | free |
| Drawing the pitch lines | librosa | your computer | free |
| Writing drills and advice, writing down what you said, the role-play receptionist | OpenAI (`gpt-4.1-mini`, `whisper-1`) | online | pennies a session |
| Lesson videos | YouTube | online | free |

**Why not just use speech-to-text?** Speech-to-text guesses what you *meant*: if you say "tink", it
writes "think". The sound model listens to what you *actually* said, so it catches the mistake.

**A detail for the curious:** the sound model was trained mostly on American speech, so it "hears"
an American R even in a British voice. To keep things fair, you are compared with how the model
hears the native voice saying the same sentence, not with a dictionary. The bias is the same on
both sides and cancels out.

**Speed:** on an ordinary 4-core laptop, a result appears about 4–6 seconds after you stop speaking.

**Your data:** your recordings are sent to OpenAI to be written down and are not saved by this app.
Your progress stays in `progress.json` on your computer.

---

## Limits

- The sound checker is not perfect. Now and then it flags a word that sounded fine or misses a
  small mistake. A word only goes on your list when the coach actually corrects it.
- Rhythm and stress are shown on the pitch lines but not scored.
- One accent for each: standard southern British (RP) and General American. No regional accents.
- Video suggestions are YouTube's top results; pick between the three if the first isn't helpful.

---

## Settings (`.env`)

| Setting | What it does |
|---------|--------------|
| `OPENAI_API_KEY` | Required. Your OpenAI key. |
| `YOUTUBE_API_KEY` | Optional. Plays lesson videos inside the app. |
| `OPENAI_MODEL` | Optional. The model that writes drills and advice (default `gpt-4.1-mini`). |
| `OPENAI_TRANSCRIBE_MODEL` | Optional. The model that writes down what you said (default `whisper-1`). |

---

## Files

| File | What it is |
|------|------------|
| `setup.sh` | One-time install |
| `start.sh` | Starts the app and opens the browser |
| `coach.py` | The app itself: voice, sound checking, coaching, videos, progress |
| `index.html` | The page you see in the browser |
| `requirements.txt` | The open-source libraries it uses |
| `.env.example` | Template for your settings |
| `.env`, `progress.json`, `videos.json` | Your keys and your data — stay on your computer, never uploaded |

---

## Windows

On Windows the easiest route is
[WSL](https://learn.microsoft.com/windows/wsl/install) (Ubuntu inside Windows): install it, open
**Ubuntu** from the Start menu, and follow the Linux steps above. Then open
http://127.0.0.1:8765 in your normal Windows browser.
