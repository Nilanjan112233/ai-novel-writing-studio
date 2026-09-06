"""Author-facing knowledge of the NovelForge application.

This catalog is intentionally separate from narrative/project knowledge. It is
shared by page guidance, navigation validation, and the Project Assistant.
"""
from __future__ import annotations

import re
from typing import Any, Dict


def _surface(
    label: str,
    group: str,
    purpose: str,
    matters: str,
    do_here: str,
    next_step: str,
    *,
    aliases: tuple[str, ...] = (),
    actions: tuple[tuple[str, str, str], ...] = (),
) -> Dict[str, Any]:
    return {
        "label": label,
        "group": group,
        "purpose": purpose,
        "why_it_matters": matters,
        "what_to_do": do_here,
        "what_happens_next": next_step,
        "aliases": list(aliases),
        "actions": [
            {"label": action, "description": description, "destination": destination}
            for action, description, destination in actions
        ],
    }


SURFACES: Dict[str, Dict[str, Any]] = {
    "dashboard": _surface("Dashboard", "Start", "Shows the novel's current health, production milestone, recent progress, and highest-value next action.", "It gives you one place to decide what deserves attention before opening a specialist workspace.", "Review the current milestone and choose the recommended next action.", "NovelForge opens the relevant workspace and re-evaluates progress after your next approved change.", aliases=("home", "project dashboard"), actions=(("Run a project cycle", "Ask the configured story team to advance the current planning work.", "dashboard"), ("Review Story Health", "Inspect the evidence behind the current health score.", "story-health"))),
    "guide": _surface("Creation Guide", "Start", "Guides the novel from initial concept through publication readiness.", "Its steps and milestones reveal what is complete and what information is still missing.", "Open the current incomplete step or inspect a milestone's blockers.", "Completing approved project knowledge updates the guide automatically.", aliases=("novel creation guide", "production pipeline", "narrative completeness"), actions=(("Continue the guide", "Open the highest-priority incomplete step.", "guide"),)),
    "vision": _surface("Story Vision", "Start", "Defines the premise, audience, genre, themes, inspirations, and narrative goals.", "The rest of the platform uses this foundation to judge whether characters, arcs, and revisions serve the intended novel.", "Clarify the story promise and the experience you want readers to have.", "Character and world design can be evaluated against a stable creative direction.", aliases=("premise", "genre", "story concept"), actions=(("Edit Story Vision", "Update the project foundation.", "vision"),)),
    "questions": _surface("Questions", "Start", "Collects decisions that the story team cannot safely assume.", "Your answers become reusable project knowledge and may create Canon Proposals when they affect official truth.", "Answer, discuss, or use a suggested answer after reviewing it.", "The Story Bible and dependent guidance refresh without asking the same question again.", aliases=("clarifying questions",), actions=(("Answer open questions", "Resolve missing story decisions.", "questions"),)),
    "characters": _surface("Character Intelligence", "Design", "Tracks character identity, motivation, emotional progression, relationships, presence, and consistency.", "Long novels feel coherent when character choices grow from established wants, beliefs, and experiences.", "Review incomplete motivations, arc movement, relationship evidence, and character warnings.", "Approved changes update the Story Bible, Knowledge Graph, and Story Health.", aliases=("characters", "character journey", "character design"), actions=(("Review characters", "Open character evidence and development.", "characters"),)),
    "world": _surface("World", "Design", "Collects locations, history, cultures, religions, rules, and other world foundations.", "Clear world rules prevent later canon conflicts and make consequences believable.", "Define the places and rules required by the current story.", "World knowledge becomes available to Canon, the Story Bible, and future planning.", aliases=("worldbuilding", "locations"), actions=(("Continue worldbuilding", "Fill the highest-priority world gap.", "world"),)),
    "power": _surface("Power System", "Design", "Defines capabilities, ranks, costs, limits, resources, and progression—or records that no power system is needed.", "Explicit limits protect tension and prevent convenient solutions.", "Describe what power can do, what it costs, and what it cannot do.", "Canon and continuity checks can validate later uses of power.", aliases=("magic system", "abilities"), actions=(("Define power rules", "Record capabilities, limits, and costs.", "power"),)),
    "factions": _surface("Factions", "Design", "Tracks organizations, leaders, goals, alliances, enemies, influence, and secrets.", "Organizations make political and social pressure consistent across a long manuscript.", "Define the groups that can change character choices or plot outcomes.", "Relationships and the Knowledge Graph connect each faction to the wider story.", aliases=("organizations",), actions=(("Review factions", "Inspect organization goals and influence.", "factions"),)),
    "relationships": _surface("Relationships", "Design", "Shows how characters and organizations are connected and how those bonds evolve.", "Relationship changes carry emotional stakes and explain shifts in trust, conflict, and loyalty.", "Inspect important bonds, missing connections, and planned payoffs.", "Character Intelligence and the Knowledge Graph reuse the approved relationship state.", aliases=("relationship graph",), actions=(("Review relationships", "Open the relationship workspace.", "relationships"),)),
    "themes": _surface("Themes", "Design", "Tracks themes, motifs, symbols, and intended thematic payoffs.", "A visible thematic through-line helps revision strengthen meaning without forcing it into every scene.", "Connect themes to characters, arcs, motifs, and payoffs.", "Narrative review can evaluate balance and repetition against the intended themes.", aliases=("motifs", "symbols"), actions=(("Review themes", "Inspect the novel's thematic framework.", "themes"),)),
    "arcs": _surface("Arc Board", "Structure", "Organizes story arcs by development status and planned chapter range.", "Arcs turn a large novel into manageable units with visible progression and ownership.", "Move from a rough arc idea to an active, developed arc.", "Arc Development exposes dependencies, maturity, chapter plans, and drafting readiness.", aliases=("arc board", "story arcs"), actions=(("Develop an arc", "Open detailed arc planning.", "arc-development"),)),
    "arc-development": _surface("Arc Development", "Structure", "Brings an arc's readiness, dependencies, chapters, scenes, character movement, clues, and artifacts together.", "It prevents drafting an arc whose required setup or story knowledge is still missing.", "Resolve blockers, approve plans, and verify drafting eligibility.", "Eligible scenes and chapters become available in Drafting.", aliases=("arc workspace", "arc maturity"), actions=(("Review arc readiness", "Inspect the selected arc's blockers.", "arc-development"), ("Open Drafting", "Draft an eligible scene or chapter.", "drafting"))),
    "threads": _surface("Plot Threads", "Structure", "Tracks promises, mysteries, foreshadowing, callbacks, unresolved arcs, and abandoned storylines.", "Readers expect meaningful setups to develop and resolve.", "Review each thread's introduction, development, references, and resolution status.", "Resolving or intentionally deferring a thread updates Story Health.", aliases=("plot thread intelligence", "dangling threads"), actions=(("Review plot threads", "Inspect unresolved and abandoned threads.", "threads"),)),
    "mysteries": _surface("Mysteries", "Structure", "Tracks each mystery's question, truth, clues, reveal plan, and resolution status.", "Mysteries need enough development to feel fair and a clear payoff to feel satisfying.", "Check unresolved mysteries, clue coverage, and reveal timing.", "Resolved mysteries update Plot Thread Intelligence and Story Health.", aliases=("unresolved mysteries", "mystery registry"), actions=(("Review mysteries", "Open mystery setup and payoff status.", "mysteries"),)),
    "timeline": _surface("Story Timeline", "Structure", "Shows the chronology inside the novel: events, order, dependencies, gaps, and character knowledge boundaries.", "A consistent story chronology prevents impossible travel, missing transitions, and premature knowledge.", "Review chronology warnings and the events connected to them.", "Approved timeline changes refresh Story Health and Character Intelligence.", aliases=("story chronology", "timeline intelligence"), actions=(("Review Story Timeline", "Inspect the novel's internal chronology.", "timeline"),)),
    "readiness": _surface("Readiness", "Structure", "Explains whether arcs and the whole project have enough approved information for the next production stage.", "Readiness prevents expensive drafting or revision work from starting with unresolved foundations.", "Inspect blockers and navigate to the system that owns each missing requirement.", "Clearing blockers advances the corresponding milestone automatically.", aliases=("publication readiness", "draft readiness"), actions=(("Review blockers", "Open readiness evidence and missing work.", "readiness"),)),
    "drafting": _surface("Drafting", "Write and revise", "Guides each scene through Plan, Generate, Review, Revise, Approve and Continue Writing.", "Drafting reuses your characters, canon, timeline, relationships, themes and approved decisions, while every alternative remains reversible.", "Choose the current scene and generate a draft. If planning checks remain, create a clearly labeled exploratory version or open the exact blockers.", "Reviewed and approved scenes become available for chapter assembly; no generated alternative replaces author prose automatically.", aliases=("continue writing", "write", "paragraph drafting", "writing desk"), actions=(("Continue writing", "Open the current scene and next writing action.", "drafting"), ("Review planning checks", "Inspect anything protecting final scene approval.", "arc-development"))),
    "editorial": _surface("Editorial", "Write and revise", "Runs Development, Line, Copy, Style, Continuity, Dialogue, Emotion, Description, Consistency and Grammar passes as protected alternatives.", "Evidence-backed revision helps you improve the reading experience while keeping the source draft unchanged.", "Review a draft, choose a focused pass, compare the proposal, approve it, then deliberately use it as a new draft version.", "The promoted version returns to Drafting for final validation and author approval.", aliases=("revision", "developmental editor", "dialogue coach", "revision pass"), actions=(("Open Editorial", "Review drafts and protected revision alternatives.", "editorial"),)),
    "manuscript": _surface("Manuscript", "Write and revise", "Assembles approved chapter versions into a governed book-level manuscript and creates publication files.", "A controlled manuscript preserves version history and validates the exact text intended for publication.", "Assemble, validate, approve, then run Publication Preflight and export the approved version.", "NovelForge creates Markdown, text, HTML, DOCX, EPUB, PDF, and a provenance package from the approved manuscript only.", aliases=("book", "publication", "publish", "export novel", "publication export"), actions=(("Review manuscript", "Open manuscript versions, validation, and publication export.", "manuscript"),)),
    "story-health": _surface("Story Health", "Understand", "Summarizes character, canon, timeline, plot, pacing, continuity, and balance evidence.", "It helps you prioritize structural problems across a long novel instead of reviewing chapters at random.", "Open a finding, read why it matters, and follow its recommended destination.", "After an approved change, Story Health records and explains the score movement.", aliases=("health score", "story health dashboard"), actions=(("Review findings", "Inspect evidence behind the current score.", "story-health"),)),
    "knowledge": _surface("Story Bible", "Understand", "Presents approved characters, world knowledge, terminology, relationships, and canon in one reference.", "A shared reference keeps authors and AI collaborators aligned on the same approved story truth.", "Browse approved knowledge and follow sources to the owning workspace.", "Approved Canon or Shared Narrative Context changes refresh the Story Bible.", aliases=("knowledge", "knowledge layers"), actions=(("Open Story Bible", "Browse approved project knowledge.", "knowledge"),)),
    "knowledge-graph": _surface("Knowledge Graph", "Understand", "Visualizes important story entities and their relationships using the existing Narrative Analysis graph.", "Connections reveal how a change to one entity can affect chapters, canon, timelines, and Story Health.", "Search for an entity, inspect its card, and expand only the relationships you need.", "Use Explain or Open to move from a connection to its evidence or owning workspace.", aliases=("graph", "story graph"), actions=(("Explore the graph", "Search and inspect story relationships.", "knowledge-graph"),)),
    "insights": _surface("AI Insights", "Understand", "Collects current high-level observations and suggested improvements from the story team.", "It provides a broad review before you choose a specialist workspace for evidence and action.", "Review each suggestion and open its responsible workspace.", "No suggestion changes the novel until you approve the relevant work.", aliases=("insights", "ai review"), actions=(("Review Story Health", "Inspect scored evidence for the insights.", "story-health"),)),
    "canon": _surface("Canon", "Govern", "Lets you browse, search, inspect, compare, activate, deactivate, and propose edits to official story facts.", "Canon is the novel's governed source of truth; every change keeps evidence and approval history.", "Inspect official facts or open the Canon Queue to review pending proposals.", "Approval updates the Story Bible and triggers fresh Narrative Analysis; rejection leaves official canon unchanged.", aliases=("canon explorer", "canon governance"), actions=(("Browse official canon", "Inspect active and inactive facts.", "canon"), ("Review Canon Queue", "Approve or reject proposed facts.", "canon-queue"))),
    "canon-queue": _surface("Canon Queue", "Govern", "Shows proposed story facts that are waiting for an author decision.", "AI suggestions and high-confidence author statements cannot silently become official canon.", "Review evidence and downstream impact, then approve or reject each proposal.", "Approval updates the Canon registry and Story Bible; rejection preserves the decision history without changing truth.", aliases=("canon proposals", "approve canon", "proposal queue"), actions=(("Review proposals", "Open the pending Canon Queue.", "canon-queue"),)),
    "discussion": _surface("Discussion Room", "Govern", "Preserves proposals, reasoning, concerns, and author decisions from the project story team.", "It gives the author a visible approval boundary instead of allowing agent ideas to become decisions automatically.", "Approve, reject, modify, discuss, or expand a proposal.", "Approved decisions become reusable project knowledge and refresh dependent guidance.", aliases=("writers room",), actions=(("Review discussions", "Inspect pending story-team proposals.", "discussion"),)),
    "workflow": _surface("Project Activity", "Govern", "Shows what the story team is doing, what completed, and where work stopped.", "Long AI tasks are easier to trust when progress and outcomes are visible.", "Review the current task and open its result or recovery action.", "Completed work appears in the Project Timeline and refreshes the relevant workspace.", aliases=("workflow", "run cycle", "background analysis", "agents"), actions=(("Run a project cycle", "Advance the current planning workflow.", "dashboard"), ("View Project Timeline", "Review completed project activity.", "project-timeline"))),
    "story-room": _surface("Story Room", "Govern", "Shows the current team, active cycle, discussion state, and project-level coordination.", "It helps you understand who is contributing and which decisions still need author attention.", "Review active work and intervene when the story team asks for a decision.", "Approved outcomes flow to the owning project systems.", aliases=("story team",), actions=(("Open Discussion Room", "Review proposals and decisions.", "discussion"),)),
    "project-timeline": _surface("Project Timeline", "Review", "Shows how the NovelForge project evolved over time, separate from events inside the story.", "It makes milestones, approvals, health movement, and AI work auditable and replayable.", "Filter events or select an entry to replay its project-state summary.", "Use the linked action to open the affected workspace.", aliases=("project history", "project evolution"), actions=(("View project evolution", "Open the Project Timeline.", "project-timeline"),)),
    "explainability-timeline": _surface("Story Health History", "Review", "Explains how Story Health and its categories changed between analysis runs.", "A score is useful only when the author can see what improved, what declined, and why.", "Compare runs and open the findings responsible for each change.", "The next analysis adds another evidence-backed change entry.", aliases=("explainability timeline", "score history", "health history"), actions=(("Review score changes", "Open Story Health History.", "explainability-timeline"),)),
    "settings": _surface("Settings", "Configure", "Connects AI providers and controls how NovelForge runs its story team.", "A verified provider lets the platform perform real AI work while keeping credentials protected.", "Connect and test a provider. Open Developer Mode only when advanced routing or diagnostics are needed.", "Verified models become available to project cycles and specialist agents.", aliases=("ai settings", "configuration", "developer mode"), actions=(("Open Settings", "Configure AI access and application preferences.", "settings"),)),
}


