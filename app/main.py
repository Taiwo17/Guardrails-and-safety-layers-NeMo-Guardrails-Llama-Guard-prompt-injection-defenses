import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


from app.llm import generate_response

logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Guardrails Security Demo", description="A baseline LLM application using FastAPI and Ollama.", version="1.0.0")

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="The message to send to the language model."
    )

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    return {
        "message": "LLM Guardrails Security Demo",
        "status": "running",
        "guardrails_enabled": False
    }

@app.get("/health")
async def health_check():
    return { "status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:
        response = await generate_response(request.message)
        return ChatResponse(response=response)
    
    except Exception as exc:
        logger.exception("Error while communicating with Ollama")    
        raise HTTPException(status_code=502, detail="Unable to generate response from the language model")

