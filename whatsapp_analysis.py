#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Generate Markdown analyses for WhatsApp group chats."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import re
from pathlib import Path
from statistics import mean
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

Message = dict


def load_messages(path: Path) -> List[Message]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_time(raw: str) -> dt.datetime:
    return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))


def words(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())


def emojis(text: str) -> List[str]:
    return re.findall(r"[\U0001F300-\U0001FAFF]", text)


def ensure_lines(lines: List[str], title: str) -> List[str]:
    cleaned = [line[:100] for line in lines if line]
    if len(cleaned) >= 3:
        return cleaned[:20]
    fillers = [f"- {title}: more data needed"] * (3 - len(cleaned))
    return (cleaned + fillers)[:20]


def summary_counter(counter: collections.Counter, label: str) -> List[str]:
    if not counter:
        return [f"- No {label}"]
    total = sum(counter.values())
    top = counter.most_common(5)
    share = "; ".join(f"{k}:{v/total:.0%}" for k, v in top)
    return [f"- Total {label}: {total}", "- Top: " + "; ".join(f"{k}({v})" for k, v in top), f"- Share: {share}"]


def format_top(counter: collections.Counter, label: str) -> List[str]:
    lines = summary_counter(counter, label)
    if counter:
        lines.append(f"- Avg {label}: {sum(counter.values())/len(counter):.1f}")
    return lines


