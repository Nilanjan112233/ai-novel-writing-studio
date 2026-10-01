import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import SettingsPage from './page'

vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
  settingsApi: {
    getMemory: vi.fn().mockResolvedValue({ mode: 'native', endpoint: 'http://127.0.0.1:8420', configured: false }),
    updateMemory: vi.fn().mockResolvedValue({ mode: 'native', endpoint: 'http://127.0.0.1:8420', configured: false }),
    testMemory: vi.fn().mockResolvedValue({ mode: 'native', native: { available: true }, tencent: { available: false, error: 'endpoint_not_configured' } }),
  },
  operationsApi: {
    getReadiness: vi.fn().mockResolvedValue({
      status: 'ready',
      summary: 'NovelForge is ready for local writing.',
      app_version: '2.0.0-rc9',
      schema_version: 9,
      checks: {},
    }),
    getPrivacy: vi.fn().mockResolvedValue({ excluded_from_support_bundles: [] }),
    createSupportBundle: vi.fn(),
    downloadSupportBundle: vi.fn(),
    submitFeedback: vi.fn(),
    createAllBackups: vi.fn(),
  },
}))

import { useSettingsStore } from '@/store/settingsStore'

const baseStore = {
  settings: {
    providers: {
      gemini: { api_key: '', configured: true, model: 'gemini-flash' },
      groq: { api_key: '', model: 'llama-3.1-8b-instant' },
      openrouter: { api_key: '', model: 'google/gemma-3-27b-it:free' },
      anthropic: { api_key: '', model: 'claude-sonnet' },
      ollama: { url: 'http://localhost:11434/api/generate', model: 'phi3', enabled: false },
    },
    fallback_priority: ['gemini', 'groq'],
    llm_delay_seconds: 1,
  },
  executionSettings: {
    execution_mode: 'full',
    default_provider: 'gemini',
    default_model: 'gemini-2.5-flash',
    enable_streaming: true,
    enable_reflection_loops: true,
    enable_dynamic_routing: true,
    max_context_tokens: 120000,
    max_cycle_cost_usd: 2,
    max_agent_calls_per_cycle: 8,
    max_reflection_loops: 2,
  },
  agentAssignments: [
    {
      agent_name: 'CharacterAgent',
      provider: 'gemini',
      model: 'gemini-2.5-flash',
      temperature: 0.7,
      max_tokens: 4096,
      enabled: true,
      use_mock_in_hybrid: false,
    },
  ],
  models: [
    { provider: 'gemini', model_id: 'gemini-2.5-flash', display_name: 'Gemini 2.5 Flash', supports_json: true, supports_streaming: true, supports_tools: false, supports_large_context: true, supports_reasoning: false, supports_multimodal: true, free_tier: false, recommended_for: ['brainstorming'], tags: ['fast'] },
    { provider: 'groq', model_id: 'llama-3.1-8b-instant', display_name: 'Llama 3.1 8B Instant', supports_json: true, supports_streaming: true, supports_tools: false, supports_large_context: false, supports_reasoning: false, supports_multimodal: false, free_tier: false, recommended_for: ['routing'], tags: ['fast'] },
    { provider: 'openrouter', model_id: 'google/gemma-3-27b-it:free', display_name: 'Gemma 3 Free', supports_json: true, supports_streaming: true, supports_tools: false, supports_large_context: false, supports_reasoning: false, supports_multimodal: false, free_tier: true, recommended_for: ['brainstorming'], tags: ['free'] },
    { provider: 'anthropic', model_id: 'claude-sonnet', display_name: 'Claude Sonnet', supports_json: true, supports_streaming: true, supports_tools: false, supports_large_context: true, supports_reasoning: true, supports_multimodal: false, free_tier: false, recommended_for: ['continuity'], tags: ['reasoning'] },
    { provider: 'ollama', model_id: 'phi3', display_name: 'Phi-3 Local', supports_json: true, supports_streaming: true, supports_tools: false, supports_large_context: false, supports_reasoning: false, supports_multimodal: false, free_tier: true, recommended_for: ['local'], tags: ['local'] },
  ],
  providerHealth: [
    { provider: 'gemini', status: 'online', active_model: 'gemini-2.5-flash', last_latency_ms: 12, working_model_count: 1, discovered_model_count: 1, daily_usage: { requests: 1, tokens: 8, estimated_cost_usd: 0 } },
  ],
  modelValidations: [
    { provider: 'gemini', model: 'gemini-2.5-flash', display_name: 'Gemini 2.5 Flash', working: true, latency_ms: 12, supports_json: false, supports_streaming: true, tokens_used: 8, tested_at: new Date().toISOString() },
  ],
  executionTraces: [
    { _id: 'trace1', provider: 'gemini', model: 'gemini-2.5-flash', agent_name: 'ProviderValidation', prompt_tokens: 4, response_tokens: 4, total_tokens: 8, latency_ms: 12, status: 'success', retry_count: 0, fallback_used: false, created_at: new Date().toISOString() },
  ],
  validationRuns: {},
  providerValidationResults: {},
  workflowTestResult: null,
  fullWorkflowTestResult: null,
  recommendations: {},
  testResults: {},
  loading: false,
  error: null,
  fetchSettings: vi.fn(),
  fetchOrchestrationSettings: vi.fn(),
  fetchModels: vi.fn(),
  fetchProviderHealth: vi.fn(),
  fetchModelValidations: vi.fn(),
  validateModels: vi.fn().mockResolvedValue({ provider: 'gemini', total: 1, working: 1, failed: 0, results: [] }),
  validateProvider: vi.fn().mockResolvedValue({ provider: 'gemini', valid: true }),
  discoverModels: vi.fn().mockResolvedValue({ provider: 'gemini', status: 'online', discovered_model_count: 1 }),
  fetchExecutionTraces: vi.fn(),
  runAIWorkflowTest: vi.fn().mockResolvedValue({ success: true }),
  runFullWorkflowTest: vi.fn().mockResolvedValue({ success: true }),
  fetchRecommendation: vi.fn(),
  updateSettings: vi.fn(),
  updateExecutionSettings: vi.fn(),
  updateAgentAssignments: vi.fn(),
  applyPreset: vi.fn(),
  testProvider: vi.fn(),
  testModel: vi.fn().mockResolvedValue({ success: true, latency_ms: 10, tokens_used: 8, json_valid: true }),
}

