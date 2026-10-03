import {defineCliConfig} from 'sanity/cli'

export default defineCliConfig({
  api: {
    projectId: '41l9o4xn',
    dataset: 'production'
  },
  deployment: {
    appId: 'miouk6g0qq6qtqcabnfvne9t',
    /**
     * Enable auto-updates for studios.
     * Learn more at https://www.sanity.io/docs/studio/latest-version-of-sanity#k47faf43faf56
     */
    autoUpdates: true,
  },
})
