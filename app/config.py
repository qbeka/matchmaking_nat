from dotenv import load_dotenv
import os

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")

# Define the allowed skills for validation
ALLOWED_SKILLS = [
    "python", "fastapi", "react", "typescript", "aws", "gcp", "azure", 
    "docker", "kubernetes", "sql", "nosql", "machine_learning", "data_analysis"
]

ALLOWED_ROLES = [
    "frontend", "backend", "fullstack", "data_science", "devops", "product_manager", "designer"
]

STAGE_3_WEIGHTS = {
    "skill_gap": 0.35,
    "role_alignment": 0.20,
    "motivation_similarity": 0.15,
    "ambiguity_fit": 0.20,
    "workload_fit": 0.10,
} 