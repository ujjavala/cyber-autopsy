import fs from 'node:fs/promises'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {loadEnv, sanityConfig} from '../agent/env.mjs'

loadEnv()
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const readJsonl = async (name) => (await fs.readFile(path.join(root, 'data', name), 'utf8')).trim().split(/\r?\n/).filter(Boolean).map(JSON.parse)
const ref = (type, id) => ({_type: 'reference', _ref: id})
const refs = (type, ids) => ids.map((id, index) => ({_type: 'reference', _ref: id, _key: `${type}-${index}` }))
const idFor = (type, key) => `cyber-autopsy-${type}-${key.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`
const status = (value) => value === 'contradicted' ? 'unknown' : value || 'unknown'

const [incidents, sources, evidence, graphs, cases] = await Promise.all([
  readJsonl('incidents.jsonl'), readJsonl('sources.jsonl'), readJsonl('evidence.jsonl'), readJsonl('attack_graphs.jsonl'), readJsonl('benchmark_cases.jsonl'),
])
const incidentById = new Map(incidents.map((item) => [item.incident_id, item]))
const sourceById = new Map(sources.map((item) => [item.source_id, item]))
const evidenceById = new Map(evidence.map((item) => [item.evidence_id, item]))
const graphByIncident = new Map(graphs.map((item) => [item.incident_id, item]))
const nodesByEvidence = new Map()
for (const graph of graphs) for (const node of graph.nodes) for (const evidenceId of node.evidence_ids) {
  const key = `${graph.incident_id}:${evidenceId}`
  nodesByEvidence.set(key, [...(nodesByEvidence.get(key) || []), node.id])
}

