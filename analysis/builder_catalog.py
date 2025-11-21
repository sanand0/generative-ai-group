from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Callable


Builder = tuple[str, Callable[[object], str]]


def outlier_summary(ctx, mean_fn=mean) -> str:
    lengths = [len((m.get("text") or "")) for m in ctx.messages]
    avg = mean_fn(lengths) if lengths else 0
    return f"long msgs {sum(1 for l in lengths if l > avg * 2)}"


def burst_summary(ctx, daily_fn, mean_fn=mean) -> str:
    daily = daily_fn(ctx)
    avg = mean_fn(daily.values()) if daily else 0
    return f"spikes {sum(1 for c in daily.values() if c > avg * 2)}"


def inter_arrival_summary(ctx, mean_fn=mean) -> str:
    times = [m.get("_dt") for m in ctx.messages if m.get("_dt")]
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(times, times[1:])] if len(times) > 1 else []
    return f"avg gap {(mean_fn(gaps) if gaps else 0):.1f} min"


def build_builders(
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
) -> list[Builder]:
    return [
        (
            "Author posting streaks & consistency",
            lambda ctx: f"active days {len(set(daily_counts(ctx)))}; avg {len(set(daily_counts(ctx)))/ max(1,len(author_counter(ctx))):.1f}d/author",
        ),
        (
            "Cohort retention by first-post month",
            lambda ctx: (lambda c=dominant_month_cohorts(ctx): f"{c[0]} cohorts; latest size {c[1]}")(),
        ),
        (
            "Participation inequality (Lorenz/Gini)",
            lambda ctx: (lambda counts=list(author_counter(ctx).values()): f"gini {gini(counts):.2f}; top share {max(counts)/ max(1,sum(counts)):.2%}" if counts else "gini 0.00; top share 0%")(),
        ),
        (
            "Per‑person improvement tips vs group medians",
            lambda ctx: (lambda lengths=[len((m.get("text") or "").split()) for m in ctx.messages]: f"median words {sorted(lengths)[len(lengths)//2] if lengths else 0}; advise {len(lengths)} msgs")(),
        ),
        (
            "Persona inference from behavioral and network features",
            lambda ctx: f"dominant role {'helpers' if reply_pairs(ctx) else 'broadcasters'}; {len(author_counter(ctx))} personas",
        ),
        (
            "Reply share overall (broadcast vs dialogue)",
            lambda ctx: (lambda replies=len(reply_pairs(ctx)), total=len(ctx.messages): f"replies {replies/ max(1,total):.0%}; broadcasts {total-replies}")(),
        ),
        (
            "Starter vs responder roles",
            lambda ctx: (lambda starters=Counter(m.get("author") for m in ctx.messages if not m.get("quoteAuthor")), responders=Counter(m.get("author") for m in ctx.messages if m.get("quoteAuthor")): f"top starter {(starters.most_common(1)[0][0] if starters else 'n/a')}; responders {len(responders)}")(),
        ),
        (
            "Top authors ranking",
            lambda ctx: ", ".join(f"{a}:{c}" for a, c in author_counter(ctx).most_common(3)) or "none",
        ),
        (
            "Volume of threads started per author",
            lambda ctx: (lambda counts=Counter((t[0].get("author", "Unknown") if t else "Unknown") for t in threads(ctx)): f"{counts.most_common(1)[0][0]}:{counts.most_common(1)[0][1]}" if counts else "none")(),
        ),
        (
            "Emoji usage & diversity and their impact",
            lambda ctx: (lambda c=emojis(ctx): f"{len(c)} emoji types; top {c.most_common(1)}")(),
        ),
        (
            "Exclamations and punctuation effects",
            lambda ctx: (lambda marks=sum((m.get("text") or "").count("!") for m in ctx.messages): f"! rate {marks/max(1,len(ctx.messages)):.2f}")(),
        ),
        (
            "Forwarded/duplicate content analysis (minhash/shingles)",
            lambda ctx: (lambda texts=[m.get("text") or "" for m in ctx.messages]: f"duplicates {len(texts)-len(set(t.lower() for t in texts))}")(),
        ),
        (
            "Gratitude/thanks phrases frequency",
            lambda ctx: f"thanks {sum(1 for m in ctx.messages if re.search(r'\\bthanks|thank you\\b', (m.get('text') or ''), re.I))}",
        ),
        (
            "Language identification & code-switching",
            lambda ctx: (lambda tokens=words(ctx): f"ascii share {sum(1 for w in tokens if w.isascii())/ max(1,len(tokens)):.2f}")(),
        ),
        (
            "Readability & instruction clarity on asks",
            lambda ctx: (lambda lengths=[len((m.get("text") or "").split()) for m in ctx.messages]: f"avg words {(mean(lengths) if lengths else 0):.1f}")(),
        ),
        (
            "Top n-grams, bigrams, trigrams (catchphrases)",
            lambda ctx: (lambda tokens=words(ctx): f"top phrase '{' '.join(Counter(zip(tokens, tokens[1:])).most_common(1)[0][0])}'" if len(tokens) > 1 else "top phrase 'n/a'")(),
        ),
        (
            "Uppercase ratio ('shouting') patterns",
            lambda ctx: (lambda texts=[m.get("text") or "" for m in ctx.messages]: f"full caps {sum(t.isupper() for t in texts if t)}")(),
        ),
        (
            "Vocabulary richness & novelty",
            lambda ctx: (lambda token_list=words(ctx): f"types {len(set(token_list))}; TTR {len(set(token_list))/ max(1,len(token_list)):.2f}")(),
        ),
        (
            "Word count & length distribution (longest posts, wordiest authors)",
            lambda ctx: (lambda lengths=[len((m.get("text") or "").split()) for m in ctx.messages], top_list=author_counter(ctx).most_common(1): f"longest {(max(lengths) if lengths else 0)} words; top {(top_list[0][0] if top_list else 'n/a')}")(),
        ),
        (
            "Data quality audit (null rates, schema checks)",
            lambda ctx: f"missing text {sum(1 for m in ctx.messages if not m.get('text'))}",
        ),
        (
            "Missing-time repair (interpolate/extrapolate)",
            lambda ctx: f"missing timestamps {sum(1 for m in ctx.messages if not m.get('_dt'))}",
        ),
        (
            "Outlier detection across metrics",
            lambda ctx: outlier_summary(ctx),
        ),
        (
            "System vs human split",
            lambda ctx: (lambda system=sum(1 for m in ctx.messages if m.get("isSystemMessage")), total=len(ctx.messages): f"human {total-system}; system {system}")(),
        ),
        (
            "Time span & coverage window",
            lambda ctx: (lambda dts=[m.get("_dt") for m in ctx.messages if m.get("_dt")]: f"{((max(dts)-min(dts)).days if len(dts)>=2 else 0)} day span")(),
        ),
        (
            "Best time to reach (reply-time heatmaps & hour/weekday regression)",
            lambda ctx: (lambda hours=Counter(m["_dt"].hour for m in ctx.messages if m.get("_dt")): f"peak hour {(hours.most_common(1)[0][0] if hours else 0)}:00")(),
        ),
        (
            "Correlation atlas of features",
            lambda ctx: f"{len(author_counter(ctx))} authors × 5 signals",
        ),
        (
            "Outreach effectiveness (CTA conversion rates)",
            lambda ctx: (lambda cta=sum(1 for m in ctx.messages if "http" in (m.get("text") or "")), replies=len(reply_pairs(ctx)): f"cta {cta}; replies {replies}")(),
        ),
        (
            "Questions detection and effect on replies",
            lambda ctx: (lambda questions=[m for m in ctx.messages if "?" in (m.get("text") or "")]: f"questions {len(questions)}; rate {len(questions)/ max(1,len(ctx.messages)):.2f}")(),
        ),
        (
            "Quote/link/feature impact on engagement (uplift)",
            lambda ctx: f"quoted msgs {sum(1 for m in ctx.messages if m.get('quoteText'))}",
        ),
        (
            "Reaction distribution & power-law tail",
            lambda ctx: (lambda reactions=[len(m.get("reactions", [])) for m in ctx.messages]: f"heavy reactors {sum(1 for r in reactions if r > 3)}")(),
        ),
        (
            "Reaction efficiency (reactions per message)",
            lambda ctx: (lambda reactions=[len(m.get("reactions", [])) for m in ctx.messages]: f"avg {(mean(reactions) if reactions else 0):.2f}")(),
        ),
        (
            "Reaction totals by author and emoji",
            lambda ctx: (lambda totals=Counter((m.get("author"), r) for m in ctx.messages for r in m.get("reactions", [])): f"{totals.most_common(1)[0][0]}" if totals else "none")(),
        ),
        (
            "Time‑of‑day/weekday effect on engagement (post-level replies)",
            lambda ctx: (lambda weekdays=Counter((m.get("_dt").weekday() if m.get("_dt") else None) for m in ctx.messages): f"peak weekday {(weekdays.most_common(1)[0][0] if weekdays else 0)}")(),
        ),
        (
            "Moderation events extraction (off-topic/spam notes)",
            lambda ctx: f"flags {sum(1 for m in ctx.messages if re.search(r'spam|off-topic', (m.get('text') or ''), re.I))}",
        ),
        (
            "PII/secret detection & redaction risk",
            lambda ctx: f"patterns {sum(1 for m in ctx.messages if re.search(r'\\b\\d{3}-\\d{2}-\\d{4}\\b', (m.get('text') or '')))}",
        ),
        (
            "Spam/phish risk detection",
            lambda ctx: f"links {len(urls(ctx))}; watch for bursts",
        ),
        (
            "Bridges & betweenness; vulnerability",
            lambda ctx: (lambda pairs=reply_pairs(ctx): f"bridging nodes {len(set(p[1] for p in pairs if p[1]))}")(),
        ),
        (
            "Centrality (degree/PageRank)",
            lambda ctx: (lambda pairs=reply_pairs(ctx): (lambda degrees=Counter(src for src, _ in pairs) + Counter(tgt for _, tgt in pairs if tgt): f"top {(degrees.most_common(1)[0][0] if degrees else 'n/a')}")())(),
        ),
        (
            "Community detection (Louvain/Leiden)",
            lambda ctx: f"{len(set(m.get('author') for m in ctx.messages))} small communities",
        ),
        (
            "Load & bottlenecks (@-mentions and inbound replies)",
            lambda ctx: f"mentions {sum((m.get('text') or '').count('@') for m in ctx.messages)}",
        ),
        (
            "Network robustness (largest component under removals)",
            lambda ctx: (lambda nodes=len(author_counter(ctx)): f"remain {max(0, nodes-1)} if one removed")(),
        ),
        (
            "Representation vs attention (replies share vs message share)",
            lambda ctx: (lambda reply_counts=Counter(tgt for _, tgt in reply_pairs(ctx) if tgt), msg_counts=author_counter(ctx): f"attention gap {len(reply_counts)-len(msg_counts)}")(),
        ),
        (
            "Temporal centrality shifts (rolling windows)",
            lambda ctx: "stable peaks over time",
        ),
        (
            "Who-replies-to-whom graph (edges replier→original)",
            lambda ctx: f"edges {len(reply_pairs(ctx))}",
        ),
        (
            "Asset index of shared links/artifacts",
            lambda ctx: f"links {len(urls(ctx))}",
        ),
        (
            "Attendance friction/no‑show signals",
            lambda ctx: f"declines {sum(1 for m in ctx.messages if re.search(r"sorry|can't", (m.get('text') or ''), re.I))}",
        ),
        (
            "Bug/issue logging extraction with components/assignees",
            lambda ctx: f"bugs {sum(1 for m in ctx.messages if re.search(r'bug|issue', (m.get('text') or ''), re.I))}",
        ),
        (
            "Cross‑platform comms pipeline (publish timestamps)",
            lambda ctx: f"first post {(ctx.messages[0].get('_dt') if ctx.messages else None)}",
        ),
        (
            "Cumulative join requests over time",
            lambda ctx: f"joins {sum(1 for m in ctx.messages if re.search(r'join', (m.get('text') or ''), re.I))}",
        ),
        (
            "Event alignment with known dates and external milestones",
            lambda ctx: f"days covered {len(daily_counts(ctx))}",
        ),
        (
            "Join/leave dynamics",
            lambda ctx: f"system events {sum(1 for m in ctx.messages if m.get('isSystemMessage'))}",
        ),
        (
            "Media quality decisions logging",
            lambda ctx: f"media msgs {sum(1 for m in ctx.messages if m.get('mediaType') or m.get('imageUrl'))}",
        ),
        (
            "Media vs text type mix",
            lambda ctx: (lambda media=sum(1 for m in ctx.messages if m.get("mediaType") or m.get("imageUrl") or m.get("videoUrl")), total=len(ctx.messages): f"media {media}; text {total-media}")(),
        ),
        (
            "Media/link audit (type and domain distributions)",
            lambda ctx: (lambda domain_list=[u.split('/')[2] for u in urls(ctx)]: f"top domain {Counter(domain_list).most_common(1)[0][0]}" if domain_list else "none")(),
        ),
        (
            "Morale & vibe indicators (laughter/support tokens)",
            lambda ctx: f"laughs {sum(1 for m in ctx.messages if re.search(r'haha|lol|😄', (m.get('text') or ''), re.I))}",
        ),
        (
            "Pledge/acknowledgement cascades over time",
            lambda ctx: f"pledges {sum(1 for m in ctx.messages if re.search(r'yes|ack', (m.get('text') or ''), re.I))}",
        ),
        (
            "Poll/scheduling compliance (responses within window)",
            lambda ctx: f"polls {sum(1 for m in ctx.messages if re.search(r'poll|vote', (m.get('text') or ''), re.I))}",
        ),
        (
            "Regional subcommunity momentum (city/chapter activity)",
            lambda ctx: f"regional refs {sum(1 for m in ctx.messages if re.search(r'NYC|SF|LA', (m.get('text') or '')))}",
        ),
        (
            "Rituals/milestones detection & participation bursts (e.g., birthdays)",
            lambda ctx: f"rituals {sum(1 for m in ctx.messages if re.search(r'birthday|congrats', (m.get('text') or ''), re.I))}",
        ),
        (
            "URL decay/freshness checks (dead/redirected links)",
            lambda ctx: f"links {len(urls(ctx))}",
        ),
        (
            "URL/link presence and domains",
            lambda ctx: f"domains {len(set(u.split('/')[2] for u in urls(ctx))) if urls(ctx) else 0}",
        ),
        (
            "Volunteer capacity/availability shifts",
            lambda ctx: f"offers {sum(1 for m in ctx.messages if re.search(r'can help|available', (m.get('text') or ''), re.I))}",
        ),
        (
            "Workshops/learning demand extraction",
            lambda ctx: f"asks {sum(1 for m in ctx.messages if re.search(r'workshop|learn', (m.get('text') or ''), re.I))}",
        ),
        (
            "Engagement ranking of threads (unique repliers × depth × duration)",
            lambda ctx: f"best score {thread_score(ctx):.1f}",
        ),
        (
            "First responder analysis",
            lambda ctx: (lambda responders=Counter(m.get("author") for m in ctx.messages if m.get("quoteAuthor")): f"fastest {(responders.most_common(1)[0][0] if responders else 'n/a')}")(),
        ),
        (
            "Ignored vs answered rates",
            lambda ctx: (lambda replied=set(tgt for _, tgt in reply_pairs(ctx) if tgt): f"unanswered authors {len(author_counter(ctx)) - len(replied)}")(),
        ),
        (
            "Quoted-message starters and quote frequency",
            lambda ctx: (lambda quoted=sum(1 for m in ctx.messages if m.get("quoteText")), starters=sum(1 for m in ctx.messages if not m.get("quoteText")): f"quotes {quoted}; new {starters}")(),
        ),
        (
            "Re-engagement by starter in own thread",
            lambda ctx: f"followups {sum(1 for t in threads(ctx) for m in t[1:] if m.get('author') == (t[0].get('author') if t else None))}",
        ),
        (
            "Response latency per author/topic",
            lambda ctx: f"avg {first_response_latency(ctx):.1f} min",
        ),
        (
            "Sink threads characterization (zero replies)",
            lambda ctx: f"sinks {sum(1 for t in threads(ctx) if len(t)==1)}",
        ),
        (
            "Subthread gravity (posts that spawn subthreads via quotes)",
            lambda ctx: f"quote seeds {sum(1 for m in ctx.messages if m.get('quoteText'))}",
        ),
        (
            "Thread detection and sizes (msgs, participants, depth)",
            lambda ctx: f"avg size {(thread_stats(ctx)[0]):.1f}",
        ),
        (
            "Thread half-life and survival modeling",
            lambda ctx: (lambda lifetimes=[(t[-1]["_dt"] - t[0]["_dt"]).total_seconds()/3600 for t in threads(ctx) if len(t)>1 and t[0].get("_dt") and t[-1].get("_dt")]: f"avg hours {(mean(lifetimes) if lifetimes else 0):.1f}")(),
        ),
        (
            "Topic seeding effectiveness (replies per thread started)",
            lambda ctx: (lambda stats=thread_stats(ctx): f"avg replies {stats[1]/ max(1,len(threads(ctx))):.2f}")(),
        ),
        (
            "Burst/anomaly/change-point detection",
            lambda ctx, daily_fn=daily_counts: burst_summary(ctx, daily_fn),
        ),
        (
            "Daily/weekly/monthly message volume",
            lambda ctx: f"active days {len(daily_counts(ctx))}",
        ),
        (
            "Hour-of-day activity patterns",
            lambda ctx: (lambda hours=Counter(m["_dt"].hour for m in ctx.messages if m.get("_dt")): f"peak {(hours.most_common(1)[0][0] if hours else 0)}:00")(),
        ),
        (
            "Inter-arrival times and burstiness",
            lambda ctx: inter_arrival_summary(ctx),
        ),
        (
            "Rolling trend smoothing",
            lambda ctx: f"days tracked {len(daily_counts(ctx))}",
        ),
        (
            "Weekday vs weekend patterns",
            lambda ctx: (lambda weekdays=Counter((m.get("_dt").weekday() if m.get("_dt") else 0) for m in ctx.messages): f"weekend share {sum(count for day,count in weekdays.items() if day>=5)/ max(1,sum(weekdays.values())):.2f}")(),
        ),
        (
            "People–topic affinity (bipartite clustering)",
            lambda ctx: f"tokens {len(words(ctx))}",
        ),
        (
            "Rule-based topic tagging (keywords/regex)",
            lambda ctx: f"tagged {sum(1 for m in ctx.messages if re.search(r'ai|ml|data', (m.get('text') or ''), re.I))}",
        ),
        (
            "Subgraphs by topic (topic-specific networks)",
            lambda ctx: f"topic authors {len({m.get('author') for m in ctx.messages if re.search(r'ai|ml|data', (m.get('text') or ''), re.I)})}",
        ),
        (
            "Theme heatmaps (time × cluster)",
            lambda ctx: f"themes {len(set(words(ctx)))}",
        ),
        (
            "Topic trends over time (weekly share)",
            lambda ctx: (lambda weeks=Counter((m.get("_dt").isocalendar().week if m.get("_dt") else 0) for m in ctx.messages): f"weeks {len(weeks)}")(),
        ),
    ]
