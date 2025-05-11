# Gen AI WhatsApp Podcast Automator

A CLI tool and Python library to transform threaded WhatsApp Gen AI group transcripts into weekly podcast scripts and audio. Designed for expert developers, this repo:

- **Parses** JSON exports of WhatsApp messages into threaded, weekly files.
- **Generates** a polished two-host dialogue script via OpenAI GPT-4.1-mini.
- **Produces** per-speaker TTS segments (OpenAI’s gpt-4o-mini-tts) and concatenates into `podcast.mp3`.

## Setup

You need:

- A [scraped WhatsApp JSON export](https://tools.s-anand.net/whatsappscraper/) of the Gen AI Group chat as [`gen-ai-messages.json`](gen-ai-messages.json):
- [`uv`](https://docs.astral.sh/uv/)
- Environment variable `OPENAI_API_KEY` with a valid OpenAI API key.
- `ffmpeg` installed and in `PATH` for audio concatenation.

```bash
git clone https://github.com/sanand0/generative-ai-group.git
cd generative-ai-group
OPENAI_API_KEY="sk-..." uv run podcast.py
```

Optionally, modify the voice style and podcast script prompts in [`config.toml`](config.toml)

This will:

1. Read and filter messages.
2. Group them by ISO-week (Monday start).
3. For each week, it creates:
   - `{week}/messages.txt` (threaded transcript).
   - `{week}/podcast.md` (dialogue script).
   - `{week}/{line}.opus` files which are concatenated into...
   - `{week}/podcast.mp3`.

How It Works:

1. `load_messages()` filters out items with null `time`, `text`, or missing `author`.
2. `group_by_week()` buckets by Monday of each ISO week.
3. `build_threads()` indexes by `messageId`, collects replies via `quoteMessageId`, sorts roots chronologically.
4. `render_message()` writes indented “– Author: Text \[reactions]” lines.
5. `get_podcast_script()` POSTs system + user prompts to OpenAI API, calculates cost.
6. `generate_podcast_audio()` splits the script by speaker, sends TTS requests, writes `.opus`, and FFmpeg-concats into MP3.

## License

[MIT License](LICENSE)
