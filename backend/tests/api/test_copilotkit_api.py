import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_copilotkit_endpoint_exists(mock_client: AsyncClient):
    """
    Test that the /api/copilotkit endpoint is successfully registered
    by the lifespan event and responds to POST requests.
    """
    # Send an empty or minimal payload to see if the route catches it.
    # We just want to ensure it's not a 404, meaning the route exists.
    payload = {
        "messages": [
            {
                "id": "msg_1",
                "role": "user",
                "content": "Test message",
                "createdAt": "2024-01-01T00:00:00Z"
            }
        ],
        "agent": "assistant",
        "state": {}
    }
    
    response = await mock_client.post("/api/copilotkit", json=payload)
    
    # If the route exists, it will either process it (200) or reject invalid format (400/422).
    # If it returns 404, the route was not registered.
    assert response.status_code != 404, "Endpoint /api/copilotkit was not found"
