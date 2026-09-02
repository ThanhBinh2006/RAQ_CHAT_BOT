import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_libraries_integration(integration_client: AsyncClient):
    """
    Integration test using a real database (raq_chatbot_test).
    This assumes that the test database is migrated and empty.
    Note: get_current_user is NOT mocked here, so we must register/login first.
    """
    # 1. Register a test user
    import uuid
    email = f"integration_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "password123"
    reg_res = await integration_client.post("/api/auth/register", json={
        "email": email,
        "password": pwd
    })
    assert reg_res.status_code in [201, 409] # Might exist from a previous run if not cleared
    
    # 2. Login
    login_res = await integration_client.post("/api/auth/login", json={
        "email": email,
        "password": pwd
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Create a library
    lib_res = await integration_client.post("/api/libraries", json={
        "name": "Integration Test Library",
        "description": "Integration testing"
    }, headers=headers)
    assert lib_res.status_code == 201
    lib_id = lib_res.json()["id"]
    
    # 4. List libraries
    list_res = await integration_client.get("/api/libraries", headers=headers)
    assert list_res.status_code == 200
    assert any(lib["id"] == lib_id for lib in list_res.json())
