import pytest
from decimal import Decimal
from task_api.models import Sale

SUMMARY_URL = "/reports/summary/"


@pytest.fixture
def completed_sale(db, product, employee):
    return Sale.objects.create(
        product=product,
        sold_by=employee,
        quantity=10,
        selling_price=product.selling_price,
        status="Completed",
    )


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSummaryReportAccess:

    def test_manager_can_access(self, manager_client):
        """Manager can access the summary report endpoint."""
        res = manager_client.get(SUMMARY_URL)
        assert res.status_code == 200

    def test_employee_cannot_access(self, employee_client):
        """Employee is forbidden from accessing the summary report."""
        res = employee_client.get(SUMMARY_URL)
        assert res.status_code == 403

    def test_unauthenticated_cannot_access(self, anon_client):
        """Unauthenticated request returns 401."""
        res = anon_client.get(SUMMARY_URL)
        assert res.status_code == 401


# ── Response structure ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSummaryReportStructure:

    def test_top_level_keys_present(self, manager_client):
        """Response contains summary, timeline, and metadata keys."""
        res = manager_client.get(SUMMARY_URL)
        assert "summary" in res.data
        assert "timeline" in res.data
        assert "metadata" in res.data

    def test_summary_keys_present(self, manager_client):
        """summary contains all expected financial fields."""
        res = manager_client.get(SUMMARY_URL)
        summary = res.data["summary"]
        for key in ("total_sales", "total_revenue", "total_sales_transactions", "gross_profit", "profit_margin"):
            assert key in summary

    def test_timeline_entry_keys(self, manager_client, completed_sale):
        """Each timeline entry contains time_period, total_sales, total_revenue, total_profit, total_sales_transactions."""
        res = manager_client.get(SUMMARY_URL)
        assert len(res.data["timeline"]) > 0
        entry = res.data["timeline"][0]
        for key in ("time_period", "total_sales", "total_revenue", "total_profit", "total_sales_transactions"):
            assert key in entry

    def test_empty_report_returns_zeros_and_empty_timeline(self, manager_client):
        """With no sales, summary values are zero and timeline is empty."""
        res = manager_client.get(SUMMARY_URL)
        summary = res.data["summary"]
        assert summary["total_sales"] == 0
        assert Decimal(str(summary["total_revenue"])) == Decimal("0")
        assert Decimal(str(summary["gross_profit"])) == Decimal("0")
        assert Decimal(str(summary["profit_margin"])) == Decimal("0")
        assert res.data["timeline"] == []


# ── Summary correctness ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSummaryReportData:

    def test_only_completed_sales_counted(self, manager_client, product, employee):
        """Pending sales are excluded from the summary."""
        Sale.objects.create(
            product=product, sold_by=employee,
            quantity=50, selling_price=product.selling_price,
            status="Pending",
        )
        res = manager_client.get(SUMMARY_URL)
        assert res.data["summary"]["total_sales"] == 0

    def test_total_sales_quantity_is_correct(self, manager_client, completed_sale):
        """total_sales matches the sum of completed sale quantities."""
        res = manager_client.get(SUMMARY_URL)
        assert res.data["summary"]["total_sales"] == completed_sale.quantity

    def test_total_sales_transactions_is_correct(self, manager_client, completed_sale):
        """total_sales_transactions counts the number of completed sale records."""
        res = manager_client.get(SUMMARY_URL)
        assert res.data["summary"]["total_sales_transactions"] == 1

    def test_total_revenue_is_correct(self, manager_client, completed_sale, product):
        """total_revenue equals quantity * selling_price."""
        expected = Decimal(str(completed_sale.quantity)) * product.selling_price
        res = manager_client.get(SUMMARY_URL)
        assert Decimal(str(res.data["summary"]["total_revenue"])) == expected

    def test_gross_profit_is_correct(self, manager_client, completed_sale, product):
        """gross_profit equals (selling_price - buying_price) * quantity."""
        revenue = Decimal(str(completed_sale.quantity)) * product.selling_price
        cost = Decimal(str(completed_sale.quantity)) * product.buying_price
        expected = revenue - cost
        res = manager_client.get(SUMMARY_URL)
        assert Decimal(str(res.data["summary"]["gross_profit"])) == expected

    def test_profit_margin_is_correct(self, manager_client, completed_sale, product):
        """profit_margin equals (gross_profit / total_revenue) * 100, rounded to 2dp."""
        revenue = Decimal(str(completed_sale.quantity)) * product.selling_price
        cost = Decimal(str(completed_sale.quantity)) * product.buying_price
        profit = revenue - cost
        expected = (profit / revenue * 100).quantize(Decimal("0.01"))
        res = manager_client.get(SUMMARY_URL)
        assert Decimal(str(res.data["summary"]["profit_margin"])) == expected


