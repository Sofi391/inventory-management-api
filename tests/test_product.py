import pytest
from task_api.models import Product

PRODUCT_URL = "/manage/products/"


def detail_url(slug):
    return f"{PRODUCT_URL}{slug}/"


@pytest.fixture
def valid_payload(supplier):
    return {
        "name": "New Product",
        "sku": "SKU-999",
        "category": "Electronics",
        "buying_price": "30.00",
        "selling_price": "60.00",
        "reorder_level": 5,
        "supplier": supplier.slug,
    }


@pytest.mark.django_db
class TestProductList:

    def test_list_products_as_manager(self, manager_client, product):
        """Manager can retrieve the full list of products."""
        res = manager_client.get(PRODUCT_URL)
        assert res.status_code == 200

    def test_list_products_as_employee(self, employee_client, product):
        """Employee can retrieve the product list (read-only access)."""
        res = employee_client.get(PRODUCT_URL)
        assert res.status_code == 200

    def test_list_products_unauthenticated(self, anon_client):
        """Unauthenticated request to product list returns 401."""
        res = anon_client.get(PRODUCT_URL)
        assert res.status_code == 401


@pytest.mark.django_db
class TestProductCreate:

    def test_create_product_as_manager(self, manager_client, valid_payload):
        """Manager can create a new product and it is persisted in the DB."""
        res = manager_client.post(PRODUCT_URL, valid_payload)
        assert res.status_code == 201
        assert Product.objects.filter(sku=valid_payload["sku"]).exists()

    def test_create_product_as_employee(self, employee_client, valid_payload):
        """Employee cannot create a product and gets 403."""
        res = employee_client.post(PRODUCT_URL, valid_payload)
        assert res.status_code == 403

    def test_create_product_unauthenticated(self, anon_client, valid_payload):
        """Unauthenticated create request returns 401."""
        res = anon_client.post(PRODUCT_URL, valid_payload)
        assert res.status_code == 401

    def test_create_product_duplicate_sku(self, manager_client, valid_payload, product):
        """Create request with an already existing SKU returns 400."""
        payload = {**valid_payload, "sku": product.sku}
        res = manager_client.post(PRODUCT_URL, payload)
        assert res.status_code == 400

    def test_create_product_missing_field(self, manager_client, valid_payload):
        """Create request missing a required field returns 400."""
        payload = {k: v for k, v in valid_payload.items() if k != "sku"}
        res = manager_client.post(PRODUCT_URL, payload)
        assert res.status_code == 400


@pytest.mark.django_db
class TestProductRetrieve:

    def test_retrieve_product_as_manager(self, manager_client, product):
        """Manager can retrieve a single product by slug."""
        res = manager_client.get(detail_url(product.slug))
        assert res.status_code == 200
        assert res.data["name"] == product.name

    def test_retrieve_product_as_employee(self, employee_client, product):
        """Employee can retrieve a single product by slug."""
        res = employee_client.get(detail_url(product.slug))
        assert res.status_code == 200

    def test_retrieve_nonexistent_product(self, manager_client):
        """Retrieve request for a non-existent slug returns 404."""
        res = manager_client.get(detail_url("does-not-exist"))
        assert res.status_code == 404


@pytest.mark.django_db
class TestProductUpdate:

    def test_update_product_as_manager(self, manager_client, product, valid_payload):
        """Manager can fully update a product with PUT."""
        payload = {**valid_payload, "name": "Updated Product"}
        res = manager_client.put(detail_url(product.slug), payload)
        assert res.status_code == 200
        product.refresh_from_db()
        assert product.name == "Updated Product"

    def test_partial_update_product_as_manager(self, manager_client, product):
        """Manager can partially update a product's selling price with PATCH."""
        res = manager_client.patch(detail_url(product.slug), {"selling_price": "99.00"})
        assert res.status_code == 200
        product.refresh_from_db()
        assert str(product.selling_price) == "99.00"

    def test_update_product_as_employee(self, employee_client, product, valid_payload):
        """Employee cannot update a product and gets 403."""
        res = employee_client.put(detail_url(product.slug), valid_payload)
        assert res.status_code == 403

    def test_current_stock_is_read_only(self, manager_client, product, valid_payload):
        """current_stock field is read-only and cannot be changed via PUT."""
        payload = {**valid_payload, "current_stock": 9999}
        manager_client.put(detail_url(product.slug), payload)
        product.refresh_from_db()
        assert product.current_stock != 9999


@pytest.mark.django_db
class TestProductDelete:

    def test_delete_product_as_manager(self, manager_client, product):
        """Manager can delete a product and it is removed from the DB."""
        res = manager_client.delete(detail_url(product.slug))
        assert res.status_code == 204
        assert not Product.objects.filter(slug=product.slug).exists()

    def test_delete_product_as_employee(self, employee_client, product):
        """Employee cannot delete a product and gets 403."""
        res = employee_client.delete(detail_url(product.slug))
        assert res.status_code == 403

    def test_delete_nonexistent_product(self, manager_client):
        """Delete request for a non-existent slug returns 404."""
        res = manager_client.delete(detail_url("does-not-exist"))
        assert res.status_code == 404
