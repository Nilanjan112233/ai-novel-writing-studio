
interface Project {
  id: string
  title: string
  project_name?: string
  story_title?: string | null
  premise: string
  idea_dump: string
  genre: string
  tone: string
  themes: string[]
  inspirations: string[]
  character_notes: string | null
  world_notes: string | null
  plot_notes: string | null
  notes: string | null
  status: string
  target_length?: string | null
  audience?: string | null
  narrative_goals?: string[]
  created_at: string
  updated_at: string
  planning_reconsideration?: {
    status?: 'pending' | 'resolved'
    message?: string
    affected_count?: number
    remaining?: number
    updated_at?: string
  } | null
}

interface Run {
  id: string
  project_id: string
  status: string
  current_agent: string
  started_at: string
  finished_at?: string
  cycle_number?: number
  metadata?: Record<string, any>
  error?: string
  error_code?: string
}

interface AgentOutput {
  id: string
  run_id: string
  agent_name: string
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

interface Question {
  id: string
  project_id: string
  text: string
  choices: string[]
  answered: boolean
  answer?: string
  cycle_number?: number
  default_recommendation?: string
  story_area?: string
  blocking?: boolean
  created_at: string
}

interface Outline {
  id: string
  project_id: string
  premise: string
  themes: string[]
  acts: Array<{ act: number; title: string; summary: string }>
  chapters: Array<{ chapter: number; title: string; summary: string }>
  created_at: string
  updated_at: string
}

interface TimelineMessage {
  id: string
  project_id: string
  cycle_number: number
  role: "user" | "agent" | "system"
  agent_name?: string
  message_type: "idea" | "critique" | "question" | "summary"
  content: string
  created_at: string
}

interface Cycle {
  id: string
  project_id: string
  cycle_number: number
  trigger_message_ids: string[]
  agents_run: string[]
  started_at: string
  finished_at?: string
  status: string
}

interface MessageCreateRequest {
  content: string
}

interface DeleteProjectResponse {
  message: string
}

interface CharacterBible extends ProviderStamped {
  id: string
  project_id: string
  name: string
  aliases: string[]
  role?: string
  age?: string
  description?: string
  personality?: string[]
  goals: string[]
  fears: string[]
  flaws: string[]
  personality_traits: string[]
  arc_start?: string
  arc_end?: string
  current_arc_state?: string
  secrets: string[]
  contradictions: string[]
  relationships: Array<Record<string, unknown>>
  notes?: string
  power?: string
  arc?: string
  current_status?: string
  future_payoffs?: string[]
  timeline?: string[]
  agent_notes?: string
  updated_at?: string
  version?: number
  contributing_agents?: string[]
  cycle_source?: number
  authority_status?: string
  candidate_status?: string
  candidate_id?: string
  source_chapter?: number
}

interface NarrativeWorldBible extends ProviderStamped {
  id?: string
  project_id: string
  locations?: Array<Record<string, unknown>>
  factions?: Array<Record<string, unknown>>
  magic_systems?: Array<Record<string, unknown>>
  religions?: Array<Record<string, unknown>>
  religion?: Array<Record<string, unknown>>
  historical_events?: Array<Record<string, unknown>>
  history?: Array<Record<string, unknown>>
  races?: Array<Record<string, unknown>>
  politics?: Array<Record<string, unknown>>
  technology?: Array<Record<string, unknown>>
  economy?: Array<Record<string, unknown>>
  academies?: Array<Record<string, unknown>>
  current_conflicts?: string[]
  world_rules?: string[]
  contradictions?: string[]
  updated_at?: string
  version?: number
  contributing_agents?: string[]
  cycle_source?: number
}

interface PlotThread extends ProviderStamped {
  id: string
  project_id: string
  title: string
  description: string
  introduced_in_cycle: number
  status: string
  related_characters: string[]
  possible_resolutions: string[]
  updated_at?: string
  authority_status?: string
  candidate_status?: string
  candidate_id?: string
}

type DraftStatus = 'draft' | 'review' | 'approved' | 'rejected' | 'archived'

interface ContinuityReport extends ProviderStamped {
  id?: string
  project_id: string
  report_id?: string
  cycle_number?: number
  arc_id?: string
  chapter_plan_id?: string
  scene_id?: string | null
  subject_type?: 'scene_plan' | 'scene_draft' | 'chapter_draft' | string
  subject_id?: string
  version_number?: number
  validation_stage?: string
  result?: 'PASS' | 'WARNING' | 'FAIL'
  issues?: Array<Record<string, string>>
  severity?: string
  recommendations?: string[]
  missing_knowledge?: string[]
  contradictions?: string[]
  artifact_violations?: string[]
  timeline_violations?: string[]
  character_violations?: string[]
  power_violations?: string[]
  dependency_violations?: string[]
  foreshadow_violations?: string[]
  chapter_membership_violations?: string[]
  scene_ordering_violations?: string[]
  warnings?: string[]
  evidence?: string[]
  created_at: string
}

interface SceneEntry extends ProviderStamped {
  id: string
  project_id: string
  title: string
  summary: string
  characters_present: string[]
  emotional_shift: string
  purpose: string
  foreshadowing: string[]
  created_at: string
}

interface SceneDraft extends ProviderStamped {
  id?: string
  project_id: string
  draft_id: string
  arc_id: string
  chapter_plan_id: string
  scene_id: string
  version_number: number
  version_label?: string
  parent_version_id?: string | null
  status: DraftStatus
  active: boolean
  generated_text: string
  operation?: string
  why?: string
  expected_impact?: string
  affected_narrative_areas?: string[]
  estimated_change_scope?: 'small' | 'medium' | 'large' | string
  preserved_elements?: string[]
  context_evidence?: string[]
  connection_from_previous?: string
  handoff_to_next?: string
  scene_goal?: string
  scene_trouble?: string
  scene_stakes?: string
  distinct_progression?: string
  canon_proposal_ids?: string[]
  favorite?: boolean
  exploratory?: boolean
  planning_gate_result?: 'PASS' | 'WARNING' | 'FAIL'
  planning_gate_blockers?: string[]
  merged_from_draft_ids?: string[]
  continuity_claims?: Record<string, string[]>
  generation_notes?: string[]
  generation_metadata?: Record<string, unknown>
  generated_by: 'SceneWriterAgent' | 'RevisionAgent' | 'author_merge'
  change_reason?: string
  validation_result?: 'PASS' | 'WARNING' | 'FAIL'
  continuity_report_id?: string
  review_reason?: string
  created_at: string
  updated_at: string
  paragraphs?: ParagraphSkeleton[]
}

export interface WritingDashboard {
  project_id: string
  current_arc?: { arc_id: string; title: string } | null
  current_chapter?: { chapter_plan_id: string; number: number; title: string } | null
  current_scene?: { scene_id: string; title: string; status: string } | null
  current_draft?: {
    draft_id: string
    version_label: string
    status: DraftStatus
    exploratory: boolean
    favorite: boolean
  } | null
  metrics: {
    words: number
    characters: number
    reading_minutes: number
    writing_streak_days: number
    last_edited?: string | null
    pending_ai_suggestions: number
    pending_revisions: number
    approved_scenes: number
    total_scenes: number
  }
  workflow: {
    active_stage: string
    steps: Array<{ title: string; complete: boolean; current: boolean }>
  }
  scene_health: {
    result: string
    blockers: string[]
    evidence: string[]
    coaching_notes?: string[]
  }
  next_action: {
    title: string
    explanation: string
    action: string
    target: string
    scene_id?: string
    draft_id?: string
    allow_exploratory?: boolean
  }
  context_used: Record<string, number>
  generated_at: string
}

export interface WritingStateChapter {
  chapter_number: number
  title: string
  workflow_mode: 'discovery' | 'structured' | string
  status: string
  active_version: number
  version_count: number
  draft_id: string
  word_count: number
  updated_at?: string | null
  approved_at?: string | null
  validation_result?: string
  continuity_report_id?: string | null
  extraction: { status: string; candidate_count: number; extraction_id?: string | null; updated_at?: string | null }
  intelligence: { status: string; intelligence_id?: string | null; finding_count: number }
}

export interface WritingState {
  project_id: string
  workflow_mode: 'discovery' | 'structured' | 'mixed' | string
  chapter_count: number
  latest_chapter?: WritingStateChapter | null
  latest_approved_chapter?: WritingStateChapter | null
  chapters: WritingStateChapter[]
  structured: { chapter_plans: number; scene_plans: number }
  pending: { review: number; enrichment: number; canon_proposals: number; author_decisions: number }
  next_action: { label: string; target: string }
  last_activity_at?: string | null
}

export interface ChapterContextView {
  project_id: string
  chapter_number: number
  learned_from_chapter: { candidate_status: string; groups: Record<string, string[]>; candidate_count: number }
  chapter_intelligence: { summary?: string; events: string[]; open_questions: string[]; characters: string[]; relationships: string[]; artifacts: string[] }
  carried_into_generation: Array<{ source_type?: string; source_id?: string; content: string; score?: number }>
  approved_prose_excerpt?: string
  approval_change?: {
    before: { source: string; candidate_groups: Record<string, string[]>; summary?: string }
    new_information: { candidate_groups: Record<string, string[]>; candidate_status: string }
    carried_forward: Array<{ source_type?: string; source_id?: string; content: string; score?: number }>
    canon_changed: boolean
    canon_change_count: number
    open_threads: string[]
    next_chapter_influence: Array<{ source_type?: string; content: string }>
  }
  source: string
}

export interface ChapterVersionComparison {
  chapter_number: number
  available: boolean
  message?: string
  left?: { draft_id: string; version: number; status: string; word_count?: number }
  right?: { draft_id: string; version: number; status: string; word_count?: number; active?: boolean }
  diff?: string
  source?: string
}

export interface WritingActivityItem {
  kind: string
  label: string
  status: string
  summary: string
  updated_at?: string | null
  safe_prose?: boolean
  retryable?: boolean
}

export interface WritingActivity {
  items: WritingActivityItem[]
  running: WritingActivityItem[]
  attention: WritingActivityItem[]
  source: string
}

export interface SceneDraftComparison {
  scene_id: string
  left: { draft_id: string; label: string; word_count: number; text: string }
  right: { draft_id: string; label: string; word_count: number; text: string }
  similarity_percent: number
  word_count_delta: number
  changes: Array<{ kind: string; before: string; after: string }>
  summary: string
}

export interface ParagraphDependencies {
  canon_facts: string[]
  characters: string[]
  locations: string[]
  relationships: string[]
  mysteries: string[]
  callbacks: string[]
}

export interface PipelineStageMetadata {
  status: string
  updated_at: string
  provider?: string | null
  model?: string | null
  token_usage: number
  estimated_cost: number
  retry_count: number
  notes: string[]
}

export interface ValidationDomainResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  validated_at: string
}

