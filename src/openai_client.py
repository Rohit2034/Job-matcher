"""
OpenAI async client wrapper for the Job Matcher project.
Handles initialization and configuration of the OpenAI API client.
Uses Azure OpenAI configuration from environment variables.
"""

import os
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()


# Initialize async Azure OpenAI client
api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

if not all([api_key, endpoint, api_version, deployment]):
    raise ValueError(
        "Missing Azure OpenAI configuration. "
        "Ensure AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
        "AZURE_OPENAI_API_VERSION, and AZURE_OPENAI_DEPLOYMENT_NAME are set in .env"
    )

client = AsyncAzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

# Store deployment name for use in API calls
DEPLOYMENT_NAME = deployment

