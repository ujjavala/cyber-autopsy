import {defineArrayMember, defineField, defineType} from 'sanity'
import {DocumentTextIcon} from '@sanity/icons/DocumentText'
import {DocumentIcon} from '@sanity/icons/Document'
import {LinkIcon} from '@sanity/icons/Link'
import {PlayIcon} from '@sanity/icons/Play'
import {TagIcon} from '@sanity/icons/Tag'
import {UserIcon} from '@sanity/icons/User'

const statusOptions = [
  {title: 'Confirmed', value: 'confirmed'},
  {title: 'Inferred', value: 'inferred'},
  {title: 'Attempted', value: 'attempted'},
  {title: 'Failed', value: 'failed'},
  {title: 'Unknown', value: 'unknown'},
]

const referenceArray = (name: string, to: {type: string}[]) =>
  defineField({
    name,
    title: name[0].toUpperCase() + name.slice(1),
    type: 'array',
    of: [defineArrayMember({type: 'reference', to})],
  })

export const incident = defineType({
  name: 'incident',
  title: 'Incident',
  type: 'document',
  icon: DocumentTextIcon,
  fields: [
    defineField({name: 'incidentId', title: 'Benchmark ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'title', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'description', type: 'text', rows: 5}),
    referenceArray('source', [{type: 'source'}]),
    defineField({name: 'sourceUrl', type: 'url'}),
    defineField({name: 'reportedDate', type: 'string'}),
    defineField({name: 'actor', type: 'string'}),
    defineField({name: 'actorType', type: 'string'}),
    defineField({name: 'evidenceQuality', type: 'string'}),
    defineField({name: 'confidence', type: 'string'}),
    defineField({name: 'organization', type: 'string'}),
    defineField({name: 'sector', type: 'string'}),
    defineField({name: 'impact', type: 'text', rows: 4}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'title', subtitle: 'incidentId'}},
})

export const source = defineType({
  name: 'source',
  title: 'Source',
  type: 'document',
  icon: LinkIcon,
  fields: [
    defineField({name: 'sourceId', title: 'Benchmark ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'title', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'publisher', type: 'string'}),
    defineField({name: 'url', type: 'url'}),
    defineField({name: 'publishedDate', type: 'string'}),
    defineField({name: 'sourceType', type: 'string'}),
    defineField({name: 'description', type: 'text', rows: 4}),
    defineField({name: 'reliabilityTier', type: 'string'}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'title', subtitle: 'publisher'}},
})

export const evidence = defineType({
  name: 'evidence',
  title: 'Evidence',
  type: 'document',
  icon: DocumentIcon,
  fields: [
    defineField({name: 'evidenceId', title: 'Evidence ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'incident', type: 'reference', to: [{type: 'incident'}], validation: (rule) => rule.required()}),
    defineField({name: 'source', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'source'}]})]}),
    defineField({name: 'timestamp', type: 'string'}),
    defineField({name: 'type', type: 'string'}),
    defineField({name: 'description', type: 'text', rows: 5, validation: (rule) => rule.required()}),
    defineField({name: 'status', type: 'string', options: {list: statusOptions}}),
    defineField({name: 'entities', type: 'array', of: [defineArrayMember({type: 'string'})]}),
    defineField({name: 'supportsEvents', title: 'Supports events', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'event'}]})]}),
    defineField({name: 'supportsClaims', title: 'Supports claims', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'claim'}]})]}),
    defineField({name: 'contradictsClaims', title: 'Contradicts claims', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'claim'}]})]}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'evidenceId', subtitle: 'description'}},
})

export const event = defineType({
  name: 'event',
  title: 'Event',
  type: 'document',
  icon: PlayIcon,
  fields: [
    defineField({name: 'eventId', title: 'Event ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'incident', type: 'reference', to: [{type: 'incident'}], validation: (rule) => rule.required()}),
    defineField({name: 'description', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'timestamp', type: 'string'}),
    defineField({name: 'status', type: 'string', options: {list: statusOptions}}),
    defineField({name: 'evidence', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'evidence'}]})]}),
    defineField({name: 'confidence', type: 'number', validation: (rule) => rule.min(0).max(1)}),
    defineField({name: 'notes', type: 'text', rows: 3}),
    defineField({name: 'mitreTactic', type: 'string'}),
    defineField({name: 'mitreTechnique', type: 'string'}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'description', subtitle: 'status'}},
})

export const relationship = defineType({
  name: 'relationship',
  title: 'Relationship',
  type: 'document',
  icon: LinkIcon,
  fields: [
    defineField({name: 'relationshipId', title: 'Relationship ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'sourceEvent', type: 'reference', to: [{type: 'event'}], validation: (rule) => rule.required()}),
    defineField({name: 'targetEvent', type: 'reference', to: [{type: 'event'}], validation: (rule) => rule.required()}),
    defineField({name: 'relationship', type: 'string', options: {list: ['precedes', 'enables', 'causes', 'depends_on']}}),
    defineField({name: 'confidence', type: 'number', validation: (rule) => rule.min(0).max(1)}),
    defineField({name: 'evidence', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'evidence'}]})]}),
    defineField({name: 'incident', type: 'reference', to: [{type: 'incident'}]}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'relationshipId', subtitle: 'relationship'}},
})

export const claim = defineType({
  name: 'claim',
  title: 'Claim',
  type: 'document',
  icon: TagIcon,
  fields: [
    defineField({name: 'claimId', title: 'Claim ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'incident', type: 'reference', to: [{type: 'incident'}], validation: (rule) => rule.required()}),
    defineField({name: 'statement', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'status', type: 'string', options: {list: [...statusOptions, {title: 'Contradicted', value: 'contradicted'}]}}),
    defineField({name: 'confidence', type: 'number', validation: (rule) => rule.min(0).max(1)}),
    defineField({name: 'evidence', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'evidence'}]})]}),
    defineField({name: 'contradicts', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'claim'}]})]}),
    defineField({name: 'notes', type: 'text', rows: 3}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'statement', subtitle: 'status'}},
})

export const investigationCase = defineType({
  name: 'investigationCase',
  title: 'Investigation Case',
  type: 'document',
  icon: UserIcon,
  fields: [
    defineField({name: 'caseId', title: 'Case ID', type: 'string', validation: (rule) => rule.required()}),
    defineField({name: 'incident', type: 'reference', to: [{type: 'incident'}], validation: (rule) => rule.required()}),
    defineField({name: 'mode', type: 'string'}),
    defineField({name: 'temporalCutoff', type: 'string'}),
    defineField({name: 'framingActor', type: 'string'}),
    defineField({name: 'knowledgeCutoff', type: 'string'}),
    defineField({name: 'notes', type: 'text', rows: 4}),
    defineField({name: 'evidence', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'evidence'}]})]}),
    defineField({name: 'events', type: 'array', of: [defineArrayMember({type: 'reference', to: [{type: 'event'}]})]}),
    defineField({name: 'externalId', title: 'Source ID', type: 'string', readOnly: true}),
  ],
  preview: {select: {title: 'caseId', subtitle: 'mode'}},
})

export const schemaTypes = [incident, source, evidence, event, relationship, claim, investigationCase]
