# Cyber Autopsy

## TL;DR: start here

From a fresh checkout:

```sh
cd /Users/ujja/code/personal/cyber-autopsy
cp .env.example .env
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,kaggle]"
```

Set `SANITY_API_TOKEN` in `.env` to a Developer/Editor API token for the
existing Sanity project. Keep the token in `.env`; it is used only by the
server-side importer and is ignored by Git.

Install the existing Studio dependencies and validate/import the benchmark:

```sh
npm --prefix studio-cyber-autopsy install
npm run sanity:validate
npm run sanity:seed
npm --prefix studio-cyber-autopsy exec sanity schema deploy
```

Start the investigation UI:

```sh
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The UI reads structured
incidents, events, relationships, claims, and evidence from Sanity. If port
3000 is already occupied, use `PORT=3001 npm run dev` and open port 3001.

### Deploy the web UI

The repository includes Vercel serverless routing and a container fallback. For
Vercel, authenticate with your own account, set the server-side Sanity secrets,
and deploy from the repository root:

```sh
npx vercel login
npx vercel link
npx vercel env add SANITY_PROJECT_ID production
npx vercel env add SANITY_DATASET production
npx vercel env add SANITY_API_TOKEN production
npx vercel --prod
```

The Vercel deployment serves the static forensic UI and `/api/cases` plus
`/api/investigate` as serverless functions. The container and Fly files remain
available as an alternative. Never commit the Sanity token or put it in
browser code.

In a second terminal, start the Sanity Studio when you need to inspect or edit
documents:

```sh
npm --prefix studio-cyber-autopsy run dev
```

Run the MCP investigation server when connecting an MCP-capable host:

```sh
npm run agent:mcp
```

### Path One: hosted Sanity Context MCP

Path One requires the agent to query real content through Sanity Context. This
repository also contains a local, reproducible MCP server, but that local
server is a fallback and is not the hosted Sanity Context endpoint used for
the competition submission.

Complete these account-side steps in the normal Sanity dashboard:

1. Open project `41l9o4xn` and go to **Context**.
2. Create a Knowledge Base for the Cyber Autopsy `production` dataset. Keep
   the indexed source within the beta limit, or enable embeddings for the full
   dataset when that option is available.
3. Create a Context MCP endpoint attached to that Knowledge Base.
4. Create an organization API token with **Context Viewer** permission.
5. Put the endpoint URL in `SANITY_CONTEXT_MCP_URL` in the local `.env` file.
   The check reuses `SANITY_API_TOKEN` automatically; set
   `SANITY_CONTEXT_TOKEN` only if the hosted endpoint requires the separate
   organization-scoped Context Viewer token.

Verify the real endpoint without printing retrieved incident content or the
token:

```sh
npm run sanity:context:check
```

The check performs MCP initialization and `tools/list`. A successful result
proves that an MCP-capable agent can reach the hosted Context endpoint. Use
that endpoint in the agent session submitted with `blog-sanity.md`.

See [Sanity Context MCP](https://www.sanity.io/docs/ai/sanity-context-mcp) for
the official endpoint and permission model.

The Knowledge Base created for this project is `kbZHPSeMHnZt`. It is built and
ready with 46 current sources: the ten incident records, twenty investigation
cases, and sixteen source records used by the hosted Context MCP endpoint.
The underlying production dataset remains larger and is not deleted or
modified by the Knowledge Base import.

Run the complete local verification suite:

```sh
.venv/bin/pytest
npm run sanity:validate
npm --prefix studio-cyber-autopsy run build -- --no-auto-updates
```

The main example questions are available as quick actions in the UI. Useful
manual checks include the `CASE-004` day-one cutoff, `CASE-011`/`CASE-012`
actor-framing pair, Rclone evidence provenance, predecessor/enabler queries,
and contradictory claims.

Cyber Autopsy is a small benchmark for reconstructing real cyber incidents from
fragmented evidence. It scores whether a model recovers supported events and
relationships, cites evidence, recognizes failed attempts and contradictions,
and expresses uncertainty without inventing details.

The current dataset contains ten incidents and 20 case definitions; 14 cases
have generated Kaggle task files. Seven tasks are the existing evaluated
Kaggle set. CASE-014 to CASE-020 extend it with an AI-agent incident,
deepfake-enabled fraud, ransomware, staged Microsoft disclosures, healthcare
ransomware, and a multi-victim credential campaign. These follow-on tasks will
use the same model-evaluation workflow. Gold graphs are being independently
reviewed as part of preparing the expanded run set.
See [the case-study research inventory](research/CASE_STUDIES_2023-2026.md)
for additional source-backed candidates, exclusions, and research rules.
Most AI-actor cases rely on vendor reporting; the Medicare case is based on
government briefings rather than public forensic logs.

## Requirements

- Python 3.10 or newer
- Kaggle account and API access only for hosted runs

Create an environment and install the project, development tools, and Kaggle
integration:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,kaggle]"
```

