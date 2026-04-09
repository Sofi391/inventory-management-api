import pytest
from decimal import Decimal
from unittest.mock import patch
from task_api.models import StockTransaction

TRANSACTION_LIST_URL = "/manage/transactions/"
TRANSACTION_CREATE_URL = "/manage/transactions/create/"


@pytest.fixture
def in_transaction(db, product, manager_user):
    return StockTransaction.objects.create(
        transaction_type="IN",
        quantity=10,
        unit_price=product.buying_price,
        product=product,
        created_by=manager_user,
        note="Restocked",
    )


@pytest.fixture
def out_transaction(db, product, manager_user):
    return StockTransaction.objects.create(
        transaction_type="OUT",
        quantity=5,
        unit_price=product.selling_price,
        product=product,
        created_by=manager_user,
        note="Manual OUT",
    )


# ── Transaction history list ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestTransactionHistory:

    def test_manager_sees_all_transactions(self, manager_client, in_transaction, out_transaction):
        """Manager can retrieve the full transaction history including all users' records."""
        res = manager_client.get(TRANSACTION_LIST_URL)
        assert res.status_code == 200
        results = res.data["results"] if "results" in res.data else res.data
        assert len(results) >= 2

    def test_employee_sees_only_own_transactions(self, employee_client, employee, product, manager_user, in_transaction):
        """Employee only sees transactions they created, not other users' transactions."""
        StockTransaction.objects.create(
            transaction_type="IN",
            quantity=3,
            unit_price=product.buying_price,
            product=product,
            created_by=employee,
            note="Employee IN",
        )
        res = employee_client.get(TRANSACTION_LIST_URL)
        assert res.status_code == 200
        results = res.data["results"] if "results" in res.data else res.data
        for tx in results:
            assert tx["created_by"]["username"] == employee.username

    def test_unauthenticated_cannot_view_transactions(self, anon_client):
        """Unauthenticated request to transaction history returns 401."""
        res = anon_client.get(TRANSACTION_LIST_URL)
        assert res.status_code == 401

    def test_filter_by_type_in(self, manager_client, in_transaction, out_transaction):
        """Filtering by ?type=IN returns only IN transactions."""
        res = manager_client.get(f"{TRANSACTION_LIST_URL}?type=IN")
        assert res.status_code == 200
        results = res.data["results"] if "results" in res.data else res.data
        for tx in results:
            assert tx["transaction_type"] == "IN"

    def test_filter_by_type_out(self, manager_client, in_transaction, out_transaction):
        """Filtering by ?type=OUT returns only OUT transactions."""
        res = manager_client.get(f"{TRANSACTION_LIST_URL}?type=OUT")
        assert res.status_code == 200
        results = res.data["results"] if "results" in res.data else res.data
        for tx in results:
            assert tx["transaction_type"] == "OUT"

    def test_total_price_is_correct(self, manager_client, in_transaction):
        """Each transaction record has total_price equal to quantity * unit_price."""
        res = manager_client.get(TRANSACTION_LIST_URL)
        results = res.data["results"] if "results" in res.data else res.data
        for tx in results:
            expected = round(float(tx["quantity"]) * float(tx["unit_price"]), 2)
            assert round(float(tx["total_price"]), 2) == expected

    def test_transaction_contains_product_and_created_by(self, manager_client, in_transaction, product, manager_user):
        """Each transaction record includes nested product and created_by fields."""
        res = manager_client.get(TRANSACTION_LIST_URL)
        results = res.data["results"] if "results" in res.data else res.data
        tx = results[0]
        assert "product" in tx
        assert "created_by" in tx
        assert tx["created_by"]["username"] == manager_user.username


# ── Manual transaction creation ───────────────────────────────────────────────

