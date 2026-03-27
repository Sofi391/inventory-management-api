from rest_framework import serializers
from .models import Product,Supplier,StockTransaction,PurchaseOrder,Sale
from django.contrib.auth.models import User



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class SimpleProductSerializer(serializers.ModelSerializer):
    supplier = serializers.SlugRelatedField(slug_field='slug',queryset=Supplier.objects.all())
    class Meta:
        model = Product
        fields = ('id', 'name', 'supplier')


class SupplierSerializer(serializers.ModelSerializer):
    products = serializers.SlugRelatedField(slug_field='slug',read_only=True,many=True)
    class Meta:
        model = Supplier
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    supplier = serializers.SlugRelatedField(slug_field='slug',queryset=Supplier.objects.all())
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['current_stock', ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(slug_field='slug',queryset=Product.objects.all())
    supplier = serializers.SlugRelatedField(slug_field='slug',queryset=Supplier.objects.all())
    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        read_only_fields = ['status','unit_price']
    def validate(self, data):
        product = data['product']
        supplier = data['supplier']
        if product.supplier != supplier:
            raise serializers.ValidationError("This supplier doesn't supply this product.")
        if data['quantity'] == 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return data
    def create(self, validated_data):
        product = validated_data['product']
        return PurchaseOrder.objects.create(unit_price=product.buying_price,**validated_data)


class SaleSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(slug_field='slug',queryset=Product.objects.all())
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['status','sold_by','selling_price']
    def validate(self, data):
        if data['quantity'] > data['product'].current_stock:
            raise serializers.ValidationError("Out of stock.")
        if data['quantity'] == 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return data


class StockTransactionSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    class Meta:
        model = StockTransaction
        fields = '__all__'


class StockTransactionCreateSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(slug_field='slug',queryset=Product.objects.all())
    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ['total_price','created_by']

