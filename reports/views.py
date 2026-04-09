import logging
import time
from datetime import timedelta, datetime, time as dt_time
from django.db.models.functions import TruncDay,TruncWeek,TruncMonth,TruncYear
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from .permissions import IsManager
from .serializers import ProductReportSerializer,StockReportSummarySerializer,TopSellingReportSerializer,TopSellingPerson,SummaryTimelineSerializer
from task_api.models import Sale,PurchaseOrder,Product
from django.utils import timezone
from django.db.models import Q, F, Sum, Avg, Count, Max, Min, ExpressionWrapper, DecimalField
from django.db import DatabaseError
from decimal import Decimal
from datetime import date

logger = logging.getLogger('reports')

VALID_SORT_FIELDS = {'sells', 'revenue', 'transactions'}
VALID_TIME_FRAMES = {'today', 'week', 'month', 'year', 'overall'}
VALID_GROUP_BY = {'day', 'week', 'month', 'year'}


def validate_date_params(from_date, to_date):
    """Raises ValueError if date params are provided but in wrong format."""
    if from_date:
        date.fromisoformat(from_date)
    if to_date:
        date.fromisoformat(to_date)


def date_to_datetime_range(from_date, to_date):
    """Convert date strings to timezone-aware datetime boundaries for index-friendly filtering."""
    from_dt = timezone.make_aware(datetime.combine(date.fromisoformat(from_date), dt_time.min)) if from_date else None
    to_dt = timezone.make_aware(datetime.combine(date.fromisoformat(to_date), dt_time.max)) if to_date else None
    return from_dt, to_dt


