from google import genai
from app.core.config import settings

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

def test_gemini():
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents="Explain what an RFP is in two sentences."
    )

    return response.text