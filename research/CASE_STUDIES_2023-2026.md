# Cyber Incident Case-Study Research (2 Oct 2023 to 2 Oct 2026)

Research inventory for broadening the Cyber Autopsy evaluation set. The date
window applies to the **incident activity**, not the date an article or inquiry
was published. A case is not automatically benchmark-ready just because it is
well known: source depth, bounded timeline, provenance, and uncertainty all
matter. Links below point to original or primary sources where available.

## What We Want To Learn

The expanded corpus should help distinguish model capability from differences
in the underlying reports. In particular, it should cover:

- human-operated, AI-assisted, and AI-agent activity without assuming that an
  incident's use of AI makes it comparable to a human intrusion;
- initial access, identity abuse, cloud/SaaS compromise, espionage, ransomware,
  data theft, fraud, and attempted or disrupted operations;
- detailed host/network telemetry, government findings, company disclosures,
  and vendor campaign assessments as separate evidence classes;
- early disclosures versus later findings, explicit unknowns, contradictions,
  attribution confidence, and impact revisions;
- both successful incidents and failed attempts, so models are not rewarded
  for assuming every reported attack achieved its objective.

## Included In The Corpus

These entries are represented in the repository's incident and benchmark data
and are part of the expanded evaluation set. Draft labels refer to gold-graph
review status, not a decision to keep tasks local.

