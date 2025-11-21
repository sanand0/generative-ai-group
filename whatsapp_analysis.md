# WhatsApp Group Analyses

## Authors & Participation

### Author posting streaks & consistency
- Ojasvi Yadav: best 2d, replies recv 21, months 4
- Kartik: best 1d, replies recv 13, months 2
- Pratik Desai: best 1d, replies recv 35, months 4
- Dev Aggarwal: best 1d, replies recv 4, months 3
- Sukesh: best 1d, replies recv 1, months 4
- Streak>=median avg replies: 1.2 vs short: 0.0
- Recent retention: 235/318 active in last 30d
- Active days total: 73

### Cohort retention by first-post month
- 2025-02-01: active 10/20 (50%), msgs/active 47.3
- 2025-03-01: active 85/183 (46%), msgs/active 16.0
- 2025-04-01: active 32/100 (32%), msgs/active 5.9
- Cohorts tracked: 318 authors over 4 months

### Participation inequality (Lorenz/Gini)
- Gini: 0.63
- Top author share: 5%; top10 hold 27%
- 1-post authors: 72; 2-post authors: 47

### Per-person improvement tips vs group medians
- Nirant K: reply rate 0.5/msg, len 19 vs group 22
- Anubhav Mishra: reply rate 0.4/msg, len 19 vs group 22
- Paras Chopra: reply rate 1.0/msg, len 13 vs group 22
- Median gap proxy: 180s; flag >60 words drop-offs

### Persona inference from behavioral and network features
- Nirant K: replies/msg 0.5, starter/responder 1.4, emojis 0
- Anubhav Mishra: replies/msg 0.4, starter/responder 2.6, emojis 0
- Paras Chopra: replies/msg 1.0, starter/responder 1.4, emojis 0
- Authors profiled: 318; mix numeric features only

### Reply share overall (broadcast vs dialogue)
- Replies: 1507/2768 (54%)
- Broadcast share: 46%
- Dialogue-heavy tags: [('ml', 212), ('events', 92)]

### Starter vs responder roles
- Nirant K: replies/start 2.4, first-resp 23
- Anubhav Mishra: replies/start 0.6, first-resp 6
- Paras Chopra: replies/start 2.2, first-resp 12
- Cheril: replies/start 1.7, first-resp 2
- Pratik Desai: replies/start 1.2, first-resp 6
- Ratios flag initiators vs helpers

### Top authors ranking
- Nirant K: msgs 146, cohort 2025-02-01, helper ratio 0.7
- Anubhav Mishra: msgs 118, cohort 2025-02-01, helper ratio 0.4
- Paras Chopra: msgs 81, cohort 2025-03-01, helper ratio 0.7
- Compare cohorts, topics, helper ratios

### Volume of threads started per author
- Anubhav Mishra: threads 72, avg replies 0.7, zero-reply est 0%
- Alok Bishoyi: threads 53, avg replies 0.9, zero-reply est 0%
- Nirant K: threads 43, avg replies 1.7, zero-reply est 0%
- Total starters: 1261; replies: 1507

## Content & Linguistics

### Emoji usage & diversity and their impact
- No emoji uses
- Diversity: 0
- Emoji density/msg: 0.00
- Reply uplift: +0.00

### Exclamations and punctuation effects
- '?' share: 26%; '!' share similar
- Both ?! vs neither reply delta proxy: 0.54
- Control for word count: favor <40 words

### Forwarded/duplicate content analysis (minhash/shingles)
- Total duplicate snippets: 22
- Top: Yes(5); Manan+91 99633 721096:07 amforward-chat(3); Exactly(2); Watercooler please(2); https:
- Share: Yes:23%; Manan+91 99633 721096:07 amforward-chat:14%; Exactly:9%; Watercooler please:9%; ht
- Events/logistics duplicates: 23
- Resolution proxy (any reply): True

### Gratitude/thanks phrases frequency
- Gratitude posts: 69
- Top thankers→helpees: [(('Sanjeed', None), 7), (('Jacob Singh', None), 3)]
- Thanks vs bug/issue replies shows closure

### Language identification & code-switching
- Total language guesses: 2768
- Top: english(2765); other(3)
- Share: english:100%; other:0%
- Code-switching noted when scripts mix
- Indic script hits: 1

### Readability & instruction clarity on asks
- 0-20 words reply share proxy: 1729/2768
- 21-40 words reply share proxy: 678/2768
- >40 words reply share proxy: 361/2768

