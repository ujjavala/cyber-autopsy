---
title: "Can an AI Reconstruct a Cyber Incident from Fragmented Evidence?"
published: false
description: "A first Kaggle evaluation of evidence-grounded cyber incident reconstruction."
tags: kaggle, ai, cybersecurity, machinelearning
---

*This is a submission for the [Kaggle Benchmarking Challenge](https://dev.to/challenges/kaggle-2026-09-23)*

## What I Benchmarked

Cyber incident reports rarely arrive as a clean, complete timeline. They describe what investigators or security teams could observe, mix those observations with analysis, and leave some questions unanswered. That is exactly where an AI-generated summary can become risky: it may sound convincing while quietly turning an inference into a fact or filling a gap with an event that the evidence never established.

I built **Cyber Autopsy** to test a narrower, practical question: when given pieces of a reported cyber incident, can a model reconstruct what happened while showing which evidence supports each claim and admitting what remains uncertain? The model must produce a timeline, connect events with causal or temporal links, cite evidence, and distinguish confirmed activity from inference, failed attempts, contradictions, and unknowns. A plausible attack story is not enough; unsupported certainty should count against it.

I chose this problem because incident reconstruction depends on more than recognizing familiar attack techniques. An analyst needs to know whether a step was observed or inferred, whether an attempt actually succeeded, and how one event led to another. Those distinctions can disappear in a fluent summary. Measuring them separately makes it easier to see whether a model is recovering the evidence or merely telling a likely-sounding story.

The first evaluation uses seven tasks built from four public reports. They include a detailed human-operated ransomware intrusion and vendor-reported campaigns involving AI-assisted activity. These are useful real-world case studies, but they are not a controlled contest between human and AI attackers: the reports differ in detail, evidence source, and corroboration. I also included two versions of one case with identical evidence but different actor framing, to see whether that wording changes the model's reconstruction.

This is a pilot, not a claim that AI attackers are more or less capable than people. It evaluates model reconstructions of reported incidents, not live attack behavior. The scorer is deterministic and reports an Evidence-Grounded Reconstruction Score (EGRS), alongside event recall and precision, causal-link quality, evidence attribution, status accuracy, uncertainty calibration, and hallucination-related measures. The temporal cutoff and framing pair are exploratory comparisons; only the framing pair holds the evidence fixed.

### Real-world case studies

The seven tasks are built from four public incident reports, not invented scenarios:

- **RansomHub intrusion (CASE-001 and CASE-004):** [The DFIR Report's “Hide Your RDP: Password Spray Leads to RansomHub Deployment”](https://thedfirreport.com/2025/06/30/hide-your-rdp-password-spray-leads-to-ransomhub-deployment/) describes a human-operated intrusion using password spraying and RDP, credential access, Rclone exfiltration, and eventual RansomHub deployment. CASE-004 reuses this incident but cuts off the evidence at the end of day one.
- **GTG-1002 espionage campaign (CASE-002, CASE-011, CASE-012):** Anthropic's [incident report](https://www.anthropic.com/news/disrupting-AI-espionage) and [technical report](https://assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf) describe an alleged AI-orchestrated campaign against roughly 30 targets. CASE-011 and CASE-012 use identical evidence with human versus AI-agent framing; they test framing sensitivity, not whether the real-world actor was human or AI. The campaign details and attribution are vendor-reported, not independently verified victim-side telemetry.
- **GTG-2002 “vibe hacking” extortion (CASE-003):** Anthropic's [August 2025 misuse report](https://www.anthropic.com/news/detecting-countering-misuse-aug-2025) describes a Claude Code-assisted data-extortion operation affecting at least 17 organisations. The ransom-note images in that report were simulated recreations and are excluded from the benchmark evidence.
- **AI-enabled credential harvesting (CASE-013):** Google GTIG/Mandiant's [September 2026 report](https://cloud.google.com/blog/topics/threat-intelligence/from-prompting-to-autonomy-the-evolution-of-adversarial-ai) describes an AI-assisted campaign that reportedly harvested thousands of credentials in under six hours. The victim and model are undisclosed, and the claims remain vendor-reported.

These are real reported incidents, but the evidence quality is not uniform: the RansomHub case is reconstructed from host and network telemetry described by The DFIR Report, while the AI-actor case studies rely on security-vendor reporting. The benchmark labels that distinction rather than treating the cases as equally observed or directly comparable.

### The seven tasks, in plain language

The short IDs are just labels: `INC` means the source incident, and `CASE` means the particular benchmark task. Each task gives the model an evidence packet and asks for the best-supported reconstruction, not a free-form guess.

- **CASE-001, the full RansomHub intrusion:** Put the reported activity in order, from password spraying and remote access through the later intrusion and ransomware deployment. The reference reconstruction contains 28 events.
- **CASE-002, the GTG-1002 espionage report:** Reconstruct Anthropic's account of the reported campaign, including what the operators attempted, what succeeded or failed, and what the report does not establish. The reference contains 17 events.
- **CASE-003, the extortion operation:** Reconstruct Anthropic's shorter account of a Claude Code-assisted data-extortion operation. This report has less step-by-step detail, so the reference reconstruction is smaller, with 8 events.
- **CASE-004, only the first day of the RansomHub case:** Revisit CASE-001 with later evidence removed. The model should not be penalized for events the supplied evidence cannot yet support; only 15 events are scored.
- **CASE-011, GTG-1002 framed as human-operated:** Use the campaign evidence while describing the operator as human-led.
- **CASE-012, the same evidence framed as AI-operated:** Keep the evidence identical to CASE-011 and change only the actor framing. Comparing these two scores gives an early look at sensitivity to wording; it cannot tell us who really operated the campaign.
- **CASE-013, AI-enabled credential harvesting:** Reconstruct Google's public account of a reported credential-harvesting campaign, keeping the sequence and links grounded in what that report says. Its reference reconstruction contains 7 events.

## Models Tested

I ran ten models from several providers against the same seven Kaggle tasks: **Gemini 3.7 Flash**, **Gemma 4 26B A4B**, **GLM-5**, **Grok 4.20 Reasoning**, **GPT-5.6 Luna**, **GPT-5.6 Sol**, **GPT-5.4 mini**, **Claude Sonnet 5**, **Claude Opus 5**, and **Qwen 3 Coder 480B**. The current benchmark view has a score for every model-task pair. Kaggle's overall score aggregates these seven tasks, which include related variants of the same incidents.

The table is the Kaggle leaderboard snapshot fetched on **2 October 2026**, after duplicate and failing task attachments were removed and the earlier evaluated versions restored. CASE-001 through CASE-011 use v3; CASE-012 and CASE-013 use their republished v1 versions. Values are EGRS percentages (Kaggle's 0-1 scores multiplied by 100). EGRS rewards recovering supported events and links, citing evidence, and representing uncertainty, while penalizing unsupported events. It is specific to this evidence-reconstruction task, not a general measure of intelligence or cybersecurity ability. Kaggle's overall score now matches the equal-weight mean across the seven task rows. Since some tasks are related variants of the same incidents, this is descriptive rather than an independent-sample leaderboard.

## Findings

| Kaggle task | Gemini Flash | Gemma 4 | GPT-5.6 Luna | GLM-5 | Grok 4.20 | Claude Sonnet 5 | Claude Opus 5 | GPT-5.6 Sol | GPT-5.4 mini | Qwen 3 Coder |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [CASE-001: Full RansomHub intrusion](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-001-reconstruct-inc-001-full/3) | 70.55 | 82.38 | 71.27 | 81.31 | 75.71 | 73.75 | 78.14 | 78.06 | 66.06 | 70.90 |
| [CASE-002: GTG-1002 espionage campaign](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-002-reconstruct-inc-002-full/3) | 79.72 | 77.21 | 80.31 | 76.22 | 83.60 | 65.05 | 68.16 | 76.71 | 69.68 | 76.30 |
| [CASE-003: Reported data-extortion operation](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-003-reconstruct-inc-003-full/3) | 76.31 | 92.11 | 84.50 | 83.80 | 84.97 | 73.11 | 71.50 | 76.12 | 84.35 | 70.31 |
| [CASE-004: RansomHub, first-day evidence only](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-004-reconstruct-inc-001-temporal-cutoff-d1/3) | 79.57 | 84.79 | 80.70 | 72.37 | 80.42 | 74.00 | 72.66 | 74.51 | 72.55 | 63.70 |
| [CASE-011: GTG-1002, human framing](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-011-reconstruct-inc-002-framing-framed-as-human/3) | 85.44 | 80.84 | 82.04 | 72.80 | 80.12 | 77.09 | 65.13 | 76.43 | 66.80 | 66.80 |
| [CASE-012: GTG-1002, AI-agent framing](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-012-reconstruct-inc-002-framing-framed-as-ai-agent-republished/1) | 77.13 | 76.91 | 79.82 | 76.83 | 70.87 | 78.42 | 69.74 | 69.42 | 68.48 | 67.53 |
| [CASE-013: Google's reported credential-harvesting campaign](https://www.kaggle.com/benchmarks/tasks/ujjavalasingh/cyber-autopsy-case-013-reconstruct-inc-004-full-republished/1) | 89.33 | 88.33 | 88.75 | 82.50 | 87.83 | 77.50 | 52.47 | 79.07 | 78.50 | 68.25 |
| **Kaggle overall** | **79.72** | **83.22** | **81.06** | **77.98** | **80.50** | **74.13** | **68.26** | **75.76** | **72.35** | **69.11** |

These are single runs, not stable model rankings. Gemma has the highest displayed overall score (83.22), followed by GPT-5.6 Luna (81.06) and Grok 4.20 (80.50). The standout case score is Gemma's 92.11 on the short extortion-report task; that is a case-specific result, not proof of general model superiority.

Several patterns stand out in these single runs:

- **Removing duplicates changed the aggregate, not the case results.** With one row per task, Kaggle's overall now matches the simple seven-task mean. The model order consequently differs from the earlier duplicate-inflated view; Grok is third overall in this snapshot.
- **The winner changes by case.** Gemma leads CASE-001 (82.38), CASE-003 (92.11), and CASE-004 (84.79); Grok leads CASE-002 (83.60); Gemini leads CASE-011 (85.44) and CASE-013 (89.33); GPT-5.6 Luna leads CASE-012 (79.82). The overall leader is not the top model on every task.
- **The first-day cutoff scores higher in this snapshot.** Gemini scores 79.57 on the day-one CASE-004 and 70.55 on full CASE-001, a 9.02-point gap. CASE-004 has a smaller gold graph (15 vs. 28 events), so this does not show that less evidence makes reconstruction easier.
- **The framing pair splits by model.** With identical evidence, human-framed minus AI-agent-framed scores range from +9.25 for Grok to -4.61 for Claude Opus 5. Gemini's gap is +8.31; five models score higher with human framing and five with AI-agent framing. This is an exploratory wording-sensitivity signal, not evidence about who operated the real campaign.
- **CASE-013 has a wide spread.** Gemini scores 89.33, while Claude Opus 5 scores 52.47 on the same reported campaign. That 36.86-point gap is a prompt- and case-specific result; one run cannot establish a stable capability difference.

CASE-013's reference has seven gold events, while the richer INC-001 case has 28. Raw EGRS should not be read as a ranking of real-world incident difficulty or attacker behavior. The Kaggle leaderboard provides the composite score; I have not treated older component-level run outputs as if they were measurements from these restored task versions. Next I would repeat each condition with multiple seeds and inspect whether missed causal links and failed actions recur. There are no repeated-trial confidence intervals, and all model comparisons here are single runs.

## Kaggle Gotchas

Building the benchmark involved a few Kaggle-specific failure modes that are worth recording because they affect task visibility and score continuity:

- **Task versions and benchmark versions are separate.** Pushing an existing task creates a new task version; it does not automatically change the version pinned in the benchmark. Scores belong to the exact task version that produced them. Switching a benchmark row to a new version does not carry the old models' scores across, so a new version can show `Fail` or blank cells until those models are run again.
- **Task metadata has a 255-character limit.** CASE-001 v4 was explicitly rejected because its description exceeded the limit. CASE-002's description also exceeded 255 characters, so we shortened it before publishing v5. Check both fields before pushing.
- **An uploaded notebook is not necessarily a usable task.** CASE-012 and CASE-013 uploads returned an entity-save error. Kaggle created version records that remained `Unspecified`, had no completed run, and could not be selected in **Add Tasks**. The benchmark displayed `Untitled Task` for those attachments. The recovery was to remove the failing attachments and add the earlier evaluated task versions, which restored the seven named rows and their saved scores.
- **The first model call can block task creation.** Fresh CASE-012/013 task records hit Gemini HTTP 429 (“model is currently experiencing heavy load”). A one-time bootstrap using a fixed model can also make subsequent model evaluations fail Kaggle's requirement to call `kbench.llm`. Keep the task model-agnostic, and do not assume a successful run under one fixed model makes it reusable across the leaderboard.
- **`Completed` is not the same as “all models finished.”** It confirms that task creation/its initial run completed. Check per-model run statuses separately, and distinguish an unrun model on a new version from a task-creation failure.
- **Visibility is independent of successful creation.** The benchmark and each task have their own visibility. Keep tasks private while they are drafts; make both the tasks and benchmark public only when the task records are valid and ready to share.

For the current results, the benchmark is pinned to the previously evaluated versions: CASE-001 through CASE-011 v3 and the republished CASE-012/013 v1 tasks. This keeps the benchmark rows named and retains their model scores while the failed newer uploads remain separate task records.

### Code Walkthrough

The model is asked for a structured reconstruction rather than a free-form incident summary. An event has a description, an evidence status, and evidence IDs; relationships connect event IDs:

```python
@dataclass
class ReconstructedEvent:
    event_id: str
    description: str
    status: str  # confirmed | inferred | unknown | attempted | failed
    evidence_ids: list[str] = field(default_factory=list)

@dataclass
class ReconstructedRelationship:
    source_event_id: str
    target_event_id: str
    relationship: str  # precedes | enables | causes | depends_on

@dataclass
class Reconstruction:
    events: list[ReconstructedEvent] = field(default_factory=list)
    relationships: list[ReconstructedRelationship] = field(default_factory=list)
    unknown_steps: list[str] = field(default_factory=list)
```

The task sends the incident packet with that schema, normalizes the structured response, and passes it to the deterministic scorer:

```python
message = SYSTEM_PROMPT + "\n\n" + build_user_prompt()
result = llm.prompt(message, schema=Reconstruction, seed=0, temperature=0)

prediction = to_prediction(result)
metrics = score_prediction(prediction, GOLD, VALID_EVIDENCE_IDS)
return metrics["egrs"] / 100.0
```

Event matching is one-to-one. Text similarity proposes candidate matches, cited evidence gives a fixed bonus, and a threshold filters weak matches:

```python
score = label_similarity(pe.get("description", ""), gn.get("label", ""))
if pe_ev and gn_ev and (set(pe_ev) & set(gn_ev)):
    score += EVIDENCE_BONUS
if score >= MATCH_THRESHOLD:
    candidates.append((score, pe["event_id"], gn["id"]))
```

EGRS combines recovery, precision, graph links, evidence attribution, status, uncertainty, and failed-action recognition, while subtracting a hallucination penalty:

```python
egrs = 100.0 * max(
    0.0,
    0.25 * recall + 0.20 * precision + 0.15 * link_f1
    + 0.15 * evidence_attribution + 0.10 * status_accuracy
    + 0.10 * unknown_calibration + 0.05 * failed_recognition
    - 0.25 * hallucination_rate,
)
```

This makes unsupported certainty costly while giving the model credit for preserving uncertainty and citing the evidence behind its reconstruction.

## My Benchmark

The live [Cyber Autopsy Kaggle benchmark and leaderboard](https://www.kaggle.com/benchmarks/ujjavalasingh/cyber-autopsy-benchmark) groups the seven restored task versions. Scores above were fetched on 2 October 2026. Individual evaluated task versions, including the restored CASE-012 and CASE-013 records, are linked in the results table.

### Expanded Case Set

Since collecting those leaderboard results, I expanded the case set with seven follow-on tasks. They will use the same sequential model-evaluation workflow as the existing tasks. The cases broaden the evidence types and incident behaviors under study:

- **CASE-014, the Medicare statistics portal incident:** Australian Government [briefings](https://www.pm.gov.au/media/press-conference-new-york) describe an AI agent that encountered blocks, tried alternative ways to obtain information, and accessed infrastructure behind a public statistics portal. The personal Medicare claims and payments system is separate; officials said no personal information was believed accessed at the time, with the investigation still underway.
- **CASE-015, the Hong Kong transfer scam:** an official [Legislative Council reply](https://www.info.gov.hk/gia/general/202406/26/P2024062600192p.htm) describes a phishing email, a prerecorded executive video meeting, follow-up instructions by instant message, and transfers totalling about HK$200 million. The source does not name the company, and police's account of the source media remains qualified.
- **CASE-016, the BumbleBee-to-Akira intrusion:** a [forensic report](https://thedfirreport.com/2026/06/29/from-bing-search-to-ransomware-bumblebee-and-adaptixc2-deliver-akira-3/) traces a poisoned software-search result through intrusion, data theft, and ransomware. That report also describes a separate Swisscom case, which is explicitly excluded from this task's timeline.
- **CASE-017 and CASE-018, Midnight Blizzard:** Microsoft's [January disclosure](https://www.microsoft.com/en-us/msrc/blog/2024/01/microsoft-actions-following-attack-by-nation-state-actor-midnight-blizzard) and [March update](https://www.microsoft.com/en-us/msrc/blog/2024/03/update-on-microsoft-actions-following-attack-by-nation-state-actor-midnight-blizzard) form two knowledge snapshots of the same intrusion. This pair tests whether a reconstruction changes appropriately as disclosure evolves; it is not two independent incidents.
- **CASE-019, Change Healthcare:** the initial [SEC filing](https://www.sec.gov/Archives/edgar/data/731766/000073176624000045/unh-20240221.htm) and CEO's [Senate testimony](https://www.finance.senate.gov/imo/media/doc/0501_witty_testimony.pdf) describe the access path, ransomware timeline, service disruption, and evolving patient-data findings. The CEO's attribution and impact statements remain source-attributed claims.
- **CASE-020, UNC5537 and Snowflake customer instances:** [Mandiant's campaign report](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion) adds credential-theft, cloud data access, and extortion. It is deliberately modeled as a multi-victim campaign, not a single victim or a breach of Snowflake's corporate systems.

These additions broaden the evaluation set, but they do not create a controlled human-versus-AI experiment: actor type, source quality, and incident context differ. The gold graphs are undergoing independent review; the leaderboard snapshot above remains the results for the seven task versions already shown there.

<!-- Add a cover image URL here before publishing on DEV.to. -->
