"""Integration tests for ThreatRecall API.

Tests full request/response cycles with real MemoryManager.
Per GOV-011: Integration tests verify component interaction.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure src is in path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from threatrecall_api.main import app
from threatrecall_api.core.config import settings
from threatrecall_api.core.tenant_storage import get_tenant_storage_path


@pytest.fixture
def test_client():
    """Create a test client with isolated temp directory."""
    # Create temp data directory
    temp_dir = tempfile.mkdtemp(prefix="threatrecall_integration_")
    
    # Override settings
    original_data_dir = settings.data_dir
    settings.data_dir = Path(temp_dir)
    
    # Clear MemoryManager cache to ensure isolation between tests
    import threatrecall_api.core.tenant_storage as ts
    ts._managers.clear()
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup
    settings.data_dir = original_data_dir
    ts._managers.clear()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_tenant(test_client):
    """Create a test tenant and return credentials."""
    response = test_client.post(
        "/admin/tenants",
        json={
            "tenant_id": "integration-test",
            "tenant_name": "Integration Test Tenant",
            "contact_email": "test@example.com"
        }
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "tenant_id": data["data"]["tenant_id"],
        "api_key": data["data"]["api_key"]
    }


class TestTenantLifecycle:
    """Test tenant creation, rotation, and deletion workflows."""
    
    def test_create_tenant_success(self, test_client):
        """Tenant creation returns proper credentials."""
        response = test_client.post(
            "/admin/tenants",
            json={
                "tenant_id": "test-tenant-1",
                "tenant_name": "Test Tenant",
                "contact_email": "admin@test.com"
            }
        )
        assert response.status_code == 201
        data = response.json()
        
        assert data["data"]["tenant_id"] == "test-tenant-1"
        assert data["data"]["tenant_name"] == "Test Tenant"
        assert data["data"]["api_key"].startswith("tr_live_")
        assert "created_at" in data["data"]
        assert "storage_path" in data["data"]
    
    def test_create_duplicate_tenant_fails(self, test_client, test_tenant):
        """Creating duplicate tenant returns 409."""
        response = test_client.post(
            "/admin/tenants",
            json={
                "tenant_id": test_tenant["tenant_id"],
                "tenant_name": "Duplicate",
                "contact_email": "dup@test.com"
            }
        )
        assert response.status_code == 409
        json_resp = response.json()
        assert "detail" in json_resp
        assert "already exists" in json_resp["detail"]["error"]["message"].lower()
    
    def test_key_rotation(self, test_client, test_tenant):
        """Key rotation generates new API key."""
        old_key = test_tenant["api_key"]
        
        response = test_client.post(
            f"/admin/tenants/{test_tenant['tenant_id']}/rotate-key",
            json={"reason": "test rotation"}
        )
        assert response.status_code == 200
        
        new_key = response.json()["data"]["new_api_key"]
        assert new_key != old_key
        assert new_key.startswith("tr_live_")
        
        # Old key should no longer work
        old_auth_response = test_client.post(
            f"/api/v1/{test_tenant['tenant_id']}/remember",
            headers={"Authorization": f"Bearer {old_key}"},
            json={"content": "test"}
        )
        assert old_auth_response.status_code == 401
        
        # New key should work
        new_auth_response = test_client.post(
            f"/api/v1/{test_tenant['tenant_id']}/remember",
            headers={"Authorization": f"Bearer {new_key}"},
            json={"content": "test"}
        )
        assert new_auth_response.status_code == 201


class TestMemoryOperations:
    """Test remember/recall/note retrieval with real MemoryManager."""
    
    def test_remember_and_recall_roundtrip(self, test_client, test_tenant):
        """Store note and retrieve via search."""
        tenant_id = test_tenant["tenant_id"]
        api_key = test_tenant["api_key"]
        
        # Store a note
        content = "APT29 using PowerShell remoting for lateral movement"
        response = test_client.post(
            f"/api/v1/{tenant_id}/remember",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "content": content,
                "metadata": {
                    "source": "CISA Alert AA24-038A",
                    "tlp": "TLP:AMBER"
                }
            }
        )
        assert response.status_code == 201
        note_id = response.json()["data"]["note_id"]
        
        # Recall via search
        response = test_client.post(
            f"/api/v1/{tenant_id}/recall",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "query": "APT29 lateral movement",
                "options": {"limit": 5}
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find our note
        note_ids = [n["note_id"] for n in data["data"]]
        assert note_id in note_ids
    
    def test_remember_deduplication(self, test_client, test_tenant):
        """Duplicate content returns 409 conflict."""
        tenant_id = test_tenant["tenant_id"]
        api_key = test_tenant["api_key"]
        
        content = "Unique test content for deduplication"
        
        # First store
        response1 = test_client.post(
            f"/api/v1/{tenant_id}/remember",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"content": content}
        )
        assert response1.status_code == 201
        
        # Second store (duplicate)
        response2 = test_client.post(
            f"/api/v1/{tenant_id}/remember",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"content": content}
        )
        assert response2.status_code == 409
        json_resp = response2.json()
        assert "detail" in json_resp
        assert "duplicate" in json_resp["detail"]["error"]["message"].lower()
    
    def test_recall_with_entity_extraction(self, test_client, test_tenant):
        """Notes include extracted entities."""
        tenant_id = test_tenant["tenant_id"]
        api_key = test_tenant["api_key"]
        
        # Store note with clear entities
        response = test_client.post(
            f"/api/v1/{tenant_id}/remember",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "content": "CVE-2024-1234 is being exploited by APT28 targeting Microsoft Exchange",
                "options": {"extract_entities": True}
            }
        )
        assert response.status_code == 201
        data = response.json()["data"]
        
        # Should have extracted entities
        assert len(data["entities"]) > 0
        entity_names = [e["name"] for e in data["entities"]]
        assert "CVE-2024-1234" in entity_names or "APT28" in entity_names
    
    def test_get_note_by_id(self, test_client, test_tenant):
        """Retrieve specific note by ID."""
        tenant_id = test_tenant["tenant_id"]
        api_key = test_tenant["api_key"]
        
        # Store note
        response = test_client.post(
            f"/api/v1/{tenant_id}/remember",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"content": "Test note for retrieval by ID"}
        )
        note_id = response.json()["data"]["note_id"]
        
        # Retrieve by ID
        response = test_client.get(
            f"/api/v1/{tenant_id}/notes/{note_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["note_id"] == note_id
        assert data["content"] == "Test note for retrieval by ID"
    
    def test_list_notes_pagination(self, test_client, test_tenant):
        """Pagination works for note listing."""
        tenant_id = test_tenant["tenant_id"]
        api_key = test_tenant["api_key"]
        
        # Store multiple notes
        for i in range(5):
            test_client.post(
                f"/api/v1/{tenant_id}/remember",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"content": f"Test note {i}"}
            )
        
        # List with limit
        response = test_client.get(
            f"/api/v1/{tenant_id}/notes?limit=2",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 2
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        
        # Get next page
        cursor = data["pagination"]["cursor"]
        response2 = test_client.get(
            f"/api/v1/{tenant_id}/notes?limit=2&cursor={cursor}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response2.status_code == 200
        assert len(response2.json()["data"]) == 2


class TestAuthentication:
    """Test authentication and authorization flows."""
    
    def test_missing_auth_header(self, test_client, test_tenant):
        """Request without auth returns 401."""
        response = test_client.post(
            f"/api/v1/{test_tenant['tenant_id']}/remember",
            json={"content": "test"}
        )
        assert response.status_code == 401
    
    def test_invalid_token(self, test_client, test_tenant):
        """Invalid token returns 401."""
        response = test_client.post(
            f"/api/v1/{test_tenant['tenant_id']}/remember",
            headers={"Authorization": "Bearer invalid_token"},
            json={"content": "test"}
        )
        assert response.status_code == 401
    
    def test_wrong_tenant_token(self, test_client):
        """Token from tenant A cannot access tenant B."""
        # Create two tenants
        resp1 = test_client.post(
            "/admin/tenants",
            json={"tenant_id": "tenant-a", "tenant_name": "A"}
        )
        resp2 = test_client.post(
            "/admin/tenants",
            json={"tenant_id": "tenant-b", "tenant_name": "B"}
        )
        
        key_a = resp1.json()["data"]["api_key"]
        
        # Try to use tenant A's key on tenant B
        response = test_client.post(
            "/api/v1/tenant-b/remember",
            headers={"Authorization": f"Bearer {key_a}"},
            json={"content": "test"}
        )
        assert response.status_code == 401


class TestHealthMonitoring:
    """Test health check endpoints."""
    
    def test_root_health_no_auth(self, test_client):
        """Root health requires no authentication."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_tenant_health_reflects_state(self, test_client, test_tenant):
        """Tenant health shows actual note count."""
        tenant_id = test_tenant["tenant_id"]
        api_key = test_tenant["api_key"]
        
        # Check initial state
        response = test_client.get(f"/api/v1/{tenant_id}/health")
        assert response.status_code == 200
        initial_count = response.json()["data"]["metrics"]["note_count"]
        
        # Add a note
        test_client.post(
            f"/api/v1/{tenant_id}/remember",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"content": "Health check test note"}
        )
        
        # Check updated state
        response = test_client.get(f"/api/v1/{tenant_id}/health")
        updated_count = response.json()["data"]["metrics"]["note_count"]
        assert updated_count == initial_count + 1


class TestErrorHandling:
    """Test error responses conform to GOV-005."""
    
    def test_validation_error_structure(self, test_client, test_tenant):
        """Validation errors follow standard envelope."""
        response = test_client.post(
            f"/api/v1/{test_tenant['tenant_id']}/remember",
            headers={"Authorization": f"Bearer {test_tenant['api_key']}"},
            json={"invalid_field": "value"}  # Missing required 'content'
        )
        assert response.status_code == 400
        
        error = response.json()["error"]
        assert "code" in error
        assert "message" in error
        assert "request_id" in error
    
    def test_not_found_error_structure(self, test_client, test_tenant):
        """404 errors follow standard envelope."""
        response = test_client.get(
            f"/api/v1/{test_tenant['tenant_id']}/notes/nonexistent-id",
            headers={"Authorization": f"Bearer {test_tenant['api_key']}"}
        )
        assert response.status_code == 404
        
        # FastAPI wraps HTTPException detail
        json_resp = response.json()
        assert "detail" in json_resp
        assert json_resp["detail"]["error"]["code"] == "RESOURCE_NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
