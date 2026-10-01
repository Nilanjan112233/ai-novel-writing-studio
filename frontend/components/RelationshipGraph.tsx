"use client"

import { useMemo } from 'react'
import ReactFlow, { Background, Controls, Edge, Node, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import { RelationshipEdge } from '@/types'

interface RelationshipGraphProps {
  relationships: RelationshipEdge[]
}

export default function RelationshipGraph({ relationships }: RelationshipGraphProps) {
  const names = useMemo(() => {
    const set = new Set<string>()
    relationships.forEach((edge) => {
      set.add(edge.character_a)
      set.add(edge.character_b)
    })
    return Array.from(set)
  }, [relationships])

  const nodes: Node[] = useMemo(
    () =>
      names.map((name, index) => ({
        id: name,
        position: {
          x: 220 + Math.cos((index / Math.max(names.length, 1)) * Math.PI * 2) * 180,
          y: 180 + Math.sin((index / Math.max(names.length, 1)) * Math.PI * 2) * 120,
        },
        data: { label: name },
        style: {
          background: '#f8fafc',
          color: '#0f172a',
          borderStyle: 'solid',
          borderWidth: '2px',
          borderColor: '#64748b',
          borderRadius: '8px',
          padding: '10px',
          width: 150,
        },
      })),
    [names]
  )

  const edges: Edge[] = useMemo(
    () =>
      relationships.map((relationship, index) => ({
        id: relationship.id || `edge-${index}`,
        source: relationship.character_a,
        target: relationship.character_b,
        label: `${relationship.type || relationship.relationship || 'relationship'} · trust ${relationship.trust ?? 'n/a'} · ${relationship.status}`,
        markerEnd: { type: MarkerType.ArrowClosed },
      })),
    [relationships]
  )

  if (relationships.length === 0) {
    return <p className="text-center py-8 text-muted-foreground">No relationships tracked yet.</p>
  }

  return (
    <div className="h-[420px] w-full" data-testid="relationship-graph">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}
