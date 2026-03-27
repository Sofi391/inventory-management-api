from rest_framework import serializers
from task_api.models import Product,Supplier



class SimpleSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ('id','name')

class ProductReportSerializer(serializers.ModelSerializer):
    supplier = SimpleSupplierSerializer()
    class Meta:
        model = Product
        fields = ('name','sku','category','buying_price','current_stock','reorder_level','supplier')


class StockReportSummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    inventory_value = serializers.FloatField()


class TopSellingReportSerializer(serializers.Serializer):
    product_name = serializers.CharField()
    prod_id = serializers.IntegerField()
    total_sells = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_sells_transactions = serializers.IntegerField()


class TopSellingPerson(serializers.Serializer):
    sells_person_name = serializers.CharField()
    sells_person_id = serializers.IntegerField()
    total_sells = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_sells_transactions = serializers.IntegerField()


class SummaryTimelineSerializer(serializers.Serializer):
    time_period = serializers.DateTimeField()
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sales_transactions = serializers.IntegerField()
    total_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
