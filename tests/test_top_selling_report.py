import pytest
from decimal import Decimal
from task_api.models import Sale

TOP_SELLING_URL = "/reports/top-selling/"


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
def second_product(db, supplier):
    from task_api.models import Product
    return Product.objects.create(
        name="Second Product",
        sku="SKU-002",
        category="Electronics",
        buying_price=Decimal("30.00"),
        selling_price=Decimal("60.00"),
        current_stock=100,
        reorder_level=10,
        supplier=supplier,
    )


@pytest.fixture
def second_completed_sale(db, second_product, employee):
    return Sale.objects.create(
        product=second_product,
        sold_by=employee,
        quantity=25,
        selling_price=second_product.selling_price,
        status="Completed",
    )


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingAccess:

    def test_manager_can_access(self, manager_client):
        """Manager can access the top selling products endpoint."""
        res = manager_client.get(TOP_SELLING_URL)
        assert res.status_code == 200

    def test_employee_cannot_access(self, employee_client):
        """Employee is forbidden from accessing the top selling products report."""
        res = employee_client.get(TOP_SELLING_URL)
        assert res.status_code == 403

    def test_unauthenticated_cannot_access(self, anon_client):
        """Unauthenticated request returns 401."""
        res = anon_client.get(TOP_SELLING_URL)
        assert res.status_code == 401


# ── Response structure ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingStructure:

    def test_response_keys_present(self, manager_client):
        """Response contains top_selling_products and metadata keys."""
        res = manager_client.get(TOP_SELLING_URL)
        assert "top_selling_products" in res.data
        assert "metadata" in res.data

    def test_product_entry_keys(self, manager_client, completed_sale):
        """Each product entry contains expected fields."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        products = res.data["top_selling_products"]
        assert len(products) > 0
        entry = products[0]
        for key in ("product_name", "prod_id", "total_sells", "total_revenue", "total_sells_transactions"):
            assert key in entry

    def test_empty_returns_empty_list(self, manager_client):
        """With no sales, top_selling_products is an empty list."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        assert res.data["top_selling_products"] == []


# ── Data correctness ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingData:

    def test_only_completed_sales_included(self, manager_client, product, employee):
        """Pending sales are excluded from the top selling report."""
        Sale.objects.create(
            product=product, sold_by=employee,
            quantity=50, selling_price=product.selling_price,
            status="Pending",
        )
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        assert res.data["top_selling_products"] == []

    def test_total_sells_is_correct(self, manager_client, completed_sale, product):
        """total_sells matches the sum of completed sale quantities for the product."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        entry = res.data["top_selling_products"][0]
        assert entry["total_sells"] == completed_sale.quantity

    def test_total_revenue_is_correct(self, manager_client, completed_sale, product):
        """total_revenue equals quantity * selling_price for the product."""
        expected = float(completed_sale.quantity * product.selling_price)
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        assert res.data["top_selling_products"][0]["total_revenue"] == expected

    def test_total_sells_transactions_is_correct(self, manager_client, completed_sale):
        """total_sells_transactions counts the number of sale records."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        assert res.data["top_selling_products"][0]["total_sells_transactions"] == 1


# ── Sorting ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingSorting:

    def test_default_sort_is_by_sells(self, manager_client, completed_sale, second_completed_sale):
        """Default sort (sells) returns highest quantity product first."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        products = res.data["top_selling_products"]
        assert products[0]["total_sells"] >= products[1]["total_sells"]

    def test_sort_by_revenue(self, manager_client, completed_sale, second_completed_sale):
        """?sort_by=revenue returns highest revenue product first."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall&sort_by=revenue")
        products = res.data["top_selling_products"]
        assert products[0]["total_revenue"] >= products[1]["total_revenue"]

    def test_sort_by_transactions(self, manager_client, completed_sale, second_completed_sale):
        """?sort_by=transactions returns highest transaction count product first."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall&sort_by=transactions")
        products = res.data["top_selling_products"]
        assert products[0]["total_sells_transactions"] >= products[1]["total_sells_transactions"]

    def test_invalid_sort_by_returns_400(self, manager_client):
        """?sort_by=<invalid> returns 400."""
        res = manager_client.get(f"{TOP_SELLING_URL}?sort_by=invalid")
        assert res.status_code == 400


# ── Time frame ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingTimeFrame:

    def test_time_overall_includes_all_sales(self, manager_client, completed_sale):
        """?time=overall includes all completed sales regardless of date."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall")
        assert len(res.data["top_selling_products"]) == 1

    def test_time_today_includes_todays_sales(self, manager_client, completed_sale):
        """?time=today includes sales created today."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=today")
        assert len(res.data["top_selling_products"]) == 1

    def test_time_week_includes_recent_sales(self, manager_client, completed_sale):
        """?time=week includes sales from the last 7 days."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=week")
        assert len(res.data["top_selling_products"]) == 1

    def test_invalid_time_frame_returns_400(self, manager_client):
        """?time=<invalid> returns 400."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=invalid")
        assert res.status_code == 400


# ── Limit ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingLimit:

    def test_limit_restricts_results(self, manager_client, completed_sale, second_completed_sale):
        """?limit=1 returns only one product."""
        res = manager_client.get(f"{TOP_SELLING_URL}?time=overall&limit=1")
        assert len(res.data["top_selling_products"]) == 1

    def test_invalid_limit_returns_400(self, manager_client):
        """?limit=abc returns 400."""
        res = manager_client.get(f"{TOP_SELLING_URL}?limit=abc")
        assert res.status_code == 400

    def test_zero_limit_returns_400(self, manager_client):
        """?limit=0 returns 400."""
        res = manager_client.get(f"{TOP_SELLING_URL}?limit=0")
        assert res.status_code == 400

    def test_metadata_reflects_limit(self, manager_client):
        """metadata.limit reflects the requested limit value."""
        res = manager_client.get(f"{TOP_SELLING_URL}?limit=5")
        assert res.data["metadata"]["limit"] == 5


# ── Date filtering ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTopSellingDateFilter:

    def test_from_date_includes_todays_sales(self, manager_client, completed_sale):
        """?from=<today> includes today's sales."""
        from django.utils.timezone import now
        today = now().date().isoformat()
        res = manager_client.get(f"{TOP_SELLING_URL}?from={today}")
        assert res.status_code == 200
        assert len(res.data["top_selling_products"]) == 1

    def test_future_from_date_returns_empty(self, manager_client, completed_sale):
        """?from=<future date> returns empty list."""
        res = manager_client.get(f"{TOP_SELLING_URL}?from=2099-01-01")
        assert res.status_code == 200
        assert res.data["top_selling_products"] == []

    def test_invalid_date_returns_400(self, manager_client):
        """Invalid date format returns 400."""
        res = manager_client.get(f"{TOP_SELLING_URL}?from=not-a-date")
        assert res.status_code == 400
