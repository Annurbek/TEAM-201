from fastapi.testclient import TestClient
from sqlalchemy.orm import configure_mappers

import app.models
from app.db.base import Base
from app.main import app


def test_root_endpoint():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "API is running"}


def test_models_are_registered_and_mappable():
    configure_mappers()

    assert "users" in Base.metadata.tables
    assert "score_history_logs" in Base.metadata.tables
    assert len(Base.metadata.tables) == 22
