# Cyber Autopsy Sanity Studio

This is the existing Studio for the Cyber Autopsy benchmark. It uses the
project and dataset configured in `sanity.config.ts` and exposes the structured
incident content model used by the local investigation agent.

Now you can do the following things:

- Run `npm run dev` from this directory to open the Studio.
- Run `npm run build` to verify the schemas compile.
- Run `npm run deploy` only when you intend to publish this existing Studio.

The root README documents the import command and the optional Knowledge Base /
MCP dashboard setup.
# Review automation

The Studio includes a Sanity-native review workflow. `Review queue` in the
structure shows unresolved `reviewTask` documents. The `review-queue-on-content-change`
Function creates a task when evidence, events, relationships, or claims lose a
source/evidence link. It does not change verdicts or publish conclusions.

Build the Function archive locally with `npm run functions:build`. Preview the
Blueprint with `npm run blueprints:plan`, then deploy only after checking the
target Stack and resource diff. Deploying the Blueprint creates a narrowly scoped
project robot token for the Function; review that permission in Sanity before
deployment.

Agent Actions are available as a draft-only reviewer assist:

```sh
SANITY_SCHEMA_ID=<schema-id> SANITY_API_TOKEN=<write-token> \
  node scripts/draft-review-agent-action.mjs <review-task-id>
```

The command writes only a draft `reviewerNotes` field. It never publishes a
review task, changes severity/status, or decides a cyber attribution claim.
