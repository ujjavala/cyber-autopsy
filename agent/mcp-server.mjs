import readline from 'node:readline'
import {context} from './sanity-context.mjs'

const tools = [
  {name: 'list_investigation_cases', description: 'List Cyber Autopsy cases available in Sanity.', inputSchema: {type: 'object', properties: {}}},
  {name: 'investigate_case', description: 'Reconstruct a case from structured Sanity evidence, events, claims, and relationships.', inputSchema: {type: 'object', properties: {caseId: {type: 'string'}, question: {type: 'string'}}, required: ['caseId', 'question']}},
]

async function handle(message) {
  if (message.method === 'initialize') return {jsonrpc: '2.0', id: message.id, result: {protocolVersion: '2024-11-05', capabilities: {tools: {}}, serverInfo: {name: 'cyber-autopsy-sanity-context', version: '1.0.0'}}}
  if (message.method === 'notifications/initialized') return null
  if (message.method === 'tools/list') return {jsonrpc: '2.0', id: message.id, result: {tools}}
  if (message.method === 'tools/call') {
    const {name, arguments: args = {}} = message.params || {}
    const value = name === 'list_investigation_cases' ? await context.listCases() : await context.investigate(args.caseId, args.question)
    return {jsonrpc: '2.0', id: message.id, result: {content: [{type: 'text', text: JSON.stringify(value)}], structuredContent: value}}
  }
  return {jsonrpc: '2.0', id: message.id, error: {code: -32601, message: `Unknown method: ${message.method}`}}
}

const input = readline.createInterface({input: process.stdin})
input.on('line', async (line) => {
  try {
    const response = await handle(JSON.parse(line))
    if (response) process.stdout.write(`${JSON.stringify(response)}\n`)
  } catch (error) {
    process.stdout.write(`${JSON.stringify({jsonrpc: '2.0', id: null, error: {code: -32000, message: error.message}})}\n`)
  }
})
