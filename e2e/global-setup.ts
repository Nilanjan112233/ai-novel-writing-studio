import fs from 'node:fs/promises'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { MongoClient } from 'mongodb'

const statePath = path.join(process.cwd(), 'artifacts', 'playwright-e2e-project-state.json')
const operationalCollections = ['project_backups', 'restore_operations', 'support_bundles', 'beta_feedback']

export default async function globalSetup() {
  const databaseName = process.env.NOVELFORGE_E2E_DATABASE || process.env.DATABASE_NAME || ''
  if (!databaseName.toLowerCase().includes('e2e')) {
    throw new Error('Refusing Playwright setup outside a dedicated E2E database.')
  }
  const client = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017')
  await client.connect()
  try {
    const database = client.db(databaseName)
    const existing = await database.collection('projects')
      .find({}, { projection: { _id: 1 } }).toArray()
    const existingProviderModels = await database.collection('provider_models')
      .find({}, { projection: { provider: 1, model_id: 1 } }).toArray()
    const existingOperationalIds: Record<string, string[]> = {}
    for (const name of operationalCollections) {
      existingOperationalIds[name] = (await database.collection(name)
        .find({}, { projection: { _id: 1 } }).toArray()).map((item) => item._id.toString())
    }
    const sourceDatabaseName = process.env.NOVELFORGE_SOURCE_DATABASE || 'novelforge'
    if (sourceDatabaseName !== databaseName) {
      const sourceSettings = await client.db(sourceDatabaseName).collection('app_settings')
        .findOne({ _id: 'global_settings' })
      if (sourceSettings) {
        await database.collection('app_settings').replaceOne(
          { _id: 'global_settings' },
          sourceSettings,
          { upsert: true },
        )
      }
      const sourceModels = await client.db(sourceDatabaseName).collection('provider_models')
        .find({}).toArray()
      for (const sourceModel of sourceModels) {
        const { _id: _sourceId, ...model } = sourceModel
        await database.collection('provider_models').updateOne(
          { provider: model.provider, model_id: model.model_id },
          { $set: model },
          { upsert: true },
        )
      }
    }
    const validationProject = await database.collection('projects').findOne({
      title: 'Phase 3C Validation: The Bell Beneath Winter',
    })
    if (!validationProject) {
      execFileSync('py', ['-3.11', 'backend/scripts/run_phase_3c_validation.py'], {
        cwd: process.cwd(),
        env: {
          ...process.env,
          DATABASE_NAME: databaseName,
        },
        stdio: 'inherit',
      })
    }
    const seededFixtures = await database.collection('projects')
      .find({ _id: { $nin: existing.map((item) => item._id) } }, { projection: { _id: 1 } })
      .toArray()
    await fs.mkdir(path.dirname(statePath), { recursive: true })
    await fs.writeFile(statePath, JSON.stringify({
      databaseName,
      existingProjectIds: existing.map((item) => item._id.toString()),
      existingProviderModelKeys: existingProviderModels.map((item) => `${item.provider}:${item.model_id}`),
      existingOperationalIds,
      seededFixtureProjectIds: seededFixtures.map((item) => item._id.toString()),
      startedAt: new Date().toISOString(),
    }, null, 2))
  } finally {
    await client.close()
  }
}
