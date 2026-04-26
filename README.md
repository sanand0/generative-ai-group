# Gen AI WhatsApp Podcast Automator

A CLI tool and Python library to transform threaded WhatsApp Gen AI group transcripts into
[a weekly podcast](https://github.com/sanand0/generative-ai-group/releases/download/main/podcast.xml) by

- **Merging and splitting** WhatsApp scraper JSON exports into weekly `messages/YYYY-MM-DD.json` shards.
- **Parsing** weekly WhatsApp messages into threaded transcript files.
- **Generating** a polished two-host dialogue script via OpenAI `gpt-5.4-mini`.
- **Narrating** the script line by line via Gemini `gemini-3.1-flash-tts-preview`, then concatenating the clips into `podcast-$WEEK.mp3`.

## Setup

You need:

- A [scraped WhatsApp JSON export](https://tools.s-anand.net/whatsappscraper/) of the Gen AI Group chat as [`gen-ai-messages.json`](gen-ai-messages.json)
- Optional incremental WhatsApp exports such as `m1.json`, `m2.json`, etc.
- [`uv`](https://docs.astral.sh/uv/)
- Environment variable `OPENAI_API_KEY` and `GEMINI_API_KEY` with valid API keys.
- `ffmpeg` installed and in `PATH` for audio concatenation.

```bash
git clone https://github.com/sanand0/generative-ai-group.git
cd generative-ai-group
uv run split_whatsapp_messages.py gen-ai-messages.json
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
uv run podcast.py
```

Optionally, modify the podcast prompt, overall TTS style, and the `[[gemini.speakers]]` voice profiles in [`config.toml`](config.toml).

To synthesize audio directly from a script file without generating it from messages:

```bash
uv run podcast.py tts-script --script-file samples/example-dialogue.md
```

For agent callers, inspect the interface and prefer JSON output:

```bash
uv run podcast.py --describe
uv run podcast.py tts-script --script-file samples/example-dialogue.md --format json
```

To merge multiple WhatsApp scraper exports into weekly JSON shards first:

```bash
uv run split_whatsapp_messages.py gen-ai-messages.json m1.json m2.json
```

This writes weekly files to `messages/` using the same week labeling as [`podcast.py`](podcast.py):

- dated files are `messages/YYYY-MM-DD.json`
- `YYYY-MM-DD` is the Sunday label computed by `group_by_week()`
- Monday-Saturday messages go into the coming Sunday file
- Sunday messages go into the following Sunday file
- the current/future incomplete week is skipped
- rows with null or malformed `time` are preserved in `messages/unknown-time.json`
- if a weekly output file already exists, it is merged first so richer later rows can overwrite partial earlier rows by `messageId`

This will:

1. Merge one or more WhatsApp scraper exports into weekly JSON shards in `messages/`.
2. Read and filter messages.
3. Group them by ISO-week (Sunday-labeled output from `group_by_week()`).
4. For each week, it creates:
   - `{week}/messages.txt` (threaded transcript).
   - `{week}/podcast.md` (dialogue script).
   - `{week}/podcast.mp3`.

Files:

├── split_whatsapp_messages.py   # Merge WhatsApp exports and write weekly JSON shards
├── podcast.py                   # Single-file application with pure functions and type hints
├── config.toml                  # Voice configurations, podcast prompts, and TTS voice settings
├── gen-ai-messages.json         # WhatsApp export input (not versioned)
├── messages/                    # Weekly merged WhatsApp JSON shards
│   ├── YYYY-MM-DD.json          # Sunday-labeled weekly JSON for one completed week
│   └── unknown-time.json        # Rows with missing or malformed ISO timestamps
├── YYYY-MM-DD/                  # Per-week output directories
│   ├── messages.txt             # Threaded transcript
│   ├── podcast-YYYY-MM-DD.md    # Generated dialogue script
│   └── podcast-YYYY-MM-DD.mp3   # Final concatenated audio
├── samples/                     # Local sample scripts and generated audio for quick listening tests
└── podcast.xml                  # RSS feed

How It Works:

1. `split_whatsapp_messages.py` loads one or more scraper exports, repairs the common missing `[` wrapper if needed, merges duplicate `messageId` rows using WhatsApp-aware field rules, and writes weekly `messages/YYYY-MM-DD.json` files.
2. `split_whatsapp_messages.py` uses the same Sunday labeling as `podcast.py`: Monday-Saturday messages go to the coming Sunday file, Sunday messages roll into the following Sunday file, and incomplete current weeks are skipped.
3. `load_messages()` in `podcast.py` filters out items with null `time`, `text`, or missing `author`.
4. `group_by_week()` buckets by Sunday of each ISO week.
5. `build_threads()` indexes by `messageId`, collects replies via `quoteMessageId`, sorts roots chronologically.
6. `render_message()` writes indented `– Author: Text [reactions]` lines.
7. `get_podcast_script()` POSTs system + user prompts to the OpenAI `/v1/responses` endpoint and asks for direct-TTS-ready `Alex:` / `Maya:` lines with inline audio tags.
8. `split_script_segments()` validates the speaker transcript, Gemini 3.1 renders one line per request, and FFmpeg concatenates the clips into the final MP3.

## Release

One-time setup of [GitHub release](https://github.com/sanand0/generative-ai-group/releases/tag/main):

```bash
gh release create main --title "Podcast" --notes "Generative AI WhatsApp Group Podcast"
```

Upload and overwrite all podcasts:

```bash
gh release upload main --clobber */podcast-*.mp3
gh release upload main --clobber podcast.xml
```

Upload specific podcast:

```bash
WEEK=... gh release upload main $WEEK/podcast-$WEEK.mp3
gh release upload main --clobber podcast.xml
```

## License

[MIT](LICENSE)
