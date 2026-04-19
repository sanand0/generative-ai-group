# Prompts

## Merge script, 28 Mar 2026

<!--

cd ~/code/generative-ai-group
dev.sh -v /home/sanand/code/tools:/home/sanand/code/tools:ro
codex --yolo --model gpt-5.4 --config model_reasoning_effort=xhigh

--->

Write a script that will accept one or more JSON files as CLI arguments - each of which will be an array of objects like `{messageId: ..., time: ..., ...}`, merge by `messageId` (prefer the one from later files, i.e. overwrite), sort by `time` ascending, split by month and save as `messages/YYYY-MM.json` (e.g. `messages/2026-03.json`).

If the output will overwrite an existing file, merge with it treating the existing file as the first file (i.e. prefer the new file's data).

These files were created using the whatsappscraper tool at `/home/sanand/code/tools/whatsappscraper/` (see the prompts.md and postmortem.md for reference and any other files). Handle the merge using this knowledge.

Use Python, NodeJS, bash + jaq, whatever you like. Optimize your choice for brevity, maintainability, and performance.

Run and test with the JSON files in the current directory.

---

Modify the script to split by week instead by month. Align with the logic in podcast.py to identify the filename (messages/yyyy-mm-dd.json) and what messages go into each file. Document this logic in the code's docstrings and CLI help message. Run and test.

I have deleted messages/* so you can test with new files created.

---

Document the updates in README.md

---

Rather than create a separate messages/$WEEK.json let's make it $WEEK/messages.json. Modify .gitignore and scripts and tests accordingly. Run and test.

Modify podcast.py to align with this new structure. Add a dry-run option that will verify without making LLM API calls and test.

<!-- codex resume 019d3265-4949-7b33-9d20-c5f788435039 -->

## Rewrite history, 28 Mar 2026

<!--

cd ~/code/generative-ai-group
dev.sh -v /home/sanand/code/tools:/home/sanand/code/tools:ro
codex --yolo --model gpt-5.4 --config model_reasoning_effort=xhigh

--->

EFFICIENTLY rewrite the entire history to avoid pushing gen-ai-messages.json or any other raw message files.
Source code, $WEEK/podcast-$WEEK.md, any other files currently committed, should be retained.
Make sure the new history is identical (dates, authorship, commit messages, etc.) except for the removal of the raw message files.
Verify against the remote to make sure that everything's identical.
Don't push.

---

When running `uv run split_whatsapp_messages.py` verify that no messages are lost.
When it prints the output, print one per line and only print modified files, not unchanged ones.

---

In case podcast.py gets an API error, print the API response body for debugging.

<!-- codex resume 019d329e-c293-7e63-9b1a-76d647b62580 -->

## Upgrade for Gemini 3.1 Flash Preview, 19 Apr 2026

<!--

cd ~/code/generative-ai-group
dev.sh
codex --yolo --model gpt-5.4 --config model_reasoning_effort=xhigh

--->

The model `gemini-3.1-flash-tts-preview` is released. The usage is documented in `notes/gemini-tts-2026-04-19.md`.

Modify `podcast.py` to use this new model, use multi-speaker TTS (without needing to split into line-level audio and concatenate them), and modify the script generation prompt to use audio tags when OpenAI generates the script.

To help test this, make podcast.py an agent-friendly CLI that can generate the audio from a given script (without needing to generate the script from messages). Test with a few small sample scripts featuring multiple speakers and audio tags. Save the sample scripts and generated audio in a `.gitignored` `samples/` directory. Let me listen to them and share feedback.

---

This works fine. We will stick to the new model and approach. Clean up old redundant code, configurations, etc. to make podcast.py simpler, shorter, more maintainable. Test on samples to make sure it still works.

<!-- codex resume 019da5a3-3768-7b71-ba99-7b0e657cba77 --yolo -->

### Update sanand0 podcast

<!--

cd ~/code/generative-ai-group
dev.sh -v /home/sanand/code/sanand0:/home/sanand/code/sanand0
codex resume 019da5a3-3768-7b71-ba99-7b0e657cba77 --yolo

--->

In a similar way, update `/home/sanand/code/sanand0/week/summary.py` to use the new TTS model and approach.
Test with a few sample scripts and await my feedback.

---

This works fine. We will stick to the new model and approach. Clean up old redundant code, configurations, etc. to make summary.py simpler, shorter, more maintainable.

<!-- codex resume 019da5a3-3768-7b71-ba99-7b0e657cba77 --yolo -->