# ── Group by ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSummaryReportGroupBy:

    def test_default_group_by_is_day(self, manager_client, completed_sale):
        """Default group_by is day — timeline entry time_period is a datetime."""
        res = manager_client.get(SUMMARY_URL)
        assert res.data["metadata"]["time_period"] == "day"
        assert len(res.data["timeline"]) == 1

    def test_group_by_week(self, manager_client, completed_sale):
        """?group_by=week groups timeline entries by week."""
        res = manager_client.get(f"{SUMMARY_URL}?group_by=week")
        assert res.status_code == 200
        assert res.data["metadata"]["time_period"] == "week"
        assert len(res.data["timeline"]) == 1

    def test_group_by_month(self, manager_client, completed_sale):
        """?group_by=month groups timeline entries by month."""
        res = manager_client.get(f"{SUMMARY_URL}?group_by=month")
        assert res.status_code == 200
        assert res.data["metadata"]["time_period"] == "month"

    def test_group_by_year(self, manager_client, completed_sale):
        """?group_by=year groups timeline entries by year."""
        res = manager_client.get(f"{SUMMARY_URL}?group_by=year")
        assert res.status_code == 200
        assert res.data["metadata"]["time_period"] == "year"

    def test_invalid_group_by_returns_400(self, manager_client):
        """?group_by=<invalid> returns 400."""
        res = manager_client.get(f"{SUMMARY_URL}?group_by=invalid")
        assert res.status_code == 400


# ── Date filtering ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSummaryReportDateFilter:

    def test_from_date_includes_todays_sales(self, manager_client, completed_sale):
        """?from=<today> includes today's sales in the summary."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{SUMMARY_URL}?from={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales_transactions"] == 1

    def test_to_date_includes_todays_sales(self, manager_client, completed_sale):
        """?to=<today> includes today's sales in the summary."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{SUMMARY_URL}?to={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales_transactions"] == 1

    def test_future_from_date_returns_zeros(self, manager_client, completed_sale):
        """?from=<future date> returns zero summary values and empty timeline."""
        res = manager_client.get(f"{SUMMARY_URL}?from=2099-01-01")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales_transactions"] == 0
        assert res.data["timeline"] == []

    def test_past_to_date_returns_zeros(self, manager_client, completed_sale):
        """?to=<past date> returns zero summary values and empty timeline."""
        res = manager_client.get(f"{SUMMARY_URL}?to=2000-01-01")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales_transactions"] == 0
        assert res.data["timeline"] == []

    def test_invalid_date_format_returns_400(self, manager_client):
        """Invalid date format returns 400."""
        res = manager_client.get(f"{SUMMARY_URL}?from=not-a-date")
        assert res.status_code == 400

    def test_metadata_reflects_date_params(self, manager_client):
        """metadata.from and metadata.to reflect the query params."""
        res = manager_client.get(f"{SUMMARY_URL}?from=2024-01-01&to=2024-12-31")
        assert res.data["metadata"]["from"] == "2024-01-01"
        assert res.data["metadata"]["to"] == "2024-12-31"
