# Prompts

## Switch to Gemini 3.8 Flash Lite TTS and Luna 6, 26 Sep 2026

<!-- Switch Podcasts to Gemini 3.8 Flash TTS: https://chatgpt.com/c/6ab73aa2-11f8-83ec-815c-c37f88ea80dc (2026-09-26T13:42:35+08:00) -->

What are Gemini 3.8 Flash Lite TTS and Gemini 3.8 Flash TTS priced at? Would either of these be cheaper than the TTS models I use in ~/code/generative-ai-group/ or ~/code/sanand0/week/ on LocalMCP2 and what's the difference? List the current models and their prices and new models and prices comparably (e.g. to generate 1 or 10 or 60 min of audio).

Let me know if they can be replaced by just swapping the model names or some other changes are required.

Are there any new features that are worth leveraging - e.g. emotions from the text, model parameters, etc.? List, prioritized by impact x ease.

---

I'd like to make the following changes:

* GPT 6 Luna (with auto thinking) as the model that generates the conversation
* Gemini 3.8 Flash Lite (configurable) as the model that generates the audio
* Ask for an appropriate return format - I don't need WAV / PCM if it can return a better format
* Use multi-turn dialogue in chunks of 10 (configurable)
* Use structured emotion / style metadata if it's really appropriate, not otherwise

Think of this as a rewrite from scratch. How would you do this, writing compact, canonical, readable, elegant code, that achieves the same outcome by intent? Create a NEW script (or set of scripts) for this and I'll test and replace the earlier flow if I'm happy.

Try this for any one week on both the repositories, save the resulting MP3 in ~/Downloads/ and I'll listen to them.

---

The output looks good.

Currently, in both directories, I run just build deploy push. Modify the existing workflow to the revised workflow, doing what it does currently, functionally. That would mean porting the podcast_v2.py into the existing scripts and removing it, testing that it works, and documenting as required.

---

In generative-ai-group, this seems to have cut out the Jina intermediary to fetch pages. Did you replace it with a direct fetch or some other HTML to markdown mechanism? I don't mind if the mechanism changes - Jina was brittle - but I'd like to include page content as context for Luna.

Similarly, is any other important functionality cut out in either repo? Just let me know and I'll decide whether to fix the rest.

---

On LocalMCP2 fix the two regressions you mentioned.

---

Let's run this for the latest week. You may delete the outputs for 20 Sep 2026 and generate the script as well as the audio for both in the same directories. This serves as a test to make sure that the implementation works.

Compare the scripts generated and let me know what's better and worse in the revised version, and which script you'd prefer to listen to. I'll review the same and suggest changes to the script prompt if required.

---

It doesn't have to be old script vs new script. For example, can we retain the benefits of the new version, but incorporate the benefits of the old without losing the new?

Here are my suggestions on how to improve the new script (which you may merge with yours):

I like that the old script was broken into logical sections by paras (\n\n)
I prefer SIMPLE, conversational language. Short words, short sentences. Like how UK Government notices are really simple and well thought through. Simplicity does not mean eliminating jargon. It means you use it when required and explain what it means in a way the audience will instantly get and never forget. Examples are always helpful, of course. Is there a standard for podcasts - sort of like the style Tim Harford uses - that's aimed at simplicity? If so, maybe we can just mention that. Or even mention a podcaster like Tim Harford or anyone who's an exemplar for their simplicity to nudge the model.

Based on this, revise the prompts and just generate the revised text (no need for the audio) and compare the output. I'll do the same and share feedback.

---

Can we make this feel more natural? Think about what makes a conversation natural. Research this. It might be the personality, quirks, curiosity, etc of the host. Maybe other things. But I think that would be the main change I'd request further: make this feel more like a real conversation between two real, interesting people. Feel free to strengthen the prompt to retain technical hooks. Test it out, revise if required, and let's freeze on that (i.e. generate the MP3, stage the commits, don't commit yet because I'll review and commit.)


## Add context of past podcasts, 14 Jul 2026

<!--
cd ~/code/generative-ai-group
dev.sh -- codex --yolo --model gpt-5.6-sol --config model_reasoning_effort=medium
-->

Update podcast.py so that when writing the podcast script, it passes the context of the last 2 weeks' podcast-*.md. Ensure that these are only for context, reference, or continuity - not for repetition.

<!-- codex resume 019f5e42-5805-7131-bc48-f1106a9dccba --yolo -->

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

---

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

### Revert due to poor quality

It turns out that the upgrade to a single-shot multi-speaker TTS with the new model has resulted in much worse quality than the previous approach of splitting into line-level audio and concatenating.

So, reverse the changes to podcast.py and summary.py that implemented these changes (by copying the original files from the earlier commits). We can retain the original script, with only one change, i.e. the use of the new `gemini-3.1-flash-tts-preview` model, but we will keep the previous approach of splitting into line-level audio and concatenating them.

Test. Then create this as a new commit on top of the previous commits, so that we can refer to the previous commits if needed.

---

Delete the latest podcast in both repositories (2026-04-19) and re-generate it. Just the audio - you can leave the script, etc. as-is.

---

Retry week regeneration - hopefully Gemini rate limits have reset by now.

---

I manually reverted the changes to podcast.py and summary.py.`/home/sanand/code/sanand0/week/{summary.py,config.toml}` to Gemini 2.5 Flash TTS Preview, regenerated and committed. No action required.

<!-- codex resume 019da5a3-3768-7b71-ba99-7b0e657cba77 --yolo -->