| Incident / case | Activity date | What it can test | Evidence caveat |
|---|---|---|---|
| INC-001 / CASE-001, RansomHub intrusion | Nov 2024 | Detailed human-operated intrusion, password spraying, lateral movement, exfiltration, ransomware, and false associations | Single forensic report; victim anonymized. [DFIR Report](https://thedfirreport.com/2025/06/30/hide-your-rdp-password-spray-leads-to-ransomhub-deployment/) |
| INC-002 / CASE-002, GTG-1002 espionage | Sep 2025 | Reported AI-orchestrated operations, human decision points, and documented AI errors | Anthropic's own platform telemetry; no public victim-side logs. [Anthropic](https://www.anthropic.com/news/disrupting-AI-espionage) |
| INC-003 / CASE-003, AI-assisted data extortion | 2025 | Human-in-the-loop AI assistance and strategic decision-making | Anthropic vendor account; some illustrative artefacts are simulations and must not be treated as evidence. [Anthropic](https://www.anthropic.com/news/detecting-countering-misuse-aug-2025) |
| INC-004 / CASE-013, AI-enabled credential harvesting | 2026 | Reported autonomous multi-agent workflow and fast campaign execution | Google/Mandiant report; victim, model, and victim-side telemetry are not public. [GTIG/Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/from-prompting-to-autonomy-the-evolution-of-adversarial-ai) |
| INC-005 / CASE-014, Medicare statistics portal | Jun 2026 | AI-agent boundary crossing, response timeline, and preliminary impact statements | Australian Government briefings; investigation was ongoing and the portal is not the personal Medicare claims service. [Prime Minister transcript](https://www.pm.gov.au/media/press-conference-new-york), [Defence/Services Australia transcript](https://www.minister.defence.gov.au/transcripts/2026-09-24/press-conference-sydney) |
| INC-006 / CASE-015, Hong Kong deepfake transfer fraud | Jan 2024 | Executive impersonation, synthetic media, human verification failure, and financial impact | Official source leaves the company unnamed; the police account qualifies the media-generation claim. [Hong Kong Government](https://www.info.gov.hk/gia/general/202406/26/P2024062600192p.htm) |
| INC-007 / CASE-016, BumbleBee to Akira | 2025 | Search-result poisoning, trojanized software, ransomware progression, and timeline reconstruction | One report contains two intrusions; the local graph deliberately excludes Swisscom-specific activity. [DFIR Report](https://thedfirreport.com/2026/06/29/from-bing-search-to-ransomware-bumblebee-and-adaptixc2-deliver-akira-3/) |
| INC-008 / CASE-017 and CASE-018, Midnight Blizzard | Nov 2023 onward | Same incident represented at January and March disclosure cutoffs; useful for testing update-sensitive reasoning and temporal knowledge | Microsoft is both victim and source; January and March statements differ in scope. [Initial disclosure](https://www.microsoft.com/en-us/msrc/blog/2024/01/microsoft-actions-following-attack-by-nation-state-actor-midnight-blizzard), [March update](https://www.microsoft.com/en-us/msrc/blog/2024/03/update-on-microsoft-actions-following-attack-by-nation-state-actor-midnight-blizzard) |
| INC-009 / CASE-019, Change Healthcare | Feb 2024 | Healthcare operations, remote-access identity controls, ransomware, and evolving data-impact claims | Initial regulatory filing and later CEO testimony are different disclosure stages; testimony is not independent forensics. [SEC filing](https://www.sec.gov/Archives/edgar/data/731766/000073176624000045/unh-20240221.htm), [Senate testimony](https://www.finance.senate.gov/imo/media/doc/0501_witty_testimony.pdf) |
| INC-010 / CASE-020, UNC5537 Snowflake campaign | 2024 | Infostealer credential reuse, SaaS data theft and extortion across multiple organizations | Campaign-level report, not a single victim reconstruction or Snowflake corporate breach. [Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion) |

## Additional Source Leads

The first three rows below are now represented in the corpus. The rest
are leads for later ingestion; keep each incident's reporting stages separate
when later disclosures materially change the known scope or sequence.

| Candidate | Activity / disclosure | Why it adds useful signal | Source and caution |
|---|---|---|---|
| Microsoft Midnight Blizzard corporate compromise (INC-008; ingested) | Began late Nov 2023; disclosed Jan 2024; updated Mar 2024 | Staged disclosure; password spray, legacy test tenant, corporate email, then later source-repository/internal-system access claims | Microsoft is victim and source; preserve time-bounded claims. [Initial](https://www.microsoft.com/en-us/msrc/blog/2024/01/microsoft-actions-following-attack-by-nation-state-actor-midnight-blizzard), [Jan guidance](https://www.microsoft.com/en-us/security/blog/2024/01/25/midnight-blizzard-guidance-for-responders-on-nation-state-attack/), [March update](https://www.microsoft.com/en-us/msrc/blog/2024/03/update-on-microsoft-actions-following-attack-by-nation-state-actor-midnight-blizzard). |
| Change Healthcare ransomware and data theft (INC-009; ingested) | Feb 2024; Senate testimony May 2024 | Healthcare disruption, remote access without MFA, lateral movement, exfiltration, ransomware, and evolving PHI/PII scope | CEO testimony is a company account in a public hearing, not independent technical forensics. [Testimony](https://www.finance.senate.gov/imo/media/doc/0501_witty_testimony.pdf), [SEC filing](https://www.sec.gov/Archives/edgar/data/731766/000073176624000045/unh-20240221.htm). |
| UNC5537 Snowflake customer-instance campaign (INC-010; ingested) | 2024; public campaign report Jun 2024 | Infostealer credential reuse, SaaS/database access, data theft and extortion | Multi-victim campaign, not one victim incident; no implication that Snowflake corporate systems were breached. [Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion). |
| UNC3944 / Scattered Spider SaaS intrusions | Activity from early 2024; report 2024 | Social engineering, identity-provider privilege abuse, cloud/SaaS access, and data exfiltration | [Google Cloud / Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications). Aggregate reporting spans multiple engagements; select a bounded victim timeline only if evidence supports it. |
| UNC3944 SMS phishing and SIM swapping | Activity during 2023; report 2023 | Human-operated social engineering, identity takeover, ransomware and extortion; a useful non-AI counterpoint | [Google Cloud / Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-sms-phishing-sim-swapping-ransomware/). The source summarizes multiple intrusions; avoid presenting the composite as one attack. |
| 2025 ransomware intrusion patterns | Activity during 2025; report 2026 | Brute force over long dwell periods, ransomware identification, and variation across cases | [Google Cloud / Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/ransomware-ttps-shifting-threat-landscape). Report is an aggregate; mine it only for individually bounded examples with explicit timelines. |
| UNC3944 VMware vSphere campaign | Mid-2025; report 2025 | Cross-domain access, help-desk social engineering, hypervisor targeting, and extortion | [Google Cloud / GTIG](https://cloud.google.com/blog/topics/threat-intelligence/defending-vsphere-from-unc3944). Multi-target campaign; victim-specific sequence and attribution confidence need careful extraction. |
| Cambodia/Thailand AI-enabled scam-center cases | Late 2024 to early 2025; research report 2025 | AI voice cloning and real-time deepfake use in impersonation and investment/romance fraud; expands beyond enterprise intrusion | [UNODC report](https://www.unodc.org/documents/Reports/UNODC_Report_Emerging_threats_-_The_intersection_of_criminal_and_technological_innovation_in_the_use_of_automation_and_AI.pdf). Secondary synthesis of law-enforcement cases; obtain the cited underlying records before making a gold graph. |
| Attempted deepfake call targeting U.S. Senator Ben Cardin | 2024 | Failed social-engineering attempt; model should infer interruption and lack of disclosed compromise, not invent a successful breach | [Associated Press report](https://apnews.com/article/senator-cardin-deepfake-video-call-ukraine-4bda61e99d3d0de7da470d2b4f8f0de5). Secondary report; seek Senate or State Department primary documentation and avoid scoring uncorroborated attribution. |

## Research-Only References And Exclusions

Useful reading does not always qualify as a benchmark incident. These examples
should remain research references or be excluded under the date/method rules:

| Item | Decision | Reason |
|---|---|---|
| Microsoft's Storm-0558 / Exchange Online compromise | Exclude from the incident window; retain as comparative background | Intrusion activity occurred May-June 2023, before 2 Oct 2023, although the CISA Cyber Safety Review Board report was published in 2024. [CSRB report](https://www.cisa.gov/sites/default/files/2024-03/CSRB%20Review%20of%20the%20Summer%202023%20MEO%20Intrusion%20Final_508c.pdf) |
| 23andMe credential-stuffing breach | Exclude under a strict incident-activity cutoff | ICO says credential stuffing ran April-September 2023; later discovery, publication, or enforcement does not shift the attack into the window. [UK ICO](https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2025/06/23andme-fined-for-failing-to-protect-uk-users-genetic-data/) |
| IcedID-to-Dagon Locker intrusion | Exclude under a strict incident-activity cutoff | A 2024 report described an intrusion chain that began in August 2023. [DFIR Report](https://thedfirreport.com/2024/04/29/from-icedid-to-dagon-locker-ransomware-in-29-days/) |
| UNC3886 VMware espionage report | Exclude from this window unless a distinct in-window intrusion is supported | The report describes long-running activity with key compromises predating the window. [Google Cloud / Mandiant](https://cloud.google.com/blog/topics/threat-intelligence/uncovering-unc3886-espionage-operations) |
| Broad AI misuse or threat-trend reports | Research-only, not one incident | Aggregated trends are valuable context but do not provide one bounded sequence and gold outcome. Example: [Google GTIG adversarial AI misuse](https://cloud.google.com/blog/topics/threat-intelligence/adversarial-misuse-generative-ai). |

## Research For Interpreting Model Results

These papers and benchmarks help explain what model scores do and do not mean.
They are related work, not extra incident records, and their headline numbers
should not be compared directly with Cyber Autopsy because the tasks, prompts,
models, tools, datasets, and scoring rules differ.

| Work | Focus | Relevance to Cyber Autopsy |
|---|---|---|
| [GenDFIR (2024)](https://arxiv.org/abs/2409.02572) | LLM plus retrieval-augmented generation for cyber incident timeline analysis | Closest conceptual match to reconstructing timelines from evidence. It motivates retrieval and semantic enrichment, but is not the same multi-source, evidence-citation and calibrated-unknown task. |
| [SECURE (2024)](https://arxiv.org/abs/2405.20441) | Seven cybersecurity-specific language-model evaluation tasks across multiple models | Useful reminder that “cyber capability” is not one scalar. Task-specific results matter; it does not test reconstruction of one incident graph from a supplied evidence packet. |
| [CyberSecEval 2 (2024)](https://arxiv.org/abs/2404.13161) | Broad suite covering cybersecurity risks and capabilities of LLMs | Context for evaluating cyber helpfulness and risk. Its cyberattack-helpfulness and code-related tasks differ from post-incident reconstruction and should not be conflated with operational attacker capability. |
| [CFA-Bench (2025)](https://iris.polito.it/handle/11583/3002951) | Forensic LLM-agent tasks including incident response, evidence correlation, and attribution | Close neighboring work; compare task construction and agent/tool conditions, not raw scores. |
| [CyberThreat-Eval (2025)](https://www.microsoft.com/en-us/research/publication/cyberthreat-eval-can-large-language-models-automate-real-world-threat-research/) | Real-world threat research with actionable detail rather than lexical-overlap-only metrics | Supports scoring grounded utility and detail, and highlights why exact string overlap is weak for incident narratives. It evaluates threat research, not a fixed gold attack graph. |
| [CTIConnect (2025/2026)](https://cticonnect.github.io/) | Retrieval-augmented question answering over heterogeneous cyber threat intelligence | Relevant to source retrieval and heterogeneous evidence. Retrieval access and document-grounding are additional variables not measured by our fixed evidence packets. |
| [Cybench (2024)](https://arxiv.org/abs/2408.08926) | Agent performance on professional-level capture-the-flag challenges across multiple models | Measures interactive task-solving in sandboxed environments, not reading and reconstructing real incident reports. Useful contrast for knowledge versus action capability. |
| [CVE-Bench (ICML 2025)](https://proceedings.mlr.press/v267/zhu25i.html) | AI-agent ability to exploit real-world web vulnerabilities in a controlled benchmark | An action/exploitation benchmark. Do not infer from those results that a model can or cannot produce an accurate forensic reconstruction. |
| [Cybersecurity AI Benchmark / CAIBench (2025)](https://arxiv.org/abs/2510.24317) | Meta-benchmark spanning CTF, cyber range, knowledge, attack/defense, and privacy tasks | Particularly relevant to interpretation: cybersecurity knowledge does not imply agentic attack/defense skill. Cyber Autopsy tests a different dimension: evidence-grounded reconstruction. |
| [LLMs Cannot Reliably Identify and Reason About Security Vulnerabilities (2024)](https://doi.org/10.1109/SP54263.2024.00210) | Multi-faceted evaluation of vulnerability detection and reasoning | Supports separating accurate narrative reasoning from code-level vulnerability identification. |

Across these works, a useful reporting discipline is to state the model and
version, exact prompt and tool access, evidence provided, run count/variance,
metric definition, and whether the result measures knowledge, retrieval,
reasoning, or action. The current Kaggle scores are one run per model-task and
the benchmark tasks mix source types and graph sizes; they are descriptive
observations, not a universal model ranking or evidence of real-world attacker
capability.

## Ingestion And Quality Rules

1. Record event start, discovery, disclosure, and update dates separately. The
   window test is based on incident activity, not when it became news.
2. Prefer primary government records, victim disclosures, court/regulatory
   filings, or named incident-response telemetry. Keep source type and source
   cluster visible; two pages repeating one company's account are not two
   independent confirmations.
3. Archive exact source bytes and hashes where access permits. If a source is
   browser-readable but blocks archival retrieval, record that limitation; do
   not invent a content hash.
4. Preserve claim attribution and time: “the company said no evidence as of
   date X” is not equivalent to “no compromise occurred.” Track later updates
   as separate evidence, not silent corrections.
5. Do not merge incidents just because a report groups them. Campaign-level
   records must be labeled campaign-level; victim-level gold requires a bounded
   victim and timeline.
6. Separate observed facts, analyst assessments, source claims, negative
   evidence, unknowns, and contradictions. Avoid turning lack of disclosure
   into evidence of absence.
7. For AI cases, record the actor's use of AI as a reported claim, the named
   model only when disclosed, the human decision points, and observed AI
   failures. Do not infer autonomy from automation or infer attacker AI use
   from a scam involving synthetic media.
8. Before a case becomes a scored Kaggle task, require independent review of
   the graph and prompt, check for test-set/training-data leakage, and disclose
   comparability limits. The present Kaggle leaderboard remains the historical
   seven-task result set; this research backlog does not change those scores.

## Next Ingestion Order

1. Obtain independent review for the four new tasks and their source attribution;
   do not treat structural/offline validation as gold-label verification.
2. Seek victim-specific source material for one UNC3944 SaaS intrusion and one
   AI scam-center case before adding more composite cases.
3. Expand with selected CISA advisories, regulator reports, court filings, and
   forensic case reports after checking incident dates and source provenance.
