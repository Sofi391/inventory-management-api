# 📦 Inventory Management System API

[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-green)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-Django%20REST%20Framework-red)](https://www.django-rest-framework.org/)
[![Pytest](https://img.shields.io/badge/Tested%20with-pytest-0a9edc?logo=pytest&logoColor=white)](https://docs.pytest.org/)

A **production-ready Inventory Management REST API** built with Django and Django REST Framework.  
The system provides **secure authentication**, **inventory & stock control**, and **advanced business analytics and reporting** for small to medium-sized businesses.

This project was designed and implemented as a **capstone-level backend system**, focusing on clean architecture, performance, and real-world business logic.
This API is designed to be easily extended into a full-stack production system.

---

## 🌐 Live Demo

You can test the live API here: [Inventory Management API Live](https://task-management-api-ft4y.onrender.com)

---

## ✨ Motivation

This project was built to simulate a **real-world inventory and sales management system** used by businesses to:

- Track products and stock levels
- Manage purchases and sales transactions
- Monitor staff performance
- Analyze revenue, costs, profit, and trends over time

The goal was to go beyond CRUD and implement **meaningful business reports**, **financial summaries**, and **analytics dashboards** that reflect how real production systems operate.

---

## 🛠 Features

### 🔐 Authentication & Authorization
- User signup with **email OTP verification**
- OTP resend & verification flow
- JWT authentication (access & refresh tokens)
- Secure login & logout with token blacklisting
- Password reset via OTP
- Role-based permissions (Manager / Staff)

### 📦 Inventory Management
- Product management with SKU, pricing, stock & reorder level
- Supplier management with product relationships
- Purchase orders with completion workflow
- Sales tracking with stock deduction
- Automatic stock transactions (IN / OUT)
- Low-stock email alerts
- Full stock transaction history

### 🔍 Filtering & Search
- Search by product name, category, SKU, supplier
- Ordering by price, stock level, creation date
- Date range filtering for suppliers
- Paginated API responses

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
- Time-based grouping:
  - Daily
  - Weekly
  - Monthly
  - Yearly
- Timeline trends for analytics dashboards

---

## 🧪 Tests

The project includes a comprehensive **pytest** test suite covering all API endpoints across authentication, inventory, and reporting.

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

### Run the Tests

```bash
pip install pytest pytest-django
pytest
```

---

## ⚙️ Tech Stack

- **Python 3.x**
- **Django 5.x**
- **Django REST Framework**
- **JWT Authentication**
- **PostgreSQL / MySQL**
- Django ORM (advanced annotations & aggregations)
- **pytest** & pytest-django for testing
- Git & GitHub for version control

---

## 🧩 Project Structure

The project is organized into three main apps:

- **accounts**  
  Handles authentication, JWT, and user management.

- **task_api**  
  Core business logic: products, sales, purchases, and inventory operations.

- **reports**  
  Advanced analytics, summaries, performance reports, and trends.

This separation ensures **scalability**, **maintainability**, and clean responsibility boundaries.

---

## 🚀 API Documentation

📮 **Postman Collection:**  
**API Documentation / Postman Collection:** [Click Here](https://documenter.getpostman.com/view/48400327/2sBXVbGYdx)

The API is fully documented via Postman, covering:
- Authentication flows
- CRUD operations
- Reporting and analytics endpoints
- Query parameters and filters

---

## ▶️ Run Locally

```bash
git clone https://github.com/Sofi391/Task_management_api_capstone.git
cd alx_capstone

python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

---

## 🎯 Learning Outcomes

Through building this project, I gained practical experience in:

- Designing real-world REST API architectures
- Implementing secure JWT-based authentication
- Writing efficient Django ORM queries using annotations and aggregations
- Building advanced reporting and analytics systems
- Enforcing permissions and role-based access control
- Translating business requirements into backend logic
- Structuring and maintaining large Django projects cleanly
- Implementing inventory, sales, and stock management workflows
- Integrating email notifications and OTP verification systems

---

## 🔮 Future Improvements

Planned enhancements to further improve scalability and usability:

- Extended sales analytics (advanced trends & performance insights)
- Redis-based caching for heavy reports
- Asynchronous email, OTP, and report generation using Celery
- CSV / Excel export for reports
- API documentation with Swagger / OpenAPI
- React-based frontend dashboard
- Role-based UI views
- Graph and chart visualizations
- Multi-warehouse inventory support

---

## 👨‍💻 About the Developer

Hi! I’m **Sofi (Sofoniyas)** — a **Junior Backend Developer** and **Software Engineering student at AASTU**, and a **graduate of the ALX Backend Engineering Program**.

I specialize in building **secure, scalable, and production-ready backend systems** using modern backend technologies. I enjoy translating real-world business requirements into clean, maintainable, and efficient backend solutions.

I’m particularly interested in:
- Backend system design and RESTful API development
- Authentication, authorization, and security best practices
- Writing clean, scalable, and maintainable backend architectures
- Building data-driven applications and backend services

This project reflects my growth in backend development and my ability to solve real-world problems using clean, maintainable code.

---

### 🤳 Connect with me:
[<img align="left" alt="LinkedIn" width="22px" src="https://cdn.jsdelivr.net/npm/simple-icons@v3/icons/linkedin.svg" />][linkedin]
[<img align="left" alt="GitHub" width="22px" src="https://cdn.jsdelivr.net/npm/simple-icons@v3/icons/github.svg" />][github]  

[linkedin]: https://linkedin.com/in/sofoniyas-alebachew-bb876b33b?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app
[github]: https://github.com/sofi391
