import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part, ChatSession
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from USER_REQUEST
PROJECT_ID = 'videograph-ai'
LOCATION = 'us-central1'
# The path to your service account file
KEY_FILE = os.path.join(os.getcwd(), 'videograph-ai-5666b2db80fa.json')

def init_vertex_ai():
    """Initializes Vertex AI with the specified credentials and project."""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(f"Service account file not found at {KEY_FILE}")
    
    creds = service_account.Credentials.from_service_account_file(KEY_FILE)
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=creds)

def get_generative_model(model_name='gemini-2.5-flash', system_instruction=None):
    """
    Returns a configured GenerativeModel instance.
    Defaults to gemini-2.5-flash as requested.
    """
    init_vertex_ai()
    
    return GenerativeModel(
        model_name=model_name,
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
            "top_p": 0.95,
        },
        system_instruction=system_instruction
    )

async def generate_content_simple(prompt, model_name='gemini-2.5-flash'):
    """Usage Pattern: Simple Request (One-off)"""
    model = get_generative_model(model_name)
    response = await model.generate_content_async(prompt)
    return response.text

def start_chat_session(history=None, model_name='gemini-2.5-flash', system_instruction=None):
    """Usage Pattern: Chat Session (Conversational)"""
    model = get_generative_model(model_name, system_instruction=system_instruction)
    return model.start_chat(history=history or [])

# Example usage (commented out):
# if __name__ == "__main__":
#     import asyncio
#     async def test():
#         res = await generate_content_simple("Hello, how are you?")
#         print(res)
#     asyncio.run(test())
