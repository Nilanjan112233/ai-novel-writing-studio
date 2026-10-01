import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

import OrchestrationInspector from './OrchestrationInspector'


test('renders selected, skipped, reasons, graph, and stop status', () => {
  render(
    <OrchestrationInspector
      plan={{
        id: 'plan-1',
        project_id: 'project-1',
        cycle_number: 4,
        trigger_type: 'manual',
        changed_entities: [],
        affected_domains: [],
        selected_agents: [],
        skipped_agents: ['WorldAgent'],
        selection_reasons: {
          WorldAgent: 'No world-related changes detected',
        },
        execution_graph: { nodes: [], edges: [] },
        limits: {
          max_agent_calls_per_cycle: 10,
          max_orchestration_depth: 5,
          max_cycle_cost_usd: 2,
        },
        tasks: [{
          id: 'task-1',
          agent_name: 'WorldAgent',
          status: 'skipped',
          reason: 'No world-related changes detected',
        }],
        status: 'completed',
        stop_reason: 'NO_CHANGE_TERMINATION: no meaningful changes detected',
        actual_agent_calls: 0,
        actual_cost_usd: 0,
        created_at: new Date().toISOString(),
      }}
    />,
  )

  expect(screen.getByTestId('orchestration-inspector')).toBeInTheDocument()
  expect(screen.getByText('Skipped Agents')).toBeInTheDocument()
  expect(screen.getByText('No world-related changes detected')).toBeInTheDocument()
  expect(screen.getByTestId('orchestration-stop-reason')).toHaveTextContent('NO_CHANGE_TERMINATION')
  expect(screen.getByTestId('orchestration-graph')).toHaveTextContent('No dependency edges')
})
