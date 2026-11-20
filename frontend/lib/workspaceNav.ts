// Navigation model for the project workspace.
//
// The workspace follows one guided path (Overview -> Plan -> Write -> Review ->
// Finish). Every section id that existed before the redesign still resolves,
// either as a tab inside one of the steps or under "More tools", so deep links
// (?section=...), the command palette and assistant navigation keep working.

export type StepId = 'overview' | 'plan' | 'write' | 'review' | 'finish' | 'more' | 'settings'

export interface SectionInfo {
  id: string
  label: string
  description: string
}

export interface StepInfo {
  id: StepId
  label: string
  number?: number
  title: string
  description: string
  sections: SectionInfo[]
}

export const STEPS: StepInfo[] = [
  {
    id: 'overview',
    label: 'Overview',
    title: 'Overview',
    description: 'Where your book stands and what to do next.',
    sections: [{ id: 'dashboard', label: 'Overview', description: 'Where your book stands and what to do next.' }],
  },
  {
    id: 'plan',
    label: 'Plan',
    number: 1,
    title: 'Plan your story',
    description: 'Shape the idea, the people and the world before you write. Everything stays editable.',
    sections: [
      { id: 'vision', label: 'Story idea', description: 'Premise, genre, themes and who the book is for.' },
      { id: 'characters', label: 'Characters', description: 'The people in your story and what they want.' },
      { id: 'world', label: 'World', description: 'Places, rules and history of your setting.' },
      { id: 'threads', label: 'Plot threads', description: 'Promises, problems and subplots to develop and resolve.' },
      { id: 'mysteries', label: 'Mysteries', description: 'Questions readers should want answered, and when to answer them.' },
      { id: 'arcs', label: 'Story arcs', description: 'The big stretches of the book, from a new problem to a changed situation.' },
      { id: 'timeline', label: 'Timeline', description: 'What happens, and when.' },
      { id: 'questions', label: 'Questions for you', description: 'Choices the AI needs you to make about the story.' },
    ],
  },
  {
    id: 'write',
    label: 'Write',
    number: 2,
    title: 'Write chapters',
    description: 'Write the next chapter with AI help, or open any chapter to read and edit it.',
    sections: [
      { id: 'writing', label: 'Chapters', description: 'Every chapter, its words and its status.' },
      { id: 'write-next', label: 'Write next chapter', description: 'Describe what should happen; the AI drafts it using your story so far.' },
      { id: 'drafting', label: 'Scene planner', description: 'Plan and draft scene by scene from your story arcs.' },
    ],
  },
  {
    id: 'review',
    label: 'Review',
    number: 3,
    title: 'Review and improve',
    description: 'Confirm what the AI learned from your chapters, check consistency and accept or reject suggested edits.',
    sections: [
      { id: 'facts', label: 'Facts to confirm', description: 'Characters, places and mysteries found in your chapters. Nothing is added until you confirm it.' },
      { id: 'story-health', label: 'Story check', description: 'Continuity, open promises and pacing across the whole book.' },
      { id: 'editorial', label: 'Suggested edits', description: 'AI revisions you can compare with the original and accept or reject.' },
    ],
  },
  {
    id: 'finish',
    label: 'Finish',
    number: 4,
    title: 'Finish the book',
    description: 'Put approved chapters together into a book and export it.',
    sections: [{ id: 'manuscript', label: 'Book & export', description: 'Assemble the book, review it and export DOCX, EPUB, PDF and more.' }],
  },
  {
    id: 'more',
    label: 'More tools',
    title: 'More tools',
    description: 'Specialist and behind-the-scenes tools. You do not need these to write your book.',
    sections: [
      { id: 'story-studio', label: 'Story chat', description: 'Ask questions about your story and get answers grounded in what you have written.' },
      { id: 'guide', label: 'Setup guide', description: 'A step-by-step guide for starting a new novel.' },
      { id: 'arc-development', label: 'Arc planner', description: 'Detailed checklists and chapter plans for each story arc.' },
      { id: 'relationships', label: 'Relationships', description: 'How characters are connected.' },
      { id: 'power', label: 'Power system', description: 'Rules, limits and costs of magic or special abilities.' },
      { id: 'factions', label: 'Factions', description: 'Groups whose goals and conflicts shape the story.' },
      { id: 'themes', label: 'Themes', description: 'The ideas, motifs and symbols your book explores.' },
      { id: 'knowledge', label: 'Who knows what', description: 'What each character knows at each point in the story.' },
      { id: 'knowledge-graph', label: 'Story map', description: 'An interactive map of characters, places and events.' },
      { id: 'canon', label: 'Story rules', description: 'Facts you have confirmed as true for this book, and any conflicts between them.' },
      { id: 'canon-queue', label: 'Proposed changes', description: 'Changes to confirmed facts waiting for your decision.' },
      { id: 'readiness', label: 'Planning checklist', description: 'What the current arc still needs before drafting.' },
      { id: 'story-room', label: 'Story room', description: 'The current arc, its goals and open problems at a glance.' },
      { id: 'discussion', label: 'AI team discussion', description: 'Proposals from the AI planning team that you can approve or change.' },
      { id: 'insights', label: 'AI insights', description: 'Weak spots the AI noticed in the plan.' },
      { id: 'workflow', label: 'AI activity', description: 'What the AI team did recently, with cost and call details.' },
      { id: 'project-timeline', label: 'Project history', description: 'A log of everything that changed in this project.' },
      { id: 'explainability-timeline', label: 'Story check history', description: 'How story check results changed over time.' },
    ],
  },
  {
    id: 'settings',
    label: 'Project settings',
    title: 'Project settings',
    description: 'Name, title, backups and AI connection.',
    sections: [{ id: 'settings', label: 'Project settings', description: 'Name, title, backups and AI connection.' }],
  },
]

export const GUIDED_STEPS = STEPS.filter((step) => step.number !== undefined)

const sectionIndex = new Map<string, { step: StepInfo; section: SectionInfo }>()
for (const step of STEPS) {
  for (const section of step.sections) sectionIndex.set(section.id, { step, section })
}

export const ALL_SECTION_IDS = new Set(sectionIndex.keys())

export function stepForSection(sectionId: string): StepInfo {
  return sectionIndex.get(sectionId)?.step ?? STEPS[0]
}

export function sectionInfo(sectionId: string): SectionInfo | undefined {
  return sectionIndex.get(sectionId)?.section
}

export function stepById(stepId: StepId): StepInfo {
  return STEPS.find((step) => step.id === stepId) ?? STEPS[0]
}

/** The step that follows this one on the guided path, if any. */
export function nextGuidedStep(stepId: StepId): StepInfo | undefined {
  const index = GUIDED_STEPS.findIndex((step) => step.id === stepId)
  if (stepId === 'overview') return GUIDED_STEPS[0]
  if (index < 0) return undefined
  return GUIDED_STEPS[index + 1]
}