export interface ParagraphSkeleton {
  id?: string
  project_id: string
  scene_id: string
  paragraph_id: string
  order: number
  purpose: string
  narrative_goal: string
  scene_goal: string
  emotion: string
  tension_level: string
  pov: string
  location: string
  dialogue_goal: string
  exposition_goal: string
  target_word_count: number
  is_locked: boolean
  approval_state: 'pending' | 'approved' | 'rejected'
  version: number
  regeneration_count: number
  dependencies: ParagraphDependencies
  processing_pipeline: Record<string, PipelineStageMetadata>
  validation_domains: Record<string, ValidationDomainResult>
  comments: any[]
  revision_notes: any[]
  branch_id?: string | null
  parent_version_id?: string | null
  created_at: string
  updated_at: string
  archived_at?: string | null
  trashed_at?: string | null
  duplicated_from_project_id?: string | null
}

/**
 * Authoritative prose content record for the Tiptap editor.
 * Stored in the `paragraph_content` MongoDB collection and returned
 * by GET /scenes/{scene_id}/paragraphs/{paragraph_id}/content.
 *
 * Distinct from ParagraphSkeleton (which holds planning metadata).
 * This document is written on every autosave and manual save.
 */
export interface ParagraphContent {
  paragraph_id: string
  scene_id: string
  project_id: string
  /** Plain-text prose as authored by the writer or accepted from AI. */
  prose: string
  /** Serialised Tiptap/ProseMirror JSON document (optional, for rich-text state). */
  editor_state?: Record<string, unknown>
  current_version_id?: string | null
  /** Monotonically increasing counter for autosave cycles (resets on manual commit). */
  autosave_version: number
  word_count: number
  character_count: number
  last_saved_by?: string | null
  updated_at?: string | null
}

export interface ParagraphSuggestion {
  suggestion_id: string
  paragraph_id: string
  suggestion_type: string
  provider: string
  model: string
  created_at: string
  status: 'pending' | 'accepted' | 'rejected'
  proposed_prose: string
  explanation: {
    editing_goal: string
    reasoning: string
    summary_of_changes: string
    trade_offs: string
    confidence?: string
  }
  generation_metadata: {
    prompt_template?: string
    prompt_version?: string
    temperature?: number
    latency_ms?: number
    estimated_cost?: number
    reasoning_mode?: string
  }
}

export interface ParagraphVersion {
  version_id: string
  paragraph_id: string
  version_number: number
  change_reason: string
  created_at: string
  created_by: string
  generation_metadata?: {
    provider?: string
    model?: string
    suggestion_type?: string
    latency_ms?: number
  } | null
  snapshot: {
    prose?: string
    purpose?: string
    narrative_goal?: string
    pov?: string
    word_count?: number
    version?: number
    approval_state?: string
    is_locked?: boolean
    [key: string]: unknown
  }
}

export type VersionLabel =
  | 'autosave'
  | 'manual'
  | 'ai_suggestion'
  | 'restore'
  | 'approval'
  | 'lock'
  | 'system'

export interface ParagraphCommentReply {
  reply_id: string
  comment_id: string
  author: string
  content: string
  created_at: string
}

export interface ParagraphComment {
  comment_id: string
  paragraph_id: string
  author: string
  content: string
  status: 'open' | 'resolved'
  created_at: string
  resolved_at?: string | null
  replies: ParagraphCommentReply[]
}



interface ChapterDraft extends ProviderStamped {
  id?: string
  project_id: string
  draft_id: string