@pytest.mark.django_db
class TestTransactionCreate:

    def test_manager_can_create_in_transaction(self, manager_client, product):
        """Manager can manually create an IN transaction to add stock (e.g. gifted stock)."""
        payload = {
            "transaction_type": "IN",
            "quantity": 20,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Gifted stock from partner",
        }
        res = manager_client.post(TRANSACTION_CREATE_URL, payload)
        assert res.status_code == 201
        product.refresh_from_db()
        assert product.current_stock == 120  # 100 base + 20 gifted

    def test_manager_can_create_out_transaction(self, manager_client, product):
        """Manager can manually create an OUT transaction to remove stock (e.g. defective items)."""
        payload = {
            "transaction_type": "OUT",
            "quantity": 10,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Defective items removed from inventory",
        }
        res = manager_client.post(TRANSACTION_CREATE_URL, payload)
        assert res.status_code == 201
        product.refresh_from_db()
        assert product.current_stock == 90  # 100 base - 10 defective

    def test_employee_cannot_create_transaction(self, employee_client, product):
        """Employee cannot manually create a stock transaction and gets 403."""
        payload = {
            "transaction_type": "IN",
            "quantity": 5,
            "unit_price": "10.00",
            "product": product.slug,
        }
        res = employee_client.post(TRANSACTION_CREATE_URL, payload)
        assert res.status_code == 403

    def test_unauthenticated_cannot_create_transaction(self, anon_client, product):
        """Unauthenticated create request returns 401."""
        payload = {
            "transaction_type": "IN",
            "quantity": 5,
            "unit_price": "10.00",
            "product": product.slug,
        }
        res = anon_client.post(TRANSACTION_CREATE_URL, payload)
        assert res.status_code == 401

    def test_created_by_is_auto_set_to_request_user(self, manager_client, manager_user, product):
        """created_by is automatically set to the authenticated manager making the request."""
        payload = {
            "transaction_type": "IN",
            "quantity": 5,
            "unit_price": "10.00",
            "product": product.slug,
        }
        manager_client.post(TRANSACTION_CREATE_URL, payload)
        tx = StockTransaction.objects.filter(product=product).first()
        assert tx.created_by == manager_user

    def test_total_price_is_auto_calculated(self, manager_client, product):
        """total_price is auto-calculated as quantity * unit_price and cannot be overridden."""
        payload = {
            "transaction_type": "IN",
            "quantity": 4,
            "unit_price": "25.00",
            "product": product.slug,
            "total_price": "999.00",  # should be ignored
        }
        manager_client.post(TRANSACTION_CREATE_URL, payload)
        tx = StockTransaction.objects.filter(product=product).first()
        assert tx.total_price == Decimal("100.00")  # 4 * 25


# ── Edge cases ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTransactionEdgeCases:

    def test_defective_items_out_reduces_stock_correctly(self, manager_client, product):
        """Writing off defective items via OUT transaction correctly reduces stock."""
        defective_qty = 15
        payload = {
            "transaction_type": "OUT",
            "quantity": defective_qty,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Defective batch — written off",
        }
        manager_client.post(TRANSACTION_CREATE_URL, payload)
        product.refresh_from_db()
        assert product.current_stock == 100 - defective_qty

    def test_gifted_stock_in_increases_stock_correctly(self, manager_client, product):
        """Recording gifted/donated stock via IN transaction correctly increases stock."""
        gifted_qty = 30
        payload = {
            "transaction_type": "IN",
            "quantity": gifted_qty,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Gifted by supplier — no cost",
        }
        manager_client.post(TRANSACTION_CREATE_URL, payload)
        product.refresh_from_db()
        assert product.current_stock == 100 + gifted_qty

    def test_out_transaction_exceeding_stock_fails(self, manager_client, product):
        """OUT transaction with quantity greater than current stock returns 400."""
        payload = {
            "transaction_type": "OUT",
            "quantity": 9999,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Should fail — not enough stock",
        }
        res = manager_client.post(TRANSACTION_CREATE_URL, payload)
        assert res.status_code == 400

    def test_out_transaction_exceeding_stock_does_not_change_stock(self, manager_client, product):
        """A failed OUT transaction leaves the product stock completely unchanged."""
        stock_before = product.current_stock
        payload = {
            "transaction_type": "OUT",
            "quantity": 9999,
            "unit_price": "0.00",
            "product": product.slug,
        }
        manager_client.post(TRANSACTION_CREATE_URL, payload)
        product.refresh_from_db()
        assert product.current_stock == stock_before

    def test_zero_cost_in_transaction_is_valid(self, manager_client, product):
        """IN transaction with unit_price of 0.00 is valid for gifted or donated stock."""
        payload = {
            "transaction_type": "IN",
            "quantity": 10,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Free sample from supplier",
        }
        res = manager_client.post(TRANSACTION_CREATE_URL, payload)
        assert res.status_code == 201

    @patch("task_api.views.low_stock_alert")
    def test_low_stock_alert_fires_on_out_transaction(self, mock_alert, manager_client, product):
        """Low stock alert fires when a manual OUT transaction drops stock to reorder level."""
        product.current_stock = product.reorder_level + 5
        product.save()
        payload = {
            "transaction_type": "OUT",
            "quantity": 5,
            "unit_price": "0.00",
            "product": product.slug,
            "note": "Defective items",
        }
        manager_client.post(TRANSACTION_CREATE_URL, payload)
        assert mock_alert.called
