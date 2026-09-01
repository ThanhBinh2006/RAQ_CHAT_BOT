import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_success(mock_client: AsyncClient, mock_db):
    """Test successful registration using the mocked database."""
    response = await mock_client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "securepassword"}
    )
    
    # mock_db.execute().scalar_one_or_none() defaults to None in our fixture
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    
    # Verify DB was called to check for existing email
    mock_db.execute.assert_called()
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_register_duplicate_email(mock_client: AsyncClient, mock_db):
    """Test registration failure when email already exists."""
    # Setup mock to simulate finding an existing user
    mock_db.execute.return_value.scalar_one_or_none.return_value = "Existing User"
    
    response = await mock_client.post(
        "/api/auth/register",
        json={"email": "existing@example.com", "password": "securepassword"}
    )
    
    assert response.status_code == 409
    assert response.json()["detail"] == "Email đã được đăng ký"

# We won't test login success extensively with simple mocks because 
# verify_password and hash_password require actual hashed data matching the db.
