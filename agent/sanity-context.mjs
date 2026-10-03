import {loadEnv, sanityConfig} from './env.mjs'

loadEnv()

const CASES_QUERY = `*[_type == "investigationCase"] | order(caseId asc) {
  caseId, mode, temporalCutoff, framingActor, knowledgeCutoff, notes,
  "incidentId": incident->incidentId,
  "incidentTitle": incident->title,
  "incidentDescription": incident->description,
  "incidentImpact": incident->impact
}`

const CASE_QUERY = `*[_type == "investigationCase" && caseId == $caseId][0] {
  caseId, mode, temporalCutoff, framingActor, knowledgeCutoff, notes,
  incident->{incidentId, title, description, actor, actorType, impact, confidence},
  evidence[]->{evidenceId, timestamp, type, description, status, entities,
    source[]->{sourceId, title, publisher, url, publishedDate}},
  events[]->{eventId, description, timestamp, status, confidence, notes,
    evidence[]->{evidenceId}},
  "incidentRef": incident._ref
}`

const RELATIONSHIPS_QUERY = `*[_type == "relationship" && incident._ref == $incidentRef] {
  relationshipId, relationship, confidence,
  "sourceEvent": sourceEvent->{eventId, description},
  "targetEvent": targetEvent->{eventId, description},
  evidence[]->{evidenceId}
}`

const CLAIMS_QUERY = `*[_type == "claim" && incident._ref == $incidentRef] {
  claimId, statement, status, confidence, notes,
  evidence[]->{evidenceId},
  contradicts[]->{claimId, statement}
}`

const INCIDENT_EVIDENCE_QUERY = `*[_type == "evidence" && incident._ref == $incidentRef] {
  evidenceId, timestamp, type, description, status, entities,
  source[]->{sourceId, title, publisher, url, publishedDate}
}`

export class SanityContext {
  constructor(config = sanityConfig()) {
    this.config = config
  }

