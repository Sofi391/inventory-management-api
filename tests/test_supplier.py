import pytest
from task_api.models import Supplier

SUPPLIER_URL = "/manage/supplier/"


def detail_url(slug):
    return f"{SUPPLIER_URL}{slug}/"


VALID_PAYLOAD = {
    "name": "New Supplier",
    "email": "new@supplier.com",
    "phone": "0911111111",
    "address": "456 Supply Ave",
}


@pytest.mark.django_db
class TestSupplierList:

    def test_list_suppliers_as_manager(self, manager_client, supplier):
        """Manager can retrieve the full list of suppliers."""
        res = manager_client.get(SUPPLIER_URL)
        assert res.status_code == 200

    def test_list_suppliers_as_employee(self, employee_client, supplier):
        """Employee can retrieve the supplier list (read-only access)."""
        res = employee_client.get(SUPPLIER_URL)
        assert res.status_code == 200

    def test_list_suppliers_unauthenticated(self, anon_client):
        """Unauthenticated request to supplier list returns 401."""
        res = anon_client.get(SUPPLIER_URL)
        assert res.status_code == 401


@pytest.mark.django_db
class TestSupplierCreate:

    def test_create_supplier_as_manager(self, manager_client):
        """Manager can create a new supplier and it is persisted in the DB."""
        res = manager_client.post(SUPPLIER_URL, VALID_PAYLOAD)
        assert res.status_code == 201
        assert Supplier.objects.filter(email=VALID_PAYLOAD["email"]).exists()

    def test_create_supplier_as_employee(self, employee_client):
        """Employee cannot create a supplier and gets 403."""
        res = employee_client.post(SUPPLIER_URL, VALID_PAYLOAD)
        assert res.status_code == 403

    def test_create_supplier_unauthenticated(self, anon_client):
        """Unauthenticated create request returns 401."""
        res = anon_client.post(SUPPLIER_URL, VALID_PAYLOAD)
        assert res.status_code == 401

    def test_create_supplier_missing_field(self, manager_client):
        """Create request missing a required field returns 400."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "email"}
        res = manager_client.post(SUPPLIER_URL, payload)
        assert res.status_code == 400


@pytest.mark.django_db
class TestSupplierRetrieve:

    def test_retrieve_supplier_as_manager(self, manager_client, supplier):
        """Manager can retrieve a single supplier by slug."""
        res = manager_client.get(detail_url(supplier.slug))
        assert res.status_code == 200
        assert res.data["name"] == supplier.name

    def test_retrieve_supplier_as_employee(self, employee_client, supplier):
        """Employee can retrieve a single supplier by slug."""
        res = employee_client.get(detail_url(supplier.slug))
        assert res.status_code == 200

    def test_retrieve_nonexistent_supplier(self, manager_client):
        """Retrieve request for a non-existent slug returns 404."""
        res = manager_client.get(detail_url("does-not-exist"))
        assert res.status_code == 404


@pytest.mark.django_db
class TestSupplierUpdate:

    def test_update_supplier_as_manager(self, manager_client, supplier):
        """Manager can fully update a supplier with PUT."""
        payload = {**VALID_PAYLOAD, "name": "Updated Supplier"}
        res = manager_client.put(detail_url(supplier.slug), payload)
        assert res.status_code == 200
        supplier.refresh_from_db()
        assert supplier.name == "Updated Supplier"

    def test_partial_update_supplier_as_manager(self, manager_client, supplier):
        """Manager can partially update a supplier with PATCH."""
        res = manager_client.patch(detail_url(supplier.slug), {"phone": "0922222222"})
        assert res.status_code == 200
        supplier.refresh_from_db()
        assert supplier.phone == "0922222222"

    def test_update_supplier_as_employee(self, employee_client, supplier):
        """Employee cannot update a supplier and gets 403."""
        res = employee_client.put(detail_url(supplier.slug), VALID_PAYLOAD)
        assert res.status_code == 403


@pytest.mark.django_db
class TestSupplierDelete:

    def test_delete_supplier_as_manager(self, manager_client, supplier):
        """Manager can delete a supplier and it is removed from the DB."""
        res = manager_client.delete(detail_url(supplier.slug))
        assert res.status_code == 204
        assert not Supplier.objects.filter(slug=supplier.slug).exists()

    def test_delete_supplier_as_employee(self, employee_client, supplier):
        """Employee cannot delete a supplier and gets 403."""
        res = employee_client.delete(detail_url(supplier.slug))
        assert res.status_code == 403

    def test_delete_nonexistent_supplier(self, manager_client):
        """Delete request for a non-existent slug returns 404."""
        res = manager_client.delete(detail_url("does-not-exist"))
        assert res.status_code == 404
