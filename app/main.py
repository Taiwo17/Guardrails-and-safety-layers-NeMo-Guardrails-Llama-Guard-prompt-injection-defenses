import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Reload the app
# uvicorn app.main:app --reload

# Activating the environment
# source .venv/Scripts/activate

# Activate Ollama
# Get-Process ollama* | Stop-Process -Force
# ollama serve

# from app.llm import generate_response -> first one using llm.py
from app.guardrails import generate_guardrailed_response

logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Guardrails Security Demo", description="A FastAPI and Ollama application protected by NeMo Guardrails.", version="1.0.0")

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="The message to send to the language model."
    )

class ChatResponse(BaseModel):
    response: str
    security_decision: str

@app.get("/")
async def root():
    return {
        "message": "LLM Guardrails Security Demo",
        "status": "running",
        "guardrails_enabled": True
    }

@app.get("/health")
async def health_check():
    return { "status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:
        result = await generate_guardrailed_response(request.message)

        logger.info(
            "Request processed with security decision: %s",
            result["security_decision"]
        )

        return ChatResponse(
            response=result["response"],
            security_decision=result["security_decision"]
        )
    except Exception:
       logger.exception("Error while processing request through NeMo")
       raise HTTPException( status_code=502, detail="Unable to process the request.")