  async query(query, params = {}) {
    const {projectId, dataset, token} = this.config
    const url = new URL(`https://${projectId}.api.sanity.io/v2025-02-19/data/query/${dataset}`)
    url.searchParams.set('query', query)
    for (const [key, value] of Object.entries(params)) url.searchParams.set(`$${key}`, JSON.stringify(value))
    const response = await fetch(url, {headers: token ? {Authorization: `Bearer ${token}`} : {}})
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body?.message || `Sanity query failed (${response.status})`)
    return body.result
  }

  async listCases() {
    return this.query(CASES_QUERY)
  }

  async loadGraph(caseId) {
    const selectedCase = await this.query(CASE_QUERY, {caseId})
    if (!selectedCase) throw new Error(`Case ${caseId} was not found in Sanity`)
    const incidentRef = selectedCase.incidentRef
    const [caseEvidence, relationships, claims] = await Promise.all([
      selectedCase.evidence?.length ? Promise.resolve(selectedCase.evidence) : this.query(INCIDENT_EVIDENCE_QUERY, {incidentRef}),
      this.query(RELATIONSHIPS_QUERY, {incidentRef}),
      this.query(CLAIMS_QUERY, {incidentRef}),
    ])
    const visibleIds = new Set(caseEvidence.map((item) => item.evidenceId))
    const events = (selectedCase.events || []).filter((event) =>
      (event.evidence || []).some((item) => visibleIds.has(item.evidenceId)),
    )
    const eventIds = new Set(events.map((event) => event.eventId))
    return {
      case: selectedCase,
      evidence: caseEvidence,
      events,
      relationships: relationships.filter((item) =>
        item.evidence?.some((evidence) => visibleIds.has(evidence.evidenceId)) &&
        eventIds.has(item.sourceEvent?.eventId) && eventIds.has(item.targetEvent?.eventId),
      ),
      claims: claims.filter((item) => item.evidence?.some((evidence) => visibleIds.has(evidence.evidenceId))),
    }
  }

  async investigate(caseId, question) {
    const graph = await this.loadGraph(caseId)
    const q = question.toLowerCase()
    let events = [...graph.events]
    let evidence = [...graph.evidence]
    let claims = [...graph.claims]
    let relationships = [...graph.relationships]
    let queryIntent = 'reconstruction'
    let focusEvent = null

    if (q.includes('end of day one') || q.includes('day one')) queryIntent = 'temporal_cutoff'
    else if (q.includes('actor framing') || q.includes('regardless of actor')) queryIntent = 'actor_framing'
    else if (q.includes('immediately before')) queryIntent = 'before'
    else if (q.includes('what enabled') || q.includes('which event enabled')) queryIntent = 'enabled_by'
    else if (q.includes('attack chain') || q.includes('chain of events') || (q.includes('how did') && q.includes('move'))) queryIntent = 'attack_chain'
    else if (q.includes('contradict') || q.includes('conflicting claim')) queryIntent = 'contradictions'
    else if (q.includes('what evidence') || q.includes('evidence supports')) queryIntent = 'evidence'
    else if (q.includes('inferred') || q.includes('uncertain') || q.includes('unknown')) queryIntent = 'status_filter'

    if (queryIntent === 'before' || queryIntent === 'enabled_by') {
      const targetTokens = q.split(/\W+/).filter((token) => token.length > 3 && !['what', 'happened', 'immediately', 'before', 'enabled', 'which', 'event', 'does', 'the'].includes(token))
      focusEvent = events
        .map((event) => ({event, score: targetTokens.reduce((total, token) => total + (`${event.eventId} ${event.description}`.toLowerCase().includes(token) ? 1 : 0), 0)}))
        .sort((a, b) => b.score - a.score)[0]?.event || null
      if (focusEvent) {
        const wanted = queryIntent === 'before' ? 'precedes' : 'enables'
        const focusedRelationships = relationships.filter((item) => item.relationship === wanted && item.targetEvent?.eventId === focusEvent.eventId)
        const relatedIds = new Set([focusEvent.eventId, ...focusedRelationships.map((item) => item.sourceEvent?.eventId)])
        events = events.filter((event) => relatedIds.has(event.eventId))
        relationships = focusedRelationships
      }
    }

    if ((q.includes('end of day one') || q.includes('day one')) && graph.case.temporalCutoff !== 'D1') {
      const dayOne = new Set(evidence.filter((item) => item.timestamp?.startsWith('D1')).map((item) => item.evidenceId))
      evidence = evidence.filter((item) => dayOne.has(item.evidenceId))
      events = events.filter((item) => item.evidence?.some((ref) => dayOne.has(ref.evidenceId)))
      const eventIds = new Set(events.map((item) => item.eventId))
      relationships = relationships.filter((item) => eventIds.has(item.sourceEvent?.eventId) && eventIds.has(item.targetEvent?.eventId))
      claims = claims.filter((item) => item.evidence?.some((ref) => dayOne.has(ref.evidenceId)))
    }

    if (q.includes('inferred')) events = events.filter((item) => item.status === 'inferred')
    if (q.includes('uncertain') || q.includes('unknown') || q.includes('contradict') || q.includes('conflicting claim')) {
      events = events.filter((item) => ['unknown', 'inferred'].includes(item.status))
      claims = claims.filter((item) => ['unknown', 'contradicted', 'inferred'].includes(item.status))
    }

    const tokens = q.split(/\W+/).filter((token) => token.length > 3 && !['what', 'does', 'from', 'with', 'event', 'evidence', 'which', 'could', 'have'].includes(token))
    if (tokens.length && !['attack_chain', 'before', 'enabled_by', 'temporal_cutoff', 'actor_framing', 'contradictions', 'status_filter'].includes(queryIntent) && !q.includes('what happened')) {
      const score = (value) => tokens.reduce((total, token) => total + (value.toLowerCase().includes(token) ? 1 : 0), 0)
      const matchingIds = new Set(evidence.filter((item) => score(`${item.evidenceId} ${item.description} ${item.type}`) > 0).map((item) => item.evidenceId))
      const matchingEvents = events.filter((item) => score(`${item.eventId} ${item.description}`) > 0 || item.evidence?.some((ref) => matchingIds.has(ref.evidenceId)))
      if (matchingEvents.length) events = matchingEvents
      if (matchingIds.size) evidence = evidence.filter((item) => matchingIds.has(item.evidenceId) || events.some((event) => event.evidence?.some((ref) => ref.evidenceId === item.evidenceId)))
    }

    const selectedEventIds = new Set(events.map((item) => item.eventId))
    relationships = relationships.filter((item) => selectedEventIds.has(item.sourceEvent?.eventId) || selectedEventIds.has(item.targetEvent?.eventId))
    const evidenceIds = new Set(evidence.map((item) => item.evidenceId))
    const contradictions = claims.filter((item) => item.status === 'contradicted' || item.contradicts?.length)
    const uncertainty = [
      ...events.filter((item) => ['unknown', 'inferred', 'failed', 'attempted'].includes(item.status)).map((item) => ({kind: 'event', ...item})),
      ...claims.filter((item) => ['unknown', 'contradicted', 'inferred'].includes(item.status)).map((item) => ({kind: 'claim', ...item})),
    ]

    return {
      case: graph.case,
      queryIntent,
      focusEvent: focusEvent ? {eventId: focusEvent.eventId, description: focusEvent.description} : null,
      framingNote: graph.case.framingActor ? `Actor framing: ${graph.case.framingActor}. Framing changes the prompt context, not the evidence.` : null,
      reconstruction: events.sort((a, b) => String(a.timestamp || '').localeCompare(String(b.timestamp || ''))),
      relationships,
      evidence: evidence.filter((item) => evidenceIds.has(item.evidenceId)),
      uncertainty,
      contradictions,
      provenance: {sanity: true, evidenceIds: [...evidenceIds]},
    }
  }
}

export const context = new SanityContext()
