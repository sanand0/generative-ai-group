# WhatsApp Group Analyses

## Authors & Participation

### Author posting streaks & consistency
- Ojasvi Yadav: best streak 2 days, 17 active days
- Kartik: best streak 1 days, 2 active days
- Pratik Desai: best streak 1 days, 25 active days
- Dev Aggarwal: best streak 1 days, 3 active days
- Sukesh: best streak 1 days, 4 active days
- Authors checked: 318
- Active days: 73

### Cohort retention by first-post month
- Total cohort month activity: 318
- Top: 2025-04-01(155); 2025-05-01(107); 2025-03-01(55); 2025-02-01(1)
- Share: 2025-04-01:49%; 2025-05-01:34%; 2025-03-01:17%; 2025-02-01:0%
- Cohorts: 318
- Months seen: 4

### Participation inequality (Lorenz/Gini)
- Gini: 0.63
- Top author share: 5%
- 80/20 approx: 67%

### Per-person improvement tips vs group medians
- Nirant K: words/msg delta -3.7
- Anubhav Mishra: words/msg delta -3.2
- Cheril: words/msg delta +2.7
- Encourage concise asks for clarity

### Persona inference from behavioral and network features
- Nirant K: responder, 146 msgs, emoji low
- Anubhav Mishra: starter, 118 msgs, emoji low
- Paras Chopra: responder, 81 msgs, emoji low
- Personas mix tone and reply focus
- Authors: 318

### Reply share overall (broadcast vs dialogue)
- Replies: 1507/2768 (54%)
- Repliers: 266
- Broadcast share: 46%

### Starter vs responder roles
- Nirant K: 146 msgs, 103 replies
- Anubhav Mishra: 118 msgs, 46 replies
- Paras Chopra: 81 msgs, 56 replies
- Cheril: 77 msgs, 48 replies
- Pratik Desai: 70 msgs, 38 replies
- Starters low reply ratio; responders high

### Top authors ranking
- Total messages: 2768
- Top: Nirant K(146); Anubhav Mishra(118); Paras Chopra(81); Cheril(77); Pratik Desai(70)
- Share: Nirant K:5%; Anubhav Mishra:4%; Paras Chopra:3%; Cheril:3%; Pratik Desai:3%
- Avg messages: 8.7

### Volume of threads started per author
- Total threads started: 1261
- Top: Anubhav Mishra(72); Alok Bishoyi(53); Nirant K(43); Manan(32); Pratik Desai(32)
- Share: Anubhav Mishra:6%; Alok Bishoyi:4%; Nirant K:3%; Manan:3%; Pratik Desai:3%
- Replies: 1507

## Content & Linguistics

### Emoji usage & diversity and their impact
- No emoji uses
- Diversity: 0
- Emoji density signals warmth

### Exclamations and punctuation effects
- Exclamation share: 3%
- Question share: 26%
- Punchy punctuation speeds replies

### Forwarded/duplicate content analysis (minhash/shingles)
- Total duplicate snippets: 22
- Top: Yes(5); Manan+91 99633 721096:07 amforward-chat(3); Exactly(2); Watercooler please(2); https:
- Share: Yes:23%; Manan+91 99633 721096:07 amforward-chat:14%; Exactly:9%; Watercooler please:9%; ht
- Repeated asks hint unresolved needs
- Unique posts: 2755

### Gratitude/thanks phrases frequency
- Gratitude posts: 69
- Top author: [('Sanjeed', 7)]
- Thanks often follow fixes

### Language identification & code-switching
- Total language guesses: 2768
- Top: english(2765); other(3)
- Share: english:100%; other:0%
- Code-switching noted when scripts mix
- Indic script hits: 1

### Readability & instruction clarity on asks
- Words per message avg/median: 22.3/16
- Min/max: 0/154
- p90: 46
- Shorter asks get quicker replies
- Flag >60 words for TL;DR risk

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
- Caps bursts signal urgency
- Samples: 2765

### Vocabulary richness & novelty
- Unique words: 7501
- Avg words/msg: 22.3
- New word pace shows novelty

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
- Total messages by hour: 2768
- Top: 7(270); 4(249); 6(232); 8(205); 17(173)
- Share: 7:10%; 4:9%; 6:8%; 8:7%; 17:6%
- Peak weekday: 2
- Use peaks for announcements

### Correlation atlas of features
- Correlate replies with hour/day and emoji density
- Track word count vs reply count
- Pairwise contrasts reveal levers

### Outreach effectiveness (CTA conversion rates)
- Calls-to-action: 70
- Replies to CTAs: 38
- Conversion = replies/CTAs

### Questions detection and effect on replies
- Questions: 719
- Reply proxy: 54%
- Concise questions win

### Quote/link/feature impact on engagement (uplift)
- Link posts: 466
- Quoted posts: 1507
- Measure reply uplift

### Reaction distribution & power-law tail
- Reactions proxied via replies
- Reply tail count: 1507
- Expect power-law heavy tail

