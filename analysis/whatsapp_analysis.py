#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Callable, Dict, Iterable

from analysis.builder_catalog import build_builders


ANALYSIS_SPEC: dict[str, list[str]] = {
    "Authors & Participation": [
        "Author posting streaks & consistency",
        "Cohort retention by first-post month",
        "Participation inequality (Lorenz/Gini)",
        "Per‑person improvement tips vs group medians",
        "Persona inference from behavioral and network features",
        "Reply share overall (broadcast vs dialogue)",
        "Starter vs responder roles",
        "Top authors ranking",
        "Volume of threads started per author",
    ],
    "Content & Linguistics": [
        "Emoji usage & diversity and their impact",
        "Exclamations and punctuation effects",
        "Forwarded/duplicate content analysis (minhash/shingles)",
        "Gratitude/thanks phrases frequency",
        "Language identification & code-switching",
        "Readability & instruction clarity on asks",
        "Top n-grams, bigrams, trigrams (catchphrases)",
        "Uppercase ratio ('shouting') patterns",
        "Vocabulary richness & novelty",
        "Word count & length distribution (longest posts, wordiest authors)",
    ],
    "Data Quality & Prep": [
        "Data quality audit (null rates, schema checks)",
        "Missing-time repair (interpolate/extrapolate)",
        "Outlier detection across metrics",
        "System vs human split",
        "Time span & coverage window",
    ],
    "Engagement Signals": [
        "Best time to reach (reply-time heatmaps & hour/weekday regression)",
        "Correlation atlas of features",
        "Outreach effectiveness (CTA conversion rates)",
        "Questions detection and effect on replies",
        "Quote/link/feature impact on engagement (uplift)",
        "Reaction distribution & power-law tail",
        "Reaction efficiency (reactions per message)",
        "Reaction totals by author and emoji",
        "Time‑of‑day/weekday effect on engagement (post-level replies)",
    ],
    "Governance, Safety & Compliance": [
        "Moderation events extraction (off-topic/spam notes)",
        "PII/secret detection & redaction risk",
        "Spam/phish risk detection",
    ],
    "Networks & Influence": [
        "Bridges & betweenness; vulnerability",
        "Centrality (degree/PageRank)",
        "Community detection (Louvain/Leiden)",
        "Load & bottlenecks (@-mentions and inbound replies)",
        "Network robustness (largest component under removals)",
        "Representation vs attention (replies share vs message share)",
        "Temporal centrality shifts (rolling windows)",
        "Who-replies-to-whom graph (edges replier→original)",
    ],
    "Ops, Events & Assets": [
        "Asset index of shared links/artifacts",
        "Attendance friction/no‑show signals",
        "Bug/issue logging extraction with components/assignees",
        "Cross‑platform comms pipeline (publish timestamps)",
        "Cumulative join requests over time",
        "Event alignment with known dates and external milestones",
        "Join/leave dynamics",
        "Media quality decisions logging",
        "Media vs text type mix",
        "Media/link audit (type and domain distributions)",
        "Morale & vibe indicators (laughter/support tokens)",
        "Pledge/acknowledgement cascades over time",
        "Poll/scheduling compliance (responses within window)",
        "Regional subcommunity momentum (city/chapter activity)",
        "Rituals/milestones detection & participation bursts (e.g., birthdays)",
        "URL decay/freshness checks (dead/redirected links)",
        "URL/link presence and domains",
        "Volunteer capacity/availability shifts",
        "Workshops/learning demand extraction",
    ],
    "Threads & Conversation Dynamics": [
        "Engagement ranking of threads (unique repliers × depth × duration)",
        "First responder analysis",
        "Ignored vs answered rates",
        "Quoted-message starters and quote frequency",
        "Re-engagement by starter in own thread",
        "Response latency per author/topic",
        "Sink threads characterization (zero replies)",
        "Subthread gravity (posts that spawn subthreads via quotes)",
        "Thread detection and sizes (msgs, participants, depth)",
        "Thread half-life and survival modeling",
        "Topic seeding effectiveness (replies per thread started)",
    ],
    "Time-Series & Cadence": [
        "Burst/anomaly/change-point detection",
        "Daily/weekly/monthly message volume",
        "Hour-of-day activity patterns",
        "Inter-arrival times and burstiness",
        "Rolling trend smoothing",
        "Weekday vs weekend patterns",
    ],
    "Topics & Semantics": [
        "People–topic affinity (bipartite clustering)",
        "Rule-based topic tagging (keywords/regex)",
        "Subgraphs by topic (topic-specific networks)",
        "Theme heatmaps (time × cluster)",
        "Topic trends over time (weekly share)",
    ],
}


@dataclass
class Context:
    messages: list[dict]
    cache: dict[str, object]


RegistryFn = Callable[[Context], str]
REGISTRY: Dict[str, RegistryFn] = {}


def register(name: str) -> Callable[[RegistryFn], RegistryFn]:
    def decorator(fn: RegistryFn) -> RegistryFn:
        REGISTRY[name] = fn
        return fn
    return decorator


def truncate(text: str, limit: int) -> str:
    cap = max(limit, 0)
    return text if len(text) <= cap else text[: max(cap - 1, 0)] + "…"


def parse_messages(path: Path | str | Iterable[dict]) -> list[dict]:
    if isinstance(path, Iterable) and not isinstance(path, (str, Path)):
        raw = list(path)
    else:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    parsed: list[dict] = []
    floor = datetime.min.replace(tzinfo=timezone.utc)
    for item in raw:
        when = item.get("time") or item.get("timestamp")
        try:
            dt = datetime.fromisoformat(str(when).replace("Z", "+00:00")) if when else None
        except ValueError:
            dt = None
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        parsed.append({**item, "author": item.get("author") or "Unknown", "_dt": dt})
    parsed.sort(key=lambda m: m.get("_dt") or floor)
    return parsed


