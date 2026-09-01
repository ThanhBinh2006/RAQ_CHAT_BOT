import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_integration_full_flow(integration_client: AsyncClient):
    """
    Integration test for Auth using the real database.
    Because this hits the real database, the user might persist.
    """
    import uuid
    # Use a unique email to avoid conflicts with previous test runs
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "integration_password123!"

    # 1. Test Register
    reg_res = await integration_client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": pwd}
    )
    assert reg_res.status_code == 201
    
    # 2. Test Register Duplicate (should fail)
    reg_res_dup = await integration_client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": pwd}
    )
    assert reg_res_dup.status_code == 409
    
    # 3. Test Login
    login_res = await integration_client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": pwd}
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # 4. Test Profile Fetch (verify token works)
    token = data["access_token"]
    profile_res = await integration_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["email"] == unique_email