WORKFLOWS = {
    "run-cycle": {
        "label": "Run Cycle",
        "summary": "Runs the configured story-team agents for the project's current planning needs.",
        "before": "NovelForge checks the current milestone, approved context, agent settings, and cost limits.",
        "after": "Results appear in Discussion Room, Project Activity, relevant planning workspaces, and the Project Timeline. Nothing becomes approved canon without the author workflow.",
        "destination": "dashboard",
        "aliases": ["run cycle", "cycle", "story team run"],
    },
    "canon-approval": {
        "label": "Canon approval",
        "summary": "Moves a reviewed proposal into official canon only after author approval.",
        "before": "The queue shows confidence, evidence, affected locations, and downstream risk.",
        "after": "Approval updates Canon and the Story Bible, then refreshes Narrative Analysis and Story Health.",
        "destination": "canon-queue",
        "aliases": ["approve canon", "reject canon", "canon queue"],
    },
    "background-analysis": {
        "label": "Background analysis",
        "summary": "Refreshes reusable Story Intelligence after approved project changes.",
        "before": "NovelForge identifies only the changed story sources.",
        "after": "Health, timelines, characters, plot threads, the graph, and guidance reuse the refreshed analysis.",
        "destination": "workflow",
        "aliases": ["background task", "analysis job", "recompute"],
    },
    "publication-export": {
        "label": "Publication export",
        "summary": "Creates reader and production files from the current approved manuscript version.",
        "before": "NovelForge checks manuscript approval and validation, then reports remaining Story Health and canon warnings without silently changing the book.",
        "after": "You can download Markdown, text, HTML, DOCX, EPUB, PDF, or a complete package containing every format and a provenance manifest.",
        "destination": "manuscript",
        "aliases": ["how do i publish", "publish my novel", "publication export", "export my book", "export novel"],
    },
    "project-lifecycle": {
        "label": "Project archive, Trash, and restore",
        "summary": "Keeps inactive projects out of the active list without immediately erasing their story data.",
        "before": "Archive is for completed or paused work. Trash is recoverable. Permanent deletion requires opening Trash and typing the project title.",
        "after": "Archived and trashed projects remain visible in their own tabs on the Projects screen, where they can be returned to Active or restored.",
        "destination": "dashboard",
        "aliases": ["archive project", "restore project", "restore a deleted project", "delete project", "trash project", "permanently delete"],
    },
}


