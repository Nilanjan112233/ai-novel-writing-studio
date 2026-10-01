"use client"

import { useEffect, useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { normalizeAgentName } from '@/store/projectStore'
import { AgentOutput, Cycle, Run } from '@/types'

type NodeStatus = 'pending' | 'active' | 'completed' | 'waiting' | 'failed'

function nodeStyle(status: NodeStatus) {
  switch (status) {
    case 'active':
      return { background: '#3b82f6', color: '#ffffff', borderStyle: 'solid', borderWidth: '2px', borderColor: '#2563eb' }
    case 'completed':
      return { background: '#22c55e', color: '#ffffff', borderStyle: 'solid', borderWidth: '2px', borderColor: '#16a34a' }
    case 'waiting':
      return { background: '#f59e0b', color: '#ffffff', borderStyle: 'solid', borderWidth: '2px', borderColor: '#d97706' }
    case 'failed':
      return { background: '#ef4444', color: '#ffffff', borderStyle: 'solid', borderWidth: '2px', borderColor: '#dc2626' }
    default:
      return { background: '#e2e8f0', color: '#1e293b', borderStyle: 'solid', borderWidth: '2px', borderColor: '#cbd5e1' }
  }
}

interface WorkflowFlowProps {
  currentRun?: Run | null
  cycles?: Cycle[]
  outputs?: AgentOutput[]
  selectedAgents?: string[]
}

function displayAgentName(agent: string) {
  const spaced = agent
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
  return spaced.replace(/\b\w/g, (match) => match.toUpperCase())
}

function stableId(agent: string, index: number) {
  return `${normalizeAgentName(agent) || 'agent'}-${index}`
}

function statusFor(agent: string, currentRun: Run | null | undefined, completedAgents: Set<string>): NodeStatus {
  const normalized = normalizeAgentName(agent)
  const current = normalizeAgentName(currentRun?.current_agent)
  if (currentRun?.status === 'failed' && current === normalized) return 'failed'
  if (currentRun?.status === 'waiting_for_user' && normalized.includes('question')) return 'waiting'
  if (currentRun?.status === 'running' && current && (current === normalized || normalized.includes(current) || current.includes(normalized))) {
    return 'active'
  }
  if (completedAgents.has(normalized) || currentRun?.status === 'completed') return 'completed'
  return 'pending'
}

export default function WorkflowFlow({ currentRun, cycles = [], outputs = [], selectedAgents = [] }: WorkflowFlowProps) {
  const latestCycle = useMemo(
    () => [...cycles].sort((a, b) => b.cycle_number - a.cycle_number)[0],
    [cycles]
  )
  const agentNames = useMemo(() => {
    const fromCycle = latestCycle?.agents_run || []
    const fromOutputs = outputs.map((output) => output.agent_name).filter(Boolean)
    const names = [...fromCycle, ...selectedAgents, ...fromOutputs]
    const unique = names.filter((name, index) => names.findIndex((item) => normalizeAgentName(item) === normalizeAgentName(name)) === index)
    return unique
  }, [latestCycle, outputs, selectedAgents])

  const completedAgents = useMemo(
    () => new Set([
      ...(latestCycle?.status === 'completed' ? latestCycle.agents_run : []),
      ...outputs.map((output) => output.agent_name),
    ].map((name) => normalizeAgentName(name))),
    [latestCycle, outputs]
  )

  const nodes: Node[] = useMemo(
    () =>
      agentNames.map((agent, index) => {
        const status = statusFor(agent, currentRun, completedAgents)
        const colors = nodeStyle(status)
        const column = index % 3
        const row = Math.floor(index / 3)
        return {
          id: stableId(agent, index),
          type: 'default',
          position: { x: column * 230, y: row * 130 },
            data: { label: displayAgentName(agent) },
            style: {
              ...colors,
              padding: '10px',
              borderRadius: '8px',
              width: 190,
              fontSize: 12,
            },
          }
        }),
    [agentNames, completedAgents, currentRun]
  )

  const current = normalizeAgentName(currentRun?.current_agent)
  const edges: Edge[] = useMemo(
    () => agentNames.slice(1).map((agent, index) => {
      const previous = agentNames[index]
      return {
        id: `e-${index}`,
        source: stableId(previous, index),
        target: stableId(agent, index + 1),
        animated: normalizeAgentName(agent) === current,
        markerEnd: { type: MarkerType.ArrowClosed },
      }
    }),
    [agentNames, current]
  )

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(nodes)
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState(edges)

  useEffect(() => {
    setFlowNodes(nodes)
  }, [nodes, setFlowNodes])

  useEffect(() => {
    setFlowEdges(edges)
  }, [edges, setFlowEdges])

  if (agentNames.length === 0) {
    return (
      <div className="flex h-48 w-full items-center justify-center text-sm text-muted-foreground" data-testid="workflow-graph">
        No agent execution has been recorded yet.
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '560px' }} data-testid="workflow-graph">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}
