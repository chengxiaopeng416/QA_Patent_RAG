import os
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("CONNECTION_STRING", "")

qwen_model_name = os.getenv("QWEN_MODEL_NAME", "")
qwen_api_key = os.getenv("QWEN_API_KEY", "")
qwen_base_url = os.getenv("QWEN_BASE_URL", "")
embeddings_model_name = os.getenv("EMBEDDINGS_MODEL_NAME", "")

secret_key = os.getenv("SECRET_KEY", "")
algorithm = os.getenv("ALGORITHM", "HS256")