SHORTCUTS = [
    {"keys": "Ctrl/Cmd+K", "action": "Open the writing command palette", "where": "Paragraph Editor"},
    {"keys": "Ctrl/Cmd+S", "action": "Save a named prose version", "where": "Paragraph Editor"},
    {"keys": "Escape", "action": "Close the command palette or active dialog", "where": "Dialogs and Paragraph Editor"},
    {"keys": "Arrow Left / Arrow Right", "action": "Move between paragraphs", "where": "Paragraph Editor command palette"},
    {"keys": "Ctrl/Cmd+Alt+Shift+D", "action": "Toggle writing diagnostics", "where": "Paragraph Editor Developer Mode"},
]

WORKFLOW_GROUPS = {
    "Shape the Story": [
        "vision", "questions", "characters", "world", "relationships", "arcs", "timeline",
    ],
    "Write the Story": ["drafting", "editorial"],
    "Keep It Consistent": ["story-health", "knowledge", "canon"],
    "Finish the Book": ["manuscript"],
    # These remain fully supported, but are inspection, specialist, governance,
    # or diagnostic surfaces rather than steps every author must visit.
    "More Tools": [
        "guide", "arc-development", "power", "factions", "themes", "threads", "mysteries",
        "readiness", "story-room", "discussion", "insights", "knowledge-graph", "canon-queue",
        "workflow", "project-timeline", "explainability-timeline", "settings",
    ],
}