  arc_id: string | null
  chapter_plan_id: string | null
  workflow_mode?: 'structured' | 'discovery' | string
  discovery_id?: string | null
  word_range?: { minimum: number; target: number; maximum: number }
  word_count?: number
  version_number: number
  parent_version_id?: string | null
  status: DraftStatus
  active: boolean
  source_scene_draft_ids: string[]
  transitions: Array<{
    from_scene_draft_id: string
    to_scene_draft_id: string
    generated_text: string
  }>
  generated_text: string
  continuity_claims?: Record<string, string[]>
  generation_notes?: string[]
  generation_metadata?: Record<string, unknown>
  generated_by: 'ChapterAssemblerAgent'
  change_reason?: string
  validation_result?: 'PASS' | 'WARNING' | 'FAIL'
  continuity_report_id?: string
  review_reason?: string
  created_at: string
  updated_at: string
}

interface StoryStudioJob {
  id: string
  job_id?: string
  project_id: string
  status: 'queued' | 'running' | 'waiting' | 'completed' | 'failed' | string
  intent?: string
  summary?: string
  progress?: { completed: number; total: number; message: string }
  error?: string | null
  created_at?: string
  completed_at?: string | null
  query?: string
  result?: StoryStudioResult
  events?: Array<{ stage: string; status: string; summary: string; created_at?: string }>
}

interface StoryStudioResult {
  job_id?: string
  intent: string | { intent?: string }
  mutation_class: string
  understood_as: string
  answer: string
  evidence?: Array<{ source?: string; label?: string; detail?: string }> | Record<string, unknown>
  navigation?: { target?: string; label?: string } | null
  navigation_actions?: Array<{ target?: string; label?: string }>
  understood?: string
  mutation_applied?: boolean
  author_decision_required?: boolean
  affected_areas?: string[]
  created_at?: string
  request_id?: string
  planning_capture?: {
    status?: string
    candidates?: Array<{ type?: string; description?: string; value?: string }>
    projection?: { counts?: Record<string, number> }
    provider?: string
    model?: string
  } | null
  writing_actions?: string[]
  draft?: {
    draft_id?: string
    chapter_number?: number
    status?: string
    word_count?: number
    range_compliant?: boolean
    target_word_min?: number | null
    target_word_count?: number | null
    target_word_max?: number | null
    validation_result?: string | null
    generated_text?: string
  }
  creative_review?: {
    focus?: string
    findings?: Array<Record<string, unknown>>
    distinctive_elements?: string[]
  }
  clarification?: {
    question?: string
    original_query?: string
    status?: string
  } | null
  continued_from_job_id?: string
  title_suggestions?: string[]
  generation_metadata?: Record<string, unknown>
  development?: {
    status?: string
    run_id?: string
    cycle_id?: string
    cycle_number?: number
    targeted?: boolean
    summary?: string
    author_phase?: string
    confirmed_planning_used?: boolean
    question?: string
    question_id?: string
    planned_agents?: string[]
    completed_agents?: string[]
    run_status?: string
  }
}

interface DiscoveryExtraction {
  id: string
  project_id: string
  source_draft_id: string
  status: 'candidate' | 'approved' | 'rejected' | string
  candidates: Array<{ type: string; value: string; confidence?: number; evidence?: string }>
  provenance?: Record<string, unknown>
  created_at?: string
  extraction_metadata?: Record<string, unknown>
}

type EditorialSubjectType = 'scene' | 'chapter' | 'arc'
type EditorialReportType = 'editorial' | 'dialogue'
type RevisionBranchStatus = 'draft' | 'review' | 'approved' | 'rejected' | 'archived'

interface EditorialFinding {
  category: string
  severity: string
  message: string
  evidence: string[]
}

interface EditorialReport {
  id?: string
  project_id: string
  report_id: string
  arc_id?: string | null
  chapter_id?: string | null
  scene_id?: string | null
  draft_id?: string | null
  version_number: number
  subject_type: EditorialSubjectType
  subject_id: string
  report_type: EditorialReportType
  score: number
  dimension_scores: Record<string, number>
  findings: EditorialFinding[]
  recommendations: string[]
  blockers: string[]
  evidence: string[]
  text_metrics?: Record<string, number | number[]>
  generation_metadata?: Record<string, unknown>
  generated_by: 'EditorAgent' | 'DialogueAgent'
  created_at: string
}

interface EditorialScore {
  id?: string
  project_id: string
  score_id: string
  subject_type: EditorialSubjectType
  subject_id: string
  score_type: 'scene_editorial' | 'chapter_editorial' | 'arc_editorial'
  score: number
  dimensions: Record<string, number>
  evidence: string[]
  calculated_at: string
}

interface RevisionBranch {
  id?: string
  project_id: string
  branch_id: string
  source_draft_id: string
  source_draft_type: 'scene' | 'chapter'
  source_version_number: number
  source_text_sha256: string
  arc_id?: string | null
  chapter_plan_id?: string | null
  scene_id?: string | null
  parent_branch_id?: string | null
  latest_revision_id?: string | null
  title: string
  revision_pass?: string
  source_status?: string
  status: RevisionBranchStatus
  review_reason?: string
  created_at: string
  updated_at: string
}

interface RevisionVersion {
  id?: string
  project_id: string
  revision_id: string
  branch_id: string
  version_number: number
  parent_revision_id?: string | null
  generated_text: string
  summary: string
  applied_recommendations: string[]
  change_reason: string
  revision_pass?: string
  changes?: string[]
  reason?: string
  affected_elements?: string[]
  estimated_improvement?: string
  what_stays_unchanged?: string[]
  promoted_draft_id?: string
  created_by: 'RevisionAgent'
  generation_metadata?: Record<string, unknown>
  created_at: string
}

interface RevisionComparison {
  branch_id: string
  source_draft_id: string
  revision_id: string
  version_number: number
  source_text: string
  revision_text: string
  similarity: number
  source_word_count: number
  revision_word_count: number
  diff: string[]
}

type ManuscriptStatus = 'draft' | 'review' | 'validated' | 'approved' | 'archived'

interface ManuscriptSourceChapter {
  chapter_number: number
  chapter_plan_id: string
  chapter_draft_id: string
  chapter_draft_version: number
  arc_id?: string | null
  title: string
  text: string
  text_sha256: string
  source_scene_draft_ids: string[]
}

interface Manuscript {
  id?: string
  project_id: string
  manuscript_id: string
  title: string
  status: ManuscriptStatus
  active: boolean
  version: number
  current_version_id?: string | null
  approved_at?: string
  archived_at?: string
  created_at: string
  updated_at: string
}

interface ManuscriptVersion {
  id?: string
  project_id: string
  version_id: string
  manuscript_id: string
  version_number: number
  parent_version_id?: string | null
  source_chapters: ManuscriptSourceChapter[]
  assembled_text: string
  chapter_count: number
  validation_result: 'PENDING' | 'PASS' | 'WARNING' | 'FAIL'
  validation_report_id?: string
  created_at: string
}

