import {createClient} from '@sanity/client'
import fs from 'node:fs'

for (const line of (fs.existsSync('.env') ? fs.readFileSync('.env', 'utf8') : '').split(/\r?\n/)) {
  const separator = line.indexOf('=')
  if (separator > 0 && !line.trim().startsWith('#')) process.env[line.slice(0, separator).trim()] ||= line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, '')
}

const documentId = process.argv[2]
const schemaId = process.env.SANITY_SCHEMA_ID
const token = process.env.SANITY_API_TOKEN
if (!documentId || !schemaId || !token) {
  console.error('Usage: SANITY_SCHEMA_ID=... SANITY_API_TOKEN=... node scripts/draft-review-agent-action.mjs <review-task-id>')
  process.exit(1)
}

const client = createClient({projectId: process.env.SANITY_PROJECT_ID || '41l9o4xn', dataset: process.env.SANITY_DATASET || 'production', apiVersion: '2025-05-01', token, useCdn: false})
const task = await client.getDocument(documentId)
if (!task || task._type !== 'reviewTask') throw new Error(`Review task not found: ${documentId}`)

const result = await client.agent.action.generate({
  schemaId,
  documentId,
  instruction: 'Write concise reviewer notes for this cyber-forensics review task. Restate only what the task says, identify the missing link, and list a verification step. Do not infer attribution, intent, or guilt. Do not change the task status or severity.',
  instructionParams: {task: {type: 'document'}},
  target: {path: 'reviewerNotes', operation: 'set'},
})
console.log(JSON.stringify({documentId, draftOnly: true, result}, null, 2))
