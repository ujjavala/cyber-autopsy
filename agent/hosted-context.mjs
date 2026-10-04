import {loadEnv} from './env.mjs'

loadEnv()

const MCP_PROTOCOL = '2024-11-05'

function config() {
  return {
    endpoint: process.env.SANITY_CONTEXT_MCP_URL || '',
    token: process.env.SANITY_CONTEXT_TOKEN || process.env.SANITY_ORG_TOKEN || process.env.SANITY_API_TOKEN || '',
  }
}

function parseResponse(body, contentType) {
  if (contentType.includes('text/event-stream')) {
    const dataLine = body.split(/\r?\n/).find((line) => line.startsWith('data:'))
    if (!dataLine) throw new Error('MCP returned an empty event stream')
    return JSON.parse(dataLine.slice(5).trim())
  }
  return JSON.parse(body)
}

async function callMcp(endpoint, token, message, sessionId = '') {
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/json, text/event-stream',
    'Content-Type': 'application/json',
  }
  if (sessionId) headers['Mcp-Session-Id'] = sessionId
  const response = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify(message),
    signal: AbortSignal.timeout(8000),
  })
  const body = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return {
    value: parseResponse(body, response.headers.get('content-type') || ''),
    sessionId: response.headers.get('mcp-session-id') || sessionId,
  }
}

function initialContextText(result) {
  return (result?.content || [])
    .filter((item) => item.type === 'text')
    .map((item) => item.text)
    .join('\n')
}

export async function getHostedContextStatus() {
  const {endpoint, token} = config()
  const status = {source: 'sanity-context', configured: Boolean(endpoint && token), reachable: false, tools: []}
  if (!endpoint || !token) {
    status.message = 'Hosted Context MCP is not configured; structured Content API remains active.'
    return status
  }

  try {
    const initialized = await callMcp(endpoint, token, {
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: MCP_PROTOCOL,
        capabilities: {},
        clientInfo: {name: 'cyber-autopsy-ui', version: '1.0.0'},
      },
    })
    if (initialized.value.error) throw new Error(initialized.value.error.message || 'MCP initialize failed')

    const listed = await callMcp(endpoint, token, {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
      params: {},
    }, initialized.sessionId)
    if (listed.value.error) throw new Error(listed.value.error.message || 'MCP tools/list failed')
    status.tools = (listed.value.result?.tools || []).map((tool) => tool.name).filter(Boolean)
    status.protocol = initialized.value.result?.protocolVersion || null
    status.reachable = true
    status.message = 'Hosted Context MCP is reachable.'

    const initial = status.tools.includes('initial_context')
      ? await callMcp(endpoint, token, {jsonrpc: '2.0', id: 3, method: 'tools/call', params: {name: 'initial_context', arguments: {}}}, initialized.sessionId)
      : null
    const text = initialContextText(initial?.value?.result)
    const knowledgeBaseId = text.match(/Knowledge base id:\s*`([^`]+)`/i)?.[1]
    const entries = text.match(/(\d+) entries\b/i)?.[1]
    if (knowledgeBaseId) status.knowledgeBaseId = knowledgeBaseId
    if (entries) status.entries = Number(entries)
    return status
  } catch (error) {
    return {...status, message: 'Hosted Context MCP could not be reached.', error: error.message}
  }
}