On Windows, activate the environment with `.venv\Scripts\activate`. The Kaggle
CLI examples below use a macOS/Linux shell; on Windows, use
`.venv\Scripts\kaggle.exe` in place of `.venv/bin/kaggle` and configure the
environment variables in the current PowerShell session.

## Local Workflow

Run the dataset referential-integrity check:

```sh
python scripts/validate_dataset.py
```

Regenerate every supported Kaggle task from the JSONL dataset:

```sh
python scripts/build_kaggle_tasks.py
```

To rebuild a single case, pass its case ID, for example:

```sh
python scripts/build_kaggle_tasks.py CASE-001
```

Generated standalone tasks are written to `kaggle/build/`. Currently generated
modes are full reconstruction, temporal cutoff, and actor framing. Perturbation
and progressive-disclosure cases are present in the data model but do not yet
have task drivers.

Run every generated task locally against the offline `perfect`, `lazy`, and
`inventive` stub models. This makes no hosted model calls:

```sh
python scripts/validate_task_offline.py
```

Run one task with one stub behaviour:

```sh
python scripts/validate_task_offline.py kaggle/build/case_001.py perfect
```

Run the test suite:

```sh
python -m pytest
```

## Gold Graph Review

Before publishing, a reviewer who did not author the graphs should check each
node and edge against its cited evidence and source, including unknowns,
contradictions, and causal claims. Record the outcome in the graph's `review`
metadata in `data/attack_graphs.jsonl`: update `review_status`,
`reviewer_count`, `last_reviewed`, and `review_notes`. Keep the graphs in draft
until that review is complete, then rebuild tasks and rerun local validation.

## Kaggle Workflow

1. Create a Kaggle API token in account settings. Put it in `.env` as
   `KAGGLE_API_TOKEN`; never commit `.env`. See `.env.example` for the remaining
   optional variables. The Kaggle CLI accepts a `KGAT_` token directly.
2. Load the environment and initialize or refresh the short-lived model proxy
   credentials:

   ```sh
   set -a
   source .env
   set +a
   .venv/bin/kaggle b auth -y --env-file .env
   .venv/bin/kaggle b init -y --env-file .env \
     --example-file /tmp/cyber-autopsy-example-task.py
   ```

   Refresh with `kaggle b auth -y --env-file .env` when proxy credentials
   expire. The Kaggle API token is separate from these model proxy credentials.
3. Complete the independent gold graph review above, then build tasks and run
   the offline validation before publishing. Task files contain their evidence
   packet and scoring logic, so they do not require an attached Kaggle Dataset.
4. Push a task using the generated slug and file. The slug is printed in the
   generated file header; for example:

   ```sh
   .venv/bin/kaggle b t push cyber-autopsy-case-001-reconstruct-inc-001-full \
     -f kaggle/build/case_001.py
   ```

   Repeat for each task you intend to publish. The generated task files include
   a push command comment with the exact slug.
5. See available models and run the task:

   ```sh
   .venv/bin/kaggle b t models
   .venv/bin/kaggle b t run <task-slug> -m <model>
   .venv/bin/kaggle b t status <task-slug>
   .venv/bin/kaggle b t download <task-slug>
   ```

6. Compose a benchmark from the pushed tasks in the Kaggle web UI. Record its
   URL and ID in `.env` only after it exists. Benchmark composition and adding
   models currently require the web UI.

## Data and Provenance

Benchmark records are JSON Lines files under `data/`. Attack graphs are in
`data/attack_graphs.jsonl`; evidence and source references are in
`data/evidence.jsonl` and `data/sources.jsonl`. Collection decisions, retrieval
timestamps, and SHA-256 hashes are in
`data/collection/collection_manifest.json`. Retrieved source bytes are stored
under `data/collection/raw/` using their SHA-256 as the filename.

