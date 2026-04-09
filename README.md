# 📦 Inventory Management System API

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-Django%20REST%20Framework-a30000?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![Pytest](https://img.shields.io/badge/Tested%20with-pytest-0a9edc?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![CI](https://github.com/Sofi391/Task_management_api_capstone/actions/workflows/django-ci.yml/badge.svg)](https://github.com/Sofi391/Task_management_api_capstone/actions/workflows/django-ci.yml)
[![Swagger](https://img.shields.io/badge/Swagger-UI-85EA2D?logo=swagger&logoColor=black)](https://task-management-api-ft4y.onrender.com/api/docs/)
[![ReDoc](https://img.shields.io/badge/ReDoc-Docs-8A2BE2?logo=readthedocs&logoColor=white)](https://task-management-api-ft4y.onrender.com/api/redoc/)
[![Loom](https://img.shields.io/badge/Loom-Demo-625DF5?logo=loom&logoColor=white)](https://www.loom.com/share/b73eff61a020489a93e32f39d733edb5)

> 🌐 **Live Demo** — Test the live API at [task-management-api-ft4y.onrender.com](https://task-management-api-ft4y.onrender.com)

> 🎬 **Video Walkthrough** — Watch the full API demo on [Loom](https://www.loom.com/share/b73eff61a020489a93e32f39d733edb5)

> 📸 **Screenshots Gallery** — Browse all API screenshots in the [Gallery](GALLERY.md)

> 📚 **API Docs** — Interactive docs available at [`/api/docs/`](https://task-management-api-ft4y.onrender.com/api/docs/) or [`/api/redoc/`](https://task-management-api-ft4y.onrender.com/api/redoc/)

> 📮 **Postman Collection** — [Click Here](https://documenter.getpostman.com/view/48400327/2sBXVbGYdx)

A **production-ready Inventory Management REST API** built with Django and Django REST Framework. The system provides **secure authentication**, **inventory & stock control**, and **advanced business analytics and reporting** for small to medium-sized businesses.

This project was designed and implemented as a **capstone-level backend system**, focusing on clean architecture, performance, and real-world business logic.

---

## 🔥 Key Highlights

- 🔐 Role-Based Access Control (Manager / Staff)
- ⚡ 200+ Automated Tests (pytest) — All Passing
- 📊 Advanced Reporting System (aggregations, profit tracking, time-based analytics)
- 🔄 Real-world Inventory Workflow (purchase → stock → sales → transactions)
- 📉 Low Stock Detection with Email Notifications
- 🧠 Query Optimization using `select_related` & `prefetch_related`
- 📝 Structured Logging + Centralized Error Handling
- 🐳 Dockerized Setup (optional/local ready)
- 📚 Interactive API Docs (Swagger / ReDoc)
- ✅ CI/CD Pipeline with GitHub Actions (auto-runs full test suite on every push)

---

## ✨ Project Overview

This project was built to simulate a **real-world inventory and sales management system** used by businesses to:

- Track products and stock levels
- Manage purchases and sales transactions
- Monitor staff performance
- Analyze revenue, costs, profit, and trends over time

The goal was to go beyond CRUD and implement **meaningful business reports**, **financial summaries**, and **analytics dashboards** that reflect how real production systems operate.

---

## 🛠 Core Features

### 🔐 Authentication & Authorization
- User signup with **email OTP verification**
- OTP resend & verification flow
- JWT authentication (access & refresh tokens)
- Secure login & logout with token blacklisting
- Password reset via OTP
- Role-based permissions (Manager / Staff)

---

### 📦 Inventory Management
- Product management with SKU, pricing, stock & reorder level
- Supplier management with product relationships
- Purchase orders with completion workflow
- Sales tracking with stock deduction
- Automatic stock transactions (IN / OUT)
- Low-stock email alerts
- Full stock transaction history

---

### 🔍 Filtering & Search
- Search by product name, category, SKU, supplier
- Ordering by price, stock level, creation date
- Date range filtering for suppliers
- Paginated API responses

---

### 📊 Reports & Analytics (Core Feature)

#### 📈 Sales Reports
- Total sales volume and revenue
- Sales filtered by date range
- Per-staff sales summaries

#### 📉 Purchase Reports
- Total purchase quantity and cost
- Time-based filtering

#### 💰 Profit Reports
- Revenue vs cost comparison
- Net profit calculation
- Profit margin percentage
- Product-level profit filtering

#### 🏆 Top Performance Analytics
- Top-selling products
- Top-performing sales staff
- Sorting by quantity, revenue, or transaction count
- Time-frame filters (today, week, month, year, overall)

#### ⏱ Summary & Timeline Reports
- Overall business summary (revenue, sales, profit)
- Time-based grouping (daily, weekly, monthly, yearly)
- Timeline trends for analytics dashboards

---

## ⚙️ Tech Stack

- **Framework**: Django 5.x with Django REST Framework
- **Database**: PostgreSQL (production) / MySQL (local development)
- **Authentication**: JWT with django-rest-framework-simplejwt
- **Documentation**: drf-spectacular with Swagger UI & ReDoc
- **Testing**: pytest & pytest-django
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **ORM**: Django ORM with advanced annotations & aggregations

---

## 🧩 Project Structure

The project is organized into three main Django apps:

- **`accounts`** — Authentication, JWT, and user management
- **`task_api`** — Core business logic: products, sales, purchases, and inventory operations
- **`reports`** — Advanced analytics, summaries, performance reports, and trends

This separation ensures **scalability**, **maintainability**, and clean responsibility boundaries.

---

## 🧪 Tests

The project includes a comprehensive **pytest** test suite with 200+ tests covering all API endpoints across authentication, inventory, and reporting.

### Test Coverage

| Module | Test File | What's Covered |
|---|---|---|
| Authentication | `test_signup.py` | Registration, OTP verification, duplicate users |
| Authentication | `test_login.py` | Login, invalid credentials, JWT token response |
| Authentication | `test_otp.py` | OTP resend, expiry, verification flow |
| Authentication | `test_password_reset.py` | OTP-based password reset flow |
| Inventory | `test_product.py` | CRUD, permissions, search, filtering |
| Inventory | `test_supplier.py` | CRUD, permissions, slug generation |
| Inventory | `test_purchase.py` | Create, complete workflow, stock updates |
| Inventory | `test_sale.py` | Create, complete workflow, stock deduction, atomic rollback |
| Inventory | `test_transaction.py` | Transaction history, manual IN/OUT, edge cases, low-stock alert |
| Reports | `test_sales_report.py` | Access control, summary totals, date filtering, staff filter |
| Reports | `test_purchase_report.py` | Access control, summary totals, date filtering |
| Reports | `test_profit_report.py` | Access control, revenue/cost/profit/margin correctness, product filter |
| Reports | `test_top_selling_report.py` | Access control, sorting, time frames, limit, date filtering |
| Reports | `test_summary_report.py` | Access control, summary correctness, group_by, timeline, date filtering |

### Continuous Integration

All tests are automatically run on every push and pull request to `master` / `main` via **GitHub Actions**. The CI pipeline spins up a PostgreSQL service, runs migrations, and executes the full pytest suite.

Workflow file: [`.github/workflows/django-ci.yml`](.github/workflows/django-ci.yml)

### Run Tests Locally

```bash
pip install pytest pytest-django
pytest
```

---

## 🚀 API Documentation

The API is fully documented using **drf-spectacular**:

| Format | URL | Description |
|---|---|---|
| [![Swagger](https://img.shields.io/badge/Swagger-UI-85EA2D?logo=swagger&logoColor=black)](https://task-management-api-ft4y.onrender.com/api/docs/) | `/api/docs/` | Interactive Swagger UI — try endpoints directly from the browser |
| [![ReDoc](https://img.shields.io/badge/ReDoc-Docs-8A2BE2?logo=readthedocs&logoColor=white)](https://task-management-api-ft4y.onrender.com/api/redoc/) | `/api/redoc/` | Clean ReDoc reference documentation |
| 📄 Raw Schema | `/api/schema/` | OpenAPI 3.0 schema in YAML format |

All endpoints are annotated with `@extend_schema` covering request/response schemas, query parameters, HTTP status codes, and error responses.

---

## ▶️ Run Locally

1️⃣ **Clone the repository**
```bash
git clone https://github.com/Sofi391/Task_management_api_capstone.git
cd alx_capstone
```

2️⃣ **Set up a virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
```

3️⃣ **Install dependencies**
```bash
pip install -r requirements.txt
```

4️⃣ **Configure environment**
```bash
cp .env.example .env
# Edit .env and set DEBUG=True along with your local MySQL credentials
```

5️⃣ **Run migrations and start the server**
```bash
python manage.py migrate
python manage.py runserver
```

---

## 🐳 Run with Docker

The project is fully containerized using **Docker** and **Docker Compose**. The setup spins up two services:

- `db` — PostgreSQL 15 with a persistent volume and health check
- `web` — Django app that waits for the database, runs migrations, then starts Gunicorn

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) installed
- A `.env` file in the project root. Copy the provided example and fill in your values:

```bash
cp .env.example .env
```

See [`.env.example`](.env.example) for all required variables.

### Start the project

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Other useful commands

```bash
# Run in detached mode
docker compose up --build -d

# Stop containers
docker compose down

# Stop and remove volumes (wipes the database)
docker compose down -v
```

---

## 🎯 Learning Outcomes

- **REST API Architecture**: Designing real-world, production-grade API systems
- **JWT Authentication**: Secure token-based auth with OTP flows and token blacklisting
- **Django ORM**: Advanced queries using annotations, aggregations, and optimizations
- **Reporting Systems**: Building financial summaries and time-based analytics
- **Role-Based Access Control**: Enforcing permissions across all endpoints
- **Inventory Workflows**: Translating business logic into clean backend operations
- **Email Integration**: OTP verification and low-stock notification systems
- **CI/CD with GitHub Actions**: Automating the full test suite on every push

---

## 🔮 Future Improvements

- Extended sales analytics (advanced trends & performance insights)
- Redis-based caching for heavy reports
- Asynchronous email, OTP, and report generation using Celery
- CSV / Excel export for reports
- React-based frontend dashboard
- Graph and chart visualizations
- Multi-warehouse inventory support

---

## 👨💻 About the Developer

Hi! I'm **Sofi (Sofoniyas)** — a **Backend Developer** and **Software Engineering student at AASTU**, and a **graduate of the ALX Backend Engineering Program**.

I specialize in building **secure, scalable, and production-ready backend systems** using modern backend technologies. I enjoy translating real-world business requirements into clean, maintainable, and efficient backend solutions.

I'm particularly interested in:

- **Backend System Architecture**: Designing scalable, maintainable backend systems
- **AI Integration**: Building production-ready AI-powered applications with RAG
- **Testing & Quality Assurance**: Comprehensive testing strategies and best practices
- **Security Implementation**: Authentication, authorization, and production security
- **Database Design**: Advanced database operations including vector databases
- **API Development**: RESTful API design with proper documentation and testing

---

### 🤝 Connect with Me

<p align="center">
  <a href="https://linkedin.com/in/sofoniyas-alebachew-bb876b33b">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" />
  </a>
  &nbsp;&nbsp;
  <a href="https://github.com/Sofi391">
    <img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
  </a>
</p>

---

*Built with ❤️ using Django REST Framework and comprehensive testing practices*
