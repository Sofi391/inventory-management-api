import pytest
from decimal import Decimal
from task_api.models import Sale

SALES_REPORT_URL = "/reports/sales/"


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
def pending_sale(db, product, employee):
    return Sale.objects.create(
        product=product,
        sold_by=employee,
        quantity=5,
        selling_price=product.selling_price,
        status="Pending",
    )


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSalesReportAccess:

    def test_manager_can_access_sales_report(self, manager_client):
        """Manager can access the sales report endpoint."""
        res = manager_client.get(SALES_REPORT_URL)
        assert res.status_code == 200

    def test_employee_cannot_access_sales_report(self, employee_client):
        """Employee is forbidden from accessing the sales report."""
        res = employee_client.get(SALES_REPORT_URL)
        assert res.status_code == 403

    def test_unauthenticated_cannot_access_sales_report(self, anon_client):
        """Unauthenticated request returns 401."""
        res = anon_client.get(SALES_REPORT_URL)
        assert res.status_code == 401


# ── Summary correctness ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSalesReportSummary:

    def test_summary_keys_present(self, manager_client, completed_sale):
        """Response contains summary, metadata keys."""
        res = manager_client.get(SALES_REPORT_URL)
        assert "summary" in res.data
        assert "metadata" in res.data

    def test_summary_counts_only_completed_sales(self, manager_client, completed_sale, pending_sale):
        """Only Completed sales are counted in the summary."""
        res = manager_client.get(SALES_REPORT_URL)
        assert res.data["summary"]["total_sales"] == 1

    def test_summary_total_quantity(self, manager_client, completed_sale):
        """total_quantity matches the sum of completed sale quantities."""
        res = manager_client.get(SALES_REPORT_URL)
        assert res.data["summary"]["total_quantity"] == completed_sale.quantity

    def test_summary_total_revenue(self, manager_client, completed_sale):
        """total_sales_revenue equals quantity * selling_price."""
        expected = Decimal(str(completed_sale.quantity)) * completed_sale.selling_price
        res = manager_client.get(SALES_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_sales_revenue"])) == expected

    def test_empty_summary_returns_zeros(self, manager_client):
        """With no sales, all summary values are zero."""
        res = manager_client.get(SALES_REPORT_URL)
        assert res.data["summary"]["total_sales"] == 0
        assert res.data["summary"]["total_quantity"] == 0
        assert Decimal(str(res.data["summary"]["total_sales_revenue"])) == Decimal("0")


# ── Date filtering ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSalesReportDateFilter:

    def test_from_date_filter(self, manager_client, completed_sale):
        """?from=<today> includes today's sales."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{SALES_REPORT_URL}?from={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales"] == 1

    def test_to_date_filter(self, manager_client, completed_sale):
        """?to=<today> includes today's sales."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{SALES_REPORT_URL}?to={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales"] == 1

    def test_future_from_date_returns_zero(self, manager_client, completed_sale):
        """?from=<future date> returns zero sales."""
        res = manager_client.get(f"{SALES_REPORT_URL}?from=2099-01-01")
        assert res.status_code == 200
        assert res.data["summary"]["total_sales"] == 0

    def test_invalid_date_format_returns_400(self, manager_client):
        """Invalid date format returns 400."""
        res = manager_client.get(f"{SALES_REPORT_URL}?from=not-a-date")
        assert res.status_code == 400


# ── Staff filter ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSalesReportStaffFilter:

    def test_staff_summary_present_when_sales_person_param_given(self, manager_client, completed_sale, employee):
        """staff_summary is included when ?sales_person= is provided."""
        res = manager_client.get(f"{SALES_REPORT_URL}?sales_person={employee.username}")
        assert res.status_code == 200
        assert "staff_summary" in res.data

    def test_staff_summary_correct_quantity(self, manager_client, completed_sale, employee):
        """staff_summary total_quantity_sold matches the employee's completed sales."""
        res = manager_client.get(f"{SALES_REPORT_URL}?sales_person={employee.username}")
        assert res.data["staff_summary"]["total_quantity_sold"] == completed_sale.quantity

    def test_staff_summary_absent_without_param(self, manager_client, completed_sale):
        """staff_summary is not included when no sales_person param is given."""
        res = manager_client.get(SALES_REPORT_URL)
        assert "staff_summary" not in res.data

    def test_unknown_sales_person_returns_zero(self, manager_client, completed_sale):
        """?sales_person=<nonexistent> returns staff_summary with zeros."""
        res = manager_client.get(f"{SALES_REPORT_URL}?sales_person=ghost_user")
        assert res.status_code == 200
        assert res.data["staff_summary"]["total_sales"] == 0

    def test_metadata_reflects_sales_person_param(self, manager_client, employee):
        """metadata.sales_person reflects the queried username."""
        res = manager_client.get(f"{SALES_REPORT_URL}?sales_person={employee.username}")
        assert res.data["metadata"]["sales_person"] == employee.username

    def test_metadata_sales_person_defaults_to_all(self, manager_client):
        """metadata.sales_person is 'All' when no filter is applied."""
        res = manager_client.get(SALES_REPORT_URL)
        assert res.data["metadata"]["sales_person"] == "All"
