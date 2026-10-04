import {defineBlueprint, defineDocumentFunction, defineRobotToken} from '@sanity/blueprints'

export default defineBlueprint({
  projectId: '41l9o4xn',
  resources: [
    defineRobotToken({
      name: 'review-queue-bot',
      label: 'Cyber Autopsy review queue bot',
      memberships: [{resourceType: 'project', resourceId: '41l9o4xn', roleNames: ['editor']}],
    }),
    defineDocumentFunction({
      name: 'review-queue-on-content-change',
      displayName: 'Review queue on content change',
      src: 'functions/review-queue',
      robotToken: '$.resources.review-queue-bot',
      event: {
        on: ['create', 'update'],
        filter: "_type in ['evidence', 'event', 'relationship', 'claim'] && !(_id in path('drafts.**'))",
        projection: '{_id, _type, title, incidentId, evidenceId, eventId, claimId, caseId, source, evidence, sourceEvent, targetEvent}',
      },
    }),
  ],
})