@extend_schema(
    tags=['Reports'],
    summary='Sales report',
    description='Returns a summary of completed sales including total quantity, revenue, and transaction count. Optionally filter by date range and/or a specific sales person.',
    parameters=[
        OpenApiParameter(name='from', description='Start date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='to', description='End date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='sales_person', description='Filter by staff username to get their personal sales summary.', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='Sales summary with optional staff breakdown and metadata.'),
        400: OpenApiResponse(description='Invalid date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class SalesReportView(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        sales_person = request.query_params.get('sales_person')
        logger.info("Sales report request | user=%s | from=%s | to=%s | sales_person=%s", request.user, from_date, to_date, sales_person)

        try:
            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            sales = Sale.objects.filter(status='Completed')
            if from_dt:
                sales = sales.filter(created_at__gte=from_dt)
            if to_dt:
                sales = sales.filter(created_at__lte=to_dt)

            revenue_expression = ExpressionWrapper(
                F('quantity')*F('selling_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            sales_summary = sales.aggregate(
                total_quantity=Sum('quantity',default=0),
                total_revenue=Sum(revenue_expression,default=0),
                total_sales=Count('id'),
            )

            response = {
                'summary': {
                    'total_quantity': sales_summary['total_quantity'],
                    'total_sales_revenue': sales_summary['total_revenue'],
                    'total_sales': sales_summary['total_sales'],
                },
            }

            if sales_person:
                sold_by = sales.filter(sold_by__username=sales_person)
                personal_summary = sold_by.aggregate(
                    total_quantity_sold=Sum('quantity',default=0),
                    total_revenue=Sum(revenue_expression,default=0),
                    total_sales=Count('id'),
                )
                response['staff_summary'] = {
                    'sales_person': sales_person,
                    'total_quantity_sold': personal_summary['total_quantity_sold'],
                    'total_sold_revenue': personal_summary['total_revenue'],
                    'total_sales': personal_summary['total_sales'],
                }

            response['metadata'] = {
                'generated_at': timezone.now(),
                'from': from_date,
                'to': to_date,
                'sales_person': sales_person if sales_person else 'All',
            }
            logger.info("Sales report generated | user=%s | elapsed=%.3fs", request.user, time.time() - start)
            return Response(response, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning("Sales report bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Sales report DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the sales report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Sales report unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the sales report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Reports'],
    summary='Purchase report',
    description='Returns a summary of completed purchase orders including total quantity, cost, and purchase count. Supports date range filtering.',
    parameters=[
        OpenApiParameter(name='from', description='Start date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='to', description='End date filter (YYYY-MM-DD).', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='Purchase summary with metadata.'),
        400: OpenApiResponse(description='Invalid date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class PurchaseReportView(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        logger.info("Purchase report request | user=%s | from=%s | to=%s", request.user, from_date, to_date)

        try:
            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            purchase = PurchaseOrder.objects.filter(status='Completed')
            if from_dt:
                purchase = purchase.filter(created_at__gte=from_dt)
            if to_dt:
                purchase = purchase.filter(created_at__lte=to_dt)

            cost_expression = ExpressionWrapper(
                F('quantity')*F('unit_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            purchase_summary = purchase.aggregate(
                total_quantity=Sum('quantity',default=0),
                total_cost=Sum(cost_expression,default=0),
                total_purchases=Count('id'),
            )

            logger.info("Purchase report generated | user=%s | elapsed=%.3fs", request.user, time.time() - start)
            return Response({
                'metadata': {
                    'generated_at': timezone.now(),
                    'from': from_date,
                    'to': to_date,
                },
                'summary': {
                    'total_quantity': purchase_summary['total_quantity'],
                    'total_cost': purchase_summary['total_cost'],
                    'total_purchases': purchase_summary['total_purchases'],
                },
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning("Purchase report bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Purchase report DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the purchase report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Purchase report unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the purchase report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Reports'],
    summary='Stock inventory report',
    description='Returns a full inventory snapshot including in-stock, low-stock, and out-of-stock products with total inventory value. Supports filtering by product name or category and date range.',
    parameters=[
        OpenApiParameter(name='name', description='Filter by product name or category (case-insensitive).', required=False, type=str),
        OpenApiParameter(name='from', description='Start date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='to', description='End date filter (YYYY-MM-DD).', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='Inventory summary with stock, low-stock, and out-of-stock product lists.'),
        400: OpenApiResponse(description='Invalid date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class StockReport(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        name = request.query_params.get('name')
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        logger.info("Stock report request | user=%s | name=%s | from=%s | to=%s", request.user, name, from_date, to_date)

        try:
            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            products = Product.objects.select_related('supplier').all()
            if name:
                products = products.filter(
                    Q(name__icontains=name) |
                    Q(category__icontains=name)
                )
            if from_dt:
                products = products.filter(created_at__gte=from_dt)
            if to_dt:
                products = products.filter(created_at__lte=to_dt)

            inventory_value = ExpressionWrapper(
                F('current_stock')*F('buying_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            in_stock = products.filter(current_stock__gt=0).aggregate(
                total_products=Count('id'),
                total_quantity=Sum('current_stock',default=0),
                inventory_value=Sum(inventory_value,default=0),
            )

            stock_products = products.filter(current_stock__gt=0).order_by('-created_at')
            out_stock = products.filter(current_stock__lte=0).order_by('-created_at')
            low_stock = products.filter(current_stock__gt=0, current_stock__lte=F('reorder_level')).order_by('-created_at')

            logger.info("Stock report generated | user=%s | elapsed=%.3fs", request.user, time.time() - start)
            return Response({
                'metadata': {
                    'generated_at': timezone.now(),
                    'from': from_date,
                    'to': to_date,
                    'filter_name': name if name else 'All',
                },
                'summary': StockReportSummarySerializer(in_stock).data,
                'stock_products': ProductReportSerializer(stock_products, many=True).data,
                'low_stock_products': ProductReportSerializer(low_stock, many=True).data,
                'out_of_stock_products': ProductReportSerializer(out_stock, many=True).data,
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning("Stock report bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Stock report DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the stock report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Stock report unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the stock report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Reports'],
    summary='Profit report',
    description='Returns revenue, cost of goods sold, gross profit, and profit margin for completed sales. Supports date range and product name filtering.',
    parameters=[
        OpenApiParameter(name='from', description='Start date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='to', description='End date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='product', description='Filter by product name (case-insensitive partial match).', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='Profit summary with revenue, cost, gross profit, margin, and volume breakdown.'),
        400: OpenApiResponse(description='Invalid date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class ProfitReport(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        product = request.query_params.get('product')
        logger.info("Profit report request | user=%s | from=%s | to=%s | product=%s", request.user, from_date, to_date, product)

        try:
            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            total_sales = Sale.objects.filter(status='Completed')
            total_purchase = PurchaseOrder.objects.filter(status='Completed')

            if from_dt:
                total_sales = total_sales.filter(created_at__gte=from_dt)
                total_purchase = total_purchase.filter(created_at__gte=from_dt)
            if to_dt:
                total_sales = total_sales.filter(created_at__lte=to_dt)
                total_purchase = total_purchase.filter(created_at__lte=to_dt)
            if product:
                total_sales = total_sales.filter(product__name__icontains=product)
                total_purchase = total_purchase.filter(product__name__icontains=product)

            total_cost_calc = ExpressionWrapper(
                F('quantity')*F('product__buying_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )
            total_revenue_calc = ExpressionWrapper(
                F('quantity')*F('selling_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )
            total_purchase_calc = ExpressionWrapper(
                F('quantity')*F('unit_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            total_purchases = total_purchase.aggregate(
                total_purchases=Sum(total_purchase_calc,default=0),
                purchase_count=Count('id'),
                total_quantity=Sum('quantity',default=0),
            )
            total_revenue = total_sales.aggregate(
                total_revenue=Sum(total_revenue_calc,default=0),
                total_cost=Sum(total_cost_calc,default=0),
                sales_count=Count('id'),
                total_quantity=Sum('quantity', default=0),
            )

            profit = total_revenue['total_revenue'] - total_revenue['total_cost']
            profit_margin = ((profit / total_revenue['total_revenue'] * 100).quantize(Decimal('.01'))
                if total_revenue['total_revenue'] > 0
                 else Decimal('0.00')
                             )

            logger.info("Profit report generated | user=%s | profit=%s | elapsed=%.3fs", request.user, profit, time.time() - start)
            return Response({
                'metadata': {
                    'generated_at': timezone.now(),
                    'from': from_date,
                    'to': to_date,
                    'filter_product': product if product else "All Products",
                },
                'summary': {
                    'total_cost': total_revenue['total_cost'],
                    'total_revenue': total_revenue['total_revenue'],
                    'total_purchase':total_purchases['total_purchases'],
                    'gross_profit': profit,
                    'profit_margin': profit_margin,
                },
                'volume': {
                    'sales_count': total_revenue['sales_count'],
                    'purchases_count': total_purchases['purchase_count'],
                },
                'quantity': {
                    'sold_quantity': total_revenue['total_quantity'],
                    'purchased_quantity': total_purchases['total_quantity'],
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning("Profit report bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Profit report DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the profit report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Profit report unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the profit report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Reports'],
    summary='Top selling products',
    description='Returns the top-selling products ranked by quantity sold, revenue, or transaction count. Supports time frame presets (today, week, month, year, overall), custom date range, and result limit.',
    parameters=[
        OpenApiParameter(name='sort_by', description='Sort field: sells (default), revenue, or transactions.', required=False, type=str),
        OpenApiParameter(name='time', description='Time frame preset: today, week (default), month, year, or overall.', required=False, type=str),
        OpenApiParameter(name='limit', description='Maximum number of results to return (default: 10).', required=False, type=int),
        OpenApiParameter(name='from', description='Custom start date filter (YYYY-MM-DD). Overrides time preset.', required=False, type=str),
        OpenApiParameter(name='to', description='Custom end date filter (YYYY-MM-DD). Overrides time preset.', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='List of top-selling products with sales totals and metadata.'),
        400: OpenApiResponse(description='Invalid sort_by, time frame, limit, or date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class TopSellingProducts(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        sort_by = request.query_params.get('sort_by', 'sells')
        time_frame = request.query_params.get('time', 'week')
        logger.info("Top selling products request | user=%s | time_frame=%s | sort_by=%s", request.user, time_frame, sort_by)

        try:
            try:
                limit = int(request.query_params.get('limit', 10))
                if limit <= 0:
                    raise ValueError("limit must be a positive integer.")
            except (ValueError, TypeError):
                logger.warning("Top selling products invalid limit | user=%s | limit=%s", request.user, request.query_params.get('limit'))
                return Response({'detail': 'Invalid limit value. Must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if sort_by not in VALID_SORT_FIELDS:
                logger.warning("Top selling products invalid sort_by | user=%s | sort_by=%s", request.user, sort_by)
                return Response({'detail': f"Invalid sort_by value. Choose from: {', '.join(VALID_SORT_FIELDS)}."}, status=status.HTTP_400_BAD_REQUEST)

            if time_frame not in VALID_TIME_FRAMES:
                logger.warning("Top selling products invalid time_frame | user=%s | time_frame=%s", request.user, time_frame)
                return Response({'detail': f"Invalid time value. Choose from: {', '.join(VALID_TIME_FRAMES)}."}, status=status.HTTP_400_BAD_REQUEST)

            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            now = timezone.now()
            sort_mapping = {
                'sells': '-total_sells',
                'revenue': '-total_revenue',
                'transactions': '-total_sells_transactions',
            }
            time_mapping = {
                'today': now - timedelta(days=1),
                'week': now - timedelta(days=7),
                'month': now - timedelta(days=30),
                'year': now - timedelta(days=365),
                'overall': None,
            }

            sells = Sale.objects.filter(status='Completed')
            filter_time = time_mapping.get(time_frame)
            if not (from_date or to_date) and filter_time:
                sells = sells.filter(created_at__gte=filter_time)
            if from_dt:
                sells = sells.filter(created_at__gte=from_dt)
            if to_dt:
                sells = sells.filter(created_at__lte=to_dt)

            total_revenue_calc = ExpressionWrapper(
                F('quantity') * F('selling_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            total_sells = sells.values(
                prod_id=F('product'),
                product_name=F('product__name')
            ).annotate(
                total_sells=Sum('quantity', default=0),
                total_revenue=Sum(total_revenue_calc, default=0),
                total_sells_transactions=Count('id'),
            ).order_by(sort_mapping[sort_by])[:limit]

            logger.info("Top selling products generated | user=%s | elapsed=%.3fs", request.user, time.time() - start)
            return Response({
                'metadata': {
                    'generated_at': timezone.now(),
                    'from': from_date,
                    'to': to_date,
                    'limit': limit,
                },
                'top_selling_products': TopSellingReportSerializer(total_sells, many=True).data,
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning("Top selling products bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Top selling products DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the top selling products report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Top selling products unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the top selling products report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Reports'],
    summary='Top performing sales staff',
    description='Returns the top-performing sales staff ranked by quantity sold, revenue, or transaction count. Supports time frame presets, custom date range, and result limit.',
    parameters=[
        OpenApiParameter(name='sort_by', description='Sort field: sells (default), revenue, or transactions.', required=False, type=str),
        OpenApiParameter(name='time', description='Time frame preset: today, week (default), month, year, or overall.', required=False, type=str),
        OpenApiParameter(name='limit', description='Maximum number of results to return (default: 10).', required=False, type=int),
        OpenApiParameter(name='from', description='Custom start date filter (YYYY-MM-DD). Overrides time preset.', required=False, type=str),
        OpenApiParameter(name='to', description='Custom end date filter (YYYY-MM-DD). Overrides time preset.', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='List of top sellers with sales totals and metadata.'),
        400: OpenApiResponse(description='Invalid sort_by, time frame, limit, or date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class TopSellingPersonsView(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        sort_by = request.query_params.get('sort_by', 'sells')
        time_frame = request.query_params.get('time', 'week')
        logger.info("Top sellers request | user=%s | time_frame=%s | sort_by=%s", request.user, time_frame, sort_by)

        try:
            try:
                limit = int(request.query_params.get('limit', 10))
                if limit <= 0:
                    raise ValueError("limit must be a positive integer.")
            except (ValueError, TypeError):
                logger.warning("Top sellers invalid limit | user=%s | limit=%s", request.user, request.query_params.get('limit'))
                return Response({'detail': 'Invalid limit value. Must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if sort_by not in VALID_SORT_FIELDS:
                logger.warning("Top sellers invalid sort_by | user=%s | sort_by=%s", request.user, sort_by)
                return Response({'detail': f"Invalid sort_by value. Choose from: {', '.join(VALID_SORT_FIELDS)}."}, status=status.HTTP_400_BAD_REQUEST)

            if time_frame not in VALID_TIME_FRAMES:
                logger.warning("Top sellers invalid time_frame | user=%s | time_frame=%s", request.user, time_frame)
                return Response({'detail': f"Invalid time value. Choose from: {', '.join(VALID_TIME_FRAMES)}."}, status=status.HTTP_400_BAD_REQUEST)

            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            now = timezone.now()
            sort_mapping = {
                'sells': '-total_sells',
                'revenue': '-total_revenue',
                'transactions': '-total_sells_transactions',
            }
            time_mapping = {
                'today': now - timedelta(days=1),
                'week': now - timedelta(days=7),
                'month': now - timedelta(days=30),
                'year': now - timedelta(days=365),
                'overall': None,
            }

            sells = Sale.objects.filter(status='Completed')
            filter_time = time_mapping.get(time_frame)
            if not (from_date or to_date) and filter_time:
                sells = sells.filter(created_at__gte=filter_time)
            if from_dt:
                sells = sells.filter(created_at__gte=from_dt)
            if to_dt:
                sells = sells.filter(created_at__lte=to_dt)

            total_revenue_calc = ExpressionWrapper(
                F('quantity') * F('selling_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            total_sells = sells.values(
                sells_person_id=F('sold_by'),
                sells_person_name=F('sold_by__username')
            ).annotate(
                total_sells=Sum('quantity', default=0),
                total_revenue=Sum(total_revenue_calc, default=0),
                total_sells_transactions=Count('id'),
            ).order_by(sort_mapping[sort_by])[:limit]

            logger.info("Top sellers generated | user=%s | elapsed=%.3fs", request.user, time.time() - start)
            return Response({
                'metadata': {
                    'generated_at': timezone.now(),
                    'active_time_frame': time_frame if not (from_date or to_date) else "custom",
                    'from': from_date,
                    'to': to_date,
                    'limit': limit,
                },
                'top_sellers': TopSellingPerson(total_sells, many=True).data,
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning("Top sellers bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Top sellers DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the top sellers report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Top sellers unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the top sellers report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Reports'],
    summary='Business summary and timeline report',
    description='Returns an overall business summary (total sales, revenue, profit, margin) and a timeline breakdown grouped by day, week, month, or year. Supports date range filtering.',
    parameters=[
        OpenApiParameter(name='group_by', description='Timeline grouping: day (default), week, month, or year.', required=False, type=str),
        OpenApiParameter(name='from', description='Start date filter (YYYY-MM-DD).', required=False, type=str),
        OpenApiParameter(name='to', description='End date filter (YYYY-MM-DD).', required=False, type=str),
    ],
    responses={
        200: OpenApiResponse(description='Business summary with profit metrics and grouped timeline data.'),
        400: OpenApiResponse(description='Invalid group_by value or date format.'),
        403: OpenApiResponse(description='Manager access only.'),
    },
)
class SummaryReports(APIView):
    permission_classes = (IsManager,)

    def get(self, request):
        start = time.time()
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        group_by = request.query_params.get('group_by', 'day')
        logger.info("Summary report request | user=%s | from=%s | to=%s | group_by=%s", request.user, from_date, to_date, group_by)

        try:
            if group_by not in VALID_GROUP_BY:
                logger.warning("Summary report invalid group_by | user=%s | group_by=%s", request.user, group_by)
                return Response({'detail': f"Invalid group_by value. Choose from: {', '.join(VALID_GROUP_BY)}."}, status=status.HTTP_400_BAD_REQUEST)

            validate_date_params(from_date, to_date)
            from_dt, to_dt = date_to_datetime_range(from_date, to_date)

            trunc_map = {
                'day': TruncDay,
                'week': TruncWeek,
                'month': TruncMonth,
                'year': TruncYear,
            }

            total_revenue_calc = ExpressionWrapper(
                F('quantity') * F('product__selling_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )
            total_cost_calc = ExpressionWrapper(
                F('quantity') * F('product__buying_price'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )

            sales = Sale.objects.filter(status='Completed')
            if from_dt:
                sales = sales.filter(created_at__gte=from_dt)
            if to_dt:
                sales = sales.filter(created_at__lte=to_dt)

            sales_summary = sales.aggregate(
                total_sales=Sum('quantity', default=0),
                total_revenue=Sum(total_revenue_calc, default=0),
                total_cost=Sum(total_cost_calc, default=0),
                total_sales_transactions=Count('id'),
            )

            profit = sales_summary['total_revenue'] - sales_summary['total_cost']
            profit_margin = ((profit / sales_summary['total_revenue'] * 100).quantize(Decimal('0.01'))
                if sales_summary['total_revenue'] > 0
                else Decimal('0.00')
                             )
            sales_list = sales.annotate(
                time_period=trunc_map[group_by]('created_at')
            ).values('time_period').annotate(
                total_sales=Sum('quantity', default=0),
                total_revenue=Sum(total_revenue_calc, default=0),
                total_profit=Sum(total_revenue_calc - total_cost_calc, default=0),
                total_sales_transactions=Count('id'),
            ).order_by('-time_period')

            logger.info("Summary report generated | user=%s | group_by=%s | elapsed=%.3fs", request.user, group_by, time.time() - start)
            return Response({
                'metadata': {
                    'generated_at': timezone.now(),
                    'from': from_date,
                    'to': to_date,
                    'time_period': group_by,
                },
                'summary': {
                    'total_sales': sales_summary['total_sales'],
                    'total_revenue': sales_summary['total_revenue'],
                    'total_sales_transactions': sales_summary['total_sales_transactions'],
                    'gross_profit': profit,
                    'profit_margin': profit_margin,
                },
                'timeline': SummaryTimelineSerializer(sales_list, many=True).data,
            })

        except ValueError as e:
            logger.warning("Summary report bad request | user=%s | error=%s", request.user, e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error("Summary report DB error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'A database error occurred while generating the summary report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error("Summary report unexpected error | user=%s | error=%s", request.user, e, exc_info=True)
            return Response({'detail': 'An unexpected error occurred while generating the summary report.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