interface ManuscriptReport {
  id?: string
  project_id: string
  report_id: string
  manuscript_id?: string | null
  version_id?: string | null
  report_type: 'deterministic_validation' | 'manuscript_review' | 'canon_review'
  result: 'PASS' | 'WARNING' | 'FAIL'
  findings: Array<Record<string, unknown>>
  failures?: Array<Record<string, unknown>>
  warnings?: Array<Record<string, unknown>>
  recommendations?: string[]
  evidence: string[]
  generated_by?: 'ManuscriptAgent' | 'CanonAgent'
  created_at: string
}

interface CanonRecord {
  id?: string
  project_id: string
  canon_id: string
  canon_type: string
  source_collection: string
  source_id: string
  source_version: number
  authority_level: string
  active: boolean
  subject: string
  field: string
  value: unknown
  evidence: unknown[]
  status?: string
  fact?: string
  source?: string
  confidence?: number
  created_at: string
  updated_at: string
}

interface CanonConflict {
  id?: string
  project_id: string
  conflict_id: string
  conflict_type: string
  domain: string
  subject: string
  field: string
  severity: string
  message: string
  canon_ids: string[]
  evidence: unknown[]
  original_source?: Record<string, unknown>
  conflicting_sources?: Array<Record<string, unknown>>
  affected_locations?: string[]
  impact?: string
  status: 'open' | 'acknowledged' | 'resolved'
  detected_at: string
  last_seen_at?: string
}

interface RelationshipEdge extends ProviderStamped {
  id: string
  project_id: string
  character_a: string
  character_b: string
  relationship?: string
  type?: string
  strength?: number
  trust?: number
  history?: string
  future_payoff?: string
  status: string
  authority_status?: string
  candidate_status?: string
  candidate_id?: string
}

interface ThemeRegistry extends ProviderStamped {
  project_id: string
  themes: string[]
  motifs: string[]
  symbols: string[]
  reinforcement_opportunities?: string[]
}

interface ForeshadowEntry extends ProviderStamped {
  id: string
  project_id: string
  setup: string
  expected_payoff: string
  resolved: boolean
}

interface ProviderStamped {
  provider?: string
  model?: string
  tokens?: number
  cost?: number
  latency?: number
  execution_trace_id?: string
  cycle_generated?: number
  timestamp?: string
  source_type?: string
  mock_used?: boolean
}

interface DiscussionMessage extends ProviderStamped {
  id: string
  project_id: string
  author: string
  role: string
  cycle: number
  reasoning: string
  references: string[]
  content: string
  timestamp: string
  summary?: string
  concerns?: string[]
  recommendation?: string
  decision_status?: string
  contradiction_status?: string
  structured_output?: Record<string, unknown>
}

interface StoryVision extends ProviderStamped {
  project_id: string
  premise: string
  genre: string
  themes: string[]
  target_length?: string | null
  inspirations: string[]
  audience?: string | null
  narrative_goals: string[]
  director_notes?: string
}

interface StoryArc extends ProviderStamped {
  id?: string
  arc_id: string
  title: string
  purpose?: string
  goal: string
  conflict?: string
  stakes?: string
  approval_status: 'draft' | 'discussed' | 'approved' | 'active' | 'completed' | 'archived'
  development_status?: 'idea' | 'discussion' | 'outline' | 'development' | 'approved' | 'active' | 'draftable' | 'completed' | 'archived'
  focus_role?: 'current' | 'next' | 'future'
  arc_maturity_score?: number
  maturity_threshold?: number
  maturity_details?: Record<string, ArcMaturityDimension>
  resolution_direction?: string
  chapter_range: Array<number | null>
  readiness_status: 'READY' | 'PARTIALLY_READY' | 'NOT_READY'
  drafting_eligible: boolean
  estimated_chapters?: number
  major_events: string[]
  conflicts: string[]
  payoffs: string[]
  mysteries: string[]
  character_changes: string[]
  character_growth?: string[]
  completion_status?: string
  dependencies: string[]
}

interface ReadinessItem {
  id?: string
  project_id: string
  item_id: string
  arc_id?: string | null
  category: string
  title: string
  description: string
  priority: 'required' | 'recommended' | 'optional'
  status: 'missing' | 'discussed' | 'proposed' | 'approved' | 'ready'
  evidence: unknown[]
  blocking: boolean
  created_at: string
  updated_at: string
}

interface ReadinessReport {
  project_id: string
  arc_id?: string | null
  status: 'READY' | 'PARTIALLY_READY' | 'NOT_READY'
  drafting_eligible: boolean
  arc_approval_status?: string | null
  counts: Record<string, number>
  total_items: number
  required_items: number
  satisfied_required_items: number
  blockers: ReadinessItem[]
  missing: ReadinessItem[]
  recommended: ReadinessItem[]
  ready: ReadinessItem[]
  evaluated_at: string
}

interface TimelineEntryV2 extends ProviderStamped {
  id?: string
  project_id: string
  entry_id: string
  arc_id?: string | null
  title: string
  summary: string
  importance: string
  status: 'planned' | 'approved' | 'drafted' | 'completed' | 'candidate'
  certainty: 'known' | 'probable' | 'unknown'
  dependencies: string[]
  chapter_range: Array<number | null>
  order: number
  authority_status?: string
  candidate_status?: string
  candidate_id?: string
}

interface CharacterProgression {
  id?: string
  project_id: string
  arc_id: string
  character: string
  current_state: string
  desired_state: string
  arc_start_state?: string
  arc_midpoint_state?: string
  arc_end_state?: string
  emotional_growth?: string
  maturity_growth?: string
  power_growth?: unknown[]
  relationship_growth?: unknown[]
  belief_changes?: unknown[]
  goal_changes?: unknown[]
  skills: unknown[]
  powers: unknown[]
  beliefs: unknown[]
  relationships: unknown[]
  maturity: unknown
  trauma: unknown[]
  goals: unknown[]
}

interface ArcMaturityDimension {
  score: number
  weight: number
  data_complete: boolean
  checklist_satisfied: number
  checklist_total: number
  evidence: string[]
}

interface ArcChecklistItem {
  id?: string
  project_id: string
  arc_id: string
  item_id: string
  category: string
  title: string
  description: string
  priority: 'required' | 'recommended' | 'optional'
  status: 'missing' | 'discussed' | 'proposed' | 'approved' | 'completed' | 'waived'
  dimension: string
  weight: number
  evidence: unknown[]
  blocking: boolean
  source: string
}

interface ArcDependency {
  id?: string
  project_id: string
  dependency_id: string
  arc_id: string
  dependency_type: string
  target_id: string
  required_state: string
  blocking: boolean
  status: 'pending' | 'satisfied' | 'blocked'
  validation_reason?: string
  evidence: unknown[]
}

interface ArcDevelopmentReport {
  project_id: string
  arc_id: string
  development_status: StoryArc['development_status']
  focus_role: StoryArc['focus_role']
  maturity_score: number
  maturity_threshold: number
  dimensions: Record<string, ArcMaturityDimension>
  checklist: {
    total: number
    satisfied: number
    required_open: Array<{ item_id: string; title: string; status: string }>
  }
  dependencies: {
    items: Array<Record<string, unknown>>
    blockers: Array<Record<string, unknown>>
    satisfied: boolean
  }
  readiness_status: ReadinessReport['status']
  draftable: boolean
  blockers: string[]
  evaluated_at: string
}

