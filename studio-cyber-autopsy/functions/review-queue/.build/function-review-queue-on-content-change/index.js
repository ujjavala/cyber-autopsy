import { createClient } from "@sanity/client";
import { documentEventHandler } from "@sanity/functions";
//#region functions/review-queue/index.ts
var rules = [
	{
		type: "evidence",
		field: "source",
		kind: "missing-source",
		severity: "critical",
		label: "Evidence has no source reference",
		action: "Attach at least one primary or corroborating source before relying on this evidence."
	},
	{
		type: "event",
		field: "evidence",
		kind: "missing-evidence",
		severity: "warning",
		label: "Event has no evidence reference",
		action: "Attach the evidence that supports this event, or mark the event as unresolved."
	},
	{
		type: "relationship",
		field: "sourceEvent",
		kind: "broken-reference",
		severity: "critical",
		label: "Relationship is missing its source event",
		action: "Repair the source event reference before using this relationship in an attack chain."
	},
	{
		type: "relationship",
		field: "targetEvent",
		kind: "broken-reference",
		severity: "critical",
		label: "Relationship is missing its target event",
		action: "Repair the target event reference before using this relationship in an attack chain."
	},
	{
		type: "relationship",
		field: "evidence",
		kind: "missing-evidence",
		severity: "warning",
		label: "Relationship has no evidence reference",
		action: "Attach evidence or explain why this relationship is an analyst inference."
	},
	{
		type: "claim",
		field: "evidence",
		kind: "missing-evidence",
		severity: "warning",
		label: "Claim has no evidence reference",
		action: "Attach evidence or downgrade the claim to an explicitly unresolved statement."
	}
];
var handler = documentEventHandler(async ({ context, event }) => {
	const document = event.data;
	if (!document?._id || !document._type || document._type === "reviewTask") return;
	const rule = rules.find((candidate) => candidate.type === document._type && candidate.field in document && !document[candidate.field]);
	if (!rule) return;
	const client = createClient({
		apiVersion: "2025-05-01",
		...context.clientOptions
	});
	const fingerprint = `${rule.kind}:${document._id}:${rule.field}`;
	if (await client.fetch("*[_type == \"reviewTask\" && fingerprint == $fingerprint && status in [\"open\", \"in-review\"]][0]._id", { fingerprint })) return;
	await client.create({
		_type: "reviewTask",
		title: `${rule.label}: ${document.title || document.incidentId || document.eventId || document.claimId || document.caseId || document._id}`,
		kind: rule.kind,
		severity: rule.severity,
		status: "open",
		summary: `The ${document._type} ${document._id} changed without the expected ${rule.field} link. This is a review prompt, not an automatic finding.`,
		suggestedAction: rule.action,
		document: {
			_ref: document._id,
			_type: "reference"
		},
		fingerprint,
		detectedBy: "Sanity Function",
		detectedAt: (/* @__PURE__ */ new Date()).toISOString()
	});
});
//#endregion
export { handler };

//# sourceMappingURL=index.js.map