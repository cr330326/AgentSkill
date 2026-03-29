# Django REST Framework 编码规范

本文件包含 DRF 项目的硬性编码规则。所有生成的代码必须遵循这些规范。
标记为 **[团队自定义]** 的规则是本团队内部约定，优先级高于 DRF 通用实践。

## 目录
- [DRF-01 ~ DRF-04] 团队自定义规则（内部强制约定）
- [DRF-05 ~ DRF-09] 项目结构
- [DRF-10 ~ DRF-14] 序列化与数据验证
- [DRF-15 ~ DRF-18] 错误处理
- [DRF-19 ~ DRF-22] 认证与权限

---

## 团队自定义规则（内部强制约定）

> 以下四条规则为本团队自定义的硬性约定（custom team rules），所有项目必须严格遵循。
> 违反这些规则的代码不允许合入。

### DRF-01 必须使用 ViewSet，禁止使用 APIView [团队自定义]

所有接口必须使用 `ViewSet`（包括 `ModelViewSet`、`GenericViewSet`、`ViewSet` 等）来编写。
禁止使用 `APIView` 或基于函数的 `@api_view` 装饰器。

**正确示例：**
```python
# ref: DRF-01
from rest_framework.viewsets import ModelViewSet
from .serializers import UserSerializer
from .models import User

class UserViewSet(ModelViewSet):
    """用户管理接口 — 使用 ModelViewSet"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

```python
# ref: DRF-01
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

class ProductViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """只读接口也必须使用 ViewSet + Mixin 组合"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

**错误示例：**
```python
# 错误！禁止使用 APIView — 违反 DRF-01
from rest_framework.views import APIView
from rest_framework.response import Response

class UserList(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
```

```python
# 错误！禁止使用函数视图 @api_view — 违反 DRF-01
from rest_framework.decorators import api_view

@api_view(["GET"])
def user_list(request):
    ...
```

### DRF-02 序列化器必须继承 BaseSerializer [团队自定义]

所有序列化器必须继承团队封装的 `BaseSerializer`（位于 `core.serializers.BaseSerializer`），
而非 DRF 原生的 `serializers.ModelSerializer` 或 `serializers.Serializer`。

`BaseSerializer` 会自动添加 `created_at` 和 `updated_at` 只读字段，无需手动声明。

**正确示例：**
```python
# ref: DRF-02
from core.serializers import BaseSerializer
from .models import Order

class OrderSerializer(BaseSerializer):
    """继承 BaseSerializer，自动包含 created_at / updated_at"""
    class Meta:
        model = Order
        fields = ["id", "order_no", "status", "total_amount"]
        # 不需要手动添加 created_at / updated_at，BaseSerializer 已处理
```

**错误示例：**
```python
# 错误！禁止直接继承 ModelSerializer — 违反 DRF-02
from rest_framework import serializers

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "order_no", "status", "total_amount", "created_at", "updated_at"]
```

```python
# 错误！禁止直接继承 Serializer — 违反 DRF-02
from rest_framework import serializers

class OrderCreateSerializer(serializers.Serializer):
    order_no = serializers.CharField()
    ...
```

### DRF-03 权限类必须定义在 permissions.py 中 [团队自定义]

所有自定义权限类必须统一放在各 app 的 `permissions.py` 文件中（或全局 `core/permissions.py`）。
禁止在 ViewSet 文件内或其他文件中内联定义权限类。

**正确示例：**
```python
# permissions.py  — ref: DRF-03
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """只允许资源所有者访问"""
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsAdminOrReadOnly(BasePermission):
    """管理员可写，其他人只读"""
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user and request.user.is_staff
```

```python
# views.py — 从 permissions.py 导入使用
from .permissions import IsOwner  # ref: DRF-03

class OrderViewSet(ModelViewSet):
    permission_classes = [IsOwner]
    ...
```

**错误示例：**
```python
# 错误！禁止在 views.py 中内联定义权限类 — 违反 DRF-03
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet

class IsOwner(BasePermission):  # 不应出现在 views.py 里
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class OrderViewSet(ModelViewSet):
    permission_classes = [IsOwner]
    ...
```

### DRF-04 URL 路由必须使用 DefaultRouter 注册 [团队自定义]

所有 ViewSet 的路由必须使用 `rest_framework.routers.DefaultRouter` 注册。
禁止使用 `SimpleRouter`、手动 `path()` / `url()` 或 `as_view()` 方式绑定 URL。

**正确示例：**
```python
# urls.py  — ref: DRF-04
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, OrderViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = router.urls
```

**错误示例：**
```python
# 错误！禁止使用 SimpleRouter — 违反 DRF-04
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r"users", UserViewSet)
```

```python
# 错误！禁止手动绑定 URL — 违反 DRF-04
from django.urls import path
from .views import UserViewSet

urlpatterns = [
    path("users/", UserViewSet.as_view({"get": "list"})),
]
```

---

## 项目结构

### DRF-05 标准目录布局

```
project-name/
├── config/                     # 项目配置（settings、根 urls、wsgi）
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py                 # 根路由，include 各 app 的 router.urls
│   └── wsgi.py
├── core/                       # 全局公共模块
│   ├── serializers.py          # BaseSerializer 定义
│   ├── permissions.py          # 全局权限类
│   ├── pagination.py           # 全局分页类
│   ├── exceptions.py           # 全局异常处理器
│   └── mixins.py               # 公共 Mixin
├── apps/
│   └── <app_name>/
│       ├── models.py
│       ├── serializers.py      # 继承 core.serializers.BaseSerializer
│       ├── views.py            # ViewSet 定义
│       ├── permissions.py      # App 级权限类
│       ├── filters.py          # 过滤器
│       ├── urls.py             # DefaultRouter 注册
│       └── tests/
├── manage.py
└── requirements/
    ├── base.txt
    ├── dev.txt
    └── prod.txt
```

### DRF-06 App 拆分原则
按业务领域拆分 Django app，每个 app 对应一组紧密相关的资源。
禁止在一个 app 中塞入不相关的业务逻辑。

### DRF-07 配置分离
使用 `settings/base.py`、`settings/dev.py`、`settings/prod.py` 分环境管理配置。
敏感配置（密钥、数据库密码）从环境变量读取，禁止硬编码。

```python
# 正确
import os
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# 错误
SECRET_KEY = "my-super-secret-key-123"
```

### DRF-08 分层原则
- ViewSet 层：接收请求，调用 Service / Manager，返回响应
- Service / Manager 层：业务逻辑、事务管理
- Model 层：数据库定义与基础查询（自定义 Manager / QuerySet）

ViewSet 不直接写复杂的 ORM 查询，业务逻辑下沉到 Service 层或 Model Manager。

### DRF-09 入口路由
根 `urls.py` 只负责 `include` 各 app 的 URL，不直接注册 ViewSet。

```python
# config/urls.py — 正确
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.orders.urls")),
]
```

---

## 序列化与数据验证

### DRF-10 读写序列化器分离
创建（Create）、更新（Update）、列表/详情（Response）使用不同的序列化器：

```python
from core.serializers import BaseSerializer  # ref: DRF-02

class UserCreateSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password"]
        extra_kwargs = {"password": {"write_only": True}}

class UserUpdateSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ["email", "display_name"]

class UserDetailSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "display_name", "is_active"]
```

### DRF-11 字段验证
使用序列化器级别的 `validate_<field>` 或 `validate` 方法进行业务校验：

```python
class OrderSerializer(BaseSerializer):
    class Meta:
        model = Order
        fields = ["id", "quantity", "price"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("数量必须大于 0")
        return value

    def validate(self, attrs):
        if attrs.get("price", 0) > 999999:
            raise serializers.ValidationError("价格超出允许范围")
        return attrs
```

### DRF-12 嵌套序列化器
关联对象使用嵌套序列化器展开，避免只返回外键 ID：

```python
class OrderDetailSerializer(BaseSerializer):
    customer = CustomerBriefSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "order_no", "customer", "total_amount"]
```

### DRF-13 枚举字段
固定选项使用 Django `TextChoices` / `IntegerChoices`：

```python
class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        CONFIRMED = "confirmed", "已确认"
        CANCELLED = "cancelled", "已取消"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
```

### DRF-14 只读字段
`id`、`created_at`、`updated_at` 等系统字段必须标记为只读：

```python
class UserDetailSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = ["id"]
        # created_at / updated_at 由 BaseSerializer 自动处理为只读（ref: DRF-02）
```

---

## 错误处理

### DRF-15 统一异常处理器
在 `core/exceptions.py` 中定义全局异常处理器，注册到 DRF settings：

```python
# core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "code": response.status_code,
                "message": response.data.get("detail", str(response.data)),
            }
        }
    return response
```

```python
# settings/base.py
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}
```

### DRF-16 业务异常类
定义可复用的业务异常，继承 `APIException`：

```python
from rest_framework.exceptions import APIException

class BusinessError(APIException):
    status_code = 400
    default_code = "business_error"

    def __init__(self, code, message, status_code=400):
        self.status_code = status_code
        self.detail = {"code": code, "message": message}
```

### DRF-17 禁止暴露内部错误
生产环境中 500 错误统一返回通用消息，不暴露堆栈信息或 SQL 查询。
使用 `DEBUG = False` 并确保异常处理器捕获所有未预期的异常。

### DRF-18 HTTP 状态码使用
- 200：GET 成功
- 201：POST 创建成功
- 204：DELETE 成功（无返回体）
- 400：请求参数无效
- 401：未认证
- 403：无权限
- 404：资源不存在
- 409：资源冲突

---

## 认证与权限

### DRF-19 认证方案
在 settings 中全局配置认证后端，不在单个 ViewSet 中重复指定：

```python
# settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}
```

### DRF-20 权限层级
权限粒度从粗到细：
1. 全局默认权限（settings 中设置 `DEFAULT_PERMISSION_CLASSES`）
2. ViewSet 级权限（`permission_classes` 属性）
3. Action 级权限（`get_permissions()` 方法）

```python
# ref: DRF-03 — 权限类定义在 permissions.py 中
class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]  # ViewSet 级

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminUser()]  # Action 级
        return super().get_permissions()
```

### DRF-21 对象级权限
对单个对象的权限检查使用 `has_object_permission`，并确保在 ViewSet 中调用 `self.check_object_permissions()`：

```python
# permissions.py  — ref: DRF-03
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.is_staff
```

### DRF-22 未认证用户处理
对于需要区分已认证/未认证用户的接口，使用 `AllowAny` 加自定义逻辑，
而非移除全局认证后端：

```python
class PublicArticleViewSet(ModelViewSet):
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Article.objects.all()
        return Article.objects.filter(is_published=True)
```
