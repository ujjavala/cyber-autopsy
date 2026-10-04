import {context} from '../agent/sanity-context.mjs'
import {getHostedContextStatus} from '../agent/hosted-context.mjs'

export default async function handler(request, response) {
  response.setHeader('Access-Control-Allow-Origin', '*')
  response.setHeader('Content-Type', 'application/json; charset=utf-8')

  try {
    const url = new URL(request.url || '/', 'https://cyber-autopsy.vercel.app')
    if (url.pathname === '/api/cases') {
      return response.status(200).json(await context.listCases())
    }
    if (url.pathname === '/api/investigate') {
      const caseId = url.searchParams.get('caseId') || 'CASE-001'
      const question = url.searchParams.get('question') || 'What happened in this incident?'
      return response.status(200).json(await context.investigate(caseId, question))
    }
    if (url.pathname === '/api/context-status') {
      return response.status(200).json(await getHostedContextStatus())
    }
    return response.status(404).json({error: 'Not found'})
  } catch (error) {
    return response.status(500).json({error: error.message})
  }
}
