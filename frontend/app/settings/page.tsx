"use client"

import { useEffect, useMemo, useState } from 'react'
import { useSettingsStore } from '@/store/settingsStore'
import { settingsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AgentModelAssignment } from '@/types'
import { Check, Code2, Loader2, RefreshCw, SlidersHorizontal, TestTube2, X } from 'lucide-react'
import OperationalReadinessPanel from '@/components/OperationalReadinessPanel'

const PROVIDERS = ['gemini', 'groq', 'openrouter', 'openai', 'anthropic', 'ollama']
const PRESETS = ['cheap', 'creative', 'balanced', 'drafting', 'continuity']

export default function SettingsPage() {
  const {
    settings,
    executionSettings,
    agentAssignments,
    models,
    providerHealth,
    modelValidations,
    validationRuns,
    providerValidationResults = {},
    testResults,
    loading,
    fetchSettings,
    updateSettings,
    updateExecutionSettings,
    updateAgentAssignments,
    applyPreset,
    testModel,
    fetchProviderHealth,
    validateModels,
    validateProvider,
    discoverModels,
  } = useSettingsStore()

  const [localSettings, setLocalSettings] = useState<any>(null)
  const [localExecution, setLocalExecution] = useState<any>(null)
  const [localAssignments, setLocalAssignments] = useState<AgentModelAssignment[]>([])
  const [testingKey, setTestingKey] = useState<string | null>(null)
  const [validatingProvider, setValidatingProvider] = useState<string | null>(null)
  const [discoveringProvider, setDiscoveringProvider] = useState<string | null>(null)
  const [developerMode, setDeveloperMode] = useState(false)
  const [memorySettings, setMemorySettings] = useState<any>(null)
  const [memoryStatus, setMemoryStatus] = useState<any>(null)
  const [memoryApiKey, setMemoryApiKey] = useState('')
  const [memorySmoke, setMemorySmoke] = useState<any>(null)
  const [memorySmokeRunning, setMemorySmokeRunning] = useState(false)

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  useEffect(() => {
    fetchProviderHealth()
  }, [fetchProviderHealth])

  useEffect(() => {
    settingsApi.getMemory().then(setMemorySettings).catch(() => setMemorySettings({ mode: 'native', endpoint: 'http://127.0.0.1:8420' }))
  }, [])

  useEffect(() => {
    if (settings) setLocalSettings(settings)
  }, [settings])

  useEffect(() => {
    if (executionSettings) setLocalExecution(executionSettings)
  }, [executionSettings])

  useEffect(() => {
    setLocalAssignments(agentAssignments)
  }, [agentAssignments])

  const providerRows = useMemo(
    () => Object.keys(localSettings?.providers || {}).filter((provider) => !['local', 'claude', 'huggingface', 'mock'].includes(provider)),
    [localSettings],
  )
  const validationFor = (provider: string, model: string) => modelValidations.find(
    (item) => item.provider === provider && item.model === model,
  )
  const modelsFor = (provider: string) => models
    .filter((model) => model.provider === provider)
    .sort((a, b) => {
      const aWorking = validationFor(provider, a.model_id)?.working ? 1 : 0
      const bWorking = validationFor(provider, b.model_id)?.working ? 1 : 0
      return bWorking - aWorking || a.display_name.localeCompare(b.display_name)
    })
  const verifiedModelsFor = (provider: string) => modelsFor(provider).filter(
    (model) => validationFor(provider, model.model_id)?.working,
  )
  const validationsFor = (provider: string) => modelValidations.filter((item) => item.provider === provider)
  const healthFor = (provider: string) => providerHealth.find((item) => item.provider === provider)

  const handleProviderChange = (provider: string, field: string, value: any) => {
    setLocalSettings({
      ...localSettings,
      providers: {
        ...localSettings?.providers,
        [provider]: {
          ...localSettings?.providers?.[provider],
          [field]: value,
        },
      },
    })
  }

  const updateAssignment = (index: number, patch: Partial<AgentModelAssignment>) => {
    setLocalAssignments((items) => items.map((item, i) => i === index ? { ...item, ...patch } : item))
  }

  const saveAll = async () => {
    if (localSettings) await updateSettings(localSettings)
    if (localExecution) await updateExecutionSettings(localExecution)
    await updateAgentAssignments(localAssignments)
    if (memorySettings) {
      const payload = { ...memorySettings }
      if (memoryApiKey.trim()) payload.api_key = memoryApiKey.trim()
      await settingsApi.updateMemory(payload)
      setMemoryApiKey('')
    }
  }

  const testMemory = async () => {
    setMemoryStatus(await settingsApi.testMemory())
  }

  const runMemorySmoke = async () => {
    setMemorySmokeRunning(true)
    try {
      setMemorySmoke(await settingsApi.smokeTestMemory())
    } finally {
      setMemorySmokeRunning(false)
    }
  }

  const runModelTest = async (provider: string, model: string) => {
    const key = `${provider}:${model}`
    setTestingKey(key)
    try {
      await testModel(provider, model)
    } finally {
      setTestingKey(null)
    }
  }

  const runValidation = async (provider: string) => {
    setValidatingProvider(provider)
    try {
      const result = await validateModels(provider)
      const firstWorking = result.results.find((item) => item.working || item.success)
      if (firstWorking && !localSettings.providers?.[provider]?.model) {
        handleProviderChange(provider, 'model', firstWorking.model)
      }
    } finally {
      setValidatingProvider(null)
    }
  }

  const runProviderValidation = async (provider: string) => {
    setValidatingProvider(provider)
    try {
      await validateProvider(provider, localSettings.providers?.[provider]?.api_key || '')
    } finally {
      setValidatingProvider(null)
    }
  }

  const runDiscovery = async (provider: string) => {
    setDiscoveringProvider(provider)
    try {
      await discoverModels(provider, localSettings.providers?.[provider]?.api_key || '')
    } finally {
      setDiscoveringProvider(null)
    }
  }

  if (!localSettings || !localExecution) {
    return <div className="p-8">Loading settings...</div>
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <OperationalReadinessPanel />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">AI Connections & Settings</h1>
            <p className="text-sm text-muted-foreground">Connect an AI provider, verify a model, and choose the default service NovelForge should use.</p>
          </div>
          <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setDeveloperMode((value) => !value)} aria-pressed={developerMode}><Code2 className="mr-2 h-4 w-4" />Developer Mode</Button><Button onClick={saveAll} disabled={loading} className="gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            {loading ? 'Saving...' : 'Save Settings'}
          </Button></div>
        </div>

        {developerMode ? (
        <section className="rounded-lg border bg-card p-5 space-y-4" data-testid="execution-settings">
          <div><h2 className="text-xl font-semibold">Advanced execution</h2><p className="text-sm text-muted-foreground">Developer controls for routing, context limits, and project-run budgets.</p></div>
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <Label htmlFor="execution-mode">Execution Mode</Label>
              <select
                id="execution-mode"
                className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm"
                value={localExecution.execution_mode}
                onChange={(event) => setLocalExecution({ ...localExecution, execution_mode: event.target.value })}
              >
                <option value="hybrid">Hybrid</option>
                <option value="full">Full AI</option>
              </select>
            </div>
            <div>
              <Label htmlFor="default-provider">Default Provider</Label>
              <select
                id="default-provider"
                className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm"
                value={localExecution.default_provider}
                onChange={(event) => {
                  const nextProvider = event.target.value
                  setLocalExecution({ ...localExecution, default_provider: nextProvider, default_model: verifiedModelsFor(nextProvider)[0]?.model_id || '' })
                }}
              >
                {PROVIDERS.map((provider) => <option key={provider} value={provider}>{provider}</option>)}
              </select>
            </div>
            <div>
              <Label htmlFor="default-model">Default Model</Label>
              <select
                id="default-model"
                className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm"
                value={localExecution.default_model}
                onChange={(event) => setLocalExecution({ ...localExecution, default_model: event.target.value })}
              >
                {verifiedModelsFor(localExecution.default_provider).length === 0 && (
                  <option value="">No verified model available</option>
                )}
                {verifiedModelsFor(localExecution.default_provider).map((model) => (
                  <option key={model.model_id} value={model.model_id}>{model.display_name} ({model.model_id})</option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="cycle-budget">Max Cycle Cost USD</Label>
              <Input id="cycle-budget" type="number" step="0.05" value={localExecution.max_cycle_cost_usd} onChange={(event) => setLocalExecution({ ...localExecution, max_cycle_cost_usd: Number(event.target.value) })} />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              ['enable_streaming', 'Streaming'],
              ['enable_reflection_loops', 'Reflection Loops'],
              ['enable_dynamic_routing', 'Dynamic Routing'],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={Boolean(localExecution[key])} onChange={(event) => setLocalExecution({ ...localExecution, [key]: event.target.checked })} />
                {label}
              </label>
            ))}
            <div>
              <Label htmlFor="context-tokens">Context Tokens</Label>
              <Input id="context-tokens" type="number" value={localExecution.max_context_tokens} onChange={(event) => setLocalExecution({ ...localExecution, max_context_tokens: Number(event.target.value) })} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => (
              <Button key={preset} variant="outline" size="sm" onClick={() => applyPreset(preset)}>
                {preset[0].toUpperCase() + preset.slice(1)}
              </Button>
            ))}
          </div>
        </section>
        ) : null}

        {developerMode && memorySettings ? (
          <section className="rounded-lg border bg-card p-5 space-y-4" data-testid="memory-provider-settings">
            <div>
              <h2 className="text-xl font-semibold">Experimental memory providers</h2>
              <p className="text-sm text-muted-foreground">Native NovelForge memory remains the default and authoritative path. TencentDB Agent Memory is optional retrieval telemetry only; it can never change canon, decisions, approved prose, or Story Bible state.</p>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <Label htmlFor="memory-mode">Memory mode</Label>
                <select id="memory-mode" className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm" value={memorySettings.mode || 'native'} onChange={(event) => setMemorySettings({ ...memorySettings, mode: event.target.value })}>
                  <option value="native">Native NovelForge (recommended)</option>
                  <option value="tencent">TencentDB experimental with native fallback</option>
                  <option value="hybrid">Hybrid comparison (Native + Tencent)</option>
                  <option value="benchmark">Benchmark both (native remains primary)</option>
                </select>
              </div>
              <div>
                <Label htmlFor="memory-endpoint">Tencent gateway endpoint</Label>
                <Input id="memory-endpoint" value={memorySettings.endpoint || ''} onChange={(event) => setMemorySettings({ ...memorySettings, endpoint: event.target.value })} placeholder="http://127.0.0.1:8420" />
              </div>
              <div>
                <Label htmlFor="memory-api-key">Gateway API key (optional)</Label>
                <Input id="memory-api-key" type="password" value={memoryApiKey} onChange={(event) => setMemoryApiKey(event.target.value)} placeholder={memorySettings.configured ? 'Configured; leave blank to keep' : 'Local gateway usually needs none'} autoComplete="off" />
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" onClick={testMemory}>Test memory gateway</Button>
              <Button type="button" variant="outline" onClick={runMemorySmoke} disabled={memorySmokeRunning}>{memorySmokeRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <TestTube2 className="mr-2 h-4 w-4" />}Run retrieval smoke gate</Button>
              {memoryStatus ? <span className="text-sm text-muted-foreground">Native: available · Tencent: {memoryStatus.tencent?.available ? 'available' : (memoryStatus.tencent?.error || 'unavailable')}</span> : <span className="text-sm text-muted-foreground">No Tencent gateway call has been made.</span>}
            </div>
            {memorySmoke ? <div className={`rounded-md border p-3 text-sm ${memorySmoke.passed ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-amber-500/40 bg-amber-500/5'}`}><strong>{memorySmoke.passed ? 'Retrieval smoke gate passed' : 'Retrieval smoke gate did not pass'}</strong><p className="mt-1 text-muted-foreground">{memorySmoke.error || `${memorySmoke.matched ?? 0}/${memorySmoke.expected ?? 10} labeled memories matched; average recall ${memorySmoke.average_recall_latency_ms ?? '—'} ms.`}</p></div> : null}
          </section>
        ) : null}

        <section id="ai-provider" className="rounded-lg border bg-card p-5 space-y-4">
          <div><h2 className="text-xl font-semibold">AI providers</h2><p className="text-sm text-muted-foreground">Add a credential, discover the available models, verify them, then choose one as the default. Stored credentials are never shown again.</p></div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {providerRows.map((rawProvider) => {
              const provider = rawProvider === 'local' ? 'ollama' : rawProvider === 'claude' ? 'anthropic' : rawProvider
              const result = testResults[`${provider}:${localSettings.providers?.[provider]?.model || ''}`]
              const providerModels = modelsFor(provider)
              const validations = validationsFor(provider)
              const workingValidations = validations.filter((item) => item.working)
              const failedValidations = validations.filter((item) => !item.working)
              const validationRun = validationRuns[provider]
              const providerValidation = providerValidationResults[provider]
              const selectedModel = localSettings.providers?.[provider]?.model || ''
              const selectedHealth = validationFor(provider, selectedModel)
              const providerStatus = healthFor(provider)
              return (
                <div key={provider} className="flex h-full min-w-0 flex-col rounded-md border p-4 space-y-3" data-testid={`provider-card-${provider}`}>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="truncate font-medium capitalize">{provider}</h3>
                    <span className={`text-xs uppercase ${providerStatus?.status === 'online' ? 'text-green-600' : providerStatus?.status === 'offline' ? 'text-red-600' : 'text-amber-600'}`}>
                      {providerStatus?.status || 'untested'}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 rounded-md bg-muted/40 p-3 text-xs">
                    <span>Provider Status</span><strong className="text-right uppercase">{providerStatus?.status || 'untested'}</strong>
                    <span>Discovered Models</span><strong className="text-right" data-testid={`discovered-count-${provider}`}>{providerModels.length}</strong>
                    <span>Working Models</span><strong className="text-right" data-testid={`working-count-${provider}`}>{workingValidations.length}</strong>
                    <span>Selected Model</span><strong className="truncate text-right">{selectedModel || 'None'}</strong>
                    <span>Latency</span><strong className="text-right">{selectedHealth?.latency_ms ?? selectedHealth?.latency ?? providerStatus?.last_latency_ms ?? 'n/a'}{(selectedHealth?.latency_ms ?? selectedHealth?.latency ?? providerStatus?.last_latency_ms) ? 'ms' : ''}</strong>
                  </div>
                  <Input
                    type="password"
                    value={localSettings.providers?.[provider]?.api_key || ''}
                    onChange={(event) => handleProviderChange(provider, 'api_key', event.target.value)}
                    placeholder={localSettings.providers?.[provider]?.configured ? 'Configured - enter a new key to replace' : 'API key'}
                  />
                  {localSettings.providers?.[provider]?.configured ? (
                    <p className="text-xs text-muted-foreground">Credential configured. The stored value is never returned.</p>
                  ) : null}
                  <select
                    className="h-10 w-full max-w-full truncate rounded-md border bg-background px-3 text-sm"
                    value={selectedModel}
                    onChange={(event) => handleProviderChange(provider, 'model', event.target.value)}
                    data-testid={`model-select-${provider}`}
                  >
                    <option value="">Select model</option>
                    {localSettings.providers?.[provider]?.model && !providerModels.some((model) => model.model_id === localSettings.providers?.[provider]?.model) && (
                      <option value={localSettings.providers[provider].model} disabled>
                        Not discovered: {localSettings.providers[provider].model}
                      </option>
                    )}
                    {providerModels.map((model) => (
                      <option key={model.model_id} value={model.model_id}>
                        {model.free_tier ? 'Free - ' : ''}{model.display_name} ({model.model_id})
                      </option>
                    ))}
                  </select>
                  {provider === 'ollama' && (
                    <Input value={localSettings.providers?.ollama?.url || ''} onChange={(event) => handleProviderChange('ollama', 'url', event.target.value)} placeholder="Ollama URL" />
                  )}
                  <div className="flex flex-wrap items-center gap-2">
                    <Button size="sm" variant="outline" className="min-w-0" onClick={() => runProviderValidation(provider)} disabled={validatingProvider === provider}>
                      {validatingProvider === provider ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Validate Key
                    </Button>
                    <Button size="sm" variant="outline" className="min-w-0 gap-2" onClick={() => runDiscovery(provider)} disabled={discoveringProvider === provider}>
                      {discoveringProvider === provider ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                      Discover Models
                    </Button>
                    <Button size="sm" variant="outline" className="min-w-0 gap-2" onClick={() => runValidation(provider)} disabled={validatingProvider === provider || providerModels.length === 0}>
                      {validatingProvider === provider ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                      Verify Working Models
                    </Button>
                    <Button size="sm" className="min-w-0 gap-2" onClick={() => runModelTest(provider, selectedModel)} disabled={!selectedModel || testingKey === `${provider}:${selectedModel}`}>
                      {testingKey === `${provider}:${selectedModel}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube2 className="h-4 w-4" />}
                      Test Selected Model
                    </Button>
                  </div>
                  {providerValidation && (
                    <p className={`text-sm ${providerValidation.valid ? 'text-green-600' : 'text-red-600'}`}>
                      {providerValidation.valid ? 'API key valid' : providerValidation.error || 'API key invalid'}
                    </p>
                  )}
                  {result && (
                    <div className={`min-w-0 break-words text-sm ${result.success ? 'text-green-600' : 'text-red-600'}`}>
                      <span className="inline-flex items-center gap-1">
                        {result.success ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                        {result.success ? 'Working' : result.error || 'Failed'}
                      </span>
                      <div>Latency: {(result.latency_ms / 1000).toFixed(1)}s</div>
                      <div>Tokens: {result.tokens_used}</div>
                      {result.error_type && <div>Error type: {result.error_type}</div>}
                    </div>
                  )}
                  {(validationRun || providerModels.length > 0) && (
                    <div className="max-h-[200px] min-w-0 overflow-auto rounded-md bg-muted/40 p-3 text-xs space-y-2" data-testid={`validation-results-${provider}`}>
                      <div className="font-medium">
                        Model Health: {validationRun?.working ?? workingValidations.length} working / {providerModels.length} discovered
                      </div>
                      <div className="space-y-1">
                        {providerModels.map((model) => {
                          const health = validationFor(provider, model.model_id)
                          return (
                            <div className={`flex items-center justify-between gap-2 ${health?.working ? 'text-green-700' : health ? 'text-red-700' : 'text-muted-foreground'}`} key={`${provider}:${model.model_id}`}>
                              <span className="truncate">{health?.working ? '✓' : health ? '✗' : '?'} {model.model_id}</span>
                              <span>{health ? `${health.latency_ms ?? health.latency ?? 0}ms` : 'Untested'}</span>
                            </div>
                          )
                        })}
                      </div>
                      {failedValidations.length > 0 && (
                        <details className="text-amber-700">
                          <summary>Failed Models ({failedValidations.length})</summary>
                          <div className="mt-1 space-y-1">
                            {failedValidations.slice(0, 6).map((item) => (
                              <div className="truncate" key={`${item.provider}:${item.model}`}>Failed {item.model}: {item.error_type || item.error_message || 'failed'}</div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>

        {developerMode ? <section className="rounded-lg border bg-card p-5 space-y-4" data-testid="agent-assignment-table">
          <h2 className="text-xl font-semibold">Per-Agent Model Assignment</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-2">Agent</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Temp</th>
                  <th>Max Tokens</th>
                  <th>Enabled</th>
                  <th>Health</th>
                </tr>
              </thead>
              <tbody>
                {localAssignments.map((assignment, index) => {
                  const key = `${assignment.provider}:${assignment.model}`
                  const result = testResults[key]
                  return (
                    <tr key={assignment.agent_name} className="border-b">
                      <td className="py-2 font-medium">{assignment.agent_name}</td>
                      <td>
                        <select className="h-9 rounded-md border bg-background px-2" value={assignment.provider} onChange={(event) => {
                          const nextProvider = event.target.value
                          updateAssignment(index, { provider: nextProvider, model: verifiedModelsFor(nextProvider)[0]?.model_id || '' })
                        }}>
                          {PROVIDERS.map((provider) => <option key={provider} value={provider}>{provider}</option>)}
                        </select>
                      </td>
                      <td>
                        <select className="h-9 w-full rounded-md border bg-background px-2" value={assignment.model} onChange={(event) => updateAssignment(index, { model: event.target.value })}>
                          {verifiedModelsFor(assignment.provider).length === 0 && <option value="">No verified model available</option>}
                          {verifiedModelsFor(assignment.provider).map((model) => (
                            <option key={model.model_id} value={model.model_id}>{model.display_name}</option>
                          ))}
                        </select>
                      </td>
                      <td><Input type="number" step="0.1" value={assignment.temperature} onChange={(event) => updateAssignment(index, { temperature: Number(event.target.value) })} /></td>
                      <td><Input type="number" value={assignment.max_tokens} onChange={(event) => updateAssignment(index, { max_tokens: Number(event.target.value) })} /></td>
                      <td><input type="checkbox" checked={assignment.enabled} onChange={(event) => updateAssignment(index, { enabled: event.target.checked })} /></td>
                      <td>
                        <Button size="sm" variant="outline" onClick={() => runModelTest(assignment.provider, assignment.model)} disabled={testingKey === key}>
                          {result?.success ? 'Connected' : 'Test'}
                        </Button>
                        {result?.error_type && <p className="text-xs text-red-600 mt-1">{result.error_type}</p>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section> : null}
      </div>
    </div>
  )
}
