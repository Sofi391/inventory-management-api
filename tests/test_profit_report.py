import pytest
from decimal import Decimal
from task_api.models import Sale, PurchaseOrder

PROFIT_REPORT_URL = "/reports/profit/"


@pytest.fixture
def completed_sale(db, product, employee):
    return Sale.objects.create(
        product=product,
        sold_by=employee,
        quantity=10,
        selling_price=product.selling_price,
        status="Completed",
    )


@pytest.fixture
def completed_purchase(db, product, supplier):
    return PurchaseOrder.objects.create(
        product=product,
        supplier=supplier,
        quantity=10,
        unit_price=product.buying_price,
        status="Completed",
    )


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfitReportAccess:

    def test_manager_can_access_profit_report(self, manager_client):
        """Manager can access the profit report endpoint."""
        res = manager_client.get(PROFIT_REPORT_URL)
        assert res.status_code == 200

    def test_employee_cannot_access_profit_report(self, employee_client):
        """Employee is forbidden from accessing the profit report."""
        res = employee_client.get(PROFIT_REPORT_URL)
        assert res.status_code == 403

    def test_unauthenticated_cannot_access_profit_report(self, anon_client):
        """Unauthenticated request returns 401."""
        res = anon_client.get(PROFIT_REPORT_URL)
        assert res.status_code == 401


# ── Response structure ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfitReportStructure:

    def test_response_keys_present(self, manager_client):
        """Response contains summary, volume, quantity, and metadata keys."""
        res = manager_client.get(PROFIT_REPORT_URL)
        assert "summary" in res.data
        assert "volume" in res.data
        assert "quantity" in res.data
        assert "metadata" in res.data

    def test_summary_keys_present(self, manager_client):
        """summary contains total_cost, total_revenue, total_purchase, gross_profit, profit_margin."""
        res = manager_client.get(PROFIT_REPORT_URL)
        summary = res.data["summary"]
        for key in ("total_cost", "total_revenue", "total_purchase", "gross_profit", "profit_margin"):
            assert key in summary

    def test_empty_report_returns_zeros(self, manager_client):
        """With no data, all summary values are zero."""
        res = manager_client.get(PROFIT_REPORT_URL)
        summary = res.data["summary"]
        assert Decimal(str(summary["total_revenue"])) == Decimal("0")
        assert Decimal(str(summary["total_cost"])) == Decimal("0")
        assert Decimal(str(summary["gross_profit"])) == Decimal("0")
        assert Decimal(str(summary["profit_margin"])) == Decimal("0")


