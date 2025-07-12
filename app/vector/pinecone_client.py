import os
from typing import List, Tuple
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from app.config import PINECONE_API_KEY, PINECONE_ENV

class PineconeClient:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PineconeClient, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, index_name="ignite-profiles"):
        if self._initialized:
            return
        self.index_name = index_name
        self.pinecone = None
        self._initialized = True

    def _get_pinecone_instance(self):
        if self.pinecone is None:
            self.pinecone = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            self._create_index_if_not_exists()
        return self.pinecone

    def _create_index_if_not_exists(self):
        index_names = self._get_pinecone_instance().list_indexes().names()
        if self.index_name not in index_names:
            self._get_pinecone_instance().create_index(
                name=self.index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud='aws', region=os.getenv("PINECONE_ENV", "us-east-1"))
            )

    async def upsert_vectors(self, items: List[Tuple[str, np.ndarray]]):
        pinecone_instance = self._get_pinecone_instance()
        index = pinecone_instance.Index(self.index_name)
        vectors_to_upsert = []
        for item_id, vector in items:
            vectors_to_upsert.append({
                "id": item_id,
                "values": vector.tolist()
            })
        if vectors_to_upsert:
            await index.upsert(vectors=vectors_to_upsert)

    async def query(self, top_k: int, vector: np.ndarray) -> List[dict]:
        pinecone_instance = self._get_pinecone_instance()
        index = pinecone_instance.Index(self.index_name)
        results = await index.query(
            vector=vector.tolist(),
            top_k=top_k,
            include_metadata=False  # Only need IDs and scores
        )
        return results['matches']

# Singleton instance
pinecone_client = PineconeClient() 