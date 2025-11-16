#!/usr/bin/env python3
"""
Deep Statistical Analysis and Robustness Checks
Finding the most defensible, surprising insights
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime
import statistics
from pathlib import Path
import math

def load_data():
    with open("gen-ai-messages.json", "r") as f:
        messages = json.load(f)
    valid = [m for m in messages if m.get("time") and m.get("text") and m.get("author")]
    return valid

def parse_time(time_str):
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

def bootstrap_confidence_interval(data, statistic_func, n_bootstrap=1000, ci=0.95):
    """Calculate bootstrap confidence interval"""
    import random
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = random.choices(data, k=len(data))
        bootstrap_stats.append(statistic_func(sample))
    bootstrap_stats.sort()
    lower_idx = int((1 - ci) / 2 * n_bootstrap)
    upper_idx = int((1 + ci) / 2 * n_bootstrap)
    return bootstrap_stats[lower_idx], bootstrap_stats[upper_idx]

def analyze_influence_robustness(messages):
    """Statistically validate the silent influencer finding"""
    print("\n" + "="*80)
    print("ROBUSTNESS CHECK: SILENT INFLUENCER EFFECT")
    print("="*80)

    msg_count = Counter(m["author"] for m in messages)
    replies_received = Counter()
    for m in messages:
        if m.get("quoteAuthor"):
            replies_received[m["quoteAuthor"]] += 1

    # Calculate influence ratios for different thresholds
    thresholds = [5, 10, 15, 20, 30, 50]

    print("\nINFLUENCE RATIO BY MINIMUM MESSAGE THRESHOLD:")
    for threshold in thresholds:
        ratios = []
        for author, count in msg_count.items():
            if count >= threshold:
                ratio = replies_received.get(author, 0) / count
                ratios.append(ratio)

        if ratios:
            mean_ratio = statistics.mean(ratios)
            median_ratio = statistics.median(ratios)
            std_ratio = statistics.stdev(ratios) if len(ratios) > 1 else 0

            # Count outliers (>2 std above mean)
            outliers = sum(1 for r in ratios if r > mean_ratio + 2*std_ratio)

            print(f"  Min {threshold} msgs: n={len(ratios)}, mean={mean_ratio:.3f}, "
                  f"median={median_ratio:.3f}, std={std_ratio:.3f}, outliers={outliers}")

    # Binned analysis - are small posters really more influential?
    print("\nMEAN INFLUENCE RATIO BY MESSAGE COUNT BIN:")
    bins = [(1,9), (10,19), (20,49), (50,99), (100,199), (200,499), (500,1000)]

    bin_data = []
    for low, high in bins:
        ratios = []
        for author, count in msg_count.items():
            if low <= count <= high:
                ratio = replies_received.get(author, 0) / count
                ratios.append(ratio)

        if len(ratios) >= 5:
            mean_r = statistics.mean(ratios)
            median_r = statistics.median(ratios)
            sem = statistics.stdev(ratios) / math.sqrt(len(ratios)) if len(ratios) > 1 else 0

            bin_data.append({
                "bin": f"{low}-{high}",
                "n": len(ratios),
                "mean": mean_r,
                "median": median_r,
                "sem": sem
            })

            print(f"  {low:3d}-{high:3d} msgs: n={len(ratios):3d}, "
                  f"mean={mean_r:.3f}±{sem:.3f}, median={median_r:.3f}")

    # Statistical test: is there a negative correlation between volume and influence?
    x_counts = []
    y_ratios = []
    for author, count in msg_count.items():
        if count >= 10:  # Only meaningful sample sizes
            ratio = replies_received.get(author, 0) / count
            x_counts.append(count)
            y_ratios.append(ratio)

    # Pearson correlation (simplified)
    n = len(x_counts)
    if n > 2:
        mean_x = statistics.mean(x_counts)
        mean_y = statistics.mean(y_ratios)

        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_counts, y_ratios))
        denom_x = sum((x - mean_x)**2 for x in x_counts) ** 0.5
        denom_y = sum((y - mean_y)**2 for y in y_ratios) ** 0.5

        correlation = numerator / (denom_x * denom_y) if denom_x * denom_y > 0 else 0

        print(f"\nCORRELATION: Message Count vs Influence Ratio (n={n})")
        print(f"  Pearson r = {correlation:.3f}")

        if correlation < -0.2:
            print("  CONFIRMED: Negative correlation - more messages = lower influence per message")
        elif correlation > 0.2:
            print("  SURPRISE: Positive correlation - more messages = higher influence per message")
        else:
            print("  NO STRONG CORRELATION")

    return bin_data

def analyze_topic_shift_significance(messages):
    """Validate topic evolution with statistical rigor"""
    print("\n" + "="*80)
    print("ROBUSTNESS CHECK: TOPIC EVOLUTION")
    print("="*80)

    # Monthly data
    monthly = defaultdict(list)
    for m in messages:
        dt = parse_time(m["time"])
        month_key = dt.strftime("%Y-%m")
        monthly[month_key].append(m)

    months = sorted(monthly.keys())

    # Key terms to track
    terms = {
        "claude": r"\bclaude\b",
        "gpt": r"\bgpt[- ]?\d*\b",
        "llama": r"\bllama\b",
        "gemini": r"\bgemini\b",
        "reasoning": r"\breason",
        "agent": r"\bagent\b",
        "rag": r"\brag\b",
    }

    # Calculate monthly proportions
    term_by_month = defaultdict(dict)
    for month in months:
        msgs = monthly[month]
        total = len(msgs)
        for term, pattern in terms.items():
            count = sum(1 for m in msgs if re.search(pattern, m["text"], re.IGNORECASE))
            term_by_month[month][term] = count / total

    # Compare first quarter to last quarter
    print("\nFIRST QUARTER vs LAST QUARTER COMPARISON:")
    if len(months) >= 6:
        first_q = months[:3]
        last_q = months[-3:]

        first_total = sum(len(monthly[m]) for m in first_q)
        last_total = sum(len(monthly[m]) for m in last_q)

        print(f"  First Q: {first_q} ({first_total} msgs)")
        print(f"  Last Q: {last_q} ({last_total} msgs)")
        print()

        for term, pattern in terms.items():
            first_count = sum(sum(1 for m in monthly[month] if re.search(pattern, m["text"], re.IGNORECASE))
                              for month in first_q)
            last_count = sum(sum(1 for m in monthly[month] if re.search(pattern, m["text"], re.IGNORECASE))
                             for month in last_q)

            first_prop = first_count / first_total
            last_prop = last_count / last_total

            # Simple proportion difference test (z-test approximation)
            pooled_p = (first_count + last_count) / (first_total + last_total)
            se = math.sqrt(pooled_p * (1 - pooled_p) * (1/first_total + 1/last_total))

            if se > 0:
                z_score = (last_prop - first_prop) / se
            else:
                z_score = 0

            pct_change = ((last_prop / first_prop) - 1) * 100 if first_prop > 0 else float('inf')

            significance = ""
            if abs(z_score) > 2.58:
                significance = "***"  # p < 0.01
            elif abs(z_score) > 1.96:
                significance = "**"   # p < 0.05
            elif abs(z_score) > 1.645:
                significance = "*"    # p < 0.10

            print(f"  {term:10s}: {first_prop*100:5.2f}% → {last_prop*100:5.2f}% "
                  f"({pct_change:+6.1f}%) z={z_score:+5.2f} {significance}")

    # Month-over-month consistency check
    print("\nMONTH-OVER-MONTH TREND CONSISTENCY:")
    for term in ["claude", "llama", "reasoning", "agent"]:
        props = [term_by_month[m][term] for m in months]
        increasing = sum(1 for i in range(1, len(props)) if props[i] > props[i-1])
        total_transitions = len(props) - 1

        print(f"  {term:10s}: {increasing}/{total_transitions} months increasing "
              f"({100*increasing/total_transitions:.0f}%)")

    return term_by_month, months

def analyze_question_engagement_paradox(messages):
    """Deep dive into the question-engagement paradox"""
    print("\n" + "="*80)
    print("ROBUSTNESS CHECK: THE QUESTION PARADOX")
    print("="*80)

    # Messages that are questions
    questions = [m for m in messages if "?" in m["text"]]
    statements = [m for m in messages if "?" not in m["text"]]

    print(f"\nBASIC COUNTS:")
    print(f"  Questions: {len(questions)} ({100*len(questions)/len(messages):.1f}%)")
    print(f"  Statements: {len(statements)} ({100*len(statements)/len(messages):.1f}%)")

    # Reaction rates
    q_reacted = sum(1 for m in questions if m.get("reactions"))
    s_reacted = sum(1 for m in statements if m.get("reactions"))

    q_react_rate = q_reacted / len(questions) if questions else 0
    s_react_rate = s_reacted / len(statements) if statements else 0

    print(f"\nREACTION RATES:")
    print(f"  Questions: {q_react_rate*100:.1f}%")
    print(f"  Statements: {s_react_rate*100:.1f}%")
    print(f"  Difference: {(s_react_rate - q_react_rate)*100:.1f} percentage points")

    # Reply generation (are they root messages that get replied to?)
    msg_by_id = {m["messageId"]: m for m in messages}
    children_count = Counter()

    for m in messages:
        if m.get("quoteMessageId"):
            children_count[m["quoteMessageId"]] += 1

    # Root messages (not replies themselves)
    root_questions = [m for m in questions if not m.get("quoteMessageId")]
    root_statements = [m for m in statements if not m.get("quoteMessageId")]

    # How many replies did root messages generate?
    q_replies = [children_count[m["messageId"]] for m in root_questions]
    s_replies = [children_count[m["messageId"]] for m in root_statements]

    q_mean_replies = statistics.mean(q_replies) if q_replies else 0
    s_mean_replies = statistics.mean(s_replies) if s_replies else 0

    q_nonzero = sum(1 for r in q_replies if r > 0)
    s_nonzero = sum(1 for r in s_replies if r > 0)

    print(f"\nROOT MESSAGE REPLY GENERATION:")
    print(f"  Root questions: {len(root_questions)}")
    print(f"    With at least 1 reply: {q_nonzero} ({100*q_nonzero/len(root_questions):.1f}%)")
    print(f"    Mean replies: {q_mean_replies:.2f}")
    print(f"  Root statements: {len(root_statements)}")
    print(f"    With at least 1 reply: {s_nonzero} ({100*s_nonzero/len(root_statements):.1f}%)")
    print(f"    Mean replies: {s_mean_replies:.2f}")

    # The paradox: Questions get fewer reactions but more replies
    print(f"\nTHE PARADOX:")
    print(f"  Questions get {(1 - q_react_rate/s_react_rate)*100:.0f}% FEWER reactions")
    print(f"  But generate {(q_mean_replies/s_mean_replies - 1)*100:.0f}% MORE replies")

    # Statistical significance
    # Proportion test for reactions
    pooled_react = (q_reacted + s_reacted) / (len(questions) + len(statements))
    se_react = math.sqrt(pooled_react * (1-pooled_react) * (1/len(questions) + 1/len(statements)))
    z_react = (s_react_rate - q_react_rate) / se_react if se_react > 0 else 0

    print(f"\nSTATISTICAL SIGNIFICANCE:")
    print(f"  Reaction difference z-score: {z_react:.2f}")
    if abs(z_react) > 2.58:
        print(f"  HIGHLY SIGNIFICANT (p < 0.01)")

    # Types of questions
    print("\nQUESTION TYPES:")
    how_questions = sum(1 for m in questions if re.search(r"\bhow\b", m["text"], re.IGNORECASE))
    what_questions = sum(1 for m in questions if re.search(r"\bwhat\b", m["text"], re.IGNORECASE))
    why_questions = sum(1 for m in questions if re.search(r"\bwhy\b", m["text"], re.IGNORECASE))
    anyone_questions = sum(1 for m in questions if re.search(r"\banyone\b", m["text"], re.IGNORECASE))

    print(f"  'How' questions: {how_questions} ({100*how_questions/len(questions):.1f}%)")
    print(f"  'What' questions: {what_questions} ({100*what_questions/len(questions):.1f}%)")
    print(f"  'Why' questions: {why_questions} ({100*why_questions/len(questions):.1f}%)")
    print(f"  'Anyone' questions: {anyone_questions} ({100*anyone_questions/len(questions):.1f}%)")

    return {
        "q_react_rate": q_react_rate,
        "s_react_rate": s_react_rate,
        "q_mean_replies": q_mean_replies,
        "s_mean_replies": s_mean_replies,
        "z_score": z_react
    }

def analyze_self_reply_phenomenon(messages):
    """Investigate the self-reply pattern"""
    print("\n" + "="*80)
    print("ROBUSTNESS CHECK: SELF-REPLY PHENOMENON")
    print("="*80)

    # Count self-replies
    self_replies = [m for m in messages if m.get("quoteAuthor") == m.get("author")]
    total_replies = [m for m in messages if m.get("quoteAuthor")]

    print(f"\nBASIC STATS:")
    print(f"  Total replies: {len(total_replies)}")
    print(f"  Self-replies: {len(self_replies)} ({100*len(self_replies)/len(total_replies):.1f}%)")

    # Who self-replies most?
    self_reply_count = Counter(m["author"] for m in self_replies)

    print("\nTOP SELF-REPLIERS:")
    for author, count in self_reply_count.most_common(10):
        # What percentage of their replies are self-replies?
        author_total_replies = sum(1 for m in total_replies if m["author"] == author)
        pct = 100 * count / author_total_replies if author_total_replies > 0 else 0
        print(f"  {author}: {count} self-replies ({pct:.0f}% of their replies)")

    # Why do people self-reply? Content analysis
    print("\nSELF-REPLY CONTENT PATTERNS:")

    # Length comparison
    self_reply_lengths = [len(m["text"]) for m in self_replies]
    other_reply_lengths = [len(m["text"]) for m in total_replies if m["author"] != m.get("quoteAuthor")]

    print(f"  Self-reply avg length: {statistics.mean(self_reply_lengths):.0f} chars")
    print(f"  Other reply avg length: {statistics.mean(other_reply_lengths):.0f} chars")

    # Contains links?
    self_with_links = sum(1 for m in self_replies if "http" in m["text"])
    other_with_links = sum(1 for m in total_replies if m["author"] != m.get("quoteAuthor") and "http" in m["text"])

    print(f"  Self-replies with links: {100*self_with_links/len(self_replies):.1f}%")
    print(f"  Other replies with links: {100*other_with_links/len(other_reply_lengths):.1f}%")

    # Time gap between original message and self-reply
    msg_by_id = {m["messageId"]: m for m in messages}
    time_gaps = []

    for m in self_replies:
        if m.get("quoteMessageId") and m["quoteMessageId"] in msg_by_id:
            original = msg_by_id[m["quoteMessageId"]]
            if original.get("time") and m.get("time"):
                gap = (parse_time(m["time"]) - parse_time(original["time"])).total_seconds() / 60
                if gap > 0:
                    time_gaps.append(gap)

    if time_gaps:
        print(f"\nTIME GAP TO SELF-REPLY:")
        print(f"  Median: {statistics.median(time_gaps):.0f} minutes")
        print(f"  Mean: {statistics.mean(time_gaps):.0f} minutes")
        print(f"  <5 min: {sum(1 for g in time_gaps if g < 5)} ({100*sum(1 for g in time_gaps if g < 5)/len(time_gaps):.1f}%)")
        print(f"  5-60 min: {sum(1 for g in time_gaps if 5 <= g < 60)} ({100*sum(1 for g in time_gaps if 5 <= g < 60)/len(time_gaps):.1f}%)")
        print(f"  1-24 hr: {sum(1 for g in time_gaps if 60 <= g < 1440)} ({100*sum(1 for g in time_gaps if 60 <= g < 1440)/len(time_gaps):.1f}%)")
        print(f"  >24 hr: {sum(1 for g in time_gaps if g >= 1440)} ({100*sum(1 for g in time_gaps if g >= 1440)/len(time_gaps):.1f}%)")

    return self_reply_count, time_gaps

def analyze_weekend_effect(messages):
    """Validate weekend behavior patterns"""
    print("\n" + "="*80)
    print("ROBUSTNESS CHECK: WEEKEND EFFECT")
    print("="*80)

    weekend_msgs = []
    weekday_msgs = []

    for m in messages:
        dt = parse_time(m["time"])
        if dt.strftime("%A") in ["Saturday", "Sunday"]:
            weekend_msgs.append(m)
        else:
            weekday_msgs.append(m)

    print(f"\nBASIC SPLIT:")
    print(f"  Weekday messages: {len(weekday_msgs)} ({100*len(weekday_msgs)/len(messages):.1f}%)")
    print(f"  Weekend messages: {len(weekend_msgs)} ({100*len(weekend_msgs)/len(messages):.1f}%)")

    # Expected if uniform: 71.4% weekday, 28.6% weekend
    expected_weekend = 2/7 * len(messages)
    print(f"  Expected if uniform: {expected_weekend:.0f} weekend msgs")
    print(f"  Actual: {len(weekend_msgs)} ({100*len(weekend_msgs)/expected_weekend:.0f}% of expected)")

    # Message quality comparison
    weekend_lengths = [len(m["text"]) for m in weekend_msgs]
    weekday_lengths = [len(m["text"]) for m in weekday_msgs]

    print(f"\nMESSAGE LENGTH:")
    print(f"  Weekday avg: {statistics.mean(weekday_lengths):.0f} chars")
    print(f"  Weekend avg: {statistics.mean(weekend_lengths):.0f} chars")

    # Reaction rates
    weekend_reacted = sum(1 for m in weekend_msgs if m.get("reactions"))
    weekday_reacted = sum(1 for m in weekday_msgs if m.get("reactions"))

    print(f"\nREACTION RATES:")
    print(f"  Weekday: {100*weekday_reacted/len(weekday_msgs):.1f}%")
    print(f"  Weekend: {100*weekend_reacted/len(weekend_msgs):.1f}%")

    # Thread depth on weekends vs weekdays
    # Root messages
    weekend_roots = [m for m in weekend_msgs if not m.get("quoteMessageId")]
    weekday_roots = [m for m in weekday_msgs if not m.get("quoteMessageId")]

    weekend_reply_rate = 1 - len(weekend_roots)/len(weekend_msgs)
    weekday_reply_rate = 1 - len(weekday_roots)/len(weekday_msgs)

    print(f"\nCONVERSATION DEPTH (% of messages that are replies):")
    print(f"  Weekday: {weekday_reply_rate*100:.1f}%")
    print(f"  Weekend: {weekend_reply_rate*100:.1f}%")

    return weekend_msgs, weekday_msgs

def export_enhanced_data(messages):
    """Export enhanced data for sophisticated visualizations"""
    print("\n" + "="*80)
    print("EXPORTING ENHANCED DATA")
    print("="*80)

    Path("_site").mkdir(exist_ok=True)

    # Build comprehensive timeline data
    daily_data = defaultdict(lambda: {
        "messages": 0,
        "authors": set(),
        "reactions": 0,
        "questions": 0,
        "links": 0,
        "replies": 0,
        "terms": defaultdict(int)
    })

    terms = {
        "claude": r"\bclaude\b",
        "gpt": r"\bgpt",
        "llama": r"\bllama\b",
        "gemini": r"\bgemini\b",
        "reasoning": r"\breason",
        "agent": r"\bagent\b",
    }

    for m in messages:
        dt = parse_time(m["time"])
        day_key = dt.strftime("%Y-%m-%d")

        daily_data[day_key]["messages"] += 1
        daily_data[day_key]["authors"].add(m["author"])
        if m.get("reactions"):
            daily_data[day_key]["reactions"] += 1
        if "?" in m["text"]:
            daily_data[day_key]["questions"] += 1
        if "http" in m["text"]:
            daily_data[day_key]["links"] += 1
        if m.get("quoteMessageId"):
            daily_data[day_key]["replies"] += 1

        for term, pattern in terms.items():
            if re.search(pattern, m["text"], re.IGNORECASE):
                daily_data[day_key]["terms"][term] += 1

    # Convert to JSON-serializable format
    timeline = []
    for day in sorted(daily_data.keys()):
        data = daily_data[day]
        timeline.append({
            "date": day,
            "messages": data["messages"],
            "unique_authors": len(data["authors"]),
            "reactions": data["reactions"],
            "questions": data["questions"],
            "links": data["links"],
            "replies": data["replies"],
            "terms": dict(data["terms"])
        })

    with open("_site/timeline_data.json", "w") as f:
        json.dump(timeline, f, indent=2)

    # Author influence data
    msg_count = Counter(m["author"] for m in messages)
    replies_received = Counter()
    for m in messages:
        if m.get("quoteAuthor"):
            replies_received[m["quoteAuthor"]] += 1

    influence_data = []
    for author, count in msg_count.items():
        if count >= 5:  # At least 5 messages
            influence_data.append({
                "author": author,
                "messages": count,
                "replies_received": replies_received.get(author, 0),
                "influence_ratio": replies_received.get(author, 0) / count
            })

    with open("_site/influence_data.json", "w") as f:
        json.dump(sorted(influence_data, key=lambda x: -x["influence_ratio"]), f, indent=2)

    # Network data for visualization
    reply_pairs = Counter()
    for m in messages:
        if m.get("quoteAuthor") and m.get("author"):
            reply_pairs[(m["author"], m["quoteAuthor"])] += 1

    # Filter to top interactions
    top_interactions = []
    for (a, b), count in reply_pairs.most_common(200):
        top_interactions.append({
            "source": a,
            "target": b,
            "weight": count
        })

    with open("_site/network_data.json", "w") as f:
        json.dump(top_interactions, f, indent=2)

    print(f"  Exported timeline_data.json ({len(timeline)} days)")
    print(f"  Exported influence_data.json ({len(influence_data)} authors)")
    print(f"  Exported network_data.json ({len(top_interactions)} interactions)")

def main():
    messages = load_data()
    print(f"Loaded {len(messages)} messages for deep analysis")

    # Run robustness checks
    bin_data = analyze_influence_robustness(messages)
    term_data, months = analyze_topic_shift_significance(messages)
    question_data = analyze_question_engagement_paradox(messages)
    self_reply_data, time_gaps = analyze_self_reply_phenomenon(messages)
    weekend_msgs, weekday_msgs = analyze_weekend_effect(messages)

    # Export enhanced data
    export_enhanced_data(messages)

    print("\n" + "="*80)
    print("DEEP ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
