import {execFileSync} from 'node:child_process'

const output = execFileSync(process.execPath, ['scripts/sanity-seed.mjs', '--dry-run'], {encoding: 'utf8'})
const summary = JSON.parse(output)
if (!summary.documents || !summary.byType.incident || !summary.byType.evidence || !summary.byType.event || !summary.byType.relationship || !summary.byType.claim || !summary.byType.investigationCase) throw new Error('Seed inventory is missing a required document type')
if (summary.byType.investigationCase < 13) throw new Error('Expected the existing benchmark case set to be represented')
console.log(`Sanity import inventory valid: ${summary.documents} documents in ${summary.batches} batches`)
