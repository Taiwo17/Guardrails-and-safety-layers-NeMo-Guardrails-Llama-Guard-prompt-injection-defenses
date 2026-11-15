import os
import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

async def generate_response(message: str) -> str:
    """
    Send a user message to Ollama and return the model response
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "stream": False
    }


    async with httpx.AsyncClient(timeout=360.0) as client:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()

        result = response.json()

        # First method
        # return result["message"]["content"]

        # Using second method for decomposition
        message_data = result.get("message")

        if not message_data:
            raise ValueError(f"Ollama response has no message field: {result}")

        content = message_data.get("content")
        if not isinstance(content, str):
            raise ValueError(f"Expected string content, received: {content!r}")

        return content
