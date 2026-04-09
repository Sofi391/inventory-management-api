import pytest
from decimal import Decimal
from unittest.mock import patch
from task_api.models import PurchaseOrder, StockTransaction

PURCHASE_URL = "/manage/purchases/"


def complete_url(pk):
    return f"{PURCHASE_URL}{pk}/complete/"


@pytest.fixture
def purchase(db, product, supplier):
    return PurchaseOrder.objects.create(
        product=product,
        supplier=supplier,
        quantity=20,
        unit_price=product.buying_price,
    )


@pytest.fixture
def completed_purchase(db, product, supplier):
    return PurchaseOrder.objects.create(
        product=product,
        supplier=supplier,
        quantity=20,
        unit_price=product.buying_price,
        status="Completed",
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPurchaseCRUD:

    def test_list_purchases_as_manager(self, manager_client, purchase):
        """Manager can retrieve the full list of purchase orders."""
        res = manager_client.get(PURCHASE_URL)
        assert res.status_code == 200

    def test_list_purchases_as_employee(self, employee_client):
        """Employee cannot access purchase orders and gets 403."""
        res = employee_client.get(PURCHASE_URL)
        assert res.status_code == 403

    def test_list_purchases_unauthenticated(self, anon_client):
        """Unauthenticated request to purchase list returns 401."""
        res = anon_client.get(PURCHASE_URL)
        assert res.status_code == 401

    def test_create_purchase_as_manager(self, manager_client, product, supplier):
        """Manager can create a purchase order linked to the correct supplier."""
        payload = {"product": product.slug, "supplier": supplier.slug, "quantity": 10}
        res = manager_client.post(PURCHASE_URL, payload)
        assert res.status_code == 201
        assert PurchaseOrder.objects.filter(product=product, quantity=10).exists()

    def test_create_purchase_wrong_supplier(self, manager_client, product, db):
        """Create purchase with a supplier that doesn't supply the product returns 400."""
        from task_api.models import Supplier
        other = Supplier.objects.create(
            name="Other Supplier", email="other@test.com",
            phone="0900000000", address="Nowhere"
        )
        payload = {"product": product.slug, "supplier": other.slug, "quantity": 10}
        res = manager_client.post(PURCHASE_URL, payload)
        assert res.status_code == 400

    def test_create_purchase_zero_quantity(self, manager_client, product, supplier):
        """Create purchase with zero quantity returns 400."""
        payload = {"product": product.slug, "supplier": supplier.slug, "quantity": 0}
        res = manager_client.post(PURCHASE_URL, payload)
        assert res.status_code == 400

    def test_create_purchase_as_employee(self, employee_client, product, supplier):
        """Employee cannot create a purchase order and gets 403."""
        payload = {"product": product.slug, "supplier": supplier.slug, "quantity": 10}
        res = employee_client.post(PURCHASE_URL, payload)
        assert res.status_code == 403

    def test_unit_price_is_auto_set_from_product(self, manager_client, product, supplier):
        """unit_price is auto-set from product buying_price and cannot be overridden."""
        payload = {
            "product": product.slug, "supplier": supplier.slug,
            "quantity": 5, "unit_price": "999.00"
        }
        manager_client.post(PURCHASE_URL, payload)
        order = PurchaseOrder.objects.filter(product=product).first()
        assert order.unit_price == Decimal(product.buying_price)


# ── Complete workflow ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPurchaseComplete:

    def test_complete_purchase_returns_200(self, manager_client, purchase):
        """Completing a pending purchase returns 200 with success message."""
        res = manager_client.post(complete_url(purchase.pk))
        assert res.status_code == 200
        assert res.data["detail"] == "Purchase Completed!"

    def test_complete_purchase_status_changes(self, manager_client, purchase):
        """Completing a purchase changes its status from Pending to Completed."""
        manager_client.post(complete_url(purchase.pk))
        purchase.refresh_from_db()
        assert purchase.status == "Completed"

    def test_complete_purchase_increases_stock(self, manager_client, purchase, product):
        """Completing a purchase increases the product stock by the purchase quantity."""
        stock_before = product.current_stock
        manager_client.post(complete_url(purchase.pk))
        product.refresh_from_db()
        assert product.current_stock == stock_before + purchase.quantity

    def test_complete_purchase_creates_in_transaction(self, manager_client, purchase, product):
        """Completing a purchase creates an IN stock transaction for the product."""
        manager_client.post(complete_url(purchase.pk))
        assert StockTransaction.objects.filter(
            product=product,
            transaction_type="IN",
            quantity=purchase.quantity,
        ).exists()

    def test_complete_already_completed_purchase(self, manager_client, completed_purchase):
        """Completing an already completed purchase returns 400."""
        res = manager_client.post(complete_url(completed_purchase.pk))
        assert res.status_code == 400

    def test_complete_purchase_as_employee(self, employee_client, purchase):
        """Employee cannot complete a purchase and gets 403."""
        res = employee_client.post(complete_url(purchase.pk))
        assert res.status_code == 403

    def test_complete_nonexistent_purchase(self, manager_client):
        """Complete action on a non-existent purchase ID returns 404."""
        res = manager_client.post(complete_url(99999))
        assert res.status_code == 404


# ── Atomic rollback ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPurchaseAtomicRollback:

    def test_rollback_on_stock_transaction_failure(self, manager_client, purchase, product):
        """If StockTransaction.save() raises an error the purchase status and stock
        are both rolled back — neither change is persisted to the DB."""
        stock_before = product.current_stock

        with patch(
            "task_api.models.StockTransaction.save",
            side_effect=Exception("Forced DB failure")
        ):
            res = manager_client.post(complete_url(purchase.pk))

        assert res.status_code == 400
        purchase.refresh_from_db()
        product.refresh_from_db()
        assert purchase.status == "Pending"
        assert product.current_stock == stock_before

    def test_no_transaction_record_on_failure(self, manager_client, purchase, product):
        """If the atomic block fails no StockTransaction record is left in the DB."""
        with patch(
            "task_api.models.StockTransaction.save",
            side_effect=Exception("Forced DB failure")
        ):
            manager_client.post(complete_url(purchase.pk))

        assert not StockTransaction.objects.filter(product=product).exists()
