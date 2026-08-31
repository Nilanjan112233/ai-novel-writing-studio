from typing import TypedDict, List, Dict, Any, Optional


class StoryState(TypedDict):
    project_id: str
    title: str
    premise: str
    idea_dump: str
    genre: str
    tone: str
    themes: List[str]
    inspirations: List[str]
    character_notes: str
    world_notes: str
    plot_notes: str
    notes: str
    
    # Persistent Timeline Context
    timeline_messages: List[Dict[str, Any]]
    new_messages: List[Dict[str, Any]]
    
    # Previous Artifacts for Revision
    previous_outline: Optional[Dict[str, Any]]
    previous_characters: Optional[List[Dict[str, Any]]]
    previous_world_bible: Optional[Dict[str, Any]]
    
    # Current Cycle Outputs
    cycle_number: int
    outputs: List[Dict[str, Any]]
    ideas: List[str]
    critiques: List[str]
    questions: List[Dict[str, Any]]
    unresolved_questions: List[Dict[str, Any]]
    answers: List[str]
    
    # Structured Artifacts
    outline: Dict[str, Any]
    characters: List[Dict[str, Any]]
    world_bible: Dict[str, Any]
    
    # Workflow Metadata
    current_agent: str
    logs: List[Dict[str, Any]]
    _on_progress: Any  # optional async callback, not persisted
