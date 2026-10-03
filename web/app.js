const $ = (selector) => document.querySelector(selector)
const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'}[character]))
const statusIcon = {confirmed: '✓', inferred: '~', attempted: '→', failed: '✕', unknown: '?'}
let caseCatalog = []

async function loadCases() {
  const response = await fetch('/api/cases')
  if (!response.ok) throw new Error('Could not load cases from Sanity')
  caseCatalog = await response.json()
  $('#case-select').innerHTML = caseCatalog.map((item) => `<option value="${esc(item.caseId)}">${esc(item.caseId)} · ${esc(item.mode)}${item.temporalCutoff ? ` · cutoff ${esc(item.temporalCutoff)}` : ''}</option>`).join('')
  updateMeta()
}

function updateMeta() {
  const item = caseCatalog.find((candidate) => candidate.caseId === $('#case-select').value)
  if (!item) { $('#case-meta').textContent = ''; $('#case-badges').innerHTML = ''; $('#case-description').textContent = ''; return }
  const badges = [`<span class="badge">${esc(item.mode)}</span>`]
  if (item.temporalCutoff) badges.push(`<span class="badge cutoff">cutoff ${esc(item.temporalCutoff)}</span>`)
  if (item.framingActor) badges.push(`<span class="badge framing">framed as ${esc(item.framingActor)}</span>`)
  $('#case-badges').innerHTML = badges.join('')
  $('#case-meta').textContent = `Sanity content · ${item.incidentId} · ${item.incidentTitle}`
  $('#case-description').textContent = [item.incidentDescription, item.notes].filter(Boolean).join(' ')
}

function render(data) {
  const reconstruction = Array.isArray(data.reconstruction) ? data.reconstruction : []
  const relationships = Array.isArray(data.relationships) ? data.relationships : []
  const uncertainty = Array.isArray(data.uncertainty) ? data.uncertainty : []
  const contradictions = Array.isArray(data.contradictions) ? data.contradictions : []
  const evidence = Array.isArray(data.evidence) ? data.evidence : []
  $('#results').hidden = false
  $('#result-summary').innerHTML = `<strong>${esc(data.case?.caseId || 'Case')}</strong><span class="summary-separator">·</span>${reconstruction.length} events<span class="summary-separator">·</span>${relationships.length} relationships<span class="summary-separator">·</span>${evidence.length} evidence items${data.queryIntent ? `<span class="summary-separator">·</span>${esc(data.queryIntent.replaceAll('_', ' '))}` : ''}`
  $('#framing-note').innerHTML = data.framingNote ? `<div class="framing">${esc(data.framingNote)}</div>` : ''
  $('#reconstruction').innerHTML = reconstruction.length ? reconstruction.map((event) => `<article class="event ${esc(event.status)}"><div class="event-top"><span class="event-id">${esc(event.eventId)} ${esc(event.timestamp || '')}</span><h3>${esc(event.description)}</h3><span class="status">${statusIcon[event.status] || '?'} ${esc(event.status)}</span></div>${event.notes ? `<p>${esc(event.notes)}</p>` : ''}<div class="citations">Evidence: ${(event.evidence || []).map((item) => esc(item.evidenceId)).join(', ')}</div></article>`).join('') : '<div class="empty">No matching events were returned from the structured case context.</div>'
  $('#relationships').innerHTML = relationships.length ? relationships.map((item) => `<div class="relationship"><strong>${esc(item.relationship)}</strong><p>${esc(item.sourceEvent?.description)} <span aria-hidden="true">→</span> ${esc(item.targetEvent?.description)}</p><div class="citations">${(item.evidence || []).map((evidence) => esc(evidence.evidenceId)).join(', ')}</div></div>`).join('') : '<div class="empty">No relationship fits the selected evidence window.</div>'
  $('#uncertainty').innerHTML = uncertainty.length ? uncertainty.map((item) => `<div class="uncertainty-item"><small>${esc(item.kind)} · ${esc(item.status)}</small>${esc(item.description || item.statement)}</div>`).join('') : '<div class="empty">No additional uncertainty was returned.</div>'
  $('#contradictions-section').hidden = !contradictions.length
  $('#contradictions').innerHTML = contradictions.map((item) => `<div class="uncertainty-item"><small>claim · ${esc(item.status)}</small>${esc(item.statement)}${item.contradicts?.length ? `<div class="citations">Contradicts: ${item.contradicts.map((claim) => esc(claim.claimId)).join(', ')}</div>` : ''}</div>`).join('')
  $('#evidence').innerHTML = evidence.length ? evidence.map((item) => `<details><summary><span class="ev-id">${esc(item.evidenceId)}</span><span class="ev-type">${esc(item.type)} · ${esc(item.timestamp || 'undated')}</span></summary><div><p>${esc(item.description)}</p><div class="source">${item.source?.map((source) => `${esc(source.publisher)} · ${esc(source.title)}${source.url ? ` · <a href="${esc(source.url)}" target="_blank" rel="noreferrer">source</a>` : ''}`).join('<br>') || 'Source metadata unavailable'}</div></div></details>`).join('') : '<div class="empty">No evidence matched this question.</div>'
}

async function investigate() {
  const button = $('#investigate')
  button.disabled = true
  $('#loading').hidden = false
  $('#error').hidden = true
  $('#results').hidden = true
  try {
    const params = new URLSearchParams({caseId: $('#case-select').value, question: $('#question').value})
    const response = await fetch(`/api/investigate?${params}`)
    const data = await response.json()
    if (!response.ok || data.error) throw new Error(data.error || 'Investigation failed')
    render(data)
  } catch (error) {
    $('#error').textContent = `${error.message}. Start the seed/import first if this Sanity dataset is empty.`
    $('#error').hidden = false
  } finally { button.disabled = false; $('#loading').hidden = true }
}

$('#case-select').addEventListener('change', updateMeta)
$('#investigate').addEventListener('click', investigate)
document.querySelectorAll('.quick-question').forEach((button) => button.addEventListener('click', () => { $('#question').value = button.dataset.question; investigate() }))
loadCases().catch((error) => { $('#error').textContent = error.message; $('#error').hidden = false })
