import pytest
from decimal import Decimal
from task_api.models import PurchaseOrder

PURCHASE_REPORT_URL = "/reports/purchases/"


@pytest.fixture
def completed_purchase(db, product, supplier):
    return PurchaseOrder.objects.create(
        product=product,
        supplier=supplier,
        quantity=20,
        unit_price=Decimal("50.00"),
        status="Completed",
    )


@pytest.fixture
def pending_purchase(db, product, supplier):
    return PurchaseOrder.objects.create(
        product=product,
        supplier=supplier,
        quantity=8,
        unit_price=Decimal("50.00"),
        status="Pending",
    )


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPurchaseReportAccess:

    def test_manager_can_access_purchase_report(self, manager_client):
        """Manager can access the purchase report endpoint."""
        res = manager_client.get(PURCHASE_REPORT_URL)
        assert res.status_code == 200

    def test_employee_cannot_access_purchase_report(self, employee_client):
        """Employee is forbidden from accessing the purchase report."""
        res = employee_client.get(PURCHASE_REPORT_URL)
        assert res.status_code == 403

    def test_unauthenticated_cannot_access_purchase_report(self, anon_client):
        """Unauthenticated request returns 401."""
        res = anon_client.get(PURCHASE_REPORT_URL)
        assert res.status_code == 401


# ── Summary correctness ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPurchaseReportSummary:

    def test_summary_and_metadata_keys_present(self, manager_client, completed_purchase):
        """Response contains summary and metadata keys."""
        res = manager_client.get(PURCHASE_REPORT_URL)
        assert "summary" in res.data
        assert "metadata" in res.data

    def test_summary_counts_only_completed_purchases(self, manager_client, completed_purchase, pending_purchase):
        """Only Completed purchases are counted in the summary."""
        res = manager_client.get(PURCHASE_REPORT_URL)
        assert res.data["summary"]["total_purchases"] == 1

    def test_summary_total_quantity(self, manager_client, completed_purchase):
        """total_quantity matches the sum of completed purchase quantities."""
        res = manager_client.get(PURCHASE_REPORT_URL)
        assert res.data["summary"]["total_quantity"] == completed_purchase.quantity

    def test_summary_total_cost(self, manager_client, completed_purchase):
        """total_cost equals quantity * unit_price for completed purchases."""
        expected = Decimal(str(completed_purchase.quantity)) * completed_purchase.unit_price
        res = manager_client.get(PURCHASE_REPORT_URL)
        assert Decimal(str(res.data["summary"]["total_cost"])) == expected

    def test_empty_summary_returns_zeros(self, manager_client):
        """With no purchases, all summary values are zero."""
        res = manager_client.get(PURCHASE_REPORT_URL)
        assert res.data["summary"]["total_purchases"] == 0
        assert res.data["summary"]["total_quantity"] == 0
        assert Decimal(str(res.data["summary"]["total_cost"])) == Decimal("0")


# ── Date filtering ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPurchaseReportDateFilter:

    def test_from_date_filter(self, manager_client, completed_purchase):
        """?from=<today> includes today's purchases."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{PURCHASE_REPORT_URL}?from={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_purchases"] == 1

    def test_to_date_filter(self, manager_client, completed_purchase):
        """?to=<today> includes today's purchases."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{PURCHASE_REPORT_URL}?to={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_purchases"] == 1

    def test_future_from_date_returns_zero(self, manager_client, completed_purchase):
        """?from=<future date> returns zero purchases."""
        res = manager_client.get(f"{PURCHASE_REPORT_URL}?from=2099-01-01")
        assert res.status_code == 200
        assert res.data["summary"]["total_purchases"] == 0

    def test_past_to_date_returns_zero(self, manager_client, completed_purchase):
        """?to=<past date> returns zero purchases."""
        res = manager_client.get(f"{PURCHASE_REPORT_URL}?to=2000-01-01")
        assert res.status_code == 200
        assert res.data["summary"]["total_purchases"] == 0

    def test_invalid_date_format_returns_400(self, manager_client):
        """Invalid date format returns 400."""
        res = manager_client.get(f"{PURCHASE_REPORT_URL}?from=not-a-date")
        assert res.status_code == 400

    def test_from_and_to_date_combined(self, manager_client, completed_purchase):
        """?from=<today>&to=<today> includes today's purchases."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{PURCHASE_REPORT_URL}?from={today}&to={today}")
        assert res.status_code == 200
        assert res.data["summary"]["total_purchases"] == 1
