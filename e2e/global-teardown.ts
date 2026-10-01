import fs from 'node:fs/promises'
import path from 'node:path'
import { MongoClient, ObjectId } from 'mongodb'

const statePath = path.join(process.cwd(), 'artifacts', 'playwright-e2e-project-state.json')

export default async function globalTeardown() {
  const state = JSON.parse(await fs.readFile(statePath, 'utf8')) as {
    databaseName: string
    existingProjectIds: string[]
    existingProviderModelKeys?: string[]
    existingOperationalIds?: Record<string, string[]>
  }
  if (!state.databaseName.toLowerCase().includes('e2e')) {
    throw new Error('Refusing Playwright cleanup outside a dedicated E2E database.')
  }
  const client = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017')
  await client.connect()
  try {
    const db = client.db(state.databaseName)
    const before = new Set(state.existingProjectIds)
    const current = await db.collection('projects').find({}, { projection: { _id: 1 } }).toArray()
    const createdIds = current.map((item) => item._id.toString()).filter((id) => !before.has(id))
    const objectIds = createdIds.filter(ObjectId.isValid).map((id) => new ObjectId(id))
    if (createdIds.length) {
      for (const { name } of await db.listCollections({}, { nameOnly: true }).toArray()) {
        const collection = db.collection(name)
        if (name === 'projects') {
          await collection.deleteMany({ _id: { $in: objectIds } })
        } else {
          await collection.deleteMany({
            $or: [
              { project_id: { $in: objectIds } },
              { project_id: { $in: createdIds } },
              { projectId: { $in: createdIds } },
            ],
          })
        }
      }
    }
    const preservedModels = new Set(state.existingProviderModelKeys || [])
    const providerModels = await db.collection('provider_models')
      .find({}, { projection: { provider: 1, model_id: 1 } }).toArray()
    const seededProviderModels = providerModels.filter(
      (item) => !preservedModels.has(`${item.provider}:${item.model_id}`),
    )
    for (const item of seededProviderModels) {
      await db.collection('provider_models').deleteOne({
        provider: item.provider,
        model_id: item.model_id,
      })
    }
    const exactCleanedOperationalIds: Record<string, string[]> = {}
    for (const [name, existingIds] of Object.entries(state.existingOperationalIds || {})) {
      const preserved = new Set(existingIds)
      const current = await db.collection(name).find({}, { projection: { _id: 1 } }).toArray()
      const created = current.filter((item) => !preserved.has(item._id.toString()))
      if (created.length) {
        await db.collection(name).deleteMany({ _id: { $in: created.map((item) => item._id) } })
      }
      exactCleanedOperationalIds[name] = created.map((item) => item._id.toString())
    }
    await fs.writeFile(statePath, JSON.stringify({
      ...state,
      exactCleanedProjectIds: createdIds,
      exactCleanedProviderModels: seededProviderModels.map((item) => `${item.provider}:${item.model_id}`),
      exactCleanedOperationalIds,
      completedAt: new Date().toISOString(),
    }, null, 2))
  } finally {
    await client.close()
  }
}
