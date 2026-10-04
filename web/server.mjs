import http from 'node:http'
import fs from 'node:fs/promises'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {context} from '../agent/sanity-context.mjs'
import {getHostedContextStatus} from '../agent/hosted-context.mjs'

const root = path.dirname(fileURLToPath(import.meta.url))
const mime = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8'}

const server = http.createServer(async (request, response) => {
  try {
    const url = new URL(request.url, 'http://localhost')
    if (url.pathname === '/healthz') return sendJson(response, {ok: true})
    if (url.pathname === '/api/cases') return sendJson(response, await context.listCases())
    if (url.pathname === '/api/investigate') {
      const caseId = url.searchParams.get('caseId') || 'CASE-001'
      const question = url.searchParams.get('question') || 'What happened in this incident?'
      return sendJson(response, await context.investigate(caseId, question))
    }
    if (url.pathname === '/api/context-status') return sendJson(response, await getHostedContextStatus())
    const file = url.pathname === '/' ? 'index.html' : url.pathname.slice(1)
    const content = await fs.readFile(path.join(root, file))
    response.writeHead(200, {'Content-Type': mime[path.extname(file)] || 'application/octet-stream'})
    response.end(content)
  } catch (error) {
    sendJson(response, {error: error.message}, 500)
  }
})

function sendJson(response, body, status = 200) {
  response.writeHead(status, {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'})
  response.end(JSON.stringify(body))
}

const port = Number(process.env.PORT || 3000)
const host = process.env.HOST || '0.0.0.0'
server.listen(port, host, () => console.log(`Cyber Autopsy UI: http://${host}:${port}`))
