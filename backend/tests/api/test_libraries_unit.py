import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_libraries_mock(mock_client: AsyncClient, mock_db):
    """
    Test GET /api/libraries using mocked database.
    Because we mocked `get_current_user` to return `test_user`, the API thinks we are logged in.
    """
    # Simulate DB returning empty list of libraries for this user
    mock_db.execute.return_value.scalars().all.return_value = []
    
    response = await mock_client.get("/api/libraries/")
    
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_create_library_mock(mock_client: AsyncClient, mock_db):
    """
    Test POST /api/libraries using mocked database.
    """
    response = await mock_client.post(
        "/api/libraries/",
        json={"name": "Mocked Library", "description": "This is a mock"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Mocked Library"
    assert data["description"] == "This is a mock"
    
    # Verify DB operations
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
