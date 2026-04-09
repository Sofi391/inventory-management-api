import logging
import time
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from .permissions import IsManagerOrReadOnly,IsManager,IsManagerOrOwner,IsManagerOrTransactionOwner
from .permissions import MANAGER_GROUP, _is_manager
from django.utils import timezone
from datetime import datetime, time as dt_time, date
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from rest_framework.viewsets import ModelViewSet
from rest_framework import filters, status, serializers
from .models import Product, Supplier, PurchaseOrder, StockTransaction,Sale,User
from .serializers import (ProductSerializer, SupplierSerializer,
                          PurchaseOrderSerializer,StockTransactionSerializer,
                          SaleSerializer,StockTransactionCreateSerializer,
                          )

logger = logging.getLogger('task_api')


def low_stock_alert(product, recipients):
    subject = f"Low Stock Alert: {product.name}"
    message = f"""
Hello,

This is an automated notification to inform you that the stock level for the following product has reached its reorder threshold.

Product details:

Product name: {product.name}

SKU: {product.sku}

Current stock: {product.current_stock}

Reorder level: {product.reorder_level}

Supplier: {product.supplier}

To avoid running out of stock, please consider restocking this product as soon as possible.

You can review the product and take action from the inventory management system.

If this message was sent in error, please ignore it.

Best regards,
The Inventory Management Team
    """
    from_email = f"Inventory Management System<{settings.EMAIL_HOST_USER}>"
    send_mail(subject, message, from_email, recipients, fail_silently=False)
    logger.info("Low stock alert sent | product=%s | stock=%s | recipients=%s", product.name, product.current_stock, recipients)


@extend_schema(tags=['Suppliers'])
class SupplierViewSet(ModelViewSet):
    queryset = Supplier.objects.all().prefetch_related('products')
    serializer_class = SupplierSerializer
    lookup_field = 'slug'
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated,IsManagerOrReadOnly]
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name','products__name','products__category')

    def get_queryset(self):
        queryset = super().get_queryset()
        from_date = self.request.query_params.get('from')
        to_date = self.request.query_params.get('to')
        if from_date:
            from_dt = timezone.make_aware(datetime.combine(date.fromisoformat(from_date), dt_time.min))
            queryset = queryset.filter(products__created_at__gte=from_dt)
        if to_date:
            to_dt = timezone.make_aware(datetime.combine(date.fromisoformat(to_date), dt_time.max))
            queryset = queryset.filter(products__created_at__lte=to_dt)
        return queryset.distinct()


@extend_schema(tags=['Products'])
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all().select_related('supplier')
    serializer_class = ProductSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated,IsManagerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = (filters.SearchFilter,filters.OrderingFilter)
    search_fields = ('name','category','sku','supplier__name')
    ordering_fields = ('buying_price','selling_price','created_at','current_stock','reorder_level')
    ordering = ('-created_at',)

    def get_queryset(self):
        queryset = super().get_queryset()
        supplier = self.request.query_params.get('supplier')
        if supplier:
            queryset = queryset.filter(supplier__name__icontains=supplier)
        return queryset


