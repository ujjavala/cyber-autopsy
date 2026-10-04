*This is a submission for the [Sanity Challenge, Path Two: Vibe-Code Something Strange](https://dev.to/challenges/sanity-2026-09-16)*

## What I Built

Cyber Autopsy is a cyber-forensics investigation room for asking structured
questions about an incident: what happened, what came before it, which evidence
supports it, what remains unknown, and what was knowable at a specific point in
time.

The project started as a Kaggle-style benchmark for evaluating whether an AI
can reconstruct an attack from fragmented reports without presenting guesses as
facts. I added Sanity as the structured content layer, an MCP-compatible
investigation server, and a forensic-themed web interface.

The core model preserves the relationships that make an investigation useful:

```text
Evidence ──supports──> Event ──precedes/enables/causes──> Event
Evidence ──supports/contradicts──> Claim
```

The UI presents each case as a small investigation console. Investigators can
select a case, read its incident description, ask a question, and inspect the
result as a reconstruction, structured event relationships, uncertainty list,
contradictory claims, and expandable evidence with source provenance.

### Why this helps cybersecurity investigations

Cybersecurity autopsy is an evidence-reconstruction problem. Analysts rarely
receive one perfect timeline; they receive authentication logs, endpoint
observations, threat reports, analyst notes, negative findings, and competing
claims. The difficult part is deciding how those pieces relate without
overstating what they prove.


![Image1](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/etdcz7onoqs6lo4tg13o.png)


Cyber Autopsy uses Sanity to make that reasoning inspectable. An analyst can
follow an event back to its supporting evidence, move through the attack graph,
check whether a claim is contradicted, and distinguish `confirmed`, `inferred`,
`attempted`, and `unknown`. This is useful for:

- reconstructing initial access, lateral movement, persistence, exfiltration,
  and impact
- producing incident timelines that retain provenance instead of flattening
  everything into a narrative summary
- testing what investigators could have known at a day-one cutoff
- comparing the same evidence under different actor framings
- teaching analysts and evaluating agents on calibrated uncertainty

The result is closer to a digital incident autopsy than a generic search box:
the system preserves the chain of evidence, the gaps in the record, and the
reasoning boundaries around each conclusion.

## Demo

The deployed demo is available at [https://cyber-autopsy.vercel.app](https://cyber-autopsy.vercel.app).
It serves the forensic UI and the Sanity-backed `/api/cases` and
`/api/investigate` routes and is publicly reachable for the competition demo.

Run the project locally when you want to inspect or modify it:

```sh
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).



![Image2](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/j24zrpfq7o7ty56iuri9.png)




## Code

The repository contains the Python benchmark, Sanity Studio, importer, MCP
server, local UI, tests, and documentation.

Repository: https://github.com/ujjavala/cyber-autopsy

Deployment: https://cyber-autopsy.vercel.app

The most relevant implementation files are:

```text
studio-cyber-autopsy/schemaTypes/index.ts  Sanity content model
scripts/sanity-seed.mjs                    repeatable JSONL importer
agent/sanity-context.mjs                   scoped GROQ investigation context
agent/mcp-server.mjs                       MCP tool surface
web/app.js                                 investigation UI behavior
web/style.css                              cyber-forensics console theme
```

## My Build Process

### AI-native IDE

I built the project collaboratively in Codex, using the repository as the
shared workspace. I started by reading the existing benchmark, data model,
frontend, Sanity Studio, and environment configuration. The implementation was
then developed in small verified phases so each change could be tested against
the real Sanity dataset and the existing Python benchmark.

### Prompts that worked

The most effective prompts were specific about both the user experience and
the evidence model:

```text
Integrate the existing Cyber Autopsy benchmark with Sanity. Preserve the
relationships between evidence, events, claims, sources, and investigation
cases. Add a repeatable importer and a context layer that can answer scoped
questions without leaking later evidence into temporal-cutoff cases.
```

```text
The Sanity dataset can be empty or partially populated. Make the UI handle
empty arrays and API errors explicitly instead of throwing when reading length.
Test every investigation scenario after the fix.
```

```text
Make the interface feel like a cyber-forensics lab: improve hierarchy,
case descriptions, icons, status signals, loading feedback, responsive layout,
and subtle motion while keeping the investigation workflow easy to scan.
```

### Where the build got stuck

The first Sanity-backed UI path assumed that the selected case always had a
populated evidence array. When the dataset was empty or the query returned an
unexpected shape, the browser surfaced:

```text
Cannot read properties of undefined (reading 'length')
```

The correction was to make the context and UI defensive: seed and validate the
dataset, distinguish a missing case from an empty evidence scope, and render a
clear error or empty state instead of dereferencing an undefined array.

Another important correction was temporal scoping. CASE-004 shares the
RansomHub incident with CASE-001 but only exposes day-one evidence. The context
now filters events, relationships, claims, and evidence against the selected
case boundary before returning the investigation result.

### Course corrections and testing

The build evolved through these corrections:

1. Added seven Sanity document types instead of storing one large incident
   blob: incidents, sources, evidence, events, relationships, claims, and
   investigation cases.
2. Added explicit references and reverse-reference patches so provenance can be
   followed in both directions.
3. Added scoped GROQ queries and MCP tools for case listing and investigation.
4. Added case descriptions because the case IDs alone were too cryptic for a
   human investigator.
5. Reworked the UI into a forensic console with status badges, trace labels,
   loading state, evidence panels, and uncertainty sections.
6. Added a favicon, README startup guide, Sanity integration write-up, and
   challenge-specific documentation.
7. Ran the full Python suite, Sanity import validation, Studio build, syntax
   checks, browser scenarios, and browser console-error checks.

The final verification included 229 Python tests, a Sanity inventory of 457
production documents, live CASE-001 and CASE-004 investigations, evidence
provenance checks, cutoff checks, and zero browser console errors. The hosted
Sanity Context Knowledge Base was also created and checked through its
read-only MCP tools; that hosted integration is the Path One capability, while
this post focuses on the strange forensic product and its build process.

### Sanity integration in the build

#### How Sanity helped

Sanity gave the project a durable, queryable content layer for the benchmark's
investigation graph. Before the integration, the dataset was primarily a group
of local JSONL files. That was reproducible, but it made the content harder to
inspect, connect, and reuse across an agent, a Studio, and a browser UI.


![Image3](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/67r5x02pjfxoz82pgn7s.png)


With Sanity, the same investigation content is modelled as linked documents.
Evidence, events, claims, relationships, incidents, and sources can be queried
independently or traversed together. This helped in four practical ways:

1. **Grounding:** an MCP-capable agent can retrieve the exact evidence and relationships
    relevant to a case instead of relying on a loose text search.
2. **Traceability:** every result can point back to evidence and source
   provenance, which makes an analyst's review possible.
3. **Scope control:** case-specific references and cutoff rules can be enforced
   in the query layer, preventing later facts from leaking into an earlier
   reconstruction.
4. **Reuse:** the same structured content model powers Sanity Studio, the
   importer, MCP server, validation workflow, and forensic UI.


![Image4](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/s4nng042udrm0gr30itv.png)


Sanity therefore acts as the investigation knowledge base, while the context
layer acts as the reasoning boundary. The agent is not asked to remember an
incident or invent a timeline; it queries structured content and returns a
calibrated reconstruction.

#### Sanity features used

##### 1. Structured document schemas

Instead of storing one large incident document, I modeled the investigation as
separate document types. This matches the way a forensic analyst works: an
incident is the case context, evidence is an observation, an event is a
reconstruction, a claim is an assertion, and a relationship explains how two
events connect.

The separation gives each kind of information a clear validation and query
boundary. For example, an `event` has a status and confidence, while an
`evidence` document has a timestamp, observation type, entities, and source
references. A `relationship` has a source event, target event, relation type,
and supporting evidence.

##### 2. References and graph-shaped content

The most important Sanity feature here is the reference field. Evidence does
not copy an event's text, and a relationship does not copy both event records.
They point to the canonical documents:

```ts
defineField({
  name: 'sourceEvent',
  type: 'reference',
  to: [{type: 'event'}],
  validation: (rule) => rule.required(),
})

defineField({
  name: 'evidence',
  type: 'array',
  of: [defineArrayMember({type: 'reference', to: [{type: 'evidence'}]})],
})
```

This turns Sanity into a navigable investigation graph. The agent can traverse
`case -> incident -> event -> evidence -> source`, then separately retrieve
`relationship` and `claim` documents for the same incident. In the UI, that
becomes a reconstruction with visible provenance instead of an unsupported
paragraph.

##### 3. Field validation and controlled statuses

The Studio schema validates required identifiers and references, constrains
confidence to the range `0..1`, and uses controlled options for evidence and
event status. The available status taxonomy is deliberately forensic:

```text
confirmed · inferred · attempted · failed · unknown
```

Claims additionally support `contradicted`. These values are used in the UI to
separate established facts from uncertain or failed steps. This prevents a
missing observation from silently becoming a confirmed event and makes
calibrated uncertainty part of the content model.

##### 4. GROQ projections and dereferencing

The context layer uses GROQ projections to request only the fields required by
an investigation. The `->` operator dereferences related documents so one
response can contain the case, incident summary, evidence, and source metadata
without the browser making a request for every individual record.

For example, the case query projects the incident and joins its evidence and
events:

```groq
*[_type == "investigationCase" && caseId == $caseId][0] {
  caseId, mode, temporalCutoff, framingActor,
  incident->{incidentId, title, description, actor, impact},
  evidence[]->{evidenceId, timestamp, type, description, status,
    source[]->{sourceId, title, publisher, url}},
  events[]->{eventId, description, timestamp, status,
    evidence[]->{evidenceId}}
}
```

This is useful for security analysis because the response remains structured.
The agent can filter on timestamps, statuses, evidence IDs, and relationship
types instead of trying to recover those distinctions from prose.

##### 5. Parameterized, scoped queries

Queries are parameterized with `caseId` and `incidentRef`. The selected case
defines the visible evidence set, and the context derives a set of allowed
evidence IDs before returning events, relationships, or claims. A relationship
is included only when its supporting evidence and both endpoint events are in
scope.

This is how the implementation handles temporal safety. `CASE-004` is not just
a label in the UI; its Sanity references define the evidence boundary. A
day-one question can also apply an additional D1 filter before the result is
rendered. The model cannot accidentally cite a later ransomware event as if it
were known on day one.

##### 6. Sanity Content API

The Node context uses Sanity's Content API with the project ID, dataset, GROQ
query, and optional server-side token. The token is loaded from `.env` on the
server and is never exposed to the browser. The browser talks to the local web
server, while the local server talks to Sanity.


![Image5](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/f2tnyydjnqh2c2b62c78.png)



That separation gives the project a safer shape:

```text
Browser UI → local investigation API → Sanity Content API
                                      ↑
                              server-side token
```

The same API boundary also makes failures explicit. A missing case produces a
clear error, while an empty evidence set is handled as an empty investigation
scope rather than causing a client-side `length` exception.

##### 7. Sanity Studio, Structure Tool, and Vision

The project includes a standalone Sanity Studio configured for the same project
and `production` dataset. The Structure Tool provides the editing workspace
for the seven document types, with previews showing useful forensic identifiers
such as `CASE-004`, `E-021`, or an event description.

The Vision Tool is enabled for inspecting and testing GROQ directly in Studio.
That is useful when developing an investigation query: I can verify a case
projection, inspect references, and test a cutoff query against the real
dataset before wiring it into the MCP context.

##### 8. Transactional mutations and repeatable import

The importer uses Sanity mutations in batches rather than hand-editing hundreds
of documents. It creates or replaces the normalized documents in dependency
order, then applies reverse-reference patches for evidence-to-event,
evidence-to-claim, and contradiction links.

The import is repeatable and testable:

```sh
npm run sanity:validate       # validate source inventory
node scripts/sanity-seed.mjs --dry-run
npm run sanity:seed           # write the content to Sanity
```

This gives the benchmark a reproducible migration path while keeping the live
knowledge base editable in Studio. It also means the dataset can be rebuilt if
the schema gains another forensic field later.

##### 9. MCP as the agent boundary

Sanity stores and retrieves the content; the MCP server exposes investigation
capabilities to an agent host. The server provides `list_investigation_cases`
and `investigate_case(caseId, question)`. Internally, those tools call the same
Sanity context used by the web UI.

This division is intentional. Sanity is responsible for content modeling,
relationships, querying, and provenance. The context layer is responsible for
case scoping and graph filtering. The MCP layer is responsible for making those
grounded operations available to an agent. The agent can therefore reason over
retrieved evidence without receiving unrestricted access to the whole dataset.

#### Content model

Sanity stores seven document types:

- `incident`: case narrative, actor, impact, confidence, and source references
- `source`: publisher, URL, publication date, type, and reliability
- `evidence`: an observation with timestamp, status, description, and provenance
- `event`: a reconstructed action or state with evidence references
- `relationship`: a typed link between events
- `claim`: an assertion that can be supported or contradicted
- `investigationCase`: a benchmark scope with mode, cutoff, and actor framing

The schema is defined with Sanity's typed helpers:

```ts
defineField({
  name: 'supportsEvents',
  type: 'array',
  of: [defineArrayMember({type: 'reference', to: [{type: 'event'}]})],
})

defineField({
  name: 'relationship',
  type: 'string',
  options: {list: ['precedes', 'enables', 'causes', 'depends_on']},
})
```

IDs from the benchmark remain explicit and stable: `INC-001`, `E-001`, `N01`,
and `CASE-004`. This makes the imported content easy to inspect in Studio and
keeps evidence references understandable in the investigation output.

#### Importing the knowledge base

The JSONL files under `data/` remain the reproducible source of truth. The
importer maps them into Sanity documents:

```text
incidents.jsonl       → incident
sources.jsonl         → source
evidence.jsonl        → evidence
attack_graphs.nodes   → event + claim
attack_graphs.edges   → relationship
benchmark_cases.jsonl → investigationCase
```

The importer writes documents in dependency order and applies reverse evidence
references in a second pass because events and evidence point to each other.

```sh
npm run sanity:validate
node scripts/sanity-seed.mjs --dry-run
npm run sanity:seed
```

The current Sanity production dataset contains 457 documents: 445 imported
Cyber Autopsy documents plus 12 existing project documents. The hosted
Context Knowledge Base is built and ready with 46 focused sources covering
incidents, investigation cases, and source records.

#### Context queries and agent behavior

`agent/sanity-context.mjs` uses scoped GROQ queries. It does not download the
entire dataset for every question:

```groq
*[_type == "investigationCase" && caseId == $caseId][0] {
  caseId, mode, temporalCutoff, framingActor,
  incident->{incidentId, title, actor, actorType},
  evidence[]->{evidenceId, timestamp, type, description, status,
    source[]->{sourceId, title, publisher, url}},
  events[]->{eventId, description, timestamp, status,
    evidence[]->{evidenceId}}
}
```

The context then resolves relationships and claims and filters them against the
case's allowed evidence IDs. That filtering is the temporal safety boundary:
`CASE-004` can answer what was knowable at the end of day one without leaking
later ransomware evidence from the full case.

The MCP server exposes two tools:

```text
list_investigation_cases
investigate_case(caseId, question)
```

The investigation function maps question intent to structured graph operations:
predecessors, enablers, supporting evidence, statuses, cutoff checks, actor
framing, and contradictions. The result is deterministic, grounded in Sanity
content, and designed to be passed to a model without requiring another model
API key in this repository.

## Sanity Project Details

```text
Project ID: 41l9o4xn
Dataset: production
Organization ID: oqf9m6vy6
Knowledge Base ID: kbZHPSeMHnZt
Hosted Studio: https://cyber-autopsy-ujjavala.sanity.studio/
```

The public Sanity project details are intentionally included so the structured
content model can be inspected. The hosted Studio is deployed from the Sanity
Studio schema, and the Context Knowledge Base is built from a curated source
of the production dataset. The server-side tokens stay in `.env`, are ignored
by Git, and are never sent to the browser.

## Agent Session

The local agent is available through the MCP server:

```sh
npm run agent:mcp
```

The project also has a hosted Sanity Context MCP endpoint for agents that can
connect to MCP. It is the read-only retrieval path used for the Path One
integration and exposes the Knowledge Base through `initial_context`,
`knowledge_base_search`, and `knowledge_base_read`. The endpoint URL is kept
in the repository's environment configuration rather than hard-coded into the
application, and no token is included in this post. The curated native-session
record is included inline below for transparency.

```text
Prompt: Query the hosted Sanity Context Knowledge Base read-only and explain
how CASE-001 moved from initial access to ransomware deployment.

MCP calls: initial_context -> knowledge_base_search -> knowledge_base_read.
The search returned RansomHub-related records and the read returned
dataset-backed provenance identifiers. The agent preserved the boundary that
retrieved content must not be stitched into unsupported claims. Codex reached
the real content but hit its usage limit before the final narrative answer.
```

The browser UI uses the same investigation context and exposes the workflow in
a more approachable way:

1. Choose a case from the case selector. The description explains the incident
   before you ask a question.
2. Read the case badges for full, temporal cutoff, progressive,
   counterfactual, or actor-framing scope.
3. Enter a question or choose a suggested investigation prompt.
4. Run the investigation and inspect the trace-numbered reconstruction.
5. Expand evidence records to verify the source and provenance yourself.

Useful sessions to capture for the final submission are:

```text
CASE-001: How did the attacker move from initial access to ransomware deployment?
CASE-001: What evidence supports the Rclone event?
CASE-004: What could we have known at the end of day one?
CASE-011/012: What does the evidence establish regardless of actor framing?
CASE-001: Are there conflicting claims?
```

### Local Verification

The current build has been checked with:

```sh
.venv/bin/pytest -q
npm run sanity:validate
npm --prefix studio-cyber-autopsy run build -- --no-auto-updates
```

The browser smoke checks cover the full investigation, the CASE-004 temporal
cutoff, case descriptions, evidence rendering, and zero browser console errors.