describe('Settings orchestration page', () => {
  const mockUseSettingsStore = vi.mocked(useSettingsStore)

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSettingsStore.mockReturnValue(baseStore as any)
  })

  it('renders execution settings and per-agent assignment table', () => {
    render(<SettingsPage />)
    expect(screen.queryByTestId('execution-settings')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Developer Mode' }))
    expect(screen.getByTestId('execution-settings')).toBeInTheDocument()
    expect(screen.getByTestId('agent-assignment-table')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-gemini')).toBeInTheDocument()
    expect(screen.getByText('CharacterAgent')).toBeInTheDocument()
  })

  it('tests a configured model through real inference endpoint contract', async () => {
    render(<SettingsPage />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Test Selected Model' })[0])
    await waitFor(() => {
      expect(baseStore.testModel).toHaveBeenCalledWith('gemini', 'gemini-flash')
    })
  })

  it('populates provider and agent dropdowns from discovered models', () => {
    render(<SettingsPage />)
    const geminiSelect = screen.getByTestId('model-select-gemini')
    expect(geminiSelect).toHaveTextContent('Gemini 2.5 Flash')
    expect(screen.getByTestId('discovered-count-gemini')).toHaveTextContent('1')
    expect(screen.getAllByRole('button', { name: 'Discover Models' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Verify Working Models' }).length).toBeGreaterThan(0)
  })

  it('shows configured state without rendering a stored credential', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Credential configured. The stored value is never returned.')).toBeInTheDocument()
    const geminiKey = screen.getByPlaceholderText('Configured - enter a new key to replace')
    expect(geminiKey).toHaveValue('')
  })
})