### Top n-grams, bigrams, trigrams (catchphrases)
- Total bigrams: 58999
- Top: it s(167); of the(127); in the(125); this is(116); https x(111)
- Share: it s:0%; of the:0%; in the:0%; this is:0%; https x:0%
- Avg bigrams: 1.6
- Catchphrases reveal recurring needs
- Unique bigrams: 37910

### Uppercase ratio ('shouting') patterns
- Uppercase % avg/median: 4.8/3
- Min/max: 0/100
- p90: 11
- >50% caps posts: 6 tied to moderation 14
- Low replies on shouting posts? review

### Vocabulary richness & novelty
- Unique words: 7501
- Avg words/msg: 22.3
- New terms adoption rate shows trendsetters

### Word count & length distribution (longest posts, wordiest authors)
- Word count avg/median: 22.3/16
- Min/max: 0/154
- p90: 46
- Wordiest author: [('Nirant K', 2715)]
- Longest post words: 154

## Data Quality & Prep

### Data quality audit (null rates, schema checks)
- Total null fields: 676
- Top: author(315); time(310); text(51)
- Share: author:47%; time:46%; text:8%
- System messages: 0
- Rows: 3078

### Missing-time repair (interpolate/extrapolate)
- Missing time entries: 310
- Interpolate via neighbors
- Extrapolate with median gap

### Outlier detection across metrics
- Word outliers: 142
- Mean±2σ: 22.3±22.0
- Inspect extreme links/quotes too

### System vs human split
- Human messages: 2768
- System messages: 0
- Verify bot/admin notices

### Time span & coverage window
- Span: 2025-02-28 → 2025-05-11 (73 days)
- Days with posts: 73
- Coverage gaps show lulls

## Engagement Signals

### Best time to reach (reply-time heatmaps & hour/weekday regression)
- Reply probability proxy by hour: [(7, 270), (4, 249), (6, 232)]
- Weekday median gap proxy: 180s
- Aim announcements at hour×weekday peaks with fastest replies

### Correlation atlas of features
- Replies vs word count correlation proxy: compact boosts replies
- Emoji density vs replies: 0.00
- Regression-ready features: links, questions, time, author role

### Outreach effectiveness (CTA conversion rates)
- CTAs: 70; replies: 38
- CTA authors: [('Nirant K', 9), ('Ravi Theja', 4)]
- Track pledges vs completion follow-ups

### Questions detection and effect on replies
- Genuine question count: 551; rhetorical/multi: 9
- Reply proxy overall: 54%
- Prioritize who/what/how/why phrasing

### Quote/link/feature impact on engagement (uplift)
- Link posts: 466
- Domain mix (code/research/social): [('x.com', 111), ('github.com', 55), ('arxiv.org', 27)]
- Quote presence and links together for uplift/depth

### Reaction distribution & power-law tail
- Reactions proxied via replies; expect heavy tail
- Tail count (top5% proxy): 75
- Estimate exponent with log-log fit before scaling

### Reaction efficiency (reactions per message)
- Ojasvi Yadav: replies made/msg 0.5, replies received/msg 0.4
- Kartik: replies made/msg 0.4, replies received/msg 1.4
- Pratik Desai: replies made/msg 0.5, replies received/msg 0.5
- Segments helpers vs attention magnets

### Reaction totals by author and emoji
- Total replies made: 1507
- Top: Nirant K(103); Paras Chopra(56); Cheril(48); Anubhav Mishra(46); shobhitic(41)
- Share: Nirant K:7%; Paras Chopra:4%; Cheril:3%; Anubhav Mishra:3%; shobhitic:3%
- Total replies received: 1507
- Balance giving vs receiving

### Time-of-day/weekday effect on engagement (post-level replies)
- Hour peaks: [(7, 270), (4, 249), (6, 232)]
- Weekday peaks: [(2, 537), (6, 436), (4, 407)]
- Cross with replies for uplift

## Governance, Safety & Compliance

### Moderation events extraction (off-topic/spam notes)
- Moderation notes: 14 (repeat offenders: [('Nirant K', 3), ('Ojasvi Yadav', 1)])
- New vs old: 13/14
- Reasons tagged: off-topic/spam/remove

### PII/secret detection & redaction risk
- Potential PII: 2
- Redact before sharing
- Add email/name regex

### Spam/phish risk detection
- Multi-link posts: 21
- Link bursts may be phishing
- Add domain allowlist

## Networks & Influence

### Bridges & betweenness; vulnerability
- High inbound replies: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]
- Potential single points: ['Paras Chopra', 'Nirant K', 'Anubhav Mishra']
- Removing hubs likely splits components; add backups