There is no source-fetch command yet. When adding a source, retrieve it
manually, calculate its hash, store the exact bytes at
`data/collection/raw/<sha256>.<extension>`, and update the collection manifest
with the URL, retrieval time, status, hash, and inclusion decision. Keep source
claims distinct from independently observed evidence.

## What Is Not Automated Yet

- Independent review of all ten gold graphs is required before publication.
- There is no automated leakage-audit script or Kaggle Dataset export command.
- Perturbation and progressive-disclosure task drivers are not generated yet.
- Benchmark composition is a manual Kaggle web workflow; leaderboard import is
  not implemented.
- There is no API or web application in this repository.

See [KAGGLE_IMPLEMENTATION_NOTES.md](KAGGLE_IMPLEMENTATION_NOTES.md) for platform
details and [LANDSCAPE_AND_DATA_AUDIT.md](LANDSCAPE_AND_DATA_AUDIT.md) for source
selection, limitations, and review status.

## Sanity investigation build

The Sanity-powered investigation build is the structured-content layer for this
benchmark. It keeps incidents, sources, evidence, events, relationships, claims,
and benchmark cases as separate documents so the agent can answer questions about
what enabled an event, which evidence supports it, what was knowable at a cutoff,
and where the record remains uncertain.

```text
User
 ↓
Cyber Autopsy UI
 ↓
Investigation Agent
 ↓
Sanity Context / MCP
 ↓
Sanity
 ├── Incidents
 ├── Sources
 ├── Evidence
 ├── Events
 ├── Relationships
 ├── Claims
 └── Investigation Cases
```

The existing Studio configuration is reused at project `41l9o4xn`, dataset
`production`. Studio schemas live in
`studio-cyber-autopsy/schemaTypes/index.ts`. The local agent uses the same
project and dataset through the Sanity Content API; it never downloads the whole
dataset. Its MCP server exposes `list_investigation_cases` and
`investigate_case`, both backed by scoped GROQ queries and evidence references.

### Local Sanity workflow

Install the existing Studio dependencies and create a root `.env` from
`.env.example`. Add a Sanity API token with write access only when importing:

```sh
cd studio-cyber-autopsy
npm install
cd ..
npm run sanity:validate
npm run sanity:seed
```

The seed is deterministic and repeatable: source IDs such as `INC-001`, `E-001`,
and `N01` are preserved in explicit fields and used to converge stable import
documents. It imports all existing benchmark cases, including `CASE-001`,
`CASE-004`, `CASE-011`, `CASE-012`, and `CASE-013`. `CASE-004` contains only its
explicit first-day evidence references, so later ransomware evidence is not
available through that case context. `CASE-011` and `CASE-012` point to the same
INC-002 evidence while exposing their different actor framing as metadata.

Run the investigation UI with:

```sh
npm run dev
```

Then open `http://localhost:3000`. The UI displays the reconstruction, event
relationships, uncertainty, and expandable provenance. The default question and
case are intentionally chosen to show the event graph, not generic text search.

Run the MCP server over stdio with:

```sh
npm run agent:mcp
```

Register that command with an MCP-capable host using the repository as its
working directory. The server requires the same `SANITY_PROJECT_ID`,
`SANITY_DATASET`, and optional read token from `.env`.

### Knowledge Base status

The structured Sanity dataset and MCP-compatible context are implemented. A
Sanity Knowledge Base or hosted dashboard connection is not provisioned by this
repository because that is an account-level/dashboard action. To finish that
optional challenge setup, create a Knowledge Base named **Cyber Autopsy Knowledge
Base** in the existing Sanity project, select `production`, and include the
`incident`, `source`, `evidence`, `event`, `relationship`, `claim`, and
`investigationCase` document types. Point its MCP/context connection at the
local `agent:mcp` command for development, or deploy that command as the project
runtime. Verify the connection with the example questions below.

### Example investigation questions

- What happened in CASE-001?
- How did the attacker move from initial access to ransomware deployment?
- What evidence supports the Rclone event?
- Which events are inferred?
- What could we have known at the end of day one?
- What does the evidence establish regardless of actor framing?

The importer does not modify the Kaggle benchmark or scoring logic. It reuses
the JSONL dataset as the source snapshot and preserves the benchmark's negative
evidence, failed attempts, unknowns, and contradiction metadata.

For the challenge write-up and a guided walkthrough, see
[blog-sanity.md](blog-sanity.md).

The separate Path Two submission draft is in
[blog-path-two.md](blog-path-two.md).
