import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockApi),
  },
}))

import { projectsApi, workflowApi, dataApi, settingsApi } from './api'

describe('API Methods', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('projectsApi', () => {
    it('getAll should return data from response', async () => {
      const mockData = [{ id: '1', title: 'Project 1' }]
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await projectsApi.getAll()
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects')
    })

    it('getById should return data from response', async () => {
      const mockData = { id: '1', title: 'Project 1' }
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await projectsApi.getById('1')
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/1')
    })

    it('create should return data from response', async () => {
      const mockData = { id: '1', title: 'New Project' }
      mockApi.post.mockResolvedValue({ data: mockData })

      const result = await projectsApi.create({ title: 'New Project' })
      expect(result).toEqual(mockData)
      expect(mockApi.post).toHaveBeenCalledWith('/api/projects', { title: 'New Project' })
    })

    it('update should return data from response', async () => {
      const mockData = { id: '1', title: 'Updated Project' }
      mockApi.put.mockResolvedValue({ data: mockData })

      const result = await projectsApi.update('1', { title: 'Updated Project' })
      expect(result).toEqual(mockData)
      expect(mockApi.put).toHaveBeenCalledWith('/api/projects/1', { title: 'Updated Project' })
    })

    it('delete should return data from response', async () => {
      const mockData = { message: 'Project deleted' }
      mockApi.delete.mockResolvedValue({ data: mockData })

      const result = await projectsApi.delete('1')
      expect(result).toEqual(mockData)
      expect(mockApi.delete).toHaveBeenCalledWith('/api/projects/1')
    })
  })

  describe('workflowApi', () => {
    it('run should return data from response', async () => {
      const mockData = { id: 'run1', status: 'running' }
      mockApi.post.mockResolvedValue({ data: mockData })

      const result = await workflowApi.run('proj1')
      expect(result).toEqual(mockData)
      expect(mockApi.post).toHaveBeenCalledWith('/api/projects/proj1/run')
    })

    it('getRuns should return data from response', async () => {
      const mockData = [{ id: 'run1', status: 'completed' }]
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await workflowApi.getRuns('proj1')
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/runs')
    })

    it('submitAnswer should return data from response', async () => {
      const mockData = { message: 'Answer submitted' }
      mockApi.post.mockResolvedValue({ data: mockData })

      const result = await workflowApi.submitAnswer('proj1', { question_id: 'q1', answer: 'A' })
      expect(result).toEqual(mockData)
      expect(mockApi.post).toHaveBeenCalledWith('/api/projects/proj1/answers', { question_id: 'q1', answer: 'A' })
    })

    it('getOutputs should return data from response', async () => {
      const mockData = [{ id: 'out1', content: 'Output' }]
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await workflowApi.getOutputs('proj1', 'run1')
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/outputs', { params: { run_id: 'run1' } })
    })
  })

  describe('dataApi', () => {
    it('getOutline should return data from response', async () => {
      const mockData = { premise: 'Test premise', acts: [] }
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await dataApi.getOutline('proj1')
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/outline')
    })

    it('getQuestions should return data from response', async () => {
      const mockData = [{ id: 'q1', text: 'Question?' }]
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await dataApi.getQuestions('proj1')
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/questions')
    })

    it('getCharacterBibles should return data from response', async () => {
      mockApi.get.mockResolvedValue({ data: [{ name: 'Mentor' }] })
      const result = await dataApi.getCharacterBibles('proj1')
      expect(result).toEqual([{ name: 'Mentor' }])
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/character-bibles')
    })

    it('draftScenes should post to scene drafting endpoint', async () => {
      mockApi.post.mockResolvedValue({ data: { message: 'ok' } })
      const result = await dataApi.draftScenes('proj1', 'arc-1')
      expect(result).toEqual({ message: 'ok' })
      expect(mockApi.post).toHaveBeenCalledWith(
        '/api/projects/proj1/draft-scenes',
        { arc_id: 'arc-1' },
      )
    })

    it('getLatestOrchestration should call orchestration endpoint', async () => {
      mockApi.get.mockResolvedValue({ data: { cycle_number: 1 } })
      const result = await dataApi.getLatestOrchestration('proj1')
      expect(result).toEqual({ cycle_number: 1 })
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/orchestration/latest')
    })

    it('getLatestContext should call context endpoint', async () => {
      mockApi.get.mockResolvedValue({ data: { token_estimate: 42 } })
      const result = await dataApi.getLatestContext('proj1')
      expect(result).toEqual({ token_estimate: 42 })
      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/proj1/context/latest')
    })
  })

  describe('settingsApi', () => {
    it('get should return data from response', async () => {
      const mockData = { provider: 'gemini' }
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await settingsApi.get()
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/settings/ai')
    })

    it('update should return data from response', async () => {
      const mockData = { provider: 'openrouter' }
      mockApi.put.mockResolvedValue({ data: mockData })

      const result = await settingsApi.update({ provider: 'openrouter' })
      expect(result).toEqual(mockData)
      expect(mockApi.put).toHaveBeenCalledWith('/api/settings/ai', { provider: 'openrouter' })
    })

    it('testModel should call real inference validation endpoint', async () => {
      const mockData = { success: true, json_valid: true }
      mockApi.post.mockResolvedValue({ data: mockData })

      const result = await settingsApi.testModel({ provider: 'mock', model: 'mock-narrative-intelligence' })
      expect(result).toEqual(mockData)
      expect(mockApi.post).toHaveBeenCalledWith('/api/ai/test-model', { provider: 'mock', model: 'mock-narrative-intelligence' })
    })

    it('updates orchestration execution settings', async () => {
      const mockData = { execution_mode: 'hybrid' }
      mockApi.put.mockResolvedValue({ data: mockData })

      const result = await settingsApi.updateExecution({ execution_mode: 'hybrid' })
      expect(result).toEqual(mockData)
      expect(mockApi.put).toHaveBeenCalledWith('/api/settings/execution', { execution_mode: 'hybrid' })
    })

    it('gets model registry entries', async () => {
      const mockData = [{ provider: 'openrouter', model_id: 'google/gemma-3-27b-it:free' }]
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await settingsApi.getModels('openrouter', true)
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/settings/models', { params: { provider: 'openrouter', refresh: true, verified_only: false } })
    })

    it('validates provider models and reads execution traces', async () => {
      mockApi.post.mockResolvedValueOnce({ data: { provider: 'gemini', total: 1, working: 1, failed: 0 } })
      mockApi.get.mockResolvedValueOnce({ data: [{ provider: 'gemini', model: 'gemini-2.5-flash', working: true }] })
      mockApi.get.mockResolvedValueOnce({ data: [{ provider: 'gemini', model: 'gemini-2.5-flash', status: 'success' }] })

      await expect(settingsApi.validateModels('gemini')).resolves.toEqual({ provider: 'gemini', total: 1, working: 1, failed: 0 })
      await expect(settingsApi.getModelValidations('gemini')).resolves.toEqual([{ provider: 'gemini', model: 'gemini-2.5-flash', working: true }])
      await expect(settingsApi.getExecutionTraces()).resolves.toEqual([{ provider: 'gemini', model: 'gemini-2.5-flash', status: 'success' }])

      expect(mockApi.post).toHaveBeenCalledWith('/api/settings/validate-models', { provider: 'gemini' })
      expect(mockApi.get).toHaveBeenCalledWith('/api/settings/model-validations', { params: { provider: 'gemini' } })
      expect(mockApi.get).toHaveBeenCalledWith('/api/settings/execution-traces', { params: { limit: 50 } })
    })

    it('runs full workflow provider smoke endpoint', async () => {
      mockApi.post.mockResolvedValue({ data: { success: true, outputs: 4 } })
      const result = await settingsApi.runFullWorkflowTest('gemini', 'gemini-2.5-flash-lite')
      expect(result).toEqual({ success: true, outputs: 4 })
      expect(mockApi.post).toHaveBeenCalledWith('/api/settings/run-full-workflow-test', { provider: 'gemini', model: 'gemini-2.5-flash-lite' })
    })

    it('gets provider health', async () => {
      const mockData = [{ provider: 'mock', status: 'online' }]
      mockApi.get.mockResolvedValue({ data: mockData })

      const result = await settingsApi.getHealth()
      expect(result).toEqual(mockData)
      expect(mockApi.get).toHaveBeenCalledWith('/api/settings/health')
    })

    it('validates providers and discovers models independently', async () => {
      mockApi.post
        .mockResolvedValueOnce({ data: { provider: 'openai', valid: true } })
        .mockResolvedValueOnce({ data: { provider: 'openai', status: 'online', discovered_model_count: 2 } })

      await expect(settingsApi.validateProvider('openai', 'key')).resolves.toEqual({ provider: 'openai', valid: true })
      await expect(settingsApi.discoverModels('openai', 'key')).resolves.toEqual({
        provider: 'openai',
        status: 'online',
        discovered_model_count: 2,
      })
      expect(mockApi.post).toHaveBeenCalledWith('/api/settings/providers/openai/validate', { api_key: 'key' })
      expect(mockApi.post).toHaveBeenCalledWith('/api/settings/providers/openai/discover', { api_key: 'key' })
    })
  })
})
