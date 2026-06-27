from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class NoteMetadata(BaseModel):
    filename: str
    title: str
    created: datetime
    modified: datetime
    tags: List[str] = []
    word_count: int = 0
    connections: List[str] = []


class Note(BaseModel):
    filename: str
    title: str
    content: str
    metadata: NoteMetadata


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = datetime.now()


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    connections: List[str] = []


class Connection(BaseModel):
    source: str
    target: str
    similarity: float
    description: str = ""


class AgentStatus(BaseModel):
    connector: str = "idle"
    evolver: str = "idle"
    last_connector_run: Optional[datetime] = None
    last_evolver_run: Optional[datetime] = None


class GraphNode(BaseModel):
    id: str
    label: str
    group: str = "note"
    size: float = 1.0


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 0.5


class BrainGraph(BaseModel):
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
