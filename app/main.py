try:
    from pollinations.helpers import version_check
    version_check.get_latest = lambda: None
    print("Successfully applied monkey patch to pollinations.ai.")
except (ImportError, AttributeError):
    # This might happen if the library structure changes in the future.
    # For now, we assume it exists and proceed.
    print("Could not apply patch to pollinations.ai. Proceeding with caution.")


from fastapi import FastAPI, HTTPException
from .model import QueryRequest, QueryResponse
from . import search_client
from . import agent

app = FastAPI(
    title="Multi-Source Research Agent API",
    description="An API that searches the web, scrapes multiple sources, and synthesizes a comprehensive answer.",
    version="4.0.0"
)

@app.post("/query/", response_model=QueryResponse, summary="Get a synthesized answer from multiple web sources")
async def process_query(request: QueryRequest):
    """
    Accepts a search query, finds and scrapes multiple relevant web pages,
    and returns a single, AI-synthesized answer based on all gathered content.
    """
    query = request.query
    print(f"Received query: '{query}'")

    # Step 1: Search and scrape multiple sources.
    # Search as many sites as possible without artificial limits
    scraped_sources = search_client.search_and_scrape_multiple_sources(query)
    print(scraped_sources)
    
    if not scraped_sources:
        raise HTTPException(
            status_code=404, 
            detail="Could not find and scrape any relevant web pages for the query."
        )

    # Step 2: Generate a synthesized answer from the gathered content.
    answer = agent.get_ai_synthesis(query, scraped_sources)
    print(answer)
    if answer == "Could not generate an answer.":
        raise HTTPException(status_code=500, detail="Content was scraped, but the AI agent failed to generate an answer.")
    
    # Step 3: Prepare and return the final response.
    source_urls = [source['url'] for source in scraped_sources]
    print("Successfully generated a synthesized answer.")
    return QueryResponse(answer=answer, sources_used=source_urls)

@app.get("/", summary="Root endpoint")
async def read_root():
    return {"message": "Welcome to the Multi-Source Research Agent API!"}

@app.get("/ping", summary="Health check endpoint")
async def ping():
    return {"status": "ok", "message": "pong"}
