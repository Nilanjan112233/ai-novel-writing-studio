import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'

import ActionableEmptyState from './ActionableEmptyState'
import StartYourNovel from './StartYourNovel'
import { dataApi, rc6Api } from '@/lib/api'


vi.mock('@/lib/api', () => ({
  dataApi: {
    askProjectAssistant: vi.fn(),
  },
  rc6Api: {
    getBeginnerFlow: vi.fn(),
    updateBeginnerStep: vi.fn(),
    createWorkspaceEntry: vi.fn(),
  },
}))

const step = {
  step_id: 'story_idea',
  order: 1,
  label: 'Story Idea',
  description: 'Capture the promise of the novel.',
  target: 'vision',
  status: 'not_started' as const,
  title: '',
  details: '',
  source_mode: null,
  required: false,
  ai_prompt: 'Suggest a story idea.',
  completed_at: null,
}
const flow = {
  project_id: 'project-1',
  steps: [
    step,
    ...['Main Character', 'World', 'Conflict', 'First Decision', 'First Arc', 'First Scene'].map((label, index) => ({
      ...step,
      step_id: label.toLowerCase().replaceAll(' ', '_'),
      order: index + 2,
      label,
    })),
  ],
  current_step: 'story_idea',
  completed_steps: 0,
  total_steps: 7,
  completion: 0,
  next_action: { label: 'Add your story idea', target: 'vision' },
}


beforeEach(() => vi.clearAllMocks())

describe('RC6 beginner author experience', () => {
  test('presents one guided start with editable, skippable, assisted steps', async () => {
    vi.mocked(rc6Api.getBeginnerFlow).mockResolvedValue(flow)
    vi.mocked(rc6Api.updateBeginnerStep).mockResolvedValue({
      ...flow,
      current_step: 'main_character',
      completed_steps: 1,
      completion: 14,
      steps: flow.steps.map((item) => item.step_id === 'story_idea'
        ? { ...item, status: 'completed' as const, title: 'Remembering Roads' }
        : item),
    })
    const changed = vi.fn()
    render(<StartYourNovel projectId="project-1" onNavigate={vi.fn()} onChanged={changed} />)
    fireEvent.click(await screen.findByTestId('start-your-novel'))
    expect(screen.getByTestId('start-your-novel-flow')).toHaveTextContent('Start Your Novel')
    expect(screen.getAllByText('Use AI suggestion')).toHaveLength(1)
    expect(screen.getByText('Decide later')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Story Idea title'), { target: { value: 'Remembering Roads' } })
    fireEvent.click(screen.getByText('Save and continue'))
    await waitFor(() => expect(rc6Api.updateBeginnerStep).toHaveBeenCalledWith(
      'project-1',
      'story_idea',
      expect.objectContaining({ action: 'save', title: 'Remembering Roads' }),
    ))
    expect(changed).toHaveBeenCalled()
  })

  test('turns an empty workspace into manual, AI, import, and guide actions', async () => {
    vi.mocked(rc6Api.createWorkspaceEntry).mockResolvedValue({
      project_id: 'project-1',
      area: 'character',
      created_id: 'character-1',
      target: 'characters',
      story_bible_version: '1',
      message: 'Created',
    })
    const created = vi.fn()
    const guide = vi.fn()
    render(<ActionableEmptyState projectId="project-1" area="character" label="Character" description="Start with a protagonist." onCreated={created} onGuide={guide} />)
    expect(screen.getByText('Create manually')).toBeInTheDocument()
    expect(screen.getByText('Generate with AI')).toBeInTheDocument()
    expect(screen.getByText('Import existing')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Continue guided setup'))
    expect(guide).toHaveBeenCalled()
    fireEvent.click(screen.getByText('Create manually'))
    fireEvent.change(screen.getByLabelText('Character name or title'), { target: { value: 'Mara Vale' } })
    fireEvent.change(screen.getByLabelText('Character details'), { target: { value: 'A patient mapmaker.' } })
    fireEvent.click(screen.getByText('Save and update project'))
    await waitFor(() => expect(rc6Api.createWorkspaceEntry).toHaveBeenCalledWith(
      'project-1',
      expect.objectContaining({ area: 'character', title: 'Mara Vale', source_mode: 'manual' }),
    ))
    expect(created).toHaveBeenCalled()
  })
})