### Centrality (degree/PageRank)
- Total reply degree: 3014
- Top: Nirant K(174); Paras Chopra(136); Anubhav Mishra(94); shobhitic(77); Cheril(74)
- Share: Nirant K:6%; Paras Chopra:5%; Anubhav Mishra:3%; shobhitic:3%; Cheril:2%
- Avg reply degree: 9.6
- High impact per word: ['Paras Chopra', 'Nirant K']

### Community detection (Louvain/Leiden)
- Graph author→quoted author; cluster for subgroups
- Edge volume: 1507; top edges [(('Pratik Desai', 'Nirant K'), 7), (('Cheril', 'Pratik Desai'), 7), 
- Label sizes show dominant topics/authors per community

### Load & bottlenecks (@-mentions and inbound replies)
- Heavy targets: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]
- Few handlers imply bottlenecks; route to widen
- Monitor @mention equivalents via quotes

### Network robustness (largest component under removals)
- Remove top hub to test components
- Reply graph size: 266
- Add redundant links to avoid fragmentation

### Representation vs attention (replies share vs message share)
- Scatter: msgs% vs replies% by author
- Nirant K: msgs 146, replies 71
- Anubhav Mishra: msgs 118, replies 48
- Paras Chopra: msgs 81, replies 80
- Surface under-heard heavy posters vs over-heard light posters

### Temporal centrality shifts (rolling windows)
- Track monthly shifts in top repliers
- Rolling windows smooth seasonality
- Current top: [('Nirant K', 103), ('Paras Chopra', 56)]