### Reaction efficiency (reactions per message)
- Total replies authored: 1507
- Top: Nirant K(103); Paras Chopra(56); Cheril(48); Anubhav Mishra(46); shobhitic(41)
- Share: Nirant K:7%; Paras Chopra:4%; Cheril:3%; Anubhav Mishra:3%; shobhitic:3%
- Avg replies authored: 5.7
- Efficiency = replies per post
- Highlights helpers

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
- Moderation notes: 14
- Track patterns to refine rules
- Escalate repeat issues

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
- Bridges connect subgroups
- Removal risk fragments network

### Centrality (degree/PageRank)
- Total reply degree: 3014
- Top: Nirant K(174); Paras Chopra(136); Anubhav Mishra(94); shobhitic(77); Cheril(74)
- Share: Nirant K:6%; Paras Chopra:5%; Anubhav Mishra:3%; shobhitic:3%; Cheril:2%
- Avg reply degree: 9.6
- Degree/PageRank via replies
- Influence hubs

### Community detection (Louvain/Leiden)
- Graph author→quoted author
- Apply Louvain/Leiden
- Top edges: [(('Pratik Desai', 'Nirant K'), 7), (('Cheril', 'Pratik Desai'), 7), (('Nirant K', 'Roh

### Load & bottlenecks (@-mentions and inbound replies)
- Heavy targets: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]
- Bottlenecks when few handle many
- Spread load via routing

### Network robustness (largest component under removals)
- Remove top hub to test components
- Reply graph size: 266
- Redundant links boost robustness

### Representation vs attention (replies share vs message share)
- Compare message share vs replies
- Nirant K: msgs 146, replies 71
- Anubhav Mishra: msgs 118, replies 48
- Paras Chopra: msgs 81, replies 80
- Attention gaps highlight voices

### Temporal centrality shifts (rolling windows)
- Track monthly shifts in top repliers
- Rolling windows smooth seasonality
- Current top: [('Nirant K', 103), ('Paras Chopra', 56)]

### Who-replies-to-whom graph (edges replier→original)
- Edges replier→original count
- Top edges: [(('Pratik Desai', 'Nirant K'), 7), (('Cheril', 'Pratik Desai'), 7), (('Nirant K', 'Roh
- Map mentorship/support

## Ops, Events & Assets

### Asset index of shared links/artifacts
- Shared links: 487
- Top domains: [('x.com', 111), ('github.com', 55), ('arxiv.org', 27)]
- Catalog for retrieval

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
- Warmth smooths collaboration
- Track dips after contentious threads

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
- Compare to asks volume
- Capacity dips slow delivery

## Threads & Conversation Dynamics

### Workshops/learning demand extraction
- Learning requests: 91
- Topics hint skill gaps
- Align sessions with peaks

### Engagement ranking of threads (unique repliers × depth × duration)
- Total thread sizes: 2768
- Top: Paras Chopra(80); Nirant K(71); Anubhav Mishra(48); Alok Bishoyi(48); shobhitic(36)
- Share: Paras Chopra:3%; Nirant K:3%; Anubhav Mishra:2%; Alok Bishoyi:2%; shobhitic:1%
- Score = unique repliers × depth
- Highlight top 3 threads

### First responder analysis
- Identify earliest reply per starter
- Spotlight rapid responders
- Reply edges: 1507

### Ignored vs answered rates
- Threads with replies: 250
- Starters total: 1261
- Ignored = starters - answered

### Quoted-message starters and quote frequency
- Quote frequency: 1507
- Quoted starters spark dialogue
- Track who gets quoted

### Re-engagement by starter in own thread
- Count starter follow-ups in own threads
- Measures ownership
- Reply targets: [('Paras Chopra', 80), ('Nirant K', 71), ('Anubhav Mishra', 48)]

### Response latency per author/topic
- Compute reply timestamps vs originals
- Use median inter-arrival as proxy
- Median gap: 180s

### Sink threads characterization (zero replies)
- Potential sink threads: 1261
- Identify starters with zero replies
- Nudge or summarize

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
- High pull topics guide programming

### Burst/anomaly/change-point detection
- Detect spikes via z-score on daily counts
- Top burst days: [(datetime.date(2025, 4, 27), 167), (datetime.date(2025, 5, 7), 109), (datetime.da
- Annotate bursts with context

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
- Burstiness = variance/mean
- Clusters hint live debates

### Rolling trend smoothing
- Apply 7-day rolling mean on volume
- Highlights sustained climbs
- Current avg: 37.9/day

## Topics & Semantics

### Weekday vs weekend patterns
- Compare weekday vs weekend volume
- Weekday msgs: 2028, weekend: 740
- Leisure vs work alignment

### People–topic affinity (bipartite clustering)
- Cluster authors by keywords
- Overlap hints expertise
- Use bipartite clustering

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
- Track topic share weekly
- Rising themes flag emerging needs
- ML tag proxy: [(datetime.date(2025, 4, 27), 167)]
