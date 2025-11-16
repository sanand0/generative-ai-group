#!/usr/bin/env python3
"""
Investigative Data Journalism: Uncovering Hidden Patterns in Generative AI Discussions
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
import statistics

# Load data
def load_data():
    with open("gen-ai-messages.json", "r") as f:
        messages = json.load(f)

    # Filter valid messages
    valid = []
    for m in messages:
        if m.get("time") and m.get("text") and m.get("author"):
            valid.append(m)

    return valid

def parse_time(time_str):
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

def analyze_participation_patterns(messages):
    """Find who talks vs who gets heard"""
    print("\n" + "="*80)
    print("ANALYSIS 1: THE PARADOX OF INFLUENCE")
    print("="*80)

    # Count messages per author
    msg_count = Counter(m["author"] for m in messages)

    # Count replies received (being quoted)
    replies_received = Counter()
    for m in messages:
        if m.get("quoteAuthor"):
            replies_received[m["quoteAuthor"]] += 1

    # Count reactions received
    reactions_received = Counter()
    for m in messages:
        if m.get("reactions"):
            reactions_received[m["author"]] += len(m["reactions"])

    # Calculate influence ratio (replies per message)
    influence_ratio = {}
    for author, count in msg_count.items():
        if count >= 10:  # At least 10 messages
            replies = replies_received.get(author, 0)
            influence_ratio[author] = replies / count

    # Top talkers
    print("\nTOP 10 BY MESSAGE COUNT:")
    for author, count in msg_count.most_common(10):
        replies = replies_received.get(author, 0)
        ratio = replies / count if count > 0 else 0
        print(f"  {author}: {count} msgs, {replies} replies, ratio={ratio:.2f}")

    # Top by influence ratio (min 20 messages)
    print("\nTOP 10 BY INFLUENCE RATIO (min 20 msgs):")
    qualified = {a: r for a, r in influence_ratio.items() if msg_count[a] >= 20}
    for author, ratio in sorted(qualified.items(), key=lambda x: -x[1])[:10]:
        print(f"  {author}: ratio={ratio:.2f}, {msg_count[author]} msgs, {replies_received[author]} replies")

    # SURPRISING FINDING: Low message count, high influence
    print("\nSURPRISING: HIGH INFLUENCE WITH FEW MESSAGES (10-50 msgs, ratio > 0.5):")
    surprising = {a: r for a, r in influence_ratio.items()
                  if 10 <= msg_count[a] <= 50 and r > 0.5}
    for author, ratio in sorted(surprising.items(), key=lambda x: -x[1])[:10]:
        print(f"  {author}: {msg_count[author]} msgs, {replies_received[author]} replies, ratio={ratio:.2f}")

    return msg_count, replies_received, reactions_received, influence_ratio

def analyze_temporal_patterns(messages):
    """When does the AI community actually engage?"""
    print("\n" + "="*80)
    print("ANALYSIS 2: THE RHYTHM OF AI DISCOURSE")
    print("="*80)

    # Hour of day analysis (UTC)
    hour_counts = Counter()
    day_counts = Counter()

    for m in messages:
        dt = parse_time(m["time"])
        hour_counts[dt.hour] += 1
        day_counts[dt.strftime("%A")] += 1

    print("\nMESSAGES BY HOUR (UTC):")
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        bar = "█" * (count // 50)
        print(f"  {hour:02d}:00  {count:4d}  {bar}")

    print("\nMESSAGES BY DAY OF WEEK:")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in day_order:
        count = day_counts.get(day, 0)
        print(f"  {day:10s}: {count:4d}")

    # Weekly trends - is engagement increasing or decreasing?
    weekly = defaultdict(int)
    for m in messages:
        dt = parse_time(m["time"])
        week_key = dt.strftime("%Y-W%U")
        weekly[week_key] += 1

    weeks = sorted(weekly.keys())
    print(f"\nWEEKLY ENGAGEMENT TREND ({len(weeks)} weeks):")
    values = [weekly[w] for w in weeks]

    # First half vs second half
    mid = len(values) // 2
    first_half = statistics.mean(values[:mid])
    second_half = statistics.mean(values[mid:])

    print(f"  First half avg: {first_half:.1f} msgs/week")
    print(f"  Second half avg: {second_half:.1f} msgs/week")
    print(f"  Change: {((second_half/first_half - 1) * 100):+.1f}%")

    # Peak week
    peak_week = max(weekly.items(), key=lambda x: x[1])
    print(f"  Peak week: {peak_week[0]} with {peak_week[1]} messages")

    return hour_counts, day_counts, weekly

def analyze_conversation_depth(messages):
    """How deep do conversations go? What triggers depth?"""
    print("\n" + "="*80)
    print("ANALYSIS 3: CONVERSATION THREADING PATTERNS")
    print("="*80)

    # Build thread structure
    msg_by_id = {m["messageId"]: m for m in messages}
    children = defaultdict(list)

    for m in messages:
        if m.get("quoteMessageId"):
            children[m["quoteMessageId"]].append(m)

    # Find root messages (not replies)
    roots = [m for m in messages if not m.get("quoteMessageId")]

    # Calculate thread depth
    def get_thread_size(msg_id, visited=None):
        if visited is None:
            visited = set()
        if msg_id in visited:
            return 0
        visited.add(msg_id)
        count = 1
        for child in children.get(msg_id, []):
            count += get_thread_size(child["messageId"], visited)
        return count

    thread_sizes = []
    for root in roots:
        size = get_thread_size(root["messageId"])
        thread_sizes.append((root, size))

    # Analyze thread sizes
    sizes = [s[1] for s in thread_sizes]
    print(f"\nTOTAL THREADS: {len(roots)}")
    print(f"  Single message (no replies): {sizes.count(1)} ({100*sizes.count(1)/len(sizes):.1f}%)")
    print(f"  2-5 messages: {sum(1 for s in sizes if 2 <= s <= 5)}")
    print(f"  6-10 messages: {sum(1 for s in sizes if 6 <= s <= 10)}")
    print(f"  10+ messages: {sum(1 for s in sizes if s > 10)}")

    if sizes:
        print(f"  Median thread size: {statistics.median(sizes):.1f}")
        print(f"  Mean thread size: {statistics.mean(sizes):.2f}")

    # Top threads
    print("\nLARGEST THREADS:")
    for root, size in sorted(thread_sizes, key=lambda x: -x[1])[:5]:
        text_preview = root["text"][:100].replace("\n", " ")
        print(f"  Size {size}: [{root['author']}] {text_preview}...")

    # What makes a thread take off?
    large_threads = [t for t in thread_sizes if t[1] >= 5]
    small_threads = [t for t in thread_sizes if t[1] == 1]

    # Word count analysis
    large_word_counts = [len(t[0]["text"].split()) for t in large_threads]
    small_word_counts = [len(t[0]["text"].split()) for t in small_threads]

    print(f"\nWORD COUNT IN INITIAL MESSAGE:")
    print(f"  Large threads (5+): avg {statistics.mean(large_word_counts):.1f} words")
    print(f"  Single messages: avg {statistics.mean(small_word_counts):.1f} words")

    # Question marks
    large_questions = sum(1 for t in large_threads if "?" in t[0]["text"])
    small_questions = sum(1 for t in small_threads if "?" in t[0]["text"])

    print(f"\nQUESTIONS (contains '?'):")
    print(f"  Large threads: {100*large_questions/len(large_threads):.1f}%")
    print(f"  Single messages: {100*small_questions/len(small_threads):.1f}%")

    return thread_sizes, children

def analyze_topic_evolution(messages):
    """How have topics shifted over time?"""
    print("\n" + "="*80)
    print("ANALYSIS 4: TOPIC EVOLUTION")
    print("="*80)

    # Key terms to track
    key_terms = {
        "openai": r"\bopenai\b",
        "claude": r"\bclaude\b",
        "gpt": r"\bgpt[- ]?\d*\b",
        "llama": r"\bllama\b",
        "gemini": r"\bgemini\b",
        "mistral": r"\bmistral\b",
        "rag": r"\brag\b",
        "agent": r"\bagent\b",
        "fine-tune": r"\bfine[- ]?tun",
        "embedding": r"\bembedding",
        "vector": r"\bvector\b",
        "prompt": r"\bprompt",
        "context": r"\bcontext\b",
        "token": r"\btoken",
        "reasoning": r"\breason",
        "multimodal": r"\bmultimodal\b",
        "vision": r"\bvision\b",
        "code": r"\bcode\b|\bcoding\b",
        "cost": r"\bcost\b|\bpric|\bexpensive\b|\bcheap\b",
        "open-source": r"\bopen[- ]?source\b|\boss\b",
    }

    # Monthly tracking
    monthly_terms = defaultdict(lambda: defaultdict(int))
    monthly_total = defaultdict(int)

    for m in messages:
        dt = parse_time(m["time"])
        month_key = dt.strftime("%Y-%m")
        monthly_total[month_key] += 1

        text_lower = m["text"].lower()
        for term, pattern in key_terms.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                monthly_terms[month_key][term] += 1

    months = sorted(monthly_total.keys())

    # Calculate term frequencies
    print("\nTERM FREQUENCY BY MONTH:")
    print("Month      ", end="")
    select_terms = ["gpt", "claude", "llama", "gemini", "agent", "rag", "reasoning"]
    for term in select_terms:
        print(f"{term:>10}", end="")
    print()

    for month in months:
        total = monthly_total[month]
        print(f"{month}  ", end="")
        for term in select_terms:
            count = monthly_terms[month][term]
            pct = 100 * count / total if total > 0 else 0
            print(f"{pct:9.1f}%", end="")
        print()

    # Rising and falling terms
    print("\nTRENDING ANALYSIS (comparing first 3 vs last 3 months):")
    if len(months) >= 6:
        first_months = months[:3]
        last_months = months[-3:]

        first_total = sum(monthly_total[m] for m in first_months)
        last_total = sum(monthly_total[m] for m in last_months)

        term_changes = {}
        for term in key_terms:
            first_count = sum(monthly_terms[m][term] for m in first_months)
            last_count = sum(monthly_terms[m][term] for m in last_months)

            first_pct = first_count / first_total if first_total > 0 else 0
            last_pct = last_count / last_total if last_total > 0 else 0

            if first_pct > 0:
                change = (last_pct - first_pct) / first_pct
            else:
                change = float('inf') if last_pct > 0 else 0

            term_changes[term] = (first_pct, last_pct, change)

        # Rising terms
        print("\n  RISING TERMS:")
        rising = sorted(term_changes.items(), key=lambda x: -x[1][2])[:5]
        for term, (first, last, change) in rising:
            if change != float('inf'):
                print(f"    {term}: {first*100:.1f}% → {last*100:.1f}% ({change*100:+.0f}%)")
            else:
                print(f"    {term}: {first*100:.1f}% → {last*100:.1f}% (NEW)")

        # Falling terms
        print("\n  FALLING TERMS:")
        falling = sorted(term_changes.items(), key=lambda x: x[1][2])[:5]
        for term, (first, last, change) in falling:
            print(f"    {term}: {first*100:.1f}% → {last*100:.1f}% ({change*100:+.0f}%)")

    return monthly_terms, monthly_total

def analyze_network_effects(messages):
    """Who actually influences whom?"""
    print("\n" + "="*80)
    print("ANALYSIS 5: SOCIAL NETWORK DYNAMICS")
    print("="*80)

    # Build reply network
    reply_pairs = Counter()
    for m in messages:
        if m.get("quoteAuthor") and m.get("author"):
            pair = (m["author"], m["quoteAuthor"])  # A replies to B
            reply_pairs[pair] += 1

    # Top interaction pairs
    print("\nTOP 10 INTERACTION PAIRS (A → B means A replies to B):")
    for (a, b), count in reply_pairs.most_common(10):
        print(f"  {a} → {b}: {count} replies")

    # Reciprocity analysis
    reciprocal = 0
    one_way = 0
    for (a, b), count in reply_pairs.items():
        if (b, a) in reply_pairs:
            reciprocal += 1
        else:
            one_way += 1

    print(f"\nRECIPROCITY:")
    print(f"  Reciprocal pairs: {reciprocal // 2}")  # Divide by 2 because counted twice
    print(f"  One-way interactions: {one_way}")
    print(f"  Reciprocity rate: {100 * reciprocal / (reciprocal + one_way):.1f}%")

    # Hub analysis - who bridges conversations?
    in_degree = Counter()  # People who get replied to
    out_degree = Counter()  # People who reply to others

    for (a, b), count in reply_pairs.items():
        out_degree[a] += count
        in_degree[b] += count

    # Bridge score = sqrt(in_degree * out_degree)
    bridge_scores = {}
    all_people = set(in_degree.keys()) | set(out_degree.keys())
    for person in all_people:
        bridge_scores[person] = (in_degree[person] * out_degree[person]) ** 0.5

    print("\nBRIDGE CONNECTORS (high in-degree AND out-degree):")
    for person, score in sorted(bridge_scores.items(), key=lambda x: -x[1])[:10]:
        print(f"  {person}: score={score:.1f}, in={in_degree[person]}, out={out_degree[person]}")

    # Lurkers who suddenly become active
    return reply_pairs, in_degree, out_degree, bridge_scores

def analyze_reaction_patterns(messages):
    """What content gets reactions? Are reactions meaningful?"""
    print("\n" + "="*80)
    print("ANALYSIS 6: THE ECONOMY OF ATTENTION (REACTIONS)")
    print("="*80)

    reacted = [m for m in messages if m.get("reactions")]
    not_reacted = [m for m in messages if not m.get("reactions")]

    print(f"\nBASIC STATS:")
    print(f"  Messages with reactions: {len(reacted)} ({100*len(reacted)/len(messages):.1f}%)")
    print(f"  Messages without reactions: {len(not_reacted)} ({100*len(not_reacted)/len(messages):.1f}%)")

    # Reaction emoji distribution
    emoji_counts = Counter()
    for m in reacted:
        for char in m["reactions"]:
            if ord(char) > 127:  # Non-ASCII (emoji)
                emoji_counts[char] += 1

    print("\nTOP REACTION EMOJIS:")
    for emoji, count in emoji_counts.most_common(10):
        print(f"  {emoji}: {count}")

    # What gets reactions?
    # Length analysis
    reacted_lengths = [len(m["text"]) for m in reacted]
    not_reacted_lengths = [len(m["text"]) for m in not_reacted]

    print(f"\nMESSAGE LENGTH:")
    print(f"  Reacted messages avg: {statistics.mean(reacted_lengths):.0f} chars")
    print(f"  Non-reacted messages avg: {statistics.mean(not_reacted_lengths):.0f} chars")

    # Links
    reacted_links = sum(1 for m in reacted if "http" in m["text"])
    not_reacted_links = sum(1 for m in not_reacted if "http" in m["text"])

    print(f"\nCONTAINS LINKS:")
    print(f"  Reacted: {100*reacted_links/len(reacted):.1f}%")
    print(f"  Non-reacted: {100*not_reacted_links/len(not_reacted):.1f}%")

    # Questions
    reacted_questions = sum(1 for m in reacted if "?" in m["text"])
    not_reacted_questions = sum(1 for m in not_reacted if "?" in m["text"])

    print(f"\nCONTAINS QUESTIONS:")
    print(f"  Reacted: {100*reacted_questions/len(reacted):.1f}%")
    print(f"  Non-reacted: {100*not_reacted_questions/len(not_reacted):.1f}%")

    # Top reacted messages
    print("\nMOST REACTED MESSAGES:")
    multi_reacted = [(m, len(m["reactions"])) for m in reacted if len(m.get("reactions", "")) > 3]
    for m, count in sorted(multi_reacted, key=lambda x: -x[1])[:5]:
        preview = m["text"][:80].replace("\n", " ")
        print(f"  [{count} reactions] [{m['author']}] {preview}...")

    return emoji_counts, reacted, not_reacted

def analyze_content_patterns(messages):
    """What linguistic patterns emerge?"""
    print("\n" + "="*80)
    print("ANALYSIS 7: LINGUISTIC PATTERNS")
    print("="*80)

    # Message length distribution
    lengths = [len(m["text"]) for m in messages]

    print(f"\nMESSAGE LENGTH DISTRIBUTION:")
    print(f"  Min: {min(lengths)} chars")
    print(f"  Max: {max(lengths)} chars")
    print(f"  Median: {statistics.median(lengths):.0f} chars")
    print(f"  Mean: {statistics.mean(lengths):.0f} chars")

    # Short vs long messages
    short = sum(1 for l in lengths if l < 50)
    medium = sum(1 for l in lengths if 50 <= l < 200)
    long_msg = sum(1 for l in lengths if l >= 200)

    print(f"\n  Short (<50 chars): {short} ({100*short/len(lengths):.1f}%)")
    print(f"  Medium (50-200): {medium} ({100*medium/len(lengths):.1f}%)")
    print(f"  Long (200+): {long_msg} ({100*long_msg/len(lengths):.1f}%)")

    # Common phrases
    print("\nCOMMON TECHNICAL PHRASES:")
    phrases = {
        "i think": r"\bi think\b",
        "i believe": r"\bi believe\b",
        "in my experience": r"\bin my experience\b",
        "has anyone": r"\bhas anyone\b",
        "does anyone": r"\bdoes anyone\b",
        "anyone know": r"\banyone know\b",
        "check this": r"\bcheck this\b",
        "thanks": r"\bthanks\b|\bthank you\b",
        "agree": r"\bagree\b",
        "disagree": r"\bdisagree\b",
    }

    for phrase, pattern in phrases.items():
        count = sum(1 for m in messages if re.search(pattern, m["text"], re.IGNORECASE))
        print(f"  '{phrase}': {count} ({100*count/len(messages):.2f}%)")

    # Sentiment indicators
    print("\nSENTIMENT INDICATORS:")
    sentiment_patterns = {
        "positive": r"\b(great|awesome|amazing|excellent|love|fantastic|brilliant)\b",
        "negative": r"\b(bad|terrible|awful|hate|worst|disappointing|poor)\b",
        "uncertain": r"\b(maybe|perhaps|possibly|might|not sure|unclear)\b",
        "confident": r"\b(definitely|certainly|absolutely|clearly|obviously)\b",
    }

    for sentiment, pattern in sentiment_patterns.items():
        count = sum(1 for m in messages if re.search(pattern, m["text"], re.IGNORECASE))
        print(f"  {sentiment}: {count} ({100*count/len(messages):.2f}%)")

    return lengths

def find_surprising_insights(messages, msg_count, replies_received, influence_ratio):
    """Hunt for the unexpected"""
    print("\n" + "="*80)
    print("SURPRISING FINDINGS - THE REAL STORY")
    print("="*80)

    # 1. Silent influencers - low message count but high impact
    print("\n1. SILENT INFLUENCERS (10-30 msgs, but >40% reply rate):")
    silent_influencers = []
    for author, ratio in influence_ratio.items():
        if 10 <= msg_count[author] <= 30 and ratio > 0.4:
            silent_influencers.append((author, msg_count[author], replies_received[author], ratio))

    for author, msgs, replies, ratio in sorted(silent_influencers, key=lambda x: -x[3])[:10]:
        print(f"  {author}: {msgs} msgs → {replies} replies ({ratio:.0%} impact)")

    # 2. Prolific but ignored
    print("\n2. PROLIFIC BUT IGNORED (100+ msgs, <10% reply rate):")
    prolific_ignored = []
    for author, count in msg_count.items():
        if count >= 100:
            ratio = replies_received.get(author, 0) / count
            if ratio < 0.1:
                prolific_ignored.append((author, count, replies_received.get(author, 0), ratio))

    for author, msgs, replies, ratio in sorted(prolific_ignored, key=lambda x: -x[1])[:10]:
        print(f"  {author}: {msgs} msgs → {replies} replies ({ratio:.0%} impact)")

    # 3. Late night vs early morning activity
    print("\n3. NIGHT OWL VS EARLY BIRD ENGAGEMENT:")
    night_msgs = []  # 0-5 UTC
    morning_msgs = []  # 6-11 UTC
    afternoon_msgs = []  # 12-17 UTC
    evening_msgs = []  # 18-23 UTC

    for m in messages:
        dt = parse_time(m["time"])
        hour = dt.hour
        if 0 <= hour < 6:
            night_msgs.append(m)
        elif 6 <= hour < 12:
            morning_msgs.append(m)
        elif 12 <= hour < 18:
            afternoon_msgs.append(m)
        else:
            evening_msgs.append(m)

    def calc_engagement(msgs):
        if not msgs:
            return 0, 0
        reacted = sum(1 for m in msgs if m.get("reactions"))
        replied = sum(1 for m in msgs if m.get("quoteMessageId"))
        return 100*reacted/len(msgs), 100*replied/len(msgs)

    night_react, night_reply = calc_engagement(night_msgs)
    morning_react, morning_reply = calc_engagement(morning_msgs)
    afternoon_react, afternoon_reply = calc_engagement(afternoon_msgs)
    evening_react, evening_reply = calc_engagement(evening_msgs)

    print(f"  Night (0-5 UTC): {len(night_msgs)} msgs, {night_react:.1f}% reacted, {night_reply:.1f}% are replies")
    print(f"  Morning (6-11 UTC): {len(morning_msgs)} msgs, {morning_react:.1f}% reacted, {morning_reply:.1f}% are replies")
    print(f"  Afternoon (12-17 UTC): {len(afternoon_msgs)} msgs, {afternoon_react:.1f}% reacted, {afternoon_reply:.1f}% are replies")
    print(f"  Evening (18-23 UTC): {len(evening_msgs)} msgs, {evening_react:.1f}% reacted, {evening_reply:.1f}% are replies")

    # 4. First movers vs followers
    print("\n4. FIRST MOVERS VS FOLLOWERS:")
    root_msgs = [m for m in messages if not m.get("quoteMessageId")]
    reply_msgs = [m for m in messages if m.get("quoteMessageId")]

    root_authors = Counter(m["author"] for m in root_msgs)
    reply_authors = Counter(m["author"] for m in reply_msgs)

    # People who start more than they follow
    print("  CONVERSATION STARTERS (ratio of root to total):")
    starter_ratio = {}
    for author in set(root_authors.keys()) | set(reply_authors.keys()):
        total = root_authors[author] + reply_authors[author]
        if total >= 20:
            starter_ratio[author] = root_authors[author] / total

    for author, ratio in sorted(starter_ratio.items(), key=lambda x: -x[1])[:10]:
        print(f"    {author}: {ratio:.0%} starter ({root_authors[author]} roots, {reply_authors[author]} replies)")

    print("  RESPONDERS (mostly reply, rarely start):")
    for author, ratio in sorted(starter_ratio.items(), key=lambda x: x[1])[:10]:
        print(f"    {author}: {ratio:.0%} starter ({root_authors[author]} roots, {reply_authors[author]} replies)")

    # 5. Weekend warriors
    print("\n5. WEEKEND WARRIORS vs WEEKDAY WORKERS:")
    weekend_msgs = [m for m in messages if parse_time(m["time"]).strftime("%A") in ["Saturday", "Sunday"]]
    weekday_msgs = [m for m in messages if parse_time(m["time"]).strftime("%A") not in ["Saturday", "Sunday"]]

    weekend_authors = Counter(m["author"] for m in weekend_msgs)
    weekday_authors = Counter(m["author"] for m in weekday_msgs)

    weekend_ratio = {}
    for author in msg_count:
        if msg_count[author] >= 20:
            weekend_pct = weekend_authors[author] / msg_count[author]
            weekend_ratio[author] = weekend_pct

    print("  WEEKEND HEAVY (>40% of messages on weekends):")
    for author, ratio in sorted(weekend_ratio.items(), key=lambda x: -x[1])[:5]:
        print(f"    {author}: {ratio:.0%} weekend ({weekend_authors[author]}/{msg_count[author]})")

    print("  WEEKDAY ONLY (<10% on weekends):")
    for author, ratio in sorted(weekend_ratio.items(), key=lambda x: x[1])[:5]:
        print(f"    {author}: {ratio:.0%} weekend ({weekend_authors[author]}/{msg_count[author]})")

    return silent_influencers

def export_data_for_visualization(messages, msg_count, replies_received, influence_ratio,
                                   hour_counts, day_counts, weekly, monthly_terms, monthly_total,
                                   thread_sizes, reply_pairs, bridge_scores):
    """Export processed data as JSON for web visualization"""
    print("\n" + "="*80)
    print("EXPORTING DATA FOR VISUALIZATION")
    print("="*80)

    export = {
        "metadata": {
            "total_messages": len(messages),
            "total_authors": len(set(m["author"] for m in messages)),
            "date_range": {
                "start": min(m["time"] for m in messages),
                "end": max(m["time"] for m in messages)
            }
        },
        "participation": {
            "top_by_count": [
                {"author": a, "count": c, "replies": replies_received.get(a, 0),
                 "ratio": replies_received.get(a, 0) / c}
                for a, c in msg_count.most_common(50)
            ],
            "top_by_influence": sorted(
                [{"author": a, "ratio": r, "count": msg_count[a], "replies": replies_received[a]}
                 for a, r in influence_ratio.items() if msg_count[a] >= 20],
                key=lambda x: -x["ratio"]
            )[:50],
            "silent_influencers": sorted(
                [{"author": a, "count": msg_count[a], "replies": replies_received[a],
                  "ratio": replies_received[a]/msg_count[a]}
                 for a in influence_ratio if 10 <= msg_count[a] <= 50 and influence_ratio[a] > 0.4],
                key=lambda x: -x["ratio"]
            )
        },
        "temporal": {
            "by_hour": [{"hour": h, "count": hour_counts.get(h, 0)} for h in range(24)],
            "by_day": [
                {"day": d, "count": day_counts.get(d, 0)}
                for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            ],
            "by_week": [
                {"week": w, "count": c}
                for w, c in sorted(weekly.items())
            ]
        },
        "topics": {
            "by_month": [
                {
                    "month": m,
                    "total": monthly_total[m],
                    "terms": dict(monthly_terms[m])
                }
                for m in sorted(monthly_total.keys())
            ]
        },
        "threads": {
            "size_distribution": {
                "single": sum(1 for _, s in thread_sizes if s == 1),
                "small": sum(1 for _, s in thread_sizes if 2 <= s <= 5),
                "medium": sum(1 for _, s in thread_sizes if 6 <= s <= 10),
                "large": sum(1 for _, s in thread_sizes if s > 10)
            },
            "top_threads": [
                {
                    "size": s,
                    "author": t["author"],
                    "text": t["text"][:200],
                    "time": t["time"]
                }
                for t, s in sorted(thread_sizes, key=lambda x: -x[1])[:20]
            ]
        },
        "network": {
            "top_interactions": [
                {"from": a, "to": b, "count": c}
                for (a, b), c in reply_pairs.most_common(50)
            ],
            "bridge_connectors": sorted(
                [{"author": a, "score": s} for a, s in bridge_scores.items()],
                key=lambda x: -x["score"]
            )[:30]
        }
    }

    Path("_site").mkdir(exist_ok=True)
    with open("_site/analysis_data.json", "w") as f:
        json.dump(export, f, indent=2)

    print(f"  Exported to _site/analysis_data.json")
    return export

def main():
    print("="*80)
    print("INVESTIGATIVE ANALYSIS: THE GENERATIVE AI GROUP")
    print("="*80)

    messages = load_data()
    print(f"Loaded {len(messages)} valid messages")
    print(f"Date range: {min(m['time'] for m in messages)} to {max(m['time'] for m in messages)}")
    print(f"Unique authors: {len(set(m['author'] for m in messages))}")

    # Run all analyses
    msg_count, replies_received, reactions_received, influence_ratio = analyze_participation_patterns(messages)
    hour_counts, day_counts, weekly = analyze_temporal_patterns(messages)
    thread_sizes, children = analyze_conversation_depth(messages)
    monthly_terms, monthly_total = analyze_topic_evolution(messages)
    reply_pairs, in_degree, out_degree, bridge_scores = analyze_network_effects(messages)
    emoji_counts, reacted, not_reacted = analyze_reaction_patterns(messages)
    lengths = analyze_content_patterns(messages)
    silent_influencers = find_surprising_insights(messages, msg_count, replies_received, influence_ratio)

    # Export for visualization
    export_data_for_visualization(
        messages, msg_count, replies_received, influence_ratio,
        hour_counts, day_counts, weekly, monthly_terms, monthly_total,
        thread_sizes, reply_pairs, bridge_scores
    )

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
