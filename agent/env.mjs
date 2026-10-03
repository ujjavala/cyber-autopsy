import fs from 'node:fs'
import path from 'node:path'

export function loadEnv(root = process.cwd()) {
  const file = path.join(root, '.env')
  if (!fs.existsSync(file)) return
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const separator = trimmed.indexOf('=')
    if (separator < 1) continue
    const key = trimmed.slice(0, separator).trim()
    const value = trimmed.slice(separator + 1).trim().replace(/^['"]|['"]$/g, '')
    if (!(key in process.env)) process.env[key] = value
  }
}

export function sanityConfig() {
  const projectId = process.env.SANITY_PROJECT_ID || '41l9o4xn'
  const dataset = process.env.SANITY_DATASET || 'production'
  return {projectId, dataset, token: process.env.SANITY_API_TOKEN || ''}
}