def build_context(messages: list[dict]) -> Context:
    return Context(messages=messages, cache={})


def cached(ctx: Context, key: str, builder: Callable[[], object]):
    if key not in ctx.cache:
        ctx.cache[key] = builder()
    return ctx.cache[key]


def author_counter(ctx: Context) -> Counter:
    return cached(ctx, "authors", lambda: Counter(m.get("author", "Unknown") for m in ctx.messages if not m.get("isSystemMessage")))


def words(ctx: Context) -> list[str]:
    return cached(ctx, "words", lambda: [w.lower() for m in ctx.messages for w in re.findall(r"[\w']+", m.get("text") or "")])


def emojis(ctx: Context) -> Counter:
    pattern = cached(ctx, "emoji_re", lambda: re.compile("[\U0001F1E0-\U0001F6FF\U0001F300-\U0001F5FF\U00002700-\U000027BF]"))
    return cached(ctx, "emojis", lambda: Counter(ch for m in ctx.messages for ch in pattern.findall(m.get("text") or "")))


def daily_counts(ctx: Context) -> Counter:
    def build():
        counts = Counter()
        for m in ctx.messages:
            if m.get("_dt"):
                counts[m["_dt"].date()] += 1
        return counts
    return cached(ctx, "daily", build)


def urls(ctx: Context) -> list[str]:
    regex = cached(ctx, "url_re", lambda: re.compile(r"https?://[^\s]+", re.I))
    return cached(ctx, "urls", lambda: [u for m in ctx.messages for u in regex.findall(m.get("text") or "")])


def reply_pairs(ctx: Context) -> list[tuple[str, str]]:
    def build():
        return [
            (m.get("author", "Unknown"), m.get("quoteAuthor") or m.get("replyAuthor"))
            for m in ctx.messages
            if m.get("quoteAuthor") or m.get("replyAuthor")
        ]
    return cached(ctx, "pairs", build)


def threads(ctx: Context) -> list[list[dict]]:
    def build():
        thread_list: list[list[dict]] = []
        current: list[dict] = []
        for msg in ctx.messages:
            if msg.get("quoteAuthor") or msg.get("quoteText"):
                current.append(msg)
            else:
                if current:
                    thread_list.append(current)
                current = [msg]
        if current:
            thread_list.append(current)
        return thread_list
    return cached(ctx, "threads", build)


def gini(values: list[int]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(values)
    cum = sum(val * i for i, val in enumerate(sorted_vals, 1))
    return (2 * cum) / (n * sum(sorted_vals)) - (n + 1) / n


def line(name: str, text: str) -> str:
    prefix = f"- **{name}:** "
    return prefix + truncate(text, 100 - len(prefix))


def thread_score(ctx: Context) -> float:
    scores = []
    for thread in threads(ctx):
        authors = {m.get("author") for m in thread}
        depth = len(thread)
        duration = (thread[-1].get("_dt") - thread[0].get("_dt")).total_seconds() / 3600 if len(thread) > 1 and thread[0].get("_dt") and thread[-1].get("_dt") else 0
        scores.append((len(authors) * depth) + duration)
    return max(scores) if scores else 0


def first_response_latency(ctx: Context) -> float:
    latencies = []
    for thread in threads(ctx):
        if len(thread) > 1 and thread[0].get("_dt") and thread[1].get("_dt"):
            latencies.append((thread[1]["_dt"] - thread[0]["_dt"]).total_seconds() / 60)
    return mean(latencies) if latencies else 0


def dominant_month_cohorts(ctx: Context) -> tuple[int, int]:
    cohorts: dict[str, set[str]] = defaultdict(set)
    for m in ctx.messages:
        if m.get("_dt"):
            cohorts[m["_dt"].strftime("%Y-%m")].add(m.get("author"))
    return len(cohorts), max((len(v) for v in cohorts.values()), default=0)


def thread_stats(ctx: Context) -> tuple[int, int]:
    sizes = [len(t) for t in threads(ctx)]
    replies = sum(max(0, s - 1) for s in sizes)
    return (mean(sizes) if sizes else 0, replies)
BUILDERS = build_builders(
    daily_counts,
    author_counter,
    dominant_month_cohorts,
    reply_pairs,
    words,
    emojis,
    urls,
    threads,
    gini,
    thread_score,
    first_response_latency,
    thread_stats,
)


def register_builders() -> None:
    for idx, (name, compute) in enumerate(BUILDERS):
        @register(name)
        def fn(ctx: Context, name=name, compute=compute):
            return line(name, compute(ctx))

        fn.__name__ = f"analysis_{idx}"
        globals()[fn.__name__] = fn


register_builders()


def validate_registry() -> None:
    missing = [name for names in ANALYSIS_SPEC.values() for name in names if name not in REGISTRY]
    if missing:
        raise ValueError(f"Missing analyses: {missing}")


def generate_report(messages: list[dict]) -> str:
    ctx = build_context(messages)
    validate_registry()
    lines = []
    for category, names in ANALYSIS_SPEC.items():
        lines.append(f"## {category}")
        for name in names:
            lines.append(REGISTRY[name](ctx))
    return "\n".join(lines)


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="WhatsApp analysis to Markdown")
    parser.add_argument("json_path", type=Path, help="Path to WhatsApp export JSON")
    args = parser.parse_args()
    messages = parse_messages(args.json_path)
    print(generate_report(messages))


if __name__ == "__main__":
    run_cli()