interface ChapterPlan {
  id?: string
  project_id: string
  chapter_plan_id: string
  arc_id: string
  chapter_number: number
  title: string
  purpose: string
  conflict: string
  character_focus: string[]
  knowledge_changes: string[]
  artifact_ids: string[]
  foreshadow_ids: string[]
  timeline_entry_ids: string[]
  status: 'planned' | 'approved' | 'drafted' | 'completed'
}

interface ScenePlanV2 extends ProviderStamped {
  id?: string
  project_id: string
  scene_id: string
  arc_id: string
  chapter_plan_id?: string | null
  title: string
  purpose: string
  conflict: string
  outcome: string
  character_focus: string[]
  character_change: string
  knowledge_changes: string[]
  foreshadow_links: string[]
  artifact_interactions: string[]
  timeline_impacts: string[]
  status: 'planned' | 'approved' | 'drafted' | 'completed'
  order: number
}

interface PowerProgression {
  id?: string
  project_id: string
  arc_id: string
  character: string
  starting_power: string
  ending_power: string
  new_abilities: unknown[]
  mastered_abilities: unknown[]
  limitations: unknown[]
  costs: unknown[]
  future_evolution: string
}

interface EvolutionEvent {
  id?: string
  project_id: string
  arc_id: string
  chapter_plan_id?: string | null
  event_type: string
  summary: string
  from_state: string
  to_state: string
  order: number
  evidence: unknown[]
  chain_node_id?: string
  evolution_id?: string
  foreshadow_id?: string
  artifact_id?: string
  knowledge_entry_id?: string
}

interface StoryRoom {
  project_id: string
  current_arc?: StoryArc | null
  active_discussions: DiscussionMessage[]
  open_planning_items: ArcChecklistItem[]
  blocked_items: ArcDependency[]
  suggestions: Array<Record<string, unknown>>
  agent_proposals: DiscussionMessage[]
  draft_queue?: Array<SceneDraft | ChapterDraft>
  review_queue?: Array<SceneDraft | ChapterDraft>
  continuity_warnings?: ContinuityReport[]
  editorial_queue?: Array<{
    subject_type: 'scene' | 'chapter'
    subject_id: string
    arc_id?: string
    chapter_plan_id?: string
    scene_id?: string
    missing_reviews: EditorialReportType[]
  }>
  revision_queue?: RevisionBranch[]
  editorial_blockers?: EditorialReport[]
  manuscript_queue?: Manuscript[]
  canon_queue?: Array<{
    type: 'canon_review'
    title: string
    last_reviewed_at?: string | null
    open_conflicts: number
  }>
  conflict_queue?: CanonConflict[]
  draft_approval_status?: {
    scene: Record<DraftStatus, number>
    chapter: Record<DraftStatus, number>
  }
  generation_history?: { total_versions: number }
  generated_at: string
}

interface KnowledgeEntry extends ProviderStamped {
  id?: string
  project_id: string
  entry_id: string
  arc_id?: string | null
  title: string
  content: string
  knowledge_type: 'WORLD_TRUTH' | 'READER_KNOWLEDGE' | 'CHARACTER_KNOWLEDGE'
  known_by: string[]
  not_known_by: string[]
  learned_how: string
  is_false: boolean
  confidence: number
  source: string
  source_id?: string
  reveal_target?: string
  world_truth_entry_id?: string | null
}

interface ArtifactRegistryEntry {
  id?: string
  project_id: string
  artifact_id: string
  item: string
  owner: string
  power: string
  hidden_power: string
  cost: string
  limitations: unknown[]
  history: string
  future_relevance: string
  status: string
  arc_ids: string[]
  character_ids: string[]
  timeline_entry_ids: string[]
  knowledge_entry_ids: string[]
}

interface PowerSystem extends ProviderStamped {
  project_id: string
  ranks: string[]
  levels: string[]
  cultivation: string
  skills: string[]
  classes: string[]
  evolution_paths: string[]
  limitations: string[]
  resources: string[]
  costs: string[]
  progression_curve: string
  progression_logic?: string
  concept_tree?: Array<Record<string, unknown>>
  compatibility_rules?: string[]
}

interface CharacterJourney extends ProviderStamped {
  id?: string
  character_name: string
  goals: string[]
  fears: string[]
  beliefs: string[]
  growth: string
  relationships: Array<Record<string, unknown>>
  status: string
  arc_progression: Array<Record<string, unknown>>
  future_plans: string[]
}

interface MysteryRegistryEntry extends ProviderStamped {
  id?: string
  setup?: string
  question?: string
  truth?: string
  hints?: string[]
  known_clues?: string[]
  hidden_clues?: string[]
  red_herrings?: string[]
  foreshadowing?: string[]
  expected_payoff?: string
  reveal_target?: string
  status?: string
  resolved?: boolean
  authority_status?: string
  candidate_status?: string
  candidate_id?: string
}

interface AIInsights extends ProviderStamped {
  project_id: string
  agent_concerns: string[]
  missing_story_areas: string[]
  weak_characters: string[]
  weak_pacing: string[]
  potential_contradictions: string[]
  suggested_improvements: string[]
  director_summary?: string
}

interface FactionRecord extends ProviderStamped {
  id?: string
  name: string
  agenda?: string
  leader?: string
  goals?: string[]
  enemies?: string[]
  allies?: string[]
  influence?: string
  secrets?: string[]
  territory?: string[]
  pressure?: string
}

interface StoryFinding {
  finding_id?: string
  category: string
  severity: string
  subject_type?: string
  subject_id?: string
  message: string
  evidence?: string[]
}

interface ChapterIntelligence {
  id?: string
  intelligence_id: string
  chapter_plan_id: string
  chapter_draft_id: string
  chapter_draft_version: number
  chapter_number: number
  chapter_summary: string
  important_events: string[]
  characters_present: string[]
  character_changes: Array<Record<string, unknown>>
  knowledge_revealed: Array<Record<string, unknown>>
  mysteries_introduced: Array<Record<string, unknown>>
  mysteries_advanced: Array<Record<string, unknown>>
  mysteries_resolved: Array<Record<string, unknown>>
  foreshadowing_introduced: Array<Record<string, unknown>>
  foreshadowing_advanced: Array<Record<string, unknown>>
  foreshadowing_resolved: Array<Record<string, unknown>>
  artifact_usage: Array<Record<string, unknown>>
  relationship_changes: Array<Record<string, unknown>>
  timeline_impact: Array<Record<string, unknown>>
  canon_impact: Array<Record<string, unknown>>
  unresolved_questions: string[]
  future_obligations: string[]
  quality_findings: StoryFinding[]
  word_count: number
  active: boolean
  generated_at: string
}

interface StoryAuditReport {
  id?: string
  report_id: string
  result: 'PASS' | 'WARNING' | 'FAIL'
  findings: StoryFinding[]
  finding_counts: Record<string, number>
  deterministic_finding_count: number
  agent_finding_count: number
  generated_by: string[]
  created_at: string
}

