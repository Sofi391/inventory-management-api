from django.db import models
from django.utils.text import slugify
import unidecode
from django.contrib.auth.models import User



class Supplier(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    slug = models.SlugField(unique=True,blank=True,null=True,max_length=100)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(unidecode.unidecode(self.name))
            slug = base_slug
            counter = 1

            # Handle duplicate slugs
            while Supplier.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.email})"



class Product(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=50)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=100, unique=True,blank=True)

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE,related_name='products',null=True,blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(unidecode.unidecode(self.name))
            slug = base_slug
            counter = 1

            # Handle duplicate slugs
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class StockTransaction(models.Model):
    types = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    transaction_type = models.CharField(choices=types,max_length=3)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True,null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='transactions')

    def __str__(self):
        return f"{self.created_by.username}-{self.product.name}-{self.transaction_type}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price

        if self.transaction_type == 'IN':
            self.product.current_stock += self.quantity
        elif self.transaction_type == 'OUT':
            if self.quantity > self.product.current_stock:
                raise ValueError("Not enough stock for this transaction")
            self.product.current_stock -= self.quantity

        self.product.save()
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    choice = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(choices=choice,max_length=10,default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='purchased')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE,related_name='supplied')

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class Sale(models.Model):
    choice = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]
    quantity = models.PositiveIntegerField()
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(choices=choice,max_length=10,default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='sold')
    sold_by = models.ForeignKey(User, on_delete=models.CASCADE,related_name='sold_by')

    def __str__(self):
        return f"{self.product.name}-{self.sold_by.username} ({self.quantity})"


