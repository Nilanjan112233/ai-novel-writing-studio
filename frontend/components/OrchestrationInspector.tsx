"use client"

import { OrchestrationRun } from '@/types'

function displayName(value: string) {
  return value
    .replace(/Agent$/, '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .trim()
}

export default function OrchestrationInspector({
  plan,
}: {
  plan?: OrchestrationRun | null
}) {
  if (!plan) {
    return (
      <div className="rounded-md border p-4 text-sm text-muted-foreground" data-testid="orchestration-inspector">
        No orchestration plan has been recorded yet.
      </div>
    )
  }

  const tasks = plan.tasks || []
  const edges = plan.execution_graph?.edges || []
  return (
    <section className="rounded-md border p-4" data-testid="orchestration-inspector">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">Orchestration Inspector</h3>
          <p className="text-sm text-muted-foreground">
            {plan.trigger_type} trigger, cycle {plan.cycle_number}
          </p>
        </div>
        <span className="rounded bg-muted px-2 py-1 text-xs font-medium" data-testid="orchestration-status">
          {plan.status}
        </span>
      </div>

      {plan.stop_reason ? (
        <p className="mt-3 rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900" data-testid="orchestration-stop-reason">
          {plan.stop_reason}
        </p>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <AgentList title="Selected Agents" agents={plan.selected_agents || []} />
        <AgentList title="Skipped Agents" agents={plan.skipped_agents || []} />
      </div>

      <div className="mt-4 space-y-2" data-testid="orchestration-tasks">
        {tasks.map((task) => (
          <div key={task.id || task.agent_name} className="rounded-md border p-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium">{displayName(task.agent_name)}</span>
              <span className="rounded bg-muted px-2 py-0.5 text-xs">{task.status}</span>
            </div>
            <p className="mt-1 text-muted-foreground">{task.reason}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-md border p-3 text-sm" data-testid="orchestration-graph">
        <p className="font-medium">Execution Graph</p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          {edges.length ? edges.map((edge, index) => (
            <span key={`${edge.from}-${edge.to}-${index}`} className="rounded bg-muted px-2 py-1">
              {displayName(edge.from)} {'->'} {displayName(edge.to)}
            </span>
          )) : <span className="text-muted-foreground">No dependency edges were required.</span>}
        </div>
      </div>

      <div className="mt-4 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
        <span>Calls: {plan.actual_agent_calls || 0}/{plan.limits?.max_agent_calls_per_cycle ?? 0}</span>
        <span>Cost: ${Number(plan.actual_cost_usd || 0).toFixed(4)}</span>
        <span>Depth: {plan.limits?.max_orchestration_depth ?? 0}</span>
      </div>
    </section>
  )
}

function AgentList({ title, agents }: { title: string; agents: string[] }) {
  return (
    <div className="rounded-md border p-3 text-sm">
      <p className="font-medium">{title}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {agents.length ? agents.map((agent) => (
          <span key={agent} className="rounded bg-muted px-2 py-1 text-xs">
            {displayName(agent)}
          </span>
        )) : <span className="text-muted-foreground">None</span>}
      </div>
    </div>
  )
}