@extend_schema(tags=['Purchases'])
class PurchaseViewSet(ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('product','supplier')
    serializer_class = PurchaseOrderSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated,IsManager]
    ordering = ('-created_at',)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('product__name','product__category')

    @extend_schema(
        summary='Complete a purchase order',
        description='Marks a pending purchase order as Completed and creates an IN stock transaction to update inventory.',
        responses={
            200: OpenApiResponse(description='Purchase completed successfully.'),
            400: OpenApiResponse(description='Purchase is already completed or a transaction error occurred.'),
        },
    )
    @action(detail=True,methods=['post'],permission_classes=[IsAuthenticated,IsManager])
    def complete(self, request, pk=None):
        start = time.time()
        purchase = self.get_object()
        logger.info("Purchase complete attempt | purchase_id=%s | user=%s", pk, request.user)
        if purchase.status != 'Pending':
            logger.warning("Purchase already %s | purchase_id=%s", purchase.status, pk)
            return Response(
                {"detail": f"Purchase is already {purchase.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            with transaction.atomic():
                purchase.status = "Completed"
                purchase.save()
                StockTransaction.objects.create(
                    transaction_type='IN',
                    quantity=purchase.quantity,
                    unit_price=purchase.unit_price,
                    product=purchase.product,
                    created_by=self.request.user,
                    note=f"Purchase Completed with id:{purchase.id}"
                )
        except Exception as e:
            logger.error("Purchase failed | purchase_id=%s | user=%s | error=%s | elapsed=%.3fs", pk, self.request.user, e, time.time() - start)
            return Response({'detail': 'Something went wrong!'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Purchase completed | purchase_id=%s | product=%s | qty=%s | elapsed=%.3fs", pk, purchase.product.name, purchase.quantity, time.time() - start)
        return Response({'detail': 'Purchase Completed!'})


@extend_schema(tags=['Sales'])
class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all().select_related('product','sold_by')
    serializer_class = SaleSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated,IsManagerOrOwner]
    ordering = ('-created_at',)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('product__name','product__category')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff or self.request.user.groups.filter(name=MANAGER_GROUP).exists():
            queryset = queryset
        else:
            queryset = queryset.filter(sold_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        product = serializer.validated_data['product']
        serializer.save(sold_by=self.request.user,selling_price=product.selling_price)

    @extend_schema(
        summary='Complete a sale',
        description='Marks a pending sale as Completed, deducts stock, creates an OUT stock transaction, and triggers a low-stock alert if needed.',
        responses={
            200: OpenApiResponse(description='Sale completed successfully.'),
            400: OpenApiResponse(description='Sale is already completed or insufficient stock.'),
        },
    )
    @action(detail=True,methods=['post'])
    def complete(self, request, pk=None):
        start = time.time()
        sales = self.get_object()
        logger.info("Sale complete attempt | sale_id=%s | user=%s", pk, request.user)
        if sales.status != 'Pending':
            logger.warning("Sale already %s | sale_id=%s", sales.status, pk)
            return Response(
                {"detail": f"Sales is already {sales.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            with transaction.atomic():
                sales.status = "Completed"
                sales.save()
                StockTransaction.objects.create(
                    transaction_type='OUT',
                    quantity=sales.quantity,
                    unit_price=sales.selling_price,
                    product=sales.product,
                    created_by=self.request.user,
                    note=f"Sales Completed with id:{sales.id}"
                )
                logger.info("Sale completed | sale_id=%s | product=%s | qty=%s | elapsed=%.3fs", pk, sales.product.name, sales.quantity, time.time() - start)
        except Exception as e:
            logger.error("Sale failed | sale_id=%s | user=%s | error=%s | elapsed=%.3fs", pk, self.request.user, e, time.time() - start)
            return Response({'detail': 'Something went wrong!'}, status=status.HTTP_400_BAD_REQUEST)

        if sales.product.current_stock <= sales.product.reorder_level:
            recipients = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
            managers = list(User.objects.filter(groups__name='Manager').values_list('email', flat=True))
            recipients = list(set(recipients + managers))
            try:
                low_stock_alert(sales.product, recipients)
            except Exception as e:
                logger.error("Failed to send low stock alert | product=%s | error=%s", sales.product.name, e)
        return Response({'detail': 'Sales Completed!'})


@extend_schema(
    tags=['Stock Transactions'],
    summary='List stock transactions',
    description='Returns a paginated list of stock transactions. Managers see all transactions; staff see only their own. Supports filtering by ?type=IN or ?type=OUT.',
    parameters=[
        OpenApiParameter(name='type', description='Filter by transaction type: IN or OUT.', required=False, type=str),
    ],
)
class StockTransactionListView(ListAPIView):
    queryset = StockTransaction.objects.all().select_related('product__supplier', 'created_by')
    serializer_class = StockTransactionSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsManagerOrTransactionOwner]

    filter_backends = (filters.SearchFilter,filters.OrderingFilter)
    search_fields = ('product__name','product__category','created_by__username')
    ordering_fields = ('created_at',)
    ordering = ('-created_at',)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.groups.filter(name=MANAGER_GROUP).exists():
            queryset = queryset
        else:
            queryset = queryset.filter(created_by=self.request.user)
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type__icontains=transaction_type)
        return queryset


@extend_schema(
    tags=['Stock Transactions'],
    summary='Create a manual stock transaction',
    description='Allows managers to manually create an IN or OUT stock transaction (e.g. gifted stock, defective write-offs). Triggers a low-stock alert if stock drops to reorder level.',
    request=StockTransactionCreateSerializer,
    responses={
        201: OpenApiResponse(description='Transaction created successfully.'),
        400: OpenApiResponse(description='Insufficient stock or validation error.'),
        403: OpenApiResponse(description='Only managers can create manual transactions.'),
    },
)
class StockTransactionCreate(CreateAPIView):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionCreateSerializer
    permission_classes = [IsAuthenticated,IsManager]

    def perform_create(self, serializer):
        start = time.time()
        try:
            tx = serializer.save(created_by=self.request.user)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)})
        logger.info("Stock transaction created | type=%s | product=%s | qty=%s | user=%s | elapsed=%.3fs",
                    tx.transaction_type, tx.product.name, tx.quantity, self.request.user, time.time() - start)
        if tx.product.current_stock <= tx.product.reorder_level:
            recipients = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
            managers = list(User.objects.filter(groups__name='Manager').values_list('email', flat=True))
            recipients = list(set(recipients + managers))
            try:
                low_stock_alert(tx.product, recipients)
            except Exception as e:
                logger.error("Failed to send low stock alert | product=%s | error=%s", tx.product.name, e)
        return tx