class ApplicationKnowledgeService:
    @property
    def valid_destinations(self) -> set[str]:
        return set(SURFACES)

    def catalog(self) -> Dict[str, Any]:
        groups = {
            label: [surface_id for surface_id in surface_ids if surface_id in SURFACES]
            for label, surface_ids in WORKFLOW_GROUPS.items()
        }
        return {"surfaces": SURFACES, "groups": groups, "workflows": WORKFLOWS, "shortcuts": SHORTCUTS}

    def surface(self, surface_id: str) -> Dict[str, Any]:
        normalized = surface_id.strip().lower()
        if normalized == "editor":
            normalized = "drafting"
        item = SURFACES.get(normalized)
        if not item:
            raise ValueError("Application destination not found")
        return {"surface_id": normalized, **item}

    def _matches(self, query: str) -> list[tuple[int, str, Dict[str, Any]]]:
        text = " ".join(query.lower().split())
        tokens = set(re.findall(r"[a-z0-9]+", text))
        matches: list[tuple[int, str, Dict[str, Any]]] = []
        for surface_id, item in SURFACES.items():
            phrases = [surface_id.replace("-", " "), item["label"].lower(), *item["aliases"]]
            score = max((8 if phrase in text else len(tokens & set(re.findall(r"[a-z0-9]+", phrase)))) for phrase in phrases)
            if score:
                matches.append((score, surface_id, item))
        return sorted(matches, key=lambda value: (-value[0], value[2]["label"]))

    def classify(self, query: str, active_surface: str = "dashboard") -> str:
        text = " ".join(query.lower().split())
        application_patterns = (
            "what does", "what is", "how does", "how do i", "where do i", "where is",
            "what happens if", "explain this page", "why am i here", "this button",
            "this page", "how can i", "keyboard shortcut", "run cycle", "canon queue",
        )
        progress_patterns = ("what should i do next", "what next", "where should i start")
        project_patterns = (
            "why is story health", "why is my", "which chapter", "unresolved", "inconsistent",
            "plot hole", "my character", "my story", "chapter ", "scene ", "warning #",
            "summarize character", "motivation", "dialogue", "emotional", "relationship evolution",
            "mystery", "foreshadow", "canon conflict", "timeline warning", "pacing problem",
        )
        if any(pattern in text for pattern in progress_patterns):
            return "combined"
        has_application = any(pattern in text for pattern in application_patterns) or bool(self._matches(query))
        has_project = any(pattern in text for pattern in project_patterns)
        if has_project:
            if has_application and any(marker in text for marker in ("where", "how do i", "which page", "open ")):
                return "combined"
            return "project"
        if has_application:
            return "application"
        return "project"

    def answer(self, query: str, active_surface: str = "dashboard") -> Dict[str, Any]:
        text = " ".join(query.lower().split())
        workflow = next((item for item in WORKFLOWS.values() if any(alias in text for alias in item["aliases"])), None)
        if workflow:
            return {
                "answer": f"{workflow['label']} {workflow['summary']} {workflow['before']} {workflow['after']}",
                "surface": self.surface(workflow["destination"]),
                "navigation_actions": [{"type": "navigate", "section": workflow["destination"], "target": workflow["destination"], "label": f"Open {SURFACES[workflow['destination']]['label']}"}],
            }
        matches = self._matches(query)
        surface_id = matches[0][1] if matches else (active_surface if active_surface in SURFACES else "dashboard")
        surface = self.surface(surface_id)
        answer = (
            f"{surface['label']} {surface['purpose']} {surface['why_it_matters']} "
            f"What to do here: {surface['what_to_do']} What happens next: {surface['what_happens_next']}"
        )
        actions = [{"type": "navigate", "target": surface_id, "section": surface_id, "label": f"Open {surface['label']}"}] + [
            {"type": "navigate", "target": action["destination"], "section": action["destination"], "label": action["label"]}
            for action in surface["actions"]
            if action["destination"] != surface_id
        ]
        return {"answer": answer, "surface": surface, "navigation_actions": actions}


application_knowledge_service = ApplicationKnowledgeService()
