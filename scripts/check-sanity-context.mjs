import {loadEnv} from '../agent/env.mjs'

loadEnv()

const endpoint = process.env.SANITY_CONTEXT_MCP_URL
const token = process.env.SANITY_CONTEXT_TOKEN || process.env.SANITY_API_TOKEN

if (!endpoint) {
  console.error('Missing SANITY_CONTEXT_MCP_URL. Create a Sanity Context MCP endpoint first.')
  process.exit(1)
}
if (!token) {
  console.error('Missing SANITY_CONTEXT_TOKEN or SANITY_API_TOKEN.')
  process.exit(1)
}
if (!process.env.SANITY_CONTEXT_TOKEN) {
  console.warn('Using SANITY_API_TOKEN for the MCP check; a Context Viewer token may be required by the hosted endpoint.')
}

async function callMcp(message, sessionId = '') {
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/json, text/event-stream',
    'Content-Type': 'application/json',
  }
  if (sessionId) headers['Mcp-Session-Id'] = sessionId
  const response = await fetch(endpoint, {method: 'POST', headers, body: JSON.stringify(message)})
  const body = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${body.slice(0, 240)}`)
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('text/event-stream')) {
    const dataLine = body.split(/\r?\n/).find((line) => line.startsWith('data:'))
    if (!dataLine) throw new Error('MCP returned an empty event stream')
    return {value: JSON.parse(dataLine.slice(5).trim()), sessionId: response.headers.get('mcp-session-id') || sessionId}
  }
  return {value: JSON.parse(body), sessionId: response.headers.get('mcp-session-id') || sessionId}
}

const initialized = await callMcp({
  jsonrpc: '2.0',
  id: 1,
  method: 'initialize',
  params: {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: {name: 'cyber-autopsy-check', version: '1.0.0'},
  },
})
if (initialized.value.error) throw new Error(initialized.value.error.message || 'MCP initialize failed')

const listed = await callMcp(
  {jsonrpc: '2.0', id: 2, method: 'tools/list', params: {}},
  initialized.sessionId,
)
if (listed.value.error) throw new Error(listed.value.error.message || 'MCP tools/list failed')

const tools = listed.value.result?.tools || []
console.log(`Sanity Context MCP is reachable: ${new URL(endpoint).origin}`)
console.log(`Protocol: ${initialized.value.result?.protocolVersion || 'unknown'}`)
console.log(`Tools exposed: ${tools.length}`)
console.log(tools.map((tool) => `- ${tool.name}`).join('\n'))
