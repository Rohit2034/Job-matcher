from openai import AsyncAzureOpenAI
import asyncio
from src.config.settings import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_CONCURRENCY
)

class AzureOpenAIConnection:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION
        )
        self.semaphore = asyncio.Semaphore(AZURE_CONCURRENCY)

    def get_client(self):
        return self.client

    def get_semaphore(self):
        return self.semaphore