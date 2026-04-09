import pytest
from decimal import Decimal
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from task_api.models import Supplier, Product


# ── helpers ──────────────────────────────────────────────────────────────────

def make_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ── users ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def manager_user(db):
    group, _ = Group.objects.get_or_create(name="Manager")
    user = User.objects.create_user(
        username="manager", email="manager@test.com", password="pass1234"
    )
    user.groups.add(group)
    return user


@pytest.fixture
def employee(db):
    return User.objects.create_user(
        username="employee", email="employee@test.com", password="pass1234"
    )


# ── authenticated API clients ─────────────────────────────────────────────────

@pytest.fixture
def manager_client(manager_user):
    return make_client(manager_user)


@pytest.fixture
def employee_client(employee):
    return make_client(employee)


@pytest.fixture
def anon_client():
    return APIClient()


# ── core model fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def supplier(db):
    return Supplier.objects.create(
        name="Test Supplier",
        email="supplier@test.com",
        phone="0911000000",
        address="123 Test St",
    )


@pytest.fixture
def product(db, supplier):
    return Product.objects.create(
        name="Test Product",
        sku="SKU-001",
        category="Electronics",
        buying_price=Decimal("50.00"),
        selling_price=Decimal("80.00"),
        current_stock=100,
        reorder_level=10,
        supplier=supplier,
    )
