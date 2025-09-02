from pydantic import BaseModel, HttpUrl
from typing import List

class CrawlRequest(BaseModel):
    url: HttpUrl

class SearchResult(BaseModel):
    url: HttpUrl
    title: str
    summary: str

# --- Models for Query-Based Searching (Updated) ---
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    """The final response, including the AI-generated answer and sources."""
    answer: str
    sources_used: List[HttpUrl]
