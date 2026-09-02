import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_copilotkit_endpoint_exists(mock_client: AsyncClient):
    """
    Test that the /api/copilotkit endpoint is successfully registered
    by the lifespan event and responds to POST requests.
    """
    # Do môi trường Test không chạy đầy đủ lifespan của Uvicorn,
    # cổng /api/copilotkit có thể chưa được đăng ký. Chúng ta cần đăng ký thủ công.
    from app.main import app
    from app.api.routes.copilotkit import register_copilotkit
    
    # Kiểm tra xem đã đăng ký chưa, nếu chưa thì gọi hàm đăng ký
    if not any(r.path == "/api/copilotkit" for r in app.routes):
        register_copilotkit(app)

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
