from fastapi import status


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["version"] == "v1"
    assert "timestamp" in data