interface StoryHealthMetrics {
  total_chapters: number
  total_words: number
  open_mysteries: number
  resolved_mysteries: number
  unresolved_promises: number
  active_artifacts: number
  abandoned_artifacts: number
  active_foreshadowing: number
  resolved_foreshadowing: number
  canon_conflicts: number
  continuity_warnings: number
  pacing_warnings: number
  abandoned_characters: number
  character_arc_completion: number
  arc_completion: number
  manuscript_readiness: string
  editorial_blockers: number
}

interface NarrativeFinding {
  finding_id: string
  domain: 'character' | 'canon' | 'timeline' | 'plot' | 'pacing' | 'continuity' | 'balance' | 'dialogue' | 'world'
  category: string
  severity: 'info' | 'low' | 'medium' | 'warning' | 'high' | 'critical'
  explanation: string
  affected_chapters: number[]
  affected_scenes: string[]
  affected_elements: string[]
  evidence: unknown[]
  recommended_actions: string[]
  confidence: number
  status?: 'open' | 'acknowledged' | 'resolved'
}

interface StoryHealth {
  metrics: StoryHealthMetrics
  story_health_score: number
  evaluation_status?: 'evaluated' | 'not_enough_story'
  status: 'healthy' | 'watch' | 'at_risk'
  latest_audit_report_id?: string
  dimension_scores?: Record<string, number>
  findings?: NarrativeFinding[]
  analysis?: {
    source_documents: number
    nodes: number
    edges: number
    findings: number
    recomputed_nodes: number
    reused_nodes: number
    duration_ms: number
    incremental: boolean
    cache_hit?: boolean
  }
  calculated_at: string
}

interface ChangeImpactItem {
  collection: string
  id: string
  title: string
  reason: string
}

interface ChangeImpact {
  id?: string
  impact_id: string
  change_type: string
  target: Record<string, unknown>
  proposed_change: Record<string, unknown>
  affected: Record<string, ChangeImpactItem[]>
  counts: Record<string, number>
  total_affected: number
  risk: 'low' | 'medium' | 'high'
  status: 'preview' | 'approved' | 'rejected'
  created_at: string
}

interface AssistantMode {
  id: string
  label: string
  description: string
}

interface NavigationAction {
  type: 'navigate'
  target: string
  section: string
  label?: string
  chapter_number?: number
  scene_id?: string
}

interface NarrativeAssistantMessage {
  id?: string
  message_id: string
  mode: string
  query: string
  answer: string
  navigation_actions: NavigationAction[]
  reasoning_layer?: 'application' | 'project' | 'combined'
  application_surface?: string | null
  evidence: {
    finding_ids: string[]
    node_ids: string[]
    chapters: number[]
    canon_facts: string[]
    timeline_events: string[]
    analysis_id?: string
    application_topics?: Array<string | null>
  }
  canon_proposal_ids: string[]
  generation_metadata: Record<string, unknown>
  created_at: string
}

interface CharacterConversationTurn {
  id?: string
  conversation_id: string
  turn_id: string
  character_name: string
  timeline_chapter: number
  author_message: string
  character_response: string
  awareness_boundary: {
    requested_chapter: number
    effective_chapter: number
    death_boundary_applied: boolean
    death_chapter?: number | null
  }
  evidence: {
    canon_ids: string[]
    timeline_node_ids: string[]
    chapter_numbers: number[]
    knowledge_entry_ids: string[]
  }
  canon_proposal_ids?: string[]
  generation_metadata: Record<string, unknown>
  created_at: string
}

interface KnowledgeGraphNode {
  id?: string
  node_id: string
  kind: string
  label: string
  chapter_numbers: number[]
  scene_ids: string[]
  source_collection: string
  source_id: string
  payload: Record<string, unknown>
  warning_count: number
  story_health_warnings: Array<{
    finding_id: string
    severity: string
    explanation: string
  }>
}

interface KnowledgeGraphEdge {
  edge_id: string
  source: string
  target: string
  relationship: string
  confidence: number
}

interface KnowledgeGraph {
  analysis_id: string
  graph_version: number
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  counts: { nodes: number; edges: number; by_kind: Record<string, number> }
  source: 'narrative_analysis_engine'
}

interface CanonProposal {
  id?: string
  proposal_id: string
  canon_type: string
  subject: string
  field: string
  value: unknown
  confidence: number
  evidence: unknown[]
  affected_chapters: number[]
  affected_scenes: string[]
  downstream_impact: ChangeImpact & { requires_confirmation?: boolean }
  impact_id: string
  source_type: string
  source_id: string
  status: 'pending' | 'approved' | 'rejected'
  review_note?: string
  created_at: string
}

interface WorkspaceRecommendation {
  recommendation_id: string
  severity: string
  message: string
  actions: string[]
  evidence: unknown[]
  affected_chapters: number[]
  affected_scenes: string[]
  why: string
  destination?: string
}

interface StoryBible {
  project_id: string
  cycle_number: number
  version: number
  updated_at: string
  sections: {
    story_vision: StoryVision
    characters: CharacterBible[]
    character_journeys: CharacterJourney[]
    world: NarrativeWorldBible
    power_system: PowerSystem
    factions: FactionRecord[]
    relationships: RelationshipEdge[]
    plot_threads: PlotThread[]
    themes: ThemeRegistry
    foreshadowing: ForeshadowEntry[]
    mysteries: MysteryRegistryEntry[]
    timeline: TimelineEntryV2[]
    arcs: StoryArc[]
    arc_development: {
      reports: ArcDevelopmentReport[]
      checklists: ArcChecklistItem[]
      dependencies: ArcDependency[]
    }
    readiness: {
      items: ReadinessItem[]
      reports: ReadinessReport[]
    }
    character_progressions: CharacterProgression[]
    power_progressions: PowerProgression[]
    knowledge: KnowledgeEntry[]
    knowledge_evolutions: EvolutionEvent[]
    artifacts: ArtifactRegistryEntry[]
    artifact_evolutions: EvolutionEvent[]
    foreshadow_chains: EvolutionEvent[]
    questions: Question[]
    active_questions: Question[]
    resolved_questions: Question[]
    ai_insights: AIInsights
    drafting: {
      chapter_plans: ChapterPlan[]
      scene_plans: ScenePlanV2[]
      legacy_scene_plans?: SceneEntry[]
      scene_drafts: SceneDraft[]
      chapter_drafts: ChapterDraft[]
      review_queue?: Array<SceneDraft | ChapterDraft>
    }
    editorial: {
      reports: EditorialReport[]
      scores: EditorialScore[]
      revision_branches: RevisionBranch[]
      revision_versions: RevisionVersion[]
    }
    manuscript: {
      manuscripts: Manuscript[]
      versions: ManuscriptVersion[]
      reports: ManuscriptReport[]
    }
    canon_governance: {
      registry: CanonRecord[]
      conflicts: CanonConflict[]
    }
    chapter_intelligence?: ChapterIntelligence[]
    story_intelligence?: {
      health?: StoryHealth
      latest_audit?: StoryAuditReport
      audits?: StoryAuditReport[]
      change_impacts?: ChangeImpact[]
    }
    interactive_intelligence?: {
      character_conversations: CharacterConversationTurn[]
      character_memories: Array<Record<string, unknown>>
      assistant_history: NarrativeAssistantMessage[]
      canon_proposals: CanonProposal[]
      source_policy: string
    }
    discussion: DiscussionMessage[]
    canon_registry: Array<Record<string, unknown>>
    decision_registry: Array<Record<string, unknown>>
    discussion_decisions: Array<Record<string, unknown>>
    canon: Record<string, unknown>
    contradictions: Array<Record<string, unknown>>
    continuity_reports: ContinuityReport[]
    workflow: {
      cycles: Cycle[]
      runs: Run[]
      latest_orchestration?: OrchestrationRun
      agents: Array<{
        id: string
        run_id: string
        agent_name: string
        summary: string
        metadata: Record<string, unknown>
        created_at: string
      }>
    }
  }
}

