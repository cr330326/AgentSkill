# Django REST Framework 最佳实践

本文件包含 DRF 项目的推荐实践。这些是软性建议而非硬性规则，
遵循可以获得更好的性能、安全性和可维护性。

## 目录
- [BP-01 ~ BP-04] 分页与过滤
- [BP-05 ~ BP-08] 性能优化
- [BP-09 ~ BP-12] 限流与安全
- [BP-13 ~ BP-16] 测试策略
- [BP-17 ~ BP-20] 部署与运维

---

## 分页与过滤

### BP-01 全局分页配置
在 settings 中配置全局分页类，避免每个 ViewSet 重复指定：

```python
# settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}
```

```python
# core/pagination.py
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
```

### BP-02 使用 django-filter 过滤后端
安装 `django-filter` 并配置为全局过滤后端，使用 `FilterSet` 声明过滤逻辑：

```python
# settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}
```

```python
# apps/orders/filters.py
import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    min_amount = django_filters.NumberFilter(field_name="total_amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="total_amount", lookup_expr="lte")
    status = django_filters.ChoiceFilter(choices=Order.Status.choices)
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")

    class Meta:
        model = Order
        fields = ["status", "min_amount", "max_amount", "created_after"]
```

```python
# apps/orders/views.py
class OrderViewSet(ModelViewSet):
    filterset_class = OrderFilter
    search_fields = ["order_no", "customer__name"]
    ordering_fields = ["created_at", "total_amount"]
    ordering = ["-created_at"]  # 默认排序
```

### BP-03 搜索字段配置
使用 `SearchFilter` 时明确指定 `search_fields`，支持前缀控制匹配模式：

```python
class UserViewSet(ModelViewSet):
    search_fields = [
        "username",          # contains（默认）
        "=email",            # exact
        "^display_name",     # startswith
    ]
```

### BP-04 游标分页（大数据量）
当数据量极大（百万级以上）时，使用 `CursorPagination` 代替 `PageNumberPagination`
避免 `OFFSET` 性能问题：

```python
from rest_framework.pagination import CursorPagination

class LargeDatasetPagination(CursorPagination):
    page_size = 50
    ordering = "-created_at"
    cursor_query_param = "cursor"
```

---

## 性能优化

### BP-05 select_related 与 prefetch_related
在 ViewSet 的 `get_queryset()` 中使用 `select_related`（外键/一对一）和
`prefetch_related`（多对多/反向外键）避免 N+1 查询：

```python
class OrderViewSet(ModelViewSet):
    def get_queryset(self):
        return Order.objects.select_related(
            "customer", "shipping_address"
        ).prefetch_related(
            "items", "items__product"
        )
```

### BP-06 延迟字段加载
列表接口不需要返回所有字段时，使用 `defer()` 或 `only()` 减少数据库查询开销：

```python
class ArticleViewSet(ModelViewSet):
    def get_queryset(self):
        if self.action == "list":
            return Article.objects.defer("content")  # 列表不加载正文
        return Article.objects.all()
```

### BP-07 缓存热点数据
对读多写少的接口使用 Django 缓存框架：

```python
from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.response import Response

class ConfigViewSet(ViewSet):
    @action(detail=False, methods=["get"])
    def public_settings(self, request):
        data = cache.get("public_settings")
        if data is None:
            data = SystemConfig.objects.get_public_settings()
            cache.set("public_settings", data, timeout=300)  # 缓存 5 分钟
        return Response(data)
```

### BP-08 批量操作
批量创建/更新使用 `bulk_create` / `bulk_update` 减少数据库往返次数：

```python
# 批量创建
objects = [MyModel(**item) for item in validated_data_list]
MyModel.objects.bulk_create(objects, batch_size=500)

# 批量更新
MyModel.objects.bulk_update(objects, fields=["status", "updated_at"], batch_size=500)
```

---

## 限流与安全

### BP-09 限流配置
全局配置限流策略，保护接口免受滥用：

```python
# settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
    },
}
```

对敏感接口设置更严格的限流：

