import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIError, RateLimitError
from tenacity import RetryError

from app.llm.openai_client import get_completion


@pytest.mark.asyncio
@patch("app.llm.openai_client.aclient", new_callable=MagicMock)
async def test_get_completion_success(mock_aclient):
    # Configure the mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Test completion"
    mock_aclient.chat.completions.create = AsyncMock(return_value=mock_response)

    # Call the function
    result = await get_completion("test prompt")

    # Assertions
    assert result == "Test completion"
    mock_aclient.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
@patch("app.llm.openai_client.aclient", new_callable=MagicMock)
async def test_get_completion_retry_on_rate_limit_error(mock_aclient):
    # Configure the mock to raise an error on the first call, then succeed
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Successful completion after retry"
    mock_aclient.chat.completions.create.side_effect = [
        RateLimitError(
            "Rate limited",
            response=MagicMock(),
            body={"message": "Rate limit exceeded"},
        ),
        AsyncMock(return_value=mock_response)(),
    ]

    # Call the function
    result = await get_completion("test prompt")

    # Assertions
    assert result == "Successful completion after retry"
    assert mock_aclient.chat.completions.create.call_count == 2


@pytest.mark.asyncio
@patch("app.llm.openai_client.aclient", new_callable=MagicMock)
async def test_get_completion_timeout(mock_aclient):
    # Configure the mock to simulate a timeout
    mock_aclient.chat.completions.create.side_effect = asyncio.TimeoutError

    # Call the function and expect a tenacity.RetryError
    with pytest.raises(RetryError):
        await get_completion("test prompt")

    # Assertions
    assert mock_aclient.chat.completions.create.call_count > 0


@pytest.mark.asyncio
@patch("app.llm.openai_client.aclient", new_callable=MagicMock)
async def test_get_completion_fails_after_max_retries(mock_aclient):
    # Configure the mock to always raise an APIError
    mock_aclient.chat.completions.create.side_effect = APIError(
        "API Error", request=MagicMock(), body=None
    )

    # Call the function and expect a RetryError after retries
    with pytest.raises(RetryError):
        await get_completion("test prompt")

    # Assertions
    assert mock_aclient.chat.completions.create.call_count == 6  # 1 initial + 5 retries 