interface MemoryResult {
  id: string
  source_type: string
  source_id: string
  content: string
  score: number
  semantic_score?: number
  metadata: Record<string, unknown>
}

interface AIExecutionSettings {
  execution_mode: 'hybrid' | 'full'
  default_provider: string
  default_model: string
  enable_streaming: boolean
  enable_reflection_loops: boolean
  enable_dynamic_routing: boolean
  max_context_tokens: number
  max_cycle_cost_usd: number
  max_agent_calls_per_cycle: number
  max_orchestration_depth: number
  provider_requests_per_minute: number
  max_reflection_loops: number
}

interface AgentModelAssignment {
  agent_name: string
  provider: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
  use_mock_in_hybrid: boolean
}

interface ProviderTestResult {
  success: boolean
  provider?: string
  model?: string
  latency_ms: number
  tokens_used: number
  json_valid: boolean
  streaming_supported?: boolean
  quota_remaining?: number | null
  quota_limit?: number | null
  warnings?: string[]
  error_type?: string
  error?: string
  suggested_fallback?: { provider: string; model: string }
  response?: unknown
}

interface ModelInfo {
  provider: string
  model_id: string
  display_name: string
  discovered_at?: string | null
  context_window?: number | null
  pricing_input?: number | null
  pricing_output?: number | null
  supports_json: boolean
  supports_streaming: boolean
  supports_tools: boolean
  supports_large_context: boolean
  supports_reasoning: boolean
  supports_multimodal: boolean
  free_tier: boolean
  recommended_for: string[]
  tags: string[]
}

interface ProviderHealth {
  id?: string
  provider: string
  status: 'online' | 'degraded' | 'offline' | 'untested'
  discovered_model_count?: number
  working_model_count?: number
  failed_model_count?: number
  active_model?: string
  last_success_at?: string
  last_latency_ms?: number
  last_error?: { type: string; message: string; created_at: string } | null
  daily_usage?: { requests?: number; tokens?: number; estimated_cost_usd?: number }
}

interface ModelValidationResult {
  provider: string
  model: string
  display_name?: string
  working: boolean
  success?: boolean
  latency?: number | null
  latency_ms?: number | null
  supports_json: boolean
  supports_streaming: boolean
  tokens_used?: number | null
  error_type?: string | null
  error_message?: string | null
  tested_at: string
  last_checked?: string
}

interface ValidateModelsResponse {
  provider: string
  total: number
  working: number
  failed: number
  results: ModelValidationResult[]
}

interface ExecutionTrace {
  _id?: string
  request_id?: string
  provider: string
  model: string
  agent_name?: string
  prompt_tokens: number
  response_tokens: number
  total_tokens: number
  cost_usd?: number
  response_length?: number
  latency_ms: number
  status: 'success' | 'failed'
  error_type?: string | null
  error_message?: string | null
  retry_count: number
  fallback_used: boolean
  created_at: string
}

interface OrchestrationTask {
  id?: string
  plan_id?: string
  agent_name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  reason: string
  order?: number | null
  started_at?: string | null
  completed_at?: string | null
  provider?: string
  model?: string
  tokens_used?: number
  cost_usd?: number
}

interface OrchestrationRun {
  id?: string
  project_id: string
  cycle_number: number
  trigger_type: 'message' | 'approval' | 'rejection' | 'answer' | 'manual'
  changed_entities: string[]
  affected_domains: string[]
  selected_agents: string[]
  skipped_agents: string[]
  selection_reasons: Record<string, string>
  execution_graph?: {
    nodes: Array<{ agent_name: string; depth?: number; selected: boolean }>
    edges: Array<{ from: string; to: string }>
  }
  limits?: {
    max_agent_calls_per_cycle: number
    max_orchestration_depth: number
    max_cycle_cost_usd: number
  }
  tasks?: OrchestrationTask[]
  status: 'pending' | 'running' | 'completed' | 'failed'
  stop_reason?: string | null
  estimated_cost_usd?: number
  actual_cost_usd?: number
  actual_agent_calls?: number
  routing_reason?: string
  agent_records?: Array<Record<string, unknown>>
  total_tokens?: number
  total_cost_usd?: number
  execution_mode?: string
  created_at: string
}

interface ContextPacketRecord {
  id?: string
  project_id: string
  cycle_number: number
  agent_name: string
  task: string
  packet: {
    active_context: unknown[]
    working_memory: unknown[]
    retrieved_memory: MemoryResult[]
    compressed_memory: unknown[]
    token_estimate: number
  }
  token_estimate: number
  created_at: string
}

interface CognitionEvent {
  id: string
  project_id: string
  cycle_number: number
  agent_name: string
  content: string
  created_at: string
}

interface ObservabilityEvent {
  id: string
  project_id: string
  cycle_number: number
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}

interface CompletenessCriterion {
  criterion_id: string
  label: string
  met: boolean
  required: boolean
  evidence: unknown[]
  target: string
  suggested_improvement: string
}

interface NarrativeCompleteness {
  project_id: string
  overall_completion: number
  current_milestone: string
  dimensions: Record<string, { dimension: string; score: number; status: string; criteria: CompletenessCriterion[]; blockers: CompletenessCriterion[]; remaining: CompletenessCriterion[] }>
  milestones: Array<{ gate_id: string; label: string; achieved: boolean; criteria: CompletenessCriterion[]; blockers: CompletenessCriterion[] }>
  remaining_work: Array<CompletenessCriterion & { dimension: string }>
  next_actions: Array<{ action_id: string; label: string; reason: string; target: string; milestone: string }>
  calculated_at: string
}

interface NarrativeCritique {
  story_health_before: number
  story_health_after: number
  analysis_id: string
  findings: Array<NarrativeFinding & { finding_type?: string; responsible_subsystem: string; suggested_improvement: string; source_service?: string }>
  critique_finding_count: number
  author_control: string
  generated_at: string
}

interface CreationGuideStep {
  step_id: string
  label: string
  why_it_matters: string
  target: string
  ai_systems: string[]
  completion: number
  required_information: string[]
  optional_improvements: string[]
}

interface NovelCreationGuide {
  steps: CreationGuideStep[]
  jump_freely: boolean
  milestones: NarrativeCompleteness['milestones']
  current_milestone: string
  next_actions: NarrativeCompleteness['next_actions']
}

interface WorkspaceCompanionMessage {
  message_id: string
  kind: 'status' | 'celebration' | 'milestone' | 'guide' | 'recommendation' | 'attention'
  title: string
  message: string
  target: string
  priority: number
  evidence: unknown[]
  read: boolean
  dismissed: boolean
  state?: 'active' | 'dismissed' | 'completed' | 'snoozed' | 'superseded'
  recommendation_key?: string
  presentation_count?: number
  action_label?: string
  explanation?: string
  created_at: string
}