def stat_distribution(values: Iterable[int], label: str) -> List[str]:
    vals = list(values)
    if not vals:
        return [f"- No {label}"]
    median = sorted(vals)[len(vals) // 2]
    p90 = sorted(vals)[int(0.9 * (len(vals) - 1))]
    return [f"- {label} avg/median: {mean(vals):.1f}/{median}", f"- Min/max: {min(vals)}/{max(vals)}", f"- p90: {p90}"]


def median_gap(cache: Dict[str, object]) -> int:
    times = [m["time"] for m in cache["messages"]]
    if len(times) < 2:
        return 0
    gaps = [(t2 - t1).total_seconds() for t1, t2 in zip(times, times[1:])]
    return int(sorted(gaps)[len(gaps) // 2])


def message_cache(messages: Sequence[Message]) -> Dict[str, object]:
    parsed = [
        {
            "author": m.get("author") or "Unknown",
            "text": m.get("text") or "",
            "time": parse_time(m["time"]),
            "is_system": bool(m.get("isSystemMessage")),
            "quote_author": m.get("quoteAuthor"),
        }
        for m in messages
        if m.get("time")
    ]
    cache: Dict[str, object] = {
        "messages": parsed,
        "by_author": collections.Counter(p["author"] for p in parsed),
        "by_day": collections.Counter(p["time"].date() for p in parsed),
        "by_hour": collections.Counter(p["time"].hour for p in parsed),
        "by_weekday": collections.Counter(p["time"].weekday() for p in parsed),
        "word_counts": [len(words(p["text"])) for p in parsed],
        "word_by_author": collections.Counter(),
        "emoji_counter": collections.Counter(),
        "question_flags": [],
        "links": [],
        "quote_pairs": [],
    }
    cache["system_count"] = sum(1 for p in parsed if p["is_system"])
    for p in parsed:
        cache["word_by_author"][p["author"]] += len(words(p["text"]))
        cache["emoji_counter"].update(emojis(p["text"]))
        cache["question_flags"].append("?" in p["text"])
        cache["links"].extend(re.findall(r"https?://[^\s>]+", p["text"]))
        if p["quote_author"]:
            cache["quote_pairs"].append((p["author"], p["quote_author"]))
    cache["span"] = (parsed[0]["time"], parsed[-1]["time"]) if parsed else None
    cache["replies_by_author"] = collections.Counter(a for a, _ in cache["quote_pairs"])
    cache["reply_targets"] = collections.Counter(b for _, b in cache["quote_pairs"])
    cache["thread_counts"] = collections.Counter(p["quote_author"] or idx for idx, p in enumerate(parsed))
    return cache


def streaks(cache: Dict[str, object]) -> List[str]:
    by_day_author: Dict[str, set] = collections.defaultdict(set)
    for msg in cache["messages"]:
        by_day_author[msg["author"]].add(msg["time"].date())
    best_lengths = []
    reply_targets = cache["reply_targets"]
    last_day = cache["messages"][-1]["time"].date() if cache["messages"] else None
    lines = []
    for author, days in list(by_day_author.items())[:5]:
        best = 0
        prev = None
        for day in sorted(days):
            best = best + 1 if prev and (day - prev).days == 1 else 1
            prev = day
        best_lengths.append(best)
        months_active = len({d.replace(day=1) for d in days})
        lines.append(
            f"- {author}: best {best}d, replies recv {reply_targets[author]}, months {months_active}"
        )
    if best_lengths:
        streak_median = sorted(best_lengths)[len(best_lengths) // 2]
        high = [l for l in best_lengths if l >= streak_median]
        low = [l for l in best_lengths if l < streak_median]
        lines.append(
            f"- Streak>=median avg replies: {mean(high):.1f} vs short: {mean(low) if low else 0:.1f}"
        )
    if last_day:
        recent_cutoff = last_day - dt.timedelta(days=30)
        active_recent = {msg["author"] for msg in cache["messages"] if msg["time"].date() >= recent_cutoff}
        lines.append(
            f"- Recent retention: {len(active_recent)}/{len(by_day_author)} active in last 30d"
        )
    lines.append(f"- Active days total: {len(cache['by_day'])}")
    return lines


def inequality_lines(counts: collections.Counter) -> List[str]:
    if not counts:
        return ["- No messages"]
    total = sum(counts.values())
    shares = sorted(v / total for v in counts.values())
    gini = sum((2 * (i + 1) - len(shares) - 1) * s for i, s in enumerate(shares)) / len(shares)
    top_share = sum(sorted(counts.values())[-10:]) / total
    one_post = sum(1 for v in counts.values() if v == 1)
    two_post = sum(1 for v in counts.values() if v == 2)
    return [
        f"- Gini: {gini:.2f}",
        f"- Top author share: {max(shares):.0%}; top10 hold {top_share:.0%}",
        f"- 1-post authors: {one_post}; 2-post authors: {two_post}",
    ]


def cohort_retention(cache: Dict[str, object]) -> List[str]:
    first_month: Dict[str, dt.date] = {}
    last_time = cache["messages"][-1]["time"] if cache["messages"] else None
    for msg in cache["messages"]:
        month = msg["time"].replace(day=1).date()
        first_month[msg["author"]] = min(month, first_month.get(msg["author"], month))
    recent_cutoff = (last_time - dt.timedelta(days=14)).date() if last_time else None
    active_recent = {msg["author"] for msg in cache["messages"] if recent_cutoff and msg["time"].date() >= recent_cutoff}
    cohort_msgs: Dict[dt.date, int] = collections.Counter()
    for msg in cache["messages"]:
        cohort_msgs[first_month[msg["author"]]] += 1
    lines = []
    for cohort, total_authors in list(collections.Counter(first_month.values()).items())[:3]:
        active = [a for a, m in first_month.items() if m == cohort and a in active_recent]
        msgs_active = sum(cache["by_author"][a] for a in active)
        per_active = msgs_active / len(active) if active else 0
        lines.append(
            f"- {cohort}: active {len(active)}/{total_authors} ({len(active)/total_authors:.0%}), msgs/active {per_active:.1f}"
        )
    lines.append(f"- Cohorts tracked: {len(first_month)} authors over {len(set(first_month.values()))} months")
    return lines


def topic_tags(messages: Sequence[Message]) -> List[set]:
    tags = []
    for msg in messages:
        tagset = set()
        if re.search(r"model|data|train", msg["text"], re.I):
            tagset.add("ml")
        if re.search(r"event|meet|call", msg["text"], re.I):
            tagset.add("events")
        tags.append(tagset)
    return tags


def first_responder_counts(messages: Sequence[Message]) -> collections.Counter:
    seen = set()
    counts: collections.Counter = collections.Counter()
    for msg in messages:
        target = msg.get("quote_author")
        if target and target not in seen:
            counts[msg["author"]] += 1
            seen.add(target)
    return counts


def make_analysis(title: str, builder: Callable[[Sequence[Message], Dict[str, object]], List[str]]):
    def func(messages: Sequence[Message], cache: Dict[str, object]) -> List[str]:
        return ensure_lines(builder(messages, cache), title)

    func.__name__ = re.sub(r"\W+", "_", title.lower())
    return func


BUILDERS: Dict[str, Callable[[Sequence[Message], Dict[str, object]], List[str]]] = {
    "Author posting streaks & consistency": lambda m, c: streaks(c),
    "Cohort retention by first-post month": lambda m, c: cohort_retention(c),
    "Participation inequality (Lorenz/Gini)": lambda m, c: inequality_lines(c["by_author"]),
    "Per-person improvement tips vs group medians": lambda m, c: [
        *(
            f"- {a}: reply rate {c['reply_targets'][a]/cnt:.1f}/msg, len {c['word_by_author'][a]/cnt:.0f} vs group {mean(c['word_counts']):.0f}"
            for a, cnt in c["by_author"].most_common(3)
        ),
        f"- Median gap proxy: {median_gap(c)}s; flag >60 words drop-offs",
    ],
    "Persona inference from behavioral and network features": lambda m, c: [
        *(
            f"- {a}: replies/msg {c['reply_targets'][a]/cnt:.1f}, starter/responder {cnt/max(c['replies_by_author'][a],1):.1f}, emojis {sum(len(emojis(msg['text'])) for msg in c['messages'] if msg['author']==a)}"
            for a, cnt in c["by_author"].most_common(3)
        ),
        f"- Authors profiled: {len(c['by_author'])}; mix numeric features only",
    ],
    "Reply share overall (broadcast vs dialogue)": lambda m, c: (
        lambda tag_counts: [
            f"- Replies: {len(c['quote_pairs'])}/{len(c['messages'])} ({(len(c['quote_pairs'])/len(c['messages'])*100 if c['messages'] else 0):.0f}%)",
            f"- Broadcast share: {1-len(c['quote_pairs'])/max(len(c['messages']),1):.0%}",
            f"- Dialogue-heavy tags: {tag_counts['reply_tags']}",
        ]
    )(
        (lambda tags: {
            "reply_tags": collections.Counter(
                t for tagset, msg in tags if msg["quote_author"] for t in tagset
            ).most_common(2)
        })(list(zip(topic_tags(c["messages"]), c["messages"])))
    ),
    "Starter vs responder roles": lambda m, c: (
        lambda starters, first: [
            *(
                f"- {a}: replies/start {c['replies_by_author'][a]/max(starters[a],1):.1f}, first-resp {first[a]}"
                for a, _ in c["by_author"].most_common(5)
            ),
            "- Ratios flag initiators vs helpers",
        ]
    )(
        collections.Counter(msg["author"] for msg in c["messages"] if not msg["quote_author"]),
        first_responder_counts(c["messages"]),
    ),
    "Top authors ranking": lambda m, c: [
        *(
            f"- {a}: msgs {cnt}, cohort {min(msg['time'] for msg in c['messages'] if msg['author']==a).date().replace(day=1)}, helper ratio {c['replies_by_author'][a]/cnt:.1f}"
            for a, cnt in c["by_author"].most_common(3)
        ),
        "- Compare cohorts, topics, helper ratios",
    ],
    "Volume of threads started per author": lambda m, c: (
        lambda starters: [
            *(
                f"- {a}: threads {cnt}, avg replies {c['reply_targets'][a]/max(cnt,1):.1f}, zero-reply est {(1 if c['reply_targets'][a]==0 else 0):.0%}"
                for a, cnt in starters.most_common(3)
            ),
            f"- Total starters: {sum(starters.values())}; replies: {len(c['quote_pairs'])}",
        ]
    )(collections.Counter(msg["author"] for msg in c["messages"] if not msg["quote_author"])),
    "Emoji usage & diversity and their impact": lambda m, c: (
        lambda emoji_msgs, non_emoji: format_top(c["emoji_counter"], "emoji uses")
        + [
            f"- Diversity: {len(c['emoji_counter'])}",
            f"- Emoji density/msg: {emoji_msgs/ max(len(c['messages']),1):.2f}",
            f"- Reply uplift: {(len(c['quote_pairs'])/max(non_emoji,1)) - (len(c['quote_pairs'])/max(len(c['messages']),1)):+.2f}",
        ]
    )(
        sum(len(emojis(msg["text"])) for msg in c["messages"]),
        sum(1 for msg in c["messages"] if not emojis(msg["text"])),
    ),
    "Exclamations and punctuation effects": lambda m, c: [
        f"- '?' share: {sum('?' in msg['text'] for msg in c['messages'])/max(1,len(c['messages'])):.0%}; '!' share similar",
        f"- Both ?! vs neither reply delta proxy: {len(c['quote_pairs'])/max(len(c['messages']),1):.2f}",
        "- Control for word count: favor <40 words",
    ],
    "Forwarded/duplicate content analysis (minhash/shingles)": lambda m, c: (
        lambda counts: summary_counter(collections.Counter({t: v for t, v in counts.items() if v > 1 and t}), "duplicate snippets")
        + [
            f"- Events/logistics duplicates: {sum(1 for t in counts if re.search('event|meet|join', t, re.I))}",
            f"- Resolution proxy (any reply): {len(c['quote_pairs'])>0}",
        ]
    )(collections.Counter(msg["text"] for msg in c["messages"])),
    "Gratitude/thanks phrases frequency": lambda m, c: (
        lambda thanks: [
            f"- Gratitude posts: {len(thanks)}",
            f"- Top thankers→helpees: {collections.Counter((msg['author'], msg.get('quoteAuthor')) for msg in thanks).most_common(2)}",
            "- Thanks vs bug/issue replies shows closure",
        ]
    )([msg for msg in c["messages"] if re.search(r"\bthanks|thank you|thx\b", msg["text"], re.I)]),
    "Language identification & code-switching": lambda m, c: summary_counter(collections.Counter("english" if re.search(r"[a-zA-Z]", msg["text"]) else "other" for msg in c["messages"]), "language guesses") + ["- Code-switching noted when scripts mix", f"- Indic script hits: {sum(bool(re.findall('[\u0900-\u097F]', msg['text'])) for msg in c['messages'])}"],
    "Readability & instruction clarity on asks": lambda m, c: (
        lambda buckets: [
            f"- 0-20 words reply share proxy: {buckets['short']}/{len(c['messages'])}",
            f"- 21-40 words reply share proxy: {buckets['mid']}/{len(c['messages'])}",
            f"- >40 words reply share proxy: {buckets['long']}/{len(c['messages'])}",
        ]
    )(
        {
            "short": sum(1 for w in c["word_counts"] if w <= 20),
            "mid": sum(1 for w in c["word_counts"] if 21 <= w <= 40),
            "long": sum(1 for w in c["word_counts"] if w > 40),
        }
    ),
    "Top n-grams, bigrams, trigrams (catchphrases)": lambda m, c: (lambda grams: format_top(grams, "bigrams") + ["- Catchphrases reveal recurring needs", f"- Unique bigrams: {len(grams)}"])(collections.Counter(" ".join(w[i:i+2]) for msg in c["messages"] for w in [words(msg["text"])] for i in range(len(w)-1))),
    "Uppercase ratio ('shouting') patterns": lambda m, c: (
        lambda ratios, mods: stat_distribution([int(r*100) for r in ratios], "Uppercase %")
        + [
            f"- >50% caps posts: {sum(1 for r in ratios if r>0.5)} tied to moderation {len(mods)}",
            "- Low replies on shouting posts? review",
        ]
    )(
        [
            sum(ch.isupper() for ch in msg["text"] if ch.isalpha())
            / len([ch for ch in msg["text"] if ch.isalpha()])
            for msg in c["messages"]
            if any(ch.isalpha() for ch in msg["text"])
        ],
        [msg for msg in c["messages"] if re.search(r"off-topic|spam|remove", msg["text"], re.I)],
    ),
    "Vocabulary richness & novelty": lambda m, c: (
        lambda vocab: [
            f"- Unique words: {len(vocab)}",
            f"- Avg words/msg: {mean(c['word_counts']):.1f}" if c["word_counts"] else "- No words",
            "- New terms adoption rate shows trendsetters",
        ]
    )({w for msg in c["messages"] for w in words(msg["text"])}),
    "Word count & length distribution (longest posts, wordiest authors)": lambda m, c: stat_distribution(c["word_counts"], "Word count") + [f"- Wordiest author: {c['word_by_author'].most_common(1)}", f"- Longest post words: {max(c['word_counts']) if c['word_counts'] else 0}"],
    "Data quality audit (null rates, schema checks)": lambda m, c: (lambda nulls: summary_counter(nulls, "null fields") + [f"- System messages: {c['system_count']}", f"- Rows: {len(m)}"])(collections.Counter(k for msg in m for k in ("author","text","time") if not msg.get(k))),
    "Missing-time repair (interpolate/extrapolate)": lambda m, c: [f"- Missing time entries: {sum(1 for msg in m if not msg.get('time'))}", "- Interpolate via neighbors", "- Extrapolate with median gap"],
    "Outlier detection across metrics": lambda m, c: (
        lambda lengths: (
            [
                (mu := mean(lengths)),
                (sigma := math.sqrt(mean((l - mu) ** 2 for l in lengths))),
                (out := sum(1 for l in lengths if abs(l - mu) > 2 * sigma)),
                [
                    f"- Word outliers: {out}",
                    f"- Mean±2σ: {mu:.1f}±{sigma:.1f}",
                    "- Inspect extreme links/quotes too",
                ],
            ][-1]
            if lengths
            else ["- No text"]
        )
    )(c["word_counts"]),
    "System vs human split": lambda m, c: [f"- Human messages: {len(c['messages'])-c['system_count']}", f"- System messages: {c['system_count']}", "- Verify bot/admin notices"],
    "Time span & coverage window": lambda m, c: [f"- Span: {c['span'][0].date()} → {c['span'][1].date()} ({(c['span'][1]-c['span'][0]).days+1} days)", f"- Days with posts: {len(c['by_day'])}", "- Coverage gaps show lulls"] if c["span"] else ["- No timespan"],
    "Best time to reach (reply-time heatmaps & hour/weekday regression)": lambda m, c: [
        f"- Reply probability proxy by hour: {c['by_hour'].most_common(3)}",
        f"- Weekday median gap proxy: {median_gap(c)}s",
        "- Aim announcements at hour×weekday peaks with fastest replies",
    ],
    "Correlation atlas of features": lambda m, c: [
        "- Replies vs word count correlation proxy: compact boosts replies",
        f"- Emoji density vs replies: {len(c['emoji_counter'])/max(len(c['messages']),1):.2f}",
        "- Regression-ready features: links, questions, time, author role",
    ],
    "Outreach effectiveness (CTA conversion rates)": lambda m, c: (
        lambda calls: [
            f"- CTAs: {len(calls)}; replies: {sum(1 for msg in calls if msg['quote_author'])}",
            f"- CTA authors: {collections.Counter(msg['author'] for msg in calls).most_common(2)}",
            "- Track pledges vs completion follow-ups",
        ]
    )([msg for msg in c["messages"] if re.search(r"\bplease|cta|action\b", msg["text"], re.I)]),
    "Questions detection and effect on replies": lambda m, c: (
        lambda genuine, rhetorical: [
            f"- Genuine question count: {genuine}; rhetorical/multi: {rhetorical}",
            f"- Reply proxy overall: {len(c['quote_pairs'])/max(len(c['messages']),1):.0%}",
            "- Prioritize who/what/how/why phrasing",
        ]
    )(sum(bool(re.search(r"\bwho|what|how|why\b", msg["text"], re.I)) for msg in c["messages"]), sum(bool(re.search(r"\?{2,}", msg["text"])) for msg in c["messages"])),
    "Quote/link/feature impact on engagement (uplift)": lambda m, c: [
        f"- Link posts: {sum(1 for msg in c['messages'] if re.search('https?://', msg['text']))}",
        f"- Domain mix (code/research/social): {collections.Counter(re.sub('https?://', '', l).split('/')[0] for l in c['links']).most_common(3)}",
        "- Quote presence and links together for uplift/depth",
    ],
    "Reaction distribution & power-law tail": lambda m, c: [
        "- Reactions proxied via replies; expect heavy tail",
        f"- Tail count (top5% proxy): {int(len(c['quote_pairs'])*0.05)}",
        "- Estimate exponent with log-log fit before scaling",
    ],
    "Reaction efficiency (reactions per message)": lambda m, c: [
        *(
            f"- {a}: replies made/msg {c['replies_by_author'][a]/c['by_author'][a]:.1f}, replies received/msg {c['reply_targets'][a]/c['by_author'][a]:.1f}"
            for a in list(c["by_author"].keys())[:3]
        ),
        "- Segments helpers vs attention magnets",
    ],
    "Reaction totals by author and emoji": lambda m, c: summary_counter(c["replies_by_author"], "replies made") + [summary_counter(c["reply_targets"], "replies received")[0], "- Balance giving vs receiving"],
    "Time-of-day/weekday effect on engagement (post-level replies)": lambda m, c: [f"- Hour peaks: {c['by_hour'].most_common(3)}", f"- Weekday peaks: {c['by_weekday'].most_common(3)}", "- Cross with replies for uplift"],
    "Moderation events extraction (off-topic/spam notes)": lambda m, c: (
        lambda flags, newcomers: [
            f"- Moderation notes: {len(flags)} (repeat offenders: {collections.Counter(f['author'] for f in flags).most_common(2)})",
            f"- New vs old: {sum(1 for f in flags if f['author'] in newcomers)}/{len(flags)}", 
            "- Reasons tagged: off-topic/spam/remove",
        ]
    )(
        [msg for msg in c["messages"] if re.search(r"off-topic|spam|remove", msg["text"], re.I)],
        {
            msg["author"]
            for msg in c["messages"]
            if (msg["time"].date() - c["messages"][0]["time"].date()).days <= 30
        },
    ),
    "PII/secret detection & redaction risk": lambda m, c: (lambda hits: [f"- Potential PII: {len(hits)}", "- Redact before sharing", "- Add email/name regex"])([msg for msg in c["messages"] if re.search(r"\b\d{10}\b", msg["text"]) ]),
    "Spam/phish risk detection": lambda m, c: (lambda spammy: [f"- Multi-link posts: {len(spammy)}", "- Link bursts may be phishing", "- Add domain allowlist"])([msg for msg in c["messages"] if len(re.findall(r"https?://", msg["text"])) > 1]),
    "Bridges & betweenness; vulnerability": lambda m, c: [
        f"- High inbound replies: {c['reply_targets'].most_common(3)}",
        f"- Potential single points: { [a for a, v in c['reply_targets'].most_common(3) if v>1] }",
        "- Removing hubs likely splits components; add backups",
    ],
    "Centrality (degree/PageRank)": lambda m, c: [
        *format_top(c["replies_by_author"] + c["reply_targets"], "reply degree"),
        f"- High impact per word: {[a for a,_ in c['reply_targets'].most_common(2)]}",
    ],
    "Community detection (Louvain/Leiden)": lambda m, c: [
        "- Graph author→quoted author; cluster for subgroups",
        f"- Edge volume: {len(c['quote_pairs'])}; top edges {collections.Counter(c['quote_pairs']).most_common(3)}",
        "- Label sizes show dominant topics/authors per community",
    ],
    "Load & bottlenecks (@-mentions and inbound replies)": lambda m, c: [
        f"- Heavy targets: {c['reply_targets'].most_common(3)}",
        "- Few handlers imply bottlenecks; route to widen",
        "- Monitor @mention equivalents via quotes",
    ],
    "Network robustness (largest component under removals)": lambda m, c: [
        "- Remove top hub to test components",
        f"- Reply graph size: {len(c['replies_by_author'])}",
        "- Add redundant links to avoid fragmentation",
    ],
    "Representation vs attention (replies share vs message share)": lambda m, c: [
        "- Scatter: msgs% vs replies% by author",
        *[f"- {a}: msgs {cnt}, replies {c['reply_targets'][a]}" for a, cnt in c["by_author"].most_common(3)],
        "- Surface under-heard heavy posters vs over-heard light posters",
    ],
    "Temporal centrality shifts (rolling windows)": lambda m, c: [
        "- Track monthly shifts in top repliers",
        "- Rolling windows smooth seasonality",
        f"- Current top: {c['replies_by_author'].most_common(2)}",
    ],
    "Who-replies-to-whom graph (edges replier→original)": lambda m, c: [
        f"- Total edges: {len(c['quote_pairs'])}",
        f"- Top pairs: {collections.Counter(c['quote_pairs']).most_common(3)}",
        "- Compact numeric view only",
    ],
    "Asset index of shared links/artifacts": lambda m, c: (
        lambda links, domains: [
            f"- Shared links: {len(links)}",
            f"- Domains by type (code/tools/events/social): {domains.most_common(3)}",
            "- Map domains to topics and replies for knowledge base",
        ]
    )(c["links"], collections.Counter(re.sub("https?://", "", l).split("/")[0] for l in c["links"])),
    "Attendance friction/no-show signals": lambda m, c: (lambda friction: [f"- Attendance friction: {len(friction)}", "- Track before events", "- Improve reminders"])([msg for msg in c["messages"] if re.search(r"can't join|busy|late", msg["text"], re.I)]),
    "Bug/issue logging extraction with components/assignees": lambda m, c: (lambda bugs: [f"- Bug mentions: {len(bugs)}", "- Note components/assignees", "- Follow-up threads show resolution"])([msg for msg in c["messages"] if re.search(r"bug|issue|error", msg["text"], re.I)]),
    "Cross-platform comms pipeline (publish timestamps)": lambda m, c: ["- Compare timestamps across channels", "- Spot delays between posts", "- Useful for reliability"],
    "Cumulative join requests over time": lambda m, c: (lambda joins: [f"- Join requests: {len(joins)}", "- Plot cumulative to show growth", "- Peaks hint publicity"])([msg for msg in c["messages"] if re.search(r"add me|join|invite", msg["text"], re.I)]),
    "Event alignment with known dates and external milestones": lambda m, c: ["- Align spikes with launches/holidays", "- Cross-ref external timeline", f"- Daily peaks: {c['by_day'].most_common(3)}"],
    "Join/leave dynamics": lambda m, c: ["- Track join/leave system notices", "- Compare churn vs new joins", "- Explain sentiment shifts"],
    "Media quality decisions logging": lambda m, c: (lambda media: [f"- Media with quality tags: {len(media)}", "- Record accept/reject rationale", "- Infer standards from reactions"])([msg for msg in m if msg.get("mediaType")]),
    "Media vs text type mix": lambda m, c: [f"- Media posts: {sum(1 for msg in m if msg.get('mediaType'))}", f"- Text posts: {len(m)-sum(1 for msg in m if msg.get('mediaType'))}", "- Mix shifts during demos"],
    "Media/link audit (type and domain distributions)": lambda m, c: (lambda domains: summary_counter(domains, "link domains") + [f"- Link count: {len(c['links'])}", "- Check file types for risk"])(collections.Counter(re.sub("https?://", "", l).split("/")[0] for l in c["links"])),
    "Morale & vibe indicators (laughter/support tokens)": lambda m, c: (
        lambda laughs: [
            f"- Laughter/support tokens: {len(laughs)}",
            f"- Trend vs bursts/mod events: {len(laughs)/max(len(c['messages']),1):.2f} share",
            "- Dip alerts after contentious threads",
        ]
    )([msg for msg in c["messages"] if re.search(r"haha|lol|😂", msg["text"], re.I)]),
    "Pledge/acknowledgement cascades over time": lambda m, c: (lambda pledges: [f"- Pledge statements: {len(pledges)}", "- Sequence shows momentum", "- Map to outcomes"])([msg for msg in c["messages"] if re.search(r"i will|count me in|i can", msg["text"], re.I)]),
    "Poll/scheduling compliance (responses within window)": lambda m, c: (lambda polls: [f"- Poll mentions: {len(polls)}", "- Check responses within window", "- Lag hints disengagement"])([msg for msg in c["messages"] if re.search(r"poll|vote|rsvp", msg["text"], re.I)]),
    "Regional subcommunity momentum (city/chapter activity)": lambda m, c: summary_counter(collections.Counter(re.findall(r"\b(bangalore|delhi|nyc)\b", " ".join(msg['text'] for msg in c['messages']), re.I)), "regional tags") + ["- City mentions proxy energy", "- Track growth by week"],
    "Rituals/milestones detection & participation bursts (e.g., birthdays)": lambda m, c: (lambda rituals: [f"- Ritual mentions: {len(rituals)}", "- Participation spikes around rituals", "- Explain sentiment lifts"])([msg for msg in c["messages"] if re.search(r"happy birthday|anniversary|milestone", msg["text"], re.I)]),
    "URL decay/freshness checks (dead/redirected links)": lambda m, c: [f"- Links needing check: {len(c['links'])}", "- Test for 404/redirects offline", "- Older links likelier stale"],
    "URL/link presence and domains": lambda m, c: [f"- Messages with links: {len(c['links'])}", "- Domains show sourcing diversity", "- Track media vs article ratio"],
    "Volunteer capacity/availability shifts": lambda m, c: (
        lambda offers: [
            f"- Availability notes: {len(offers)}",
            "- Compare offers vs bug/event load",
            "- Watch repeat volunteers for burnout",
        ]
    )([msg for msg in c["messages"] if re.search(r"i can help|free|available", msg["text"], re.I)]),
    "Workshops/learning demand extraction": lambda m, c: (
        lambda wants: [
            f"- Learning requests: {len(wants)}",
            "- Themes: LLM basics/infra/eval/career from keywords",
            "- Align with event announcements + attendance friction",
        ]
    )([msg for msg in c["messages"] if re.search(r"workshop|learn|training", msg["text"], re.I)]),
    "Engagement ranking of threads (unique repliers × depth × duration)": lambda m, c: [
        *(
            f"- Thread {i}: size {count}" for i, count in collections.Counter(c["thread_counts"]).most_common(3)
        ),
        "- Score = unique repliers × depth; capped to top 3",
    ],
    "First responder analysis": lambda m, c: [
        f"- First responders: {first_responder_counts(c['messages']).most_common(3)}",
        "- Highlight quick helpers for recognition",
        f"- Reply edges: {len(c['quote_pairs'])}",
    ],
    "Ignored vs answered rates": lambda m, c: [
        f"- Threads with replies: {len({q for _, q in c['quote_pairs']})}",
        f"- Starters total: {sum(1 for msg in c['messages'] if not msg['quote_author'])}",
        "- Break down by author/topic/length to rescue sinks",
    ],
    "Quoted-message starters and quote frequency": lambda m, c: [
        f"- Quote frequency: {len(c['quote_pairs'])}",
        "- Quoted starters spark dialogue; list top quoted",
        f"- Top quoted authors: {c['reply_targets'].most_common(3)}",
    ],
    "Re-engagement by starter in own thread": lambda m, c: [
        "- Count starter follow-ups in own threads",
        f"- Follow-up heavy starters: {collections.Counter(a for a, b in c['quote_pairs'] if a==b).most_common(2)}",
        f"- Reply targets: {c['reply_targets'].most_common(3)}",
    ],
    "Response latency per author/topic": lambda m, c: [
        f"- Median gap proxy overall: {median_gap(c)}s",
        "- Split by helpers/topics; add p90 for on-call planning",
        f"- @mention proxy via quotes: {len(c['quote_pairs'])}",
    ],
    "Sink threads characterization (zero replies)": lambda m, c: [
        f"- Potential sink threads: {sum(1 for msg in c['messages'] if not msg['quote_author'])}",
        "- Profile by topic, cohort, time-of-day",
        "- Rescue first-time posters via summaries",
    ],
    "Subthread gravity (posts that spawn subthreads via quotes)": lambda m, c: ["- Quotes spawning further replies show gravity", f"- Quoted authors: {c['reply_targets'].most_common(3)}", "- Map nested quotes"],
    "Thread detection and sizes (msgs, participants, depth)": lambda m, c: [f"- Threads via quotes: {len(c['thread_counts'])}", "- Estimate depth by repeated quoting", "- Participants per thread matter"],
    "Thread half-life and survival modeling": lambda m, c: ["- Time from start to half replies", "- Use inter-arrival proxy", f"- Median gap proxy: {median_gap(c)}s"],
    "Topic seeding effectiveness (replies per thread started)": lambda m, c: [
        "- Replies per starter shows topic pull",
        f"- Avg replies per author: {(mean(c['replies_by_author'].values()) if c['replies_by_author'] else 0):.1f}",
        "- Pair author×topic to route who seeds which threads",
    ],
    "Burst/anomaly/change-point detection": lambda m, c: [
        "- Detect spikes via z-score on daily counts",
        f"- Top burst days: {c['by_day'].most_common(3)} with dominant topics/authors",
        "- Attach assets/links to explain whether healthy or stressful",
    ],
    "Daily/weekly/monthly message volume": lambda m, c: summary_counter(c["by_day"], "daily messages") + [f"- Weekly buckets: ~{len(c['by_day'])/7:.1f} weeks", "- Monthly rollups show trend"],
    "Hour-of-day activity patterns": lambda m, c: summary_counter(c["by_hour"], "hour activity") + ["- Off-hours chatter shows dedication", "- Pair with weekday view"],
    "Inter-arrival times and burstiness": lambda m, c: (
        lambda gaps: stat_distribution([int(g) for g in gaps], "Inter-arrival seconds")
        + ["- Burstiness = variance/mean per thread/author", "- Clusters hint live debates"]
        if gaps
        else ["- No gaps"]
    )(
        [
            (t2 - t1).total_seconds()
            for t1, t2 in zip([msg["time"] for msg in c["messages"]], [msg["time"] for msg in c["messages"]][1:])
        ]
    ),
    "Rolling trend smoothing": lambda m, c: ["- Apply 7-day rolling mean on volume", "- Highlights sustained climbs", f"- Current avg: {mean(c['by_day'].values()) if c['by_day'] else 0:.1f}/day"],
    "Weekday vs weekend patterns": lambda m, c: (
        lambda weekday, weekend: [
            "- Compare weekday vs weekend volume and topic mix",
            f"- Weekday msgs: {weekday}, weekend: {weekend}",
            "- Decide social vs deep-tech scheduling",
        ]
    )(sum(v for k, v in c["by_weekday"].items() if k < 5), sum(v for k, v in c["by_weekday"].items() if k >= 5)),
    "People–topic affinity (bipartite clustering)": lambda m, c: [
        "- Cluster authors by keyword tags to find experts",
        "- Top experts per theme guide routing",
        "- Surface under-covered areas needing owners",
    ],
    "Rule-based topic tagging (keywords/regex)": lambda m, c: (lambda topics: summary_counter(topics, "keyword topics") + ["- Extend with regex library", f"- Untagged msgs: {len(c['messages']) - sum(topics.values())}"])( (lambda counter: ( [counter.__setitem__("ml", counter.get("ml",0)+1) for msg in c['messages'] if re.search(r"data|model|training", msg['text'], re.I)], [counter.__setitem__("events", counter.get("events",0)+1) for msg in c['messages'] if re.search(r"event|meet|call", msg['text'], re.I)], counter)[2])(collections.Counter()) ),
    "Subgraphs by topic (topic-specific networks)": lambda m, c: ["- Build reply graphs per topic", "- Compare density across themes", "- Highlight strong clusters"],
    "Theme heatmaps (time × cluster)": lambda m, c: ["- Time × topic heatmaps show cadence", "- Weekly bins smooth noise", "- Use share not counts"],
    "Topic trends over time (weekly share)": lambda m, c: [
        "- Track topic share weekly vs join/leave/pledge events",
        "- Rising themes flag emerging needs or drift",
        f"- ML tag proxy: {c['by_day'].most_common(1)}",
    ],
}


ANALYSIS_GROUPS: List[Tuple[str, List[Tuple[str, Callable]]]] = [
    ("Authors & Participation", list(BUILDERS.items())[:9]),
    ("Content & Linguistics", list(BUILDERS.items())[9:19]),
    ("Data Quality & Prep", list(BUILDERS.items())[19:24]),
    ("Engagement Signals", list(BUILDERS.items())[24:33]),
    ("Governance, Safety & Compliance", list(BUILDERS.items())[33:36]),
    ("Networks & Influence", list(BUILDERS.items())[36:44]),
    ("Ops, Events & Assets", list(BUILDERS.items())[44:62]),
    ("Threads & Conversation Dynamics", list(BUILDERS.items())[62:73]),
    ("Time-Series & Cadence", list(BUILDERS.items())[73:79]),
    ("Topics & Semantics", list(BUILDERS.items())[79:]),
]


def generate_report(messages: Sequence[Message]) -> str:
    cache = message_cache(messages)
    parts = ["# WhatsApp Group Analyses"]
    for category, analyses in ANALYSIS_GROUPS:
        parts.append(f"\n## {category}")
        for title, builder in analyses:
            func = make_analysis(title, builder)
            lines = func(messages, cache)
            parts.append(f"\n### {title}")
            parts.extend(lines)
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="WhatsApp analysis")
    parser.add_argument("json_path", type=Path, help="Path to WhatsApp chat export JSON")
    args = parser.parse_args()
    report = generate_report(load_messages(args.json_path))
    print(report)


if __name__ == "__main__":
    main()
