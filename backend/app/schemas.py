from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CompanyProfile(BaseModel):
    user_id: str
    company_name: str = ""
    rut: str = ""
    categories: str = ""
    rubros_keywords: str = ""
    keywords_globales: str = ""
    keywords_excluir: str = ""
    margin_min: float = 0.0
    margin_target: float = 0.0
    delivery_days: str = ""
    risk_rules: str = ""

class InventoryItem(BaseModel):
    sku: Optional[str] = None
    name: str
    synonyms: Optional[str] = None
    cost: Optional[float] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    restock_days: Optional[int] = None
    supplier: Optional[str] = None

class InventoryUploadResponse(BaseModel):
    user_id: str
    imported: int

class InventoryMatch(BaseModel):
    required: str
    matches: List[Dict[str, Any]] = Field(default_factory=list)

class AnalyzeResponse(BaseModel):
    filename: str
    extracted_chars: int
    summary: str
    requirements: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    proposal_markdown: str
    # Nuevos: ítems & matches contra inventario
    required_items: List[str] = Field(default_factory=list)
    inventory_matches: List[InventoryMatch] = Field(default_factory=list)
    debug: Dict[str, Any] = Field(default_factory=dict)

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    used_gateway: bool



class ActionRequest(BaseModel):
    user_id: str = Field(..., description="Usuario demo (demo1/demo2/demo3)")
    action: str = Field(..., description="Nombre de acción predefinida")
    payload: Dict[str, Any] = Field(default_factory=dict)

class ActionResponse(BaseModel):
    ok: bool = True
    action: str
    status: str
    result: Dict[str, Any] = Field(default_factory=dict)
    raw: str = ""


class JobSummary(BaseModel):
    id: int
    user_id: str
    action: str
    status: str
    created_at: str
    updated_at: str


class JobDetail(JobSummary):
    payload_json: Optional[str] = None
    result_json: Optional[str] = None
    raw: Optional[str] = None
    error: Optional[str] = None
