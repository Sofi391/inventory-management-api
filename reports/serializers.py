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


# --- Response serializers for API docs ---

class MetadataSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    from_date = serializers.DateField(allow_null=True, source='from')
    to_date = serializers.DateField(allow_null=True, source='to')


class SalesSummarySerializer(serializers.Serializer):
    total_quantity = serializers.IntegerField()
    total_sales_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sales = serializers.IntegerField()

class StaffSummarySerializer(serializers.Serializer):
    sales_person = serializers.CharField()
    total_quantity_sold = serializers.IntegerField()
    total_sold_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sales = serializers.IntegerField()

class SalesReportResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    summary = SalesSummarySerializer()
    staff_summary = StaffSummarySerializer(required=False)


class PurchaseSummarySerializer(serializers.Serializer):
    total_quantity = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_purchases = serializers.IntegerField()

class PurchaseReportResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    summary = PurchaseSummarySerializer()


class StockReportResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    summary = StockReportSummarySerializer()
    stock_products = ProductReportSerializer(many=True)
    low_stock_products = ProductReportSerializer(many=True)
    out_of_stock_products = ProductReportSerializer(many=True)


class ProfitSummarySerializer(serializers.Serializer):
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_purchase = serializers.DecimalField(max_digits=15, decimal_places=2)
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)

class ProfitVolumeSerializer(serializers.Serializer):
    sales_count = serializers.IntegerField()
    purchases_count = serializers.IntegerField()

class ProfitQuantitySerializer(serializers.Serializer):
    sold_quantity = serializers.IntegerField()
    purchased_quantity = serializers.IntegerField()

class ProfitReportResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    summary = ProfitSummarySerializer()
    volume = ProfitVolumeSerializer()
    quantity = ProfitQuantitySerializer()


class TopSellingProductsResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    top_selling_products = TopSellingReportSerializer(many=True)


class TopSellersResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    top_sellers = TopSellingPerson(many=True)


class SummarySummarySerializer(serializers.Serializer):
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sales_transactions = serializers.IntegerField()
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)

class SummaryReportResponseSerializer(serializers.Serializer):
    metadata = MetadataSerializer()
    summary = SummarySummarySerializer()
    timeline = SummaryTimelineSerializer(many=True)
