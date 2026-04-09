import pytest
from decimal import Decimal
from unittest.mock import patch
from task_api.models import Sale, StockTransaction

SALE_URL = "/manage/sales/"


def complete_url(pk):
    return f"{SALE_URL}{pk}/complete/"


@pytest.fixture
def sale(db, product, employee):
    return Sale.objects.create(
        product=product,
        sold_by=employee,
        quantity=5,
        selling_price=product.selling_price,
    )


@pytest.fixture
def completed_sale(db, product, employee):
    return Sale.objects.create(
        product=product,
        sold_by=employee,
        quantity=5,
        selling_price=product.selling_price,
        status="Completed",
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaleCRUD:

    def test_list_sales_as_manager(self, manager_client, sale):
        """Manager can retrieve the full list of all sales."""
        res = manager_client.get(SALE_URL)
        assert res.status_code == 200

    def test_list_sales_as_employee_sees_only_own(self, employee_client, employee, sale, product, manager_user):
        """Employee can only see sales they created, not other users' sales."""
        Sale.objects.create(
            product=product, sold_by=manager_user,
            quantity=2, selling_price=product.selling_price
        )
        res = employee_client.get(SALE_URL)
        assert res.status_code == 200
        results = res.data["results"] if "results" in res.data else res.data
        for s in results:
            assert s["sold_by"] == employee.id

    def test_list_sales_unauthenticated(self, anon_client):
        """Unauthenticated request to sales list returns 401."""
        res = anon_client.get(SALE_URL)
        assert res.status_code == 401

    def test_create_sale_as_employee(self, employee_client, product):
        """Employee can create a sale for a product with sufficient stock."""
        res = employee_client.post(SALE_URL, {"product": product.slug, "quantity": 5})
        assert res.status_code == 201
        assert Sale.objects.filter(product=product, quantity=5).exists()

    def test_create_sale_as_manager(self, manager_client, product):
        """Manager can also create a sale."""
        res = manager_client.post(SALE_URL, {"product": product.slug, "quantity": 3})
        assert res.status_code == 201

    def test_create_sale_unauthenticated(self, anon_client, product):
        """Unauthenticated create request returns 401."""
        res = anon_client.post(SALE_URL, {"product": product.slug, "quantity": 1})
        assert res.status_code == 401

    def test_create_sale_exceeds_stock(self, employee_client, product):
        """Creating a sale with quantity greater than current stock returns 400."""
        res = employee_client.post(SALE_URL, {"product": product.slug, "quantity": 9999})
        assert res.status_code == 400

    def test_create_sale_zero_quantity(self, employee_client, product):
        """Creating a sale with zero quantity returns 400."""
        res = employee_client.post(SALE_URL, {"product": product.slug, "quantity": 0})
        assert res.status_code == 400

    def test_sold_by_is_auto_set_to_request_user(self, employee_client, employee, product):
        """sold_by is automatically set to the authenticated user making the request."""
        employee_client.post(SALE_URL, {"product": product.slug, "quantity": 1})
        sale = Sale.objects.filter(product=product).first()
        assert sale.sold_by == employee

    def test_selling_price_is_auto_set_from_product(self, employee_client, product):
        """selling_price is auto-set from the product and cannot be overridden."""
        employee_client.post(SALE_URL, {"product": product.slug, "quantity": 1, "selling_price": "999.00"})
        sale = Sale.objects.filter(product=product).first()
        assert sale.selling_price == Decimal(product.selling_price)


# ── Complete workflow ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaleComplete:

    def test_complete_sale_returns_200(self, employee_client, sale):
        """Completing a pending sale returns 200 with success message."""
        res = employee_client.post(complete_url(sale.pk))
        assert res.status_code == 200
        assert res.data["detail"] == "Sales Completed!"

    def test_complete_sale_status_changes(self, employee_client, sale):
        """Completing a sale changes its status from Pending to Completed."""
        employee_client.post(complete_url(sale.pk))
        sale.refresh_from_db()
        assert sale.status == "Completed"

    def test_complete_sale_decreases_stock(self, employee_client, sale, product):
        """Completing a sale decreases the product stock by the sale quantity."""
        stock_before = product.current_stock
        employee_client.post(complete_url(sale.pk))
        product.refresh_from_db()
        assert product.current_stock == stock_before - sale.quantity

    def test_complete_sale_creates_out_transaction(self, employee_client, sale, product):
        """Completing a sale creates an OUT stock transaction for the product."""
        employee_client.post(complete_url(sale.pk))
        assert StockTransaction.objects.filter(
            product=product,
            transaction_type="OUT",
            quantity=sale.quantity,
        ).exists()

    def test_complete_already_completed_sale(self, employee_client, completed_sale):
        """Completing an already completed sale returns 400."""
        res = employee_client.post(complete_url(completed_sale.pk))
        assert res.status_code == 400

    def test_employee_cannot_complete_other_users_sale(self, employee_client, product, manager_user):
        """Employee cannot complete a sale that belongs to another user.
        The queryset filters it out entirely so Django returns 404 instead of 403."""
        other_sale = Sale.objects.create(
            product=product, sold_by=manager_user,
            quantity=2, selling_price=product.selling_price
        )
        res = employee_client.post(complete_url(other_sale.pk))
        assert res.status_code == 404

    def test_complete_nonexistent_sale(self, employee_client):
        """Complete action on a non-existent sale ID returns 404."""
        res = employee_client.post(complete_url(99999))
        assert res.status_code == 404

    @patch("task_api.views.low_stock_alert")
    def test_low_stock_alert_fires_when_stock_hits_reorder_level(self, mock_alert, employee_client, product, employee):
        """Low stock alert is triggered when stock drops to or below the reorder level."""
        product.current_stock = product.reorder_level + 1
        product.save()
        sale = Sale.objects.create(
            product=product, sold_by=employee,
            quantity=1, selling_price=product.selling_price
        )
        employee_client.post(complete_url(sale.pk))
        assert mock_alert.called

    @patch("task_api.views.low_stock_alert")
    def test_low_stock_alert_does_not_fire_when_stock_is_sufficient(self, mock_alert, employee_client, product, employee):
        """Low stock alert is not triggered when stock remains above the reorder level."""
        sale = Sale.objects.create(
            product=product, sold_by=employee,
            quantity=1, selling_price=product.selling_price
        )
        employee_client.post(complete_url(sale.pk))
        assert not mock_alert.called


# ── Atomic rollback ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSaleAtomicRollback:

    def test_rollback_on_stock_transaction_failure(self, employee_client, sale, product):
        """If StockTransaction.save() raises an error the sale status and stock
        are both rolled back — neither change is persisted to the DB."""
        stock_before = product.current_stock

        with patch(
            "task_api.models.StockTransaction.save",
            side_effect=Exception("Forced DB failure")
        ):
            res = employee_client.post(complete_url(sale.pk))

        assert res.status_code == 400
        sale.refresh_from_db()
        product.refresh_from_db()
        assert sale.status == "Pending"
        assert product.current_stock == stock_before

    def test_no_transaction_record_on_failure(self, employee_client, sale, product):
        """If the atomic block fails no StockTransaction record is left in the DB."""
        with patch(
            "task_api.models.StockTransaction.save",
            side_effect=Exception("Forced DB failure")
        ):
            employee_client.post(complete_url(sale.pk))

        assert not StockTransaction.objects.filter(product=product).exists()