```python
from rest_framework.throttling import UserRateThrottle

class LoginRateThrottle(UserRateThrottle):
    rate = "5/minute"

class AuthViewSet(ViewSet):
    throttle_classes = [LoginRateThrottle]
    ...
```

### BP-10 CORS 配置
使用 `django-cors-headers`，明确配置允许的域名，禁止使用通配符：

```python
# settings/base.py
CORS_ALLOWED_ORIGINS = [
    "https://your-frontend.com",
    "https://admin.your-frontend.com",
]
CORS_ALLOW_CREDENTIALS = True
```

### BP-11 敏感数据过滤
序列化器中排除密码、token 等敏感字段，日志中脱敏：

```python
class UserDetailSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "display_name"]
        # 不包含 password, api_key, secret_token 等字段
```

### BP-12 请求体大小限制
限制文件上传大小和请求体大小：

```python
# settings/base.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024      # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024       # 10MB
```

```python
from rest_framework.parsers import MultiPartParser

class FileUploadViewSet(ViewSet):
    parser_classes = [MultiPartParser]

    def create(self, request):
        file = request.FILES.get("file")
        if file and file.size > 10 * 1024 * 1024:
            raise BusinessError("FILE_TOO_LARGE", "文件大小不得超过 10MB")
        ...
```

---

## 测试策略

### BP-13 使用 APITestCase
DRF 测试使用 `APITestCase` 和 `APIClient`：

```python
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

class UserViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_users(self):
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_user_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/v1/users/", {"username": "new"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### BP-14 数据库隔离
每个测试用例使用 `TransactionTestCase` 或默认的事务回滚机制保持数据隔离。
使用 `factory_boy` 或 `fixtures` 生成测试数据：

```python
import factory
from apps.users.models import User

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
```

### BP-15 权限测试
每个 ViewSet 至少测试：已认证用户正常访问、未认证被拒绝、无权限被拒绝：

```python
class OrderPermissionTests(APITestCase):
    def test_owner_can_view(self):
        """资源所有者可以查看"""
        ...

    def test_non_owner_cannot_view(self):
        """非所有者无法查看"""
        ...

    def test_admin_can_delete(self):
        """管理员可以删除"""
        ...

    def test_non_admin_cannot_delete(self):
        """普通用户无法删除"""
        ...
```

### BP-16 测试覆盖目标
- 每个 ViewSet 的每个 action 至少有正常路径和一个异常路径的测试
- 自定义权限类必须有独立的单元测试
- 序列化器的自定义验证逻辑必须有测试
- 不测试 DRF 框架本身的行为（如内置字段校验）

---

## 部署与运维

### BP-17 健康检查接口
提供 `/health/` 端点检查服务和依赖状态：

```python
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import connection

class HealthViewSet(ViewSet):
    permission_classes = []
    authentication_classes = []

    @action(detail=False, methods=["get"])
    def check(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return Response({"status": "healthy", "database": "connected"})
        except Exception:
            return Response(
                {"status": "unhealthy", "database": "disconnected"},
                status=503,
            )
```

### BP-18 结构化日志
使用 `structlog` 或 Django logging 输出结构化日志：

```python
import structlog
logger = structlog.get_logger()

class OrderViewSet(ModelViewSet):
    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info(
            "order_created",
            order_id=instance.id,
            user_id=self.request.user.id,
            total=str(instance.total_amount),
        )
```

### BP-19 API 版本管理
通过 URL 前缀管理 API 版本：

```python
# config/urls.py
urlpatterns = [
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.orders.urls")),
    # 未来版本
    # path("api/v2/", include("apps.users.urls_v2")),
]
```

使用 DRF 内置的版本控制类时优先选择 `URLPathVersioning`：

```python
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "ALLOWED_VERSIONS": ["v1", "v2"],
}
```

### BP-20 Gunicorn 生产部署
使用 Gunicorn + UvicornWorker（异步）或 Gunicorn sync worker 部署：

```bash
# 同步 worker（Django 默认行为）
gunicorn config.wsgi:application \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile -

# 如果项目使用了 ASGI（Django Channels 等）
uvicorn config.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```
