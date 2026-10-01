"use client"

import { useEffect, useMemo, useState } from 'react'
import {
  Bot,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  Focus,
  GitBranch,
  Loader2,
  MessageSquare,
  Network,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  X,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { dataApi } from '@/lib/api'
import { authorText, EvidenceList } from '@/components/AuthorValue'
import type {
  AssistantMode,
  CanonProposal,
  CharacterBible,
  CharacterConversationTurn,
  KnowledgeGraph,
  KnowledgeGraphNode,
  NarrativeAssistantMessage,
  NavigationAction,
  WorkspaceRecommendation,
} from '@/types'


type StudioTab = 'assistant' | 'characters' | 'graph' | 'proposals' | 'intelligence'

interface InteractiveNarrativeStudioProps {
  projectId: string
  characters: CharacterBible[]
  activeSurface?: string
  initialTab?: StudioTab
  compact?: boolean
  onNavigate: (section: string, action?: NavigationAction) => void
  onRefresh?: () => Promise<void> | void
}

const tabs: Array<{ id: StudioTab; label: string; Icon: typeof Bot }> = [
  { id: 'assistant', label: 'Assistant', Icon: Bot },
  { id: 'characters', label: 'Characters', Icon: UserRound },
  { id: 'graph', label: 'Graph', Icon: Network },
  { id: 'proposals', label: 'Canon Queue', Icon: ShieldCheck },
  { id: 'intelligence', label: 'Context', Icon: Sparkles },
]

const graphColors: Record<string, string> = {
  character: '#8b5cf6',
  relationship: '#ec4899',
  location: '#10b981',
  organization: '#f59e0b',
  power: '#ef4444',
  artifact: '#14b8a6',
  mystery: '#6366f1',
  plot_thread: '#3b82f6',
  timeline: '#64748b',
  canon: '#22c55e',
}

function valueText(value: unknown) {
  return authorText(value)
}

function EvidenceBadge({ message }: { message: NarrativeAssistantMessage }) {
  const count = message.evidence.finding_ids.length + message.evidence.node_ids.length
  if (message.reasoning_layer === 'application') {
    return <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] text-sky-800">Application guide</span>
  }
  return (
    <span className="rounded-full border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
      {count} supporting story reference{count === 1 ? '' : 's'}
    </span>
  )
}

