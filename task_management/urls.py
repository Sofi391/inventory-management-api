from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('manage/',include('task_api.urls')),
    path('accounts/',include('accounts.urls')),
    path('reports/',include('reports.urls')),
]