const docs = []
const reverseReferencePatches = []
for (const item of sources) docs.push({_id: idFor('source', item.source_id), _type: 'source', sourceId: item.source_id, title: item.title, publisher: item.publisher, url: item.url, publishedDate: item.published_at, sourceType: item.source_type, description: item.notes, reliabilityTier: item.reliability_tier, externalId: item.source_id})
for (const item of incidents) {
  const source = item.source_ids.map((sourceId) => sourceById.get(sourceId)).find(Boolean)
  docs.push({_id: idFor('incident', item.incident_id), _type: 'incident', incidentId: item.incident_id, title: item.title, description: item.summary, source: refs('source', item.source_ids.map((sourceId) => idFor('source', sourceId))), sourceUrl: source?.url, reportedDate: item.public_disclosure_date, actor: item.actor, actorType: item.actor_type, evidenceQuality: item.confidence, confidence: item.confidence, organization: item.organization, sector: item.sector, impact: item.impact, externalId: item.incident_id})
}
for (const item of evidence) docs.push({_id: idFor('evidence', item.evidence_id), _type: 'evidence', evidenceId: item.evidence_id, incident: ref('incident', idFor('incident', item.incident_id)), source: refs('source', item.source_ids.map((sourceId) => idFor('source', sourceId))), timestamp: item.timestamp, type: item.type, description: item.content, status: item.evidence_strength, entities: item.entities, externalId: item.evidence_id})
for (const graph of graphs) {
  for (const node of graph.nodes) {
    const source = node.mitre || {}
    docs.push({_id: idFor('event', `${graph.incident_id}-${node.id}`), _type: 'event', eventId: node.id, incident: ref('incident', idFor('incident', graph.incident_id)), description: node.label, timestamp: node.evidence_ids.map((id) => evidenceById.get(id)?.timestamp).filter(Boolean).sort()[0], status: status(node.status), evidence: refs('evidence', node.evidence_ids.map((id) => idFor('evidence', id))), confidence: node.status === 'confirmed' ? 0.95 : node.status === 'inferred' ? 0.65 : 0.4, notes: node.notes, mitreTactic: source.mitre_tactic, mitreTechnique: source.mitre_technique, externalId: `${graph.incident_id}:${node.id}`})
    docs.push({_id: idFor('claim', `${graph.incident_id}-${node.id}`), _type: 'claim', claimId: node.id, incident: ref('incident', idFor('incident', graph.incident_id)), statement: node.label, status: node.status, confidence: node.status === 'confirmed' ? 0.95 : node.status === 'inferred' ? 0.65 : 0.35, evidence: refs('evidence', node.evidence_ids.map((id) => idFor('evidence', id))), notes: node.notes, externalId: `${graph.incident_id}:${node.id}`})
  }
  for (const edge of graph.edges) docs.push({_id: idFor('relationship', `${graph.incident_id}-${edge.id}`), _type: 'relationship', relationshipId: edge.id, sourceEvent: ref('event', idFor('event', `${graph.incident_id}-${edge.source}`)), targetEvent: ref('event', idFor('event', `${graph.incident_id}-${edge.target}`)), relationship: edge.relation, confidence: 0.8, evidence: refs('evidence', edge.evidence_ids.map((id) => idFor('evidence', id))), incident: ref('incident', idFor('incident', graph.incident_id)), externalId: `${graph.incident_id}:${edge.id}`})
}
for (const item of evidence) {
  const graph = graphByIncident.get(item.incident_id)
  const supported = item.supports_nodes || []
  const contradicted = (item.contradicts || []).flatMap((evidenceId) => nodesByEvidence.get(`${item.incident_id}:${evidenceId}`) || [])
  const doc = docs.find((candidate) => candidate._id === idFor('evidence', item.evidence_id))
  if (!doc) continue
  doc.supportsEvents = refs('event', supported.map((nodeId) => idFor('event', `${item.incident_id}-${nodeId}`)))
  doc.supportsClaims = refs('claim', supported.map((nodeId) => idFor('claim', `${item.incident_id}-${nodeId}`)))
  doc.contradictsClaims = refs('claim', contradicted.map((nodeId) => idFor('claim', `${item.incident_id}-${nodeId}`)))
  reverseReferencePatches.push({patch: {id: doc._id, set: {supportsEvents: doc.supportsEvents, supportsClaims: doc.supportsClaims, contradictsClaims: doc.contradictsClaims}}})
  for (const supportingNodeId of supported) {
    const claim = docs.find((candidate) => candidate._id === idFor('claim', `${item.incident_id}-${supportingNodeId}`))
    if (claim) claim.contradicts = [...(claim.contradicts || []), ...refs('claim', contradicted.filter((nodeId) => nodeId !== supportingNodeId).map((nodeId) => idFor('claim', `${item.incident_id}-${nodeId}`)))]
  }
  if (!graph) throw new Error(`No graph for ${item.incident_id}`)
}
for (const item of cases) {
  const incident = incidentById.get(item.incident_id)
  const allEvidence = evidence.filter((candidate) => candidate.incident_id === item.incident_id)
  const caseEvidence = item.evidence_ids?.length ? item.evidence_ids : allEvidence.map((candidate) => candidate.evidence_id)
  const graph = graphByIncident.get(item.incident_id)
  const eventIds = graph.nodes.filter((node) => node.evidence_ids.some((evidenceId) => caseEvidence.includes(evidenceId))).map((node) => node.id)
  docs.push({_id: idFor('case', item.case_id), _type: 'investigationCase', caseId: item.case_id, incident: ref('incident', idFor('incident', item.incident_id)), mode: item.mode, temporalCutoff: item.temporal_cutoff, framingActor: item.framing_actor, knowledgeCutoff: item.knowledge_cutoff, notes: item.notes, evidence: refs('evidence', caseEvidence.map((id) => idFor('evidence', id))), events: refs('event', eventIds.map((id) => idFor('event', `${item.incident_id}-${id}`))), externalId: item.case_id})
}

const typeOrder = ['source', 'incident', 'evidence', 'event', 'claim', 'relationship', 'investigationCase']
const orderedDocs = typeOrder.flatMap((type) => docs.filter((doc) => doc._type === type))
const mutations = orderedDocs.map((doc) => ({createOrReplace: {...doc, supportsEvents: undefined, supportsClaims: undefined, contradictsClaims: undefined}})).concat(reverseReferencePatches)
const batches = []
for (let index = 0; index < mutations.length; index += 100) batches.push(mutations.slice(index, index + 100))
const {projectId, dataset, token} = sanityConfig()
const dryRun = process.argv.includes('--dry-run')
if (dryRun) {
  console.log(JSON.stringify({documents: docs.length, batches: batches.length, byType: docs.reduce((counts, doc) => ({...counts, [doc._type]: (counts[doc._type] || 0) + 1}), {})}, null, 2))
  process.exit(0)
}
if (!token) throw new Error('SANITY_API_TOKEN is required for importing. Copy .env.example to .env and add a write token.')
for (const batch of batches) {
  const response = await fetch(`https://${projectId}.api.sanity.io/v2025-02-19/data/mutate/${dataset}`, {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`}, body: JSON.stringify({mutations: batch})})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body?.message || JSON.stringify(body) || `Sanity import failed (${response.status})`)
  console.log(`Imported ${batch.length} documents`)
}
console.log(`Imported ${docs.length} documents into ${projectId}/${dataset}`)