function Severity({ value }: { value: string }) {
  const normalized = value.toLowerCase()
  const classes = normalized === 'critical' || normalized === 'high'
    ? 'border-red-300 bg-red-50 text-red-700'
    : normalized === 'medium' || normalized === 'warning'
      ? 'border-amber-300 bg-amber-50 text-amber-700'
      : 'border-slate-300 bg-slate-50 text-slate-700'
  return <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${classes}`}>{value}</span>
}

export default function InteractiveNarrativeStudio({
  projectId,
  characters,
  activeSurface = 'dashboard',
  initialTab = 'assistant',
  compact = false,
  onNavigate,
  onRefresh,
}: InteractiveNarrativeStudioProps) {
  const [tab, setTab] = useState<StudioTab>(initialTab)
  const [modes, setModes] = useState<AssistantMode[]>([])
  const [mode, setMode] = useState('story_coach')
  const [assistantQuery, setAssistantQuery] = useState('')
  const [assistantHistory, setAssistantHistory] = useState<NarrativeAssistantMessage[]>([])
  const [selectedCharacter, setSelectedCharacter] = useState('')
  const [characterMessage, setCharacterMessage] = useState('')
  const [chapterNumber, setChapterNumber] = useState(1)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const [characterHistory, setCharacterHistory] = useState<CharacterConversationTurn[]>([])
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
  const [graphKind, setGraphKind] = useState('')
  const [graphSearch, setGraphSearch] = useState('')
  const [graphLimit, setGraphLimit] = useState(compact ? 24 : 48)
  const [centerNodeId, setCenterNodeId] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<KnowledgeGraphNode | null>(null)
  const [nodeDetail, setNodeDetail] = useState<Record<string, unknown> | null>(null)
  const [proposals, setProposals] = useState<CanonProposal[]>([])
  const [proposalSearch, setProposalSearch] = useState('')
  const [proposalStatus, setProposalStatus] = useState('pending')
  const [proposalType, setProposalType] = useState('all')
  const [proposalLimit, setProposalLimit] = useState(30)
  const [graphLoading, setGraphLoading] = useState(true)
  const [proposalLoading, setProposalLoading] = useState(true)
  const [confirmedProposals, setConfirmedProposals] = useState<Set<string>>(new Set())
  const [recommendations, setRecommendations] = useState<WorkspaceRecommendation[]>([])
  const [explanation, setExplanation] = useState<Record<string, unknown> | null>(null)
  const [proposalDraft, setProposalDraft] = useState({ subject: '', field: '', value: '', canon_type: 'world' })
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  const graphKinds = useMemo(
    () => Object.keys(graph?.counts.by_kind || {}).sort(),
    [graph],
  )

  async function loadGraph(kind = graphKind, search = graphSearch) {
    setGraphLoading(true)
    try {
      const result = await dataApi.getKnowledgeGraph(projectId, kind || undefined, search)
      setGraph(result as KnowledgeGraph)
      setSelectedNode(null)
      setNodeDetail(null)
    } finally {
      setGraphLoading(false)
    }
  }

  async function loadProposals() {
    setProposalLoading(true)
    try {
      setProposals(await dataApi.getCanonProposals(projectId) as CanonProposal[])
    } finally {
      setProposalLoading(false)
    }
  }

  async function loadWorkspaceIntelligence() {
    const result = await dataApi.getWorkspaceIntelligence(projectId, { surface: activeSurface })
    setRecommendations(result.recommendations || [])
  }

  useEffect(() => {
    let active = true
    void dataApi.getAssistantModes(projectId).then((value) => { if (active) setModes(value) }).catch(() => undefined)
    void dataApi.getAssistantHistory(projectId).then((value) => { if (active) setAssistantHistory(value) }).catch(() => undefined)
    void dataApi.getKnowledgeGraph(projectId).then((value) => { if (active) setGraph(value) }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Knowledge Graph could not load') }).finally(() => { if (active) setGraphLoading(false) })
    void dataApi.getCanonProposals(projectId).then((value) => { if (active) setProposals(value) }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Canon proposals could not load') }).finally(() => { if (active) setProposalLoading(false) })
    void dataApi.getWorkspaceIntelligence(projectId, { surface: activeSurface }).then((value) => { if (active) setRecommendations(value.recommendations || []) }).catch(() => undefined)
    return () => { active = false }
  }, [activeSurface, projectId])

  useEffect(() => {
    if (!selectedCharacter && characters[0]?.name) setSelectedCharacter(characters[0].name)
  }, [characters, selectedCharacter])

  useEffect(() => {
    if (!selectedCharacter) return
    dataApi.getCharacterConversationHistory(projectId, selectedCharacter)
      .then((history) => setCharacterHistory(history))
      .catch(() => setCharacterHistory([]))
  }, [projectId, selectedCharacter])

  async function askAssistant() {
    if (!assistantQuery.trim()) return
    setBusy('assistant')
    setError('')
    try {
      const requestId = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `assistant-${Date.now()}-${Math.random()}`
      const response = await dataApi.askProjectAssistant(projectId, assistantQuery, mode, activeSurface, undefined, requestId) as NarrativeAssistantMessage
      setAssistantHistory((current) => current.some((item) => item.message_id === response.message_id)
        ? current
        : [...current, response])
      setAssistantQuery('')
      if (response.canon_proposal_ids.length) await loadProposals()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Assistant request failed')
    } finally {
      setBusy('')
    }
  }

  async function talkToCharacter() {
    if (!selectedCharacter || !characterMessage.trim()) return
    setBusy('character')
    setError('')
    try {
      const response = await dataApi.converseWithCharacter(projectId, {
        character_name: selectedCharacter,
        message: characterMessage,
        chapter_number: chapterNumber,
        conversation_id: conversationId,
      }) as CharacterConversationTurn
      setConversationId(response.conversation_id)
      setCharacterHistory((current) => [...current, response])
      setCharacterMessage('')
      if (response.canon_proposal_ids?.length) await loadProposals()
      await onRefresh?.()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Character conversation failed')
    } finally {
      setBusy('')
    }
  }

  async function inspectNode(node: KnowledgeGraphNode) {
    setSelectedNode(node)
    setBusy(`node:${node.node_id}`)
    try {
      setNodeDetail(await dataApi.getKnowledgeGraphNode(projectId, node.node_id))
    } finally {
      setBusy('')
    }
  }

  async function decideProposal(proposal: CanonProposal, decision: 'approved' | 'rejected') {
    setBusy(`proposal:${proposal.proposal_id}`)
    setError('')
    try {
      await dataApi.reviewCanonProposal(projectId, proposal.proposal_id, {
        decision,
        confirm_high_impact: confirmedProposals.has(proposal.proposal_id),
      })
      // Keep the completed decision visible instead of making it appear to
      // vanish from the default Pending view before the author sees success.
      setProposalStatus('all')
      await Promise.all([loadProposals(), loadGraph()])
      await onRefresh?.()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Proposal decision failed')
    } finally {
      setBusy('')
    }
  }

  async function createProposal() {
    if (!proposalDraft.subject.trim() || !proposalDraft.field.trim()) return
    setBusy('create-proposal')
    try {
      await dataApi.createCanonProposal(projectId, {
        ...proposalDraft,
        confidence: 1,
        evidence: ['Author-created proposal in Interactive Narrative Studio'],
      })
      setProposalDraft({ subject: '', field: '', value: '', canon_type: 'world' })
      await loadProposals()
    } finally {
      setBusy('')
    }
  }

  async function explain(findingId: string) {
    setBusy(`explain:${findingId}`)
    try {
      setExplanation(await dataApi.explainNarrativeFinding(projectId, findingId))
    } finally {
      setBusy('')
    }
  }

  const graphNodes = graph?.nodes || []
  const proposalTypes = [...new Set(proposals.map((proposal) => proposal.canon_type))].sort()
  const filteredProposals = proposals.filter((proposal) => {
    const haystack = `${proposal.subject} ${proposal.field} ${valueText(proposal.value)}`.toLowerCase()
    return (!proposalSearch || haystack.includes(proposalSearch.toLowerCase()))
      && (proposalStatus === 'all' || proposal.status === proposalStatus)
      && (proposalType === 'all' || proposal.canon_type === proposalType)
  })
  const nearDuplicateProposalIds = useMemo(() => {
    const groups = new Map<string, CanonProposal[]>()
    proposals.forEach((proposal) => {
      const subjectLead = proposal.subject.toLowerCase().match(/[a-z0-9]+/)?.[0] || ''
      const key = `${proposal.canon_type}:${proposal.field.trim().toLowerCase()}:${subjectLead}`
      groups.set(key, [...(groups.get(key) || []), proposal])
    })
    const duplicates = new Set<string>()
    const tokens = (proposal: CanonProposal) => new Set(
      `${proposal.subject} ${valueText(proposal.value)}`.toLowerCase().match(/[a-z0-9]+/g)?.filter((token) => token.length > 2) || [],
    )
    groups.forEach((items) => {
      for (let left = 0; left < items.length; left += 1) {
        const leftTokens = tokens(items[left])
        for (let right = left + 1; right < items.length; right += 1) {
          const rightTokens = tokens(items[right])
          const intersection = [...leftTokens].filter((token) => rightTokens.has(token)).length
          const union = new Set([...leftTokens, ...rightTokens]).size
          if (union && intersection / union >= 0.72) {
            duplicates.add(items[left].proposal_id)
            duplicates.add(items[right].proposal_id)
          }
        }
      }
    })
    return duplicates
  }, [proposals])
  const neighborhood = centerNodeId
    ? new Set([centerNodeId, ...(graph?.edges || []).filter((edge) => edge.source === centerNodeId || edge.target === centerNodeId).flatMap((edge) => [edge.source, edge.target])])
    : null
  const visibleNodes = graphNodes.filter((node) => !neighborhood || neighborhood.has(node.node_id)).slice(0, graphLimit)
  const positions = new Map(visibleNodes.map((node, index) => [
    node.node_id,
    { x: 50 + (index % 8) * 95, y: 45 + Math.floor(index / 8) * 76 },
  ]))

  return (
    <section
      className={`flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border bg-card ${compact ? 'h-full border-0 rounded-none' : ''}`}
      data-testid="interactive-narrative-studio"
    >
      <header className="border-b p-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="font-semibold text-foreground">Interactive Narrative Studio</h2>
            <p className="text-xs text-muted-foreground">Application guidance and story answers, each grounded in the right source</p>
          </div>
        </div>
        <nav className="mt-3 flex gap-1 overflow-x-auto" aria-label="Interactive Narrative Studio modes">
          {tabs.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`flex shrink-0 items-center gap-1 rounded-md px-2 py-1.5 text-xs ${tab === id ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}
              data-testid={`interactive-tab-${id}`}
            >
              <Icon className="h-3.5 w-3.5" />
              {compact && id !== tab ? <span className="sr-only">{label}</span> : label}
            </button>
          ))}
        </nav>
      </header>

      {error ? (
        <div role="alert" className="m-3 rounded-md border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {tab === 'assistant' ? (
          <div className="space-y-3" data-testid="project-assistant-panel">
            <label className="block text-xs font-medium">
              Conversation mode
              <select
                value={mode}
                onChange={(event) => setMode(event.target.value)}
                className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
                aria-label="Assistant mode"
              >
                {modes.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <p className="text-xs text-muted-foreground">{modes.find((item) => item.id === mode)?.description}</p>
            <div className="space-y-3" aria-live="polite">
              {assistantHistory.length === 0 ? (
                <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  Ask about your novel or the application: “Why is Story Health low?” and “What does this page do?” use separate knowledge layers.
                </div>
              ) : assistantHistory.map((message) => (
                <article key={message.message_id} className="rounded-lg border p-3 text-sm" data-testid="assistant-message">
                  <p className="font-medium text-foreground">You: {message.query}</p>
                  <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{message.answer}</p>
                  <div className="mt-2 flex flex-wrap gap-2"><EvidenceBadge message={message} /></div>
                  {message.navigation_actions.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {message.navigation_actions.map((action, index) => (
                        <Button
                          key={`${action.target}-${index}`}
                          size="sm"
                          variant="outline"
                          onClick={() => onNavigate(action.section, action)}
                          data-testid="assistant-navigation-action"
                        >
                          {action.label || `Open ${action.target}`} <ChevronRight className="ml-1 h-3 w-3" />
                        </Button>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
            <Textarea
              value={assistantQuery}
              onChange={(event) => setAssistantQuery(event.target.value)}
              placeholder="Which mysteries remain unresolved?"
              aria-label="Ask the project assistant"
              rows={3}
            />
            <Button onClick={() => void askAssistant()} disabled={busy === 'assistant' || !assistantQuery.trim()} data-testid="ask-project-assistant">
              {busy === 'assistant' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
              Ask project assistant
            </Button>
          </div>
        ) : null}

        {tab === 'characters' ? (
          <div className="space-y-3" data-testid="character-conversation-panel">
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="text-xs font-medium">
                Character
                <select
                  value={selectedCharacter}
                  onChange={(event) => { setSelectedCharacter(event.target.value); setConversationId(undefined) }}
                  className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
                  aria-label="Conversation character"
                >
                  {characters.map((character) => <option key={character.name} value={character.name}>{character.name}</option>)}
                </select>
              </label>
              <label className="text-xs font-medium">
                Timeline chapter
                <Input
                  type="number"
                  min={0}
                  value={chapterNumber}
                  onChange={(event) => setChapterNumber(Number(event.target.value))}
                  aria-label="Conversation timeline chapter"
                />
              </label>
            </div>
            <div className="space-y-3" aria-live="polite">
              {characterHistory.map((turn) => (
                <article key={turn.turn_id} className="rounded-lg border p-3 text-sm" data-testid="character-conversation-turn">
                  <p className="font-medium">You: {turn.author_message}</p>
                  <p className="mt-2 text-muted-foreground">{turn.character_response}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                    <span className="rounded-full border px-2 py-0.5">Chapter {turn.awareness_boundary.effective_chapter} awareness</span>
                    {turn.awareness_boundary.death_boundary_applied ? (
                      <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-amber-700">Death boundary enforced</span>
                    ) : null}
                    <span className="rounded-full border px-2 py-0.5">{turn.evidence.canon_ids.length} canon facts</span>
                  </div>
                </article>
              ))}
            </div>
            {characters.length === 0 ? <p className="text-sm text-muted-foreground">No analyzed characters are available.</p> : null}
            <Textarea
              value={characterMessage}
              onChange={(event) => setCharacterMessage(event.target.value)}
              placeholder="What are you afraid to tell Soren?"
              aria-label="Message character"
              rows={3}
            />
            <Button onClick={() => void talkToCharacter()} disabled={busy === 'character' || !selectedCharacter || !characterMessage.trim()} data-testid="send-character-message">
              {busy === 'character' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <MessageSquare className="mr-2 h-4 w-4" />}
              Speak with {selectedCharacter || 'character'}
            </Button>
          </div>
        ) : null}

        {tab === 'graph' ? (
          <div className="space-y-3" data-testid="knowledge-graph-panel">
            <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
              <select value={graphKind} onChange={(event) => setGraphKind(event.target.value)} className="rounded-md border bg-background p-2 text-sm" aria-label="Knowledge graph type">
                <option value="">All node types</option>
                {graphKinds.map((kind) => <option key={kind} value={kind}>{kind.replace('_', ' ')}</option>)}
              </select>
              <Input value={graphSearch} onChange={(event) => setGraphSearch(event.target.value)} placeholder="Search graph" aria-label="Search knowledge graph" />
              <Button variant="outline" onClick={() => void loadGraph()}>Filter</Button>
            </div>
            {graphLoading ? <p className="rounded border p-3 text-sm" role="status"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" />Loading story relationships…</p> : null}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <p>{graph?.counts.nodes || 0} story elements · {graph?.counts.edges || 0} relationships</p>
              <div className="flex gap-2">{centerNodeId ? <Button size="sm" variant="ghost" onClick={() => setCenterNodeId(null)}>Show full graph</Button> : null}{graphLimit < graphNodes.length ? <Button size="sm" variant="ghost" onClick={() => setGraphLimit((value) => value + 40)}>Load more</Button> : null}</div>
            </div>
            <div className="overflow-x-auto rounded-lg border bg-slate-950/95" data-testid="knowledge-graph-canvas">
              <svg width={810} height={Math.max(240, 100 + Math.ceil(visibleNodes.length / 8) * 76)} role="img" aria-label="Interactive story knowledge graph">
                {(graph?.edges || []).slice(0, 240).map((edge) => {
                  const source = positions.get(edge.source)
                  const target = positions.get(edge.target)
                  if (!source || !target) return null
                  return <line key={edge.edge_id} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#475569" strokeWidth="1" opacity="0.6" />
                })}
                {visibleNodes.map((node) => {
                  const position = positions.get(node.node_id)!
                  const active = selectedNode?.node_id === node.node_id
                  return (
                    <g key={node.node_id} role="button" tabIndex={0} onClick={() => void inspectNode(node)} onKeyDown={(event) => { if (event.key === 'Enter') void inspectNode(node) }} aria-label={`${node.kind}: ${node.label}`} className="cursor-pointer">
                      <circle cx={position.x} cy={position.y} r={active ? 18 : 14} fill={graphColors[node.kind] || '#94a3b8'} stroke={active ? '#ffffff' : 'transparent'} strokeWidth="3" />
                      {node.warning_count ? <circle cx={position.x + 12} cy={position.y - 12} r="6" fill="#ef4444" /> : null}
                      <text x={position.x} y={position.y + 28} textAnchor="middle" fill="#e2e8f0" fontSize="10">{node.label.slice(0, 15)}</text>
                    </g>
                  )
                })}
              </svg>
            </div>
            {selectedNode ? (
              <article className="rounded-lg border p-3" data-testid="knowledge-graph-inspector">
                <div className="flex items-center justify-between gap-2">
                  <div><p className="text-xs uppercase text-muted-foreground">{selectedNode.kind}</p><h3 className="font-semibold">{selectedNode.label}</h3></div>
                  {busy === `node:${selectedNode.node_id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">Chapters: {selectedNode.chapter_numbers.join(', ') || 'project-wide'} · {selectedNode.warning_count} warnings</p>
                <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                  <div className="rounded bg-muted/60 p-2"><dt className="text-xs font-semibold text-muted-foreground">Summary</dt><dd className="mt-1">{valueText((nodeDetail?.summary as unknown) || selectedNode.payload)}</dd></div>
                  <div className="rounded bg-muted/60 p-2"><dt className="text-xs font-semibold text-muted-foreground">Importance</dt><dd className="mt-1">{Math.max(selectedNode.warning_count, selectedNode.story_health_warnings.length) ? `${Math.max(selectedNode.warning_count, selectedNode.story_health_warnings.length)} active concern${Math.max(selectedNode.warning_count, selectedNode.story_health_warnings.length) === 1 ? '' : 's'}` : 'No current Story Health concerns are linked to this element'}</dd></div>
                  <div className="rounded bg-muted/60 p-2"><dt className="text-xs font-semibold text-muted-foreground">Related chapters</dt><dd className="mt-1">{selectedNode.chapter_numbers.length ? selectedNode.chapter_numbers.map((chapter) => `Chapter ${chapter}`).join(', ') : 'Project-wide'}</dd></div>
                  <div className="rounded bg-muted/60 p-2"><dt className="text-xs font-semibold text-muted-foreground">Connected entities</dt><dd className="mt-1">{Array.isArray(nodeDetail?.connected_entities) ? nodeDetail.connected_entities.length : 0}</dd></div>
                </dl>
                <div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => setCenterNodeId(selectedNode.node_id)}><Focus className="mr-1 h-3 w-3" />Center here</Button><Button size="sm" variant="outline" onClick={() => onNavigate(selectedNode.kind === 'canon' ? 'canon' : selectedNode.kind === 'timeline' ? 'timeline' : selectedNode.kind === 'character' ? 'characters' : 'knowledge')}>Open related workspace</Button></div>
                {selectedNode.story_health_warnings.map((warning) => (
                  <button key={warning.finding_id} type="button" onClick={() => void explain(warning.finding_id)} className="mt-2 block w-full rounded border p-2 text-left text-xs hover:bg-muted">
                    <Severity value={warning.severity} /> <span className="ml-1">{warning.explanation}</span>
                  </button>
                ))}
              </article>
            ) : null}
          </div>
        ) : null}

        {tab === 'proposals' ? (
          <div className="space-y-3" data-testid="canon-proposal-panel">
            <div className="rounded-lg border p-3">
              <h3 className="text-sm font-semibold">Create governed proposal</h3>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <Input value={proposalDraft.subject} onChange={(event) => setProposalDraft((value) => ({ ...value, subject: event.target.value }))} placeholder="Subject" aria-label="Canon proposal subject" />
                <Input value={proposalDraft.field} onChange={(event) => setProposalDraft((value) => ({ ...value, field: event.target.value }))} placeholder="Field" aria-label="Canon proposal field" />
                <Input value={proposalDraft.value} onChange={(event) => setProposalDraft((value) => ({ ...value, value: event.target.value }))} placeholder="Proposed value" aria-label="Canon proposal value" />
                <select value={proposalDraft.canon_type} onChange={(event) => setProposalDraft((value) => ({ ...value, canon_type: event.target.value }))} className="rounded-md border bg-background p-2 text-sm" aria-label="Canon proposal type">
                  {['character', 'world', 'timeline', 'relationship', 'artifact', 'power', 'knowledge', 'faction', 'mystery'].map((kind) => <option key={kind}>{kind}</option>)}
                </select>
              </div>
              <Button className="mt-2" size="sm" variant="outline" onClick={() => void createProposal()} disabled={busy === 'create-proposal'}>Add to proposal queue</Button>
            </div>
            <div className="grid gap-2 sm:grid-cols-3" data-testid="canon-proposal-filters">
              <Input value={proposalSearch} onChange={(event) => { setProposalSearch(event.target.value); setProposalLimit(30) }} placeholder="Search subject, fact, or value" aria-label="Search canon proposals" />
              <select value={proposalStatus} onChange={(event) => { setProposalStatus(event.target.value); setProposalLimit(30) }} className="rounded-md border bg-background p-2 text-sm" aria-label="Filter canon proposals by status"><option value="all">All statuses</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option></select>
              <select value={proposalType} onChange={(event) => { setProposalType(event.target.value); setProposalLimit(30) }} className="rounded-md border bg-background p-2 text-sm" aria-label="Filter canon proposals by type"><option value="all">All story types</option>{proposalTypes.map((kind) => <option key={kind} value={kind}>{kind.replaceAll('_', ' ')}</option>)}</select>
            </div>
            {proposalLoading ? <p className="rounded border p-3 text-sm" role="status"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" />Loading canon proposals independently…</p> : null}
            {!proposalLoading && filteredProposals.length === 0 ? <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No canon proposals match these filters.</p> : filteredProposals.slice(0, proposalLimit).map((proposal) => (
              <article key={proposal.proposal_id} className="rounded-lg border p-3 text-sm" data-testid="canon-proposal-card">
                <div className="flex items-start justify-between gap-2">
                  <div><p className="text-xs uppercase text-muted-foreground">{proposal.canon_type} · {proposal.source_type === 'manual' ? 'Author proposal' : 'AI suggestion'}</p><h3 className="font-semibold">{proposal.subject} — {proposal.field.replaceAll('_', ' ')}</h3></div>
                  <span className="rounded-full border px-2 py-0.5 text-xs">{proposal.status}</span>
                </div>
                <p className="mt-2 rounded bg-muted p-2">{valueText(proposal.value)}</p>
                {nearDuplicateProposalIds.has(proposal.proposal_id) ? <p className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">A near-identical proposal is also in this queue. Review each source before deciding; NovelForge will not approve them as a group.</p> : null}
                <div className="mt-2 grid gap-2 text-xs sm:grid-cols-3">
                  <span>Confidence {Math.round(proposal.confidence * 100)}%</span>
                  <span>{proposal.evidence.length} evidence items</span>
                  <span>{proposal.downstream_impact.total_affected || 0} downstream records</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">Chapters {proposal.affected_chapters.join(', ') || 'none'} · Scenes {proposal.affected_scenes.join(', ') || 'none'} · Risk {proposal.downstream_impact.risk}</p>
                {proposal.status === 'pending' ? (
                  <div className="mt-3 space-y-2">
                    {proposal.downstream_impact.requires_confirmation ? (
                      <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={confirmedProposals.has(proposal.proposal_id)} onChange={(event) => setConfirmedProposals((current) => { const next = new Set(current); event.target.checked ? next.add(proposal.proposal_id) : next.delete(proposal.proposal_id); return next })} />Confirm high-impact change</label>
                    ) : null}
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => void decideProposal(proposal, 'approved')} disabled={busy === `proposal:${proposal.proposal_id}`} data-testid="approve-canon-proposal"><Check className="mr-1 h-3 w-3" />Approve</Button>
                      <Button size="sm" variant="outline" onClick={() => void decideProposal(proposal, 'rejected')} disabled={busy === `proposal:${proposal.proposal_id}`}><X className="mr-1 h-3 w-3" />Reject</Button>
                    </div>
                  </div>
                ) : null}
              </article>
            ))}
            {filteredProposals.length > proposalLimit ? <Button variant="outline" onClick={() => setProposalLimit((value) => value + 30)}>Show 30 more proposals</Button> : null}
          </div>
        ) : null}

        {tab === 'intelligence' ? (
          <div className="min-w-0 space-y-3" data-testid="workspace-intelligence-panel">
            <div className="flex flex-wrap items-center justify-between gap-2"><div className="min-w-0"><h3 className="font-semibold">Recommendations for this page</h3><p className="text-xs text-muted-foreground">Grounded in current Story Intelligence</p></div><Button className="shrink-0" size="sm" variant="outline" onClick={() => void loadWorkspaceIntelligence()}>Refresh</Button></div>
            {recommendations.map((item) => (
              <article key={item.recommendation_id} className="min-w-0 rounded-lg border p-3 text-sm" data-testid="workspace-recommendation">
                <div className="flex min-w-0 items-start gap-2"><Severity value={item.severity} /><span className="min-w-0 flex-1 break-words font-medium">{item.message}</span></div>
                <p className="mt-2 text-xs text-muted-foreground">{item.why}</p>
                <p className="mt-1 text-xs">Chapters {item.affected_chapters.join(', ') || 'project-wide'} · Scenes {item.affected_scenes.join(', ') || 'none'}</p>
                <div className="mt-2 flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void explain(item.recommendation_id)}><CircleHelp className="mr-1 h-3 w-3" />Why was this generated?</Button><Button size="sm" onClick={() => onNavigate(item.destination || 'story-health')}>Review in {item.destination === 'characters' ? 'Character Intelligence' : item.destination === 'threads' ? 'Plot Threads' : item.destination === 'timeline' ? 'Story Timeline' : item.destination === 'canon' ? 'Canon' : 'Story Health'}</Button></div>
              </article>
            ))}
            {explanation ? (
              <article className="rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm" data-testid="explainability-panel">
                <div className="flex items-center gap-2"><BookOpen className="h-4 w-4 text-primary" /><h3 className="font-semibold">Evidence explanation</h3></div>
                <p className="mt-2">{valueText(explanation.why)}</p>
                <div className="mt-3"><p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Supporting evidence</p><EvidenceList values={Array.isArray(explanation.evidence) ? explanation.evidence : []} /></div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs"><span className="rounded bg-muted px-2 py-1">{Array.isArray(explanation.canon_facts) ? explanation.canon_facts.length : 0} canon references</span><span className="rounded bg-muted px-2 py-1">{Array.isArray(explanation.timeline_events) ? explanation.timeline_events.length : 0} timeline references</span></div>
              </article>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  )
}
