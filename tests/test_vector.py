import pytest
import numpy as np
from unittest.mock import patch, AsyncMock
from app.vector.pinecone_client import PineconeClient

@pytest.mark.asyncio
async def test_upsert_and_query():
    with patch.object(PineconeClient, "upsert_vectors", new_callable=AsyncMock) as mock_upsert, \
         patch.object(PineconeClient, "query", new_callable=AsyncMock) as mock_query:
        
        mock_query.return_value = [{'id': 'test_id', 'score': 1.0}]
        
        client = PineconeClient()
        test_id = "test_vector_1"
        test_vector = np.random.rand(1536)
        
        await client.upsert_vectors([(test_id, test_vector)])
        mock_upsert.assert_called_once()
        
        results = await client.query(top_k=1, vector=test_vector)
        mock_query.assert_called_once()
        
        assert len(results) == 1
        assert results[0]['id'] == 'test_id'

@pytest.mark.asyncio
async def test_query_empty_results():
    with patch.object(PineconeClient, "query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        client = PineconeClient()
        results = await client.query(top_k=5, vector=np.random.rand(1536))
        assert results == []

@pytest.mark.asyncio
async def test_upsert_raises_exception():
    with patch.object(PineconeClient, "upsert_vectors", new_callable=AsyncMock) as mock_upsert:
        mock_upsert.side_effect = Exception("UPSERT FAILED")
        client = PineconeClient()
        with pytest.raises(Exception, match="UPSERT FAILED"):
            await client.upsert_vectors([("id", np.random.rand(1536))]) 