# ── Summary correctness ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfitReportSummary:

    def test_total_revenue_is_correct(self, manager_client, completed_sale, product):
        """total_revenue equals quantity * selling_price of completed sales."""
        expected = Decimal(str(completed_sale.quantity)) * product.selling_price
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_revenue"])) == expected

    def test_total_cost_is_correct(self, manager_client, completed_sale, product):
        """total_cost equals quantity * buying_price of completed sales."""
        expected = Decimal(str(completed_sale.quantity)) * product.buying_price
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_cost"])) == expected

    def test_gross_profit_is_revenue_minus_cost(self, manager_client, completed_sale, product):
        """gross_profit equals total_revenue - total_cost."""
        revenue = Decimal(str(completed_sale.quantity)) * product.selling_price
        cost = Decimal(str(completed_sale.quantity)) * product.buying_price
        expected_profit = revenue - cost
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["gross_profit"])) == expected_profit

    def test_profit_margin_is_correct(self, manager_client, completed_sale, product):
        """profit_margin equals (gross_profit / total_revenue) * 100, rounded to 2dp."""
        revenue = Decimal(str(completed_sale.quantity)) * product.selling_price
        cost = Decimal(str(completed_sale.quantity)) * product.buying_price
        profit = revenue - cost
        expected_margin = (profit / revenue * 100).quantize(Decimal("0.01"))
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["profit_margin"])) == expected_margin

    def test_total_purchase_cost_is_correct(self, manager_client, completed_purchase, product):
        """total_purchase equals quantity * unit_price of completed purchase orders."""
        expected = Decimal(str(completed_purchase.quantity)) * completed_purchase.unit_price
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_purchase"])) == expected

    def test_only_completed_sales_counted(self, manager_client, product, employee):
        """Pending sales are excluded from revenue and cost calculations."""
        Sale.objects.create(
            product=product, sold_by=employee,
            quantity=50, selling_price=product.selling_price,
            status="Pending",
        )
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_revenue"])) == Decimal("0")

    def test_only_completed_purchases_counted(self, manager_client, product, supplier):
        """Pending purchase orders are excluded from total_purchase."""
        PurchaseOrder.objects.create(
            product=product, supplier=supplier,
            quantity=50, unit_price=product.buying_price,
            status="Pending",
        )
        res = manager_client.get(PROFIT_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_purchase"])) == Decimal("0")

    def test_volume_counts_are_correct(self, manager_client, completed_sale, completed_purchase):
        """volume.sales_count and purchases_count reflect completed records."""
        res = manager_client.get(PROFIT_REPORT_URL)
        assert res.data["volume"]["sales_count"] == 1
        assert res.data["volume"]["purchases_count"] == 1

    def test_quantity_fields_are_correct(self, manager_client, completed_sale, completed_purchase):
        """quantity.sold_quantity and purchased_quantity match completed records."""
        res = manager_client.get(PROFIT_REPORT_URL)
        assert res.data["quantity"]["sold_quantity"] == completed_sale.quantity
        assert res.data["quantity"]["purchased_quantity"] == completed_purchase.quantity


# ── Date filtering ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfitReportDateFilter:

    def test_from_date_includes_todays_data(self, manager_client, completed_sale, completed_purchase):
        """?from=<today> includes today's sales and purchases."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{PROFIT_REPORT_URL}?from={today}")
        assert res.status_code == 200
        assert res.data["volume"]["sales_count"] == 1

    def test_to_date_includes_todays_data(self, manager_client, completed_sale):
        """?to=<today> includes today's sales."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{PROFIT_REPORT_URL}?to={today}")
        assert res.status_code == 200
        assert res.data["volume"]["sales_count"] == 1

    def test_future_from_date_returns_zeros(self, manager_client, completed_sale):
        """?from=<future date> returns zero revenue and profit."""
        res = manager_client.get(f"{PROFIT_REPORT_URL}?from=2099-01-01")
        assert res.status_code == 200
        assert Decimal(str(res.data["summary"]["total_revenue"])) == Decimal("0")

    def test_past_to_date_returns_zeros(self, manager_client, completed_sale):
        """?to=<past date> returns zero revenue and profit."""
        res = manager_client.get(f"{PROFIT_REPORT_URL}?to=2000-01-01")
        assert res.status_code == 200
        assert Decimal(str(res.data["summary"]["total_revenue"])) == Decimal("0")

    def test_invalid_date_format_returns_400(self, manager_client):
        """Invalid date format returns 400."""
        res = manager_client.get(f"{PROFIT_REPORT_URL}?from=not-a-date")
        assert res.status_code == 400


# ── Product filter ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfitReportProductFilter:

    def test_product_filter_matches_existing_product(self, manager_client, completed_sale, product):
        """?product=<name> returns revenue for that product."""
        res = manager_client.get(f"{PROFIT_REPORT_URL}?product={product.name}")
        assert res.status_code == 200
        assert res.data["volume"]["sales_count"] == 1

    def test_product_filter_nonexistent_returns_zeros(self, manager_client, completed_sale):
        """?product=<nonexistent> returns zero revenue and profit."""
        res = manager_client.get(f"{PROFIT_REPORT_URL}?product=ghost_product")
        assert res.status_code == 200
        assert Decimal(str(res.data["summary"]["total_revenue"])) == Decimal("0")
        assert Decimal(str(res.data["summary"]["gross_profit"])) == Decimal("0")

    def test_metadata_reflects_product_filter(self, manager_client, product):
        """metadata.filter_product reflects the queried product name."""
        res = manager_client.get(f"{PROFIT_REPORT_URL}?product={product.name}")
        assert res.data["metadata"]["filter_product"] == product.name

    def test_metadata_defaults_to_all_products(self, manager_client):
        """metadata.filter_product is 'All Products' when no filter is applied."""
        res = manager_client.get(PROFIT_REPORT_URL)
        assert res.data["metadata"]["filter_product"] == "All Products"
