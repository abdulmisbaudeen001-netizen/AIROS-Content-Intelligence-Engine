"""
AIROS Content Intelligence Engine
Short-Term Memory — current workflow state, in-memory only.
Cleared when the workflow completes or the process restarts.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class WorkflowState:
    """Tracks the live state of one publishing run."""

    workflow_id: str
    window: str                           # morning | afternoon | evening
    started_at: datetime = field(default_factory=datetime.utcnow)

    # Stage outputs — populated as the pipeline advances
    discovered_topics: List[Dict[str, Any]] = field(default_factory=list)
    selected_topic_id: Optional[int] = None
    collected_source_ids: List[int] = field(default_factory=list)
    verified_fact_ids: List[int] = field(default_factory=list)
    draft_id: Optional[int] = None
    seo_id: Optional[int] = None
    published_article_id: Optional[int] = None

    # Control flags
    current_stage: str = "idle"           # trend | source | verify | expand | edit | write | seo | quality | publish | learn
    failed_stages: List[str] = field(default_factory=list)
    retry_count: int = 0
    completed: bool = False
    error: Optional[str] = None


# Global workflow registry — one per concurrent run
_active_workflows: Dict[str, WorkflowState] = {}


def start_workflow(workflow_id: str, window: str) -> WorkflowState:
    state = WorkflowState(workflow_id=workflow_id, window=window)
    _active_workflows[workflow_id] = state
    return state


def get_workflow(workflow_id: str) -> Optional[WorkflowState]:
    return _active_workflows.get(workflow_id)


def update_stage(workflow_id: str, stage: str):
    state = _active_workflows.get(workflow_id)
    if state:
        state.current_stage = stage


def mark_stage_failed(workflow_id: str, stage: str, error: str):
    state = _active_workflows.get(workflow_id)
    if state:
        state.failed_stages.append(stage)
        state.error = error


def complete_workflow(workflow_id: str):
    state = _active_workflows.get(workflow_id)
    if state:
        state.completed = True
        state.current_stage = "done"


def clear_workflow(workflow_id: str):
    _active_workflows.pop(workflow_id, None)


def all_active() -> Dict[str, WorkflowState]:
    return dict(_active_workflows)