interface WorkspaceCompanionFeed {
  messages: WorkspaceCompanionMessage[]
  headline?: WorkspaceCompanionMessage | null
  story_health: number | null
  current_milestone: string | null
  next_actions: NarrativeCompleteness['next_actions']
  state?: 'idle' | 'working' | 'celebrating' | 'notifying' | 'sleeping'
  welcome_back?: boolean
  recap?: string | null
  behavior: { motion: string; interruptive: boolean; respects_reduced_motion: boolean }
  refreshed_at: string
}

interface ApplicationAction {
  label: string
  description: string
  destination: string
}

interface ApplicationSurface {
  surface_id?: string
  label: string
  group: string
  purpose: string
  why_it_matters: string
  what_to_do: string
  what_happens_next: string
  aliases: string[]
  actions: ApplicationAction[]
}

interface ApplicationKnowledge {
  surfaces: Record<string, ApplicationSurface>
  groups: Record<string, string[]>
  workflows: Record<string, Record<string, unknown>>
  shortcuts: Array<{ keys: string; action: string; where: string }>
}

interface ProjectTimelineEntry {
  entry_id: string
  date: string
  action: string
  summary: string
  actor: 'You' | 'NovelForge'
  affected_systems: string[]
  destination: string
  chapter_number?: number | null
  scene_order?: number | null
  scene_label?: string | null
  changes: { story_health?: number | null; canon?: number | null; timeline?: number | null }
  replay: { event: string; outcome: string; destination: string }
}

interface ProjectTimeline {
  project_id: string
  entries: ProjectTimelineEntry[]
  count: number
  story_timeline_is_separate: boolean
}

interface ExplainabilityChange {
  change_id: string
  date: string
  overall: { from?: number; to?: number; delta: number }
  score_changes: Array<{ category: string; label: string; from?: number; to?: number; delta: number }>
  reasons: Array<{ direction: string; domain: string; message: string; finding_id: string; destination: string }>
  what_happened: string
  why_it_matters: string
  suggested_next_step: string
}

interface ExplainabilityTimeline {
  project_id: string
  changes: ExplainabilityChange[]
  count: number
}

interface BeginnerStep {
  step_id: string
  order: number
  label: string
  description: string
  target: string
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped'
  title: string
  details: string
  can_skip: boolean
  can_edit: boolean
  ai_prompt: string
  completed_at?: string | null
}

interface BeginnerFlow {
  project_id: string
  current_step: string
  completed_steps: number
  total_steps: number
  completion: number
  first_scene_ready: boolean
  steps: BeginnerStep[]
  next_action: { label: string; target: string; step_id: string; reason: string }
}

interface DecisionHistoryItem {
  version: number
  answer: string
  action: string
  reason: string
  created_at: string
}

interface EditableDecision {
  question_id: string
  question: string
  answered: boolean
  current_answer?: string | null
  version: number
  history: DecisionHistoryItem[]
  impact_preview: Record<string, unknown>
  can_change: boolean
  can_undo: boolean
  can_reopen: boolean
}

interface ProjectLibraryItem {
  id: string
  title: string
  project_name?: string
  story_title?: string | null
  status: string
  genre: string
  tone: string
  favorite: boolean
  created_at: string
  updated_at: string
  last_opened_at?: string | null
  story_consistency?: number | null
  completeness?: number | null
  milestone: string
}

interface ProjectLibraryPage {
  items: ProjectLibraryItem[]
  page: number
  page_size: number
  total: number
  pages: number
  has_next: boolean
  counts: Record<string, number>
}

interface WorkspaceBootstrap {
  project_id: string
  project: Record<string, unknown>
  story_bible: StoryBible
  story_health: StoryHealth
  completeness: NarrativeCompleteness
  companion: WorkspaceCompanionFeed
  version: string
  generated_at: string
  readiness?: Record<string, string>
  performance?: Record<string, number>
  cache?: Record<string, unknown>
}

export type {
  Project,
  Run,
  AgentOutput,
  Question,
  Outline,
  TimelineMessage,
  Cycle,
  MessageCreateRequest,
  DeleteProjectResponse,
  CharacterBible,
  NarrativeWorldBible,
  PlotThread,
  ContinuityReport,
  SceneEntry,
  DraftStatus,
  SceneDraft,
  ChapterDraft,
  StoryStudioJob,
  StoryStudioResult,
  DiscoveryExtraction,
  EditorialSubjectType,
  EditorialReportType,
  RevisionBranchStatus,
  EditorialFinding,
  EditorialReport,
  EditorialScore,
  RevisionBranch,
  RevisionVersion,
  RevisionComparison,
  ManuscriptStatus,
  ManuscriptSourceChapter,
  Manuscript,
  ManuscriptVersion,
  ManuscriptReport,
  CanonRecord,
  CanonConflict,
  RelationshipEdge,
  ThemeRegistry,
  ForeshadowEntry,
  ProviderStamped,
  DiscussionMessage,
  StoryVision,
  StoryArc,
  ReadinessItem,
  ReadinessReport,
  TimelineEntryV2,
  CharacterProgression,
  ArcMaturityDimension,
  ArcChecklistItem,
  ArcDependency,
  ArcDevelopmentReport,
  ChapterPlan,
  ScenePlanV2,
  PowerProgression,
  EvolutionEvent,
  StoryRoom,
  KnowledgeEntry,
  ArtifactRegistryEntry,
  PowerSystem,
  CharacterJourney,
  MysteryRegistryEntry,
  AIInsights,
  FactionRecord,
  StoryFinding,
  ChapterIntelligence,
  StoryAuditReport,
  StoryHealthMetrics,
  StoryHealth,
  NarrativeFinding,
  ChangeImpactItem,
  ChangeImpact,
  AssistantMode,
  NavigationAction,
  NarrativeAssistantMessage,
  CharacterConversationTurn,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
  KnowledgeGraph,
  CanonProposal,
  WorkspaceRecommendation,
  StoryBible,
  MemoryResult,
  AIExecutionSettings,
  AgentModelAssignment,
  ProviderTestResult,
  ModelInfo,
  ProviderHealth,
  ModelValidationResult,
  ValidateModelsResponse,
  ExecutionTrace,
  OrchestrationTask,
  OrchestrationRun,
  ContextPacketRecord,
  CognitionEvent,
  ObservabilityEvent,
  CompletenessCriterion,
  NarrativeCompleteness,
  NarrativeCritique,
  CreationGuideStep,
  NovelCreationGuide,
  WorkspaceCompanionMessage,
  WorkspaceCompanionFeed,
  ApplicationAction,
  ApplicationSurface,
  ApplicationKnowledge,
  ProjectTimelineEntry,
  ProjectTimeline,
  ExplainabilityChange,
  ExplainabilityTimeline,
  BeginnerStep,
  BeginnerFlow,
  DecisionHistoryItem,
  EditableDecision,
  ProjectLibraryItem,
  ProjectLibraryPage,
  WorkspaceBootstrap,
}
