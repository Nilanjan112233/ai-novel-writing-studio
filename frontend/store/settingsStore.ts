import { create } from 'zustand'
import { settingsApi } from '@/lib/api'
import { AgentModelAssignment, AIExecutionSettings, ExecutionTrace, ModelInfo, ModelValidationResult, ProviderHealth, ProviderTestResult, ValidateModelsResponse } from '@/types'

interface SettingsState {
  settings: any
  executionSettings: AIExecutionSettings | null
  agentAssignments: AgentModelAssignment[]
  models: ModelInfo[]
  providerHealth: ProviderHealth[]
  modelValidations: ModelValidationResult[]
  executionTraces: ExecutionTrace[]
  validationRuns: Record<string, ValidateModelsResponse>
  providerValidationResults: Record<string, any>
  workflowTestResult: any
  fullWorkflowTestResult: any
  recommendations: Record<string, any>
  testResults: Record<string, ProviderTestResult>
  loading: boolean
  error: string | null
  
  fetchSettings: () => Promise<void>
  fetchOrchestrationSettings: () => Promise<void>
  fetchModels: (provider?: string, refresh?: boolean) => Promise<void>
  fetchProviderHealth: () => Promise<void>
  fetchModelValidations: (provider?: string) => Promise<void>
  validateModels: (provider: string) => Promise<ValidateModelsResponse>
  validateProvider: (provider: string, apiKey?: string) => Promise<any>
  discoverModels: (provider: string, apiKey?: string) => Promise<any>
  fetchExecutionTraces: () => Promise<void>
  runAIWorkflowTest: (provider: string, model: string) => Promise<any>
  runFullWorkflowTest: (provider: string, model: string) => Promise<any>
  fetchRecommendation: (taskType: string) => Promise<any>
  updateSettings: (data: any) => Promise<void>
  updateExecutionSettings: (data: Partial<AIExecutionSettings>) => Promise<void>
  updateAgentAssignments: (data: AgentModelAssignment[]) => Promise<void>
  applyPreset: (preset: string) => Promise<void>
  testProvider: (provider: string, settings?: any) => Promise<any>
  testModel: (provider: string, model: string) => Promise<ProviderTestResult>
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  executionSettings: null,
  agentAssignments: [],
  models: [],
  providerHealth: [],
  modelValidations: [],
  executionTraces: [],
  validationRuns: {},
  providerValidationResults: {},
  workflowTestResult: null,
  fullWorkflowTestResult: null,
  recommendations: {},
  testResults: {},
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null })
    try {
      const [settings, executionSettings, agentAssignments, models, providerHealth, modelValidations, executionTraces] = await Promise.all([
        settingsApi.get(),
        settingsApi.getExecution(),
        settingsApi.getAgentAssignments(),
        settingsApi.getModels(undefined, false, false).catch(() => []),
        settingsApi.getHealth().catch(() => []),
        settingsApi.getModelValidations().catch(() => []),
        settingsApi.getExecutionTraces().catch(() => []),
      ])
      set({ settings, executionSettings, agentAssignments, models, providerHealth, modelValidations, executionTraces, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false, settings: { providers: {} } })
    }
  },

  fetchOrchestrationSettings: async () => {
    set({ loading: true, error: null })
    try {
      const [executionSettings, agentAssignments] = await Promise.all([
        settingsApi.getExecution(),
        settingsApi.getAgentAssignments(),
      ])
      set({ executionSettings, agentAssignments, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  fetchModels: async (provider, refresh = false) => {
    set({ loading: true, error: null })
    try {
      const models = await settingsApi.getModels(provider, refresh, false)
      set((state) => ({
        models: provider
          ? [...state.models.filter((model) => model.provider !== provider), ...models]
          : models,
        loading: false,
      }))
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  fetchProviderHealth: async () => {
    try {
      const providerHealth = await settingsApi.getHealth()
      set({ providerHealth })
    } catch (error: any) {
      set({ error: error.message })
    }
  },

  fetchModelValidations: async (provider) => {
    try {
      const modelValidations = await settingsApi.getModelValidations(provider)
      set({ modelValidations })
    } catch (error: any) {
      set({ error: error.message })
    }
  },

  validateModels: async (provider) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.validateModels(provider)
      const [models, modelValidations, providerHealth, executionTraces] = await Promise.all([
        settingsApi.getModels(undefined, false, false).catch(() => []),
        settingsApi.getModelValidations().catch(() => []),
        settingsApi.getHealth().catch(() => []),
        settingsApi.getExecutionTraces().catch(() => []),
      ])
      set((state) => ({
        loading: false,
        validationRuns: { ...state.validationRuns, [provider]: response },
        models,
        modelValidations,
        providerHealth,
        executionTraces,
      }))
      return response
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  validateProvider: async (provider, apiKey) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.validateProvider(provider, apiKey)
      set((state) => ({
        loading: false,
        providerValidationResults: {
          ...state.providerValidationResults,
          [provider]: response,
        },
      }))
      return response
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  discoverModels: async (provider, apiKey) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.discoverModels(provider, apiKey)
      const [models, providerHealth] = await Promise.all([
        settingsApi.getModels(undefined, false, false).catch(() => []),
        settingsApi.getHealth().catch(() => []),
      ])
      set({ models, providerHealth, loading: false })
      return response
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  fetchExecutionTraces: async () => {
    try {
      const executionTraces = await settingsApi.getExecutionTraces()
      set({ executionTraces })
    } catch (error: any) {
      set({ error: error.message })
    }
  },

  runAIWorkflowTest: async (provider, model) => {
    set({ loading: true, error: null })
    try {
      const workflowTestResult = await settingsApi.runAIWorkflowTest(provider, model)
      const executionTraces = await settingsApi.getExecutionTraces().catch(() => [])
      set({ workflowTestResult, executionTraces, loading: false })
      return workflowTestResult
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  runFullWorkflowTest: async (provider, model) => {
    set({ loading: true, error: null })
    try {
      const fullWorkflowTestResult = await settingsApi.runFullWorkflowTest(provider, model)
      const executionTraces = await settingsApi.getExecutionTraces().catch(() => [])
      set({ fullWorkflowTestResult, executionTraces, loading: false })
      return fullWorkflowTestResult
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  fetchRecommendation: async (taskType) => {
    const response = await settingsApi.getRecommendation({ task_type: taskType })
    set((state) => ({ recommendations: { ...state.recommendations, [taskType]: response } }))
    return response
  },

  updateSettings: async (data: any) => {
    set({ loading: true, error: null })
    try {
      await settingsApi.update(data)
      const response = await settingsApi.get()
      set({ settings: response, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  updateExecutionSettings: async (data) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.updateExecution(data)
      set({ executionSettings: response, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  updateAgentAssignments: async (data) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.updateAgentAssignments(data)
      set({ agentAssignments: response, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  applyPreset: async (preset) => {
    set({ loading: true, error: null })
    try {
      const executionSettings = await settingsApi.applyPreset(preset)
      set({ executionSettings, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  testProvider: async (provider: string, settings?: any) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.test(provider, settings)
      set({ loading: false })
      return response
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  testModel: async (provider: string, model: string) => {
    set({ loading: true, error: null })
    try {
      const response = await settingsApi.testModel({ provider, model })
      const [executionTraces, modelValidations, providerHealth] = await Promise.all([
        settingsApi.getExecutionTraces().catch(() => []),
        settingsApi.getModelValidations().catch(() => []),
        settingsApi.getHealth().catch(() => []),
      ])
      set((state) => ({
        loading: false,
        executionTraces,
        modelValidations,
        providerHealth,
        testResults: {
          ...state.testResults,
          [`${provider}:${model}`]: response,
        },
      }))
      return response
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },
}))