### Who-replies-to-whom graph (edges replier→original)
- Total edges: 1507
- Top pairs: [(('Pratik Desai', 'Nirant K'), 7), (('Cheril', 'Pratik Desai'), 7), (('Nirant K', 'Roh
- Compact numeric view only

## Ops, Events & Assets

### Asset index of shared links/artifacts
- Shared links: 487
- Domains by type (code/tools/events/social): [('x.com', 111), ('github.com', 55), ('arxiv.org', 27)
- Map domains to topics and replies for knowledge base

### Attendance friction/no-show signals
- Attendance friction: 77
- Track before events
- Improve reminders

### Bug/issue logging extraction with components/assignees
- Bug mentions: 71
- Note components/assignees
- Follow-up threads show resolution

### Cross-platform comms pipeline (publish timestamps)
- Compare timestamps across channels
- Spot delays between posts
- Useful for reliability

### Cumulative join requests over time
- Join requests: 16
- Plot cumulative to show growth
- Peaks hint publicity

### Event alignment with known dates and external milestones
- Align spikes with launches/holidays
- Cross-ref external timeline
- Daily peaks: [(datetime.date(2025, 4, 27), 167), (datetime.date(2025, 5, 7), 109), (datetime.date(

### Join/leave dynamics
- Track join/leave system notices
- Compare churn vs new joins
- Explain sentiment shifts

### Media quality decisions logging
- Media with quality tags: 0
- Record accept/reject rationale
- Infer standards from reactions

### Media vs text type mix
- Media posts: 0
- Text posts: 3078
- Mix shifts during demos

### Media/link audit (type and domain distributions)
- Total link domains: 487
- Top: x.com(111); github.com(55); arxiv.org(27); huggingface.co(22); www.linkedin.com(16)
- Share: x.com:23%; github.com:11%; arxiv.org:6%; huggingface.co:5%; www.linkedin.com:3%
- Link count: 487
- Check file types for risk

### Morale & vibe indicators (laughter/support tokens)
- Laughter/support tokens: 15
- Trend vs bursts/mod events: 0.01 share
- Dip alerts after contentious threads

### Pledge/acknowledgement cascades over time
- Pledge statements: 48
- Sequence shows momentum
- Map to outcomes

### Poll/scheduling compliance (responses within window)
- Poll mentions: 5
- Check responses within window
- Lag hints disengagement

### Regional subcommunity momentum (city/chapter activity)
- No regional tags
- City mentions proxy energy
- Track growth by week

### Rituals/milestones detection & participation bursts (e.g., birthdays)
- Ritual mentions: 0
- Participation spikes around rituals
- Explain sentiment lifts

### URL decay/freshness checks (dead/redirected links)
- Links needing check: 487
- Test for 404/redirects offline
- Older links likelier stale

### URL/link presence and domains
- Messages with links: 487
- Domains show sourcing diversity
- Track media vs article ratio

### Volunteer capacity/availability shifts
- Availability notes: 53
- Compare offers vs bug/event load
- Watch repeat volunteers for burnout

## Threads & Conversation Dynamics

### Workshops/learning demand extraction
- Learning requests: 91
- Themes: LLM basics/infra/eval/career from keywords
- Align with event announcements + attendance friction

### Engagement ranking of threads (unique repliers × depth × duration)
- Thread Paras Chopra: size 80
- Thread Nirant K: size 71
- Thread Anubhav Mishra: size 48
- Score = unique repliers × depth; capped to top 3

### First responder analysis
- First responders: [('Nirant K', 23), ('Paras Chopra', 12), ('shobhitic', 11)]
- Highlight quick helpers for recognition
- Reply edges: 1507

### Ignored vs answered rates
- Threads with replies: 250
- Starters total: 1261
- Break down by author/topic/length to rescue sinks

### Quoted-message starters and quote frequency
- Quote frequency: 1507
- Quoted starters spark dialogue; list top quoted
- Top quoted authors: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]

### Re-engagement by starter in own thread
- Count starter follow-ups in own threads
- Follow-up heavy starters: [('Anubhav Mishra', 6), ('Cheril', 6)]
- Reply targets: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]

### Response latency per author/topic
- Median gap proxy overall: 180s
- Split by helpers/topics; add p90 for on-call planning
- @mention proxy via quotes: 1507

### Sink threads characterization (zero replies)
- Potential sink threads: 1261
- Profile by topic, cohort, time-of-day
- Rescue first-time posters via summaries

### Subthread gravity (posts that spawn subthreads via quotes)
- Quotes spawning further replies show gravity
- Quoted authors: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]
- Map nested quotes

### Thread detection and sizes (msgs, participants, depth)
- Threads via quotes: 1511
- Estimate depth by repeated quoting
- Participants per thread matter

### Thread half-life and survival modeling
- Time from start to half replies
- Use inter-arrival proxy
- Median gap proxy: 180s

## Time-Series & Cadence

### Topic seeding effectiveness (replies per thread started)
- Replies per starter shows topic pull
- Avg replies per author: 5.7
- Pair author×topic to route who seeds which threads

### Burst/anomaly/change-point detection
- Detect spikes via z-score on daily counts
- Top burst days: [(datetime.date(2025, 4, 27), 167), (datetime.date(2025, 5, 7), 109), (datetime.da
- Attach assets/links to explain whether healthy or stressful

### Daily/weekly/monthly message volume
- Total daily messages: 2768
- Top: 2025-04-27(167); 2025-05-07(109); 2025-03-28(74); 2025-03-10(73); 2025-04-16(68)
- Share: 2025-04-27:6%; 2025-05-07:4%; 2025-03-28:3%; 2025-03-10:3%; 2025-04-16:2%
- Weekly buckets: ~10.4 weeks
- Monthly rollups show trend

### Hour-of-day activity patterns
- Total hour activity: 2768
- Top: 7(270); 4(249); 6(232); 8(205); 17(173)
- Share: 7:10%; 4:9%; 6:8%; 8:7%; 17:6%
- Off-hours chatter shows dedication
- Pair with weekday view

### Inter-arrival times and burstiness
- Inter-arrival seconds avg/median: 2251.7/180
- Min/max: -4578000/4579260
- p90: 5820
- Burstiness = variance/mean per thread/author
- Clusters hint live debates

### Rolling trend smoothing
- Apply 7-day rolling mean on volume
- Highlights sustained climbs
- Current avg: 37.9/day

## Topics & Semantics

### Weekday vs weekend patterns
- Compare weekday vs weekend volume and topic mix
- Weekday msgs: 2028, weekend: 740
- Decide social vs deep-tech scheduling

### People–topic affinity (bipartite clustering)
- Cluster authors by keyword tags to find experts
- Top experts per theme guide routing
- Surface under-covered areas needing owners

### Rule-based topic tagging (keywords/regex)
- Total keyword topics: 558
- Top: ml(417); events(141)
- Share: ml:75%; events:25%
- Extend with regex library
- Untagged msgs: 2210

### Subgraphs by topic (topic-specific networks)
- Build reply graphs per topic
- Compare density across themes
- Highlight strong clusters

### Theme heatmaps (time × cluster)
- Time × topic heatmaps show cadence
- Weekly bins smooth noise
- Use share not counts

### Topic trends over time (weekly share)
- Track topic share weekly vs join/leave/pledge events
- Rising themes flag emerging needs or drift
- ML tag proxy: [(datetime.date(2025, 4, 27), 167)]
