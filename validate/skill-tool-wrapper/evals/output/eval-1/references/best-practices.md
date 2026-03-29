# React + TypeScript 最佳实践

本文件包含推荐但非强制的设计模式和实践建议。
遵循这些实践可以提升代码质量、性能和可维护性。

## 目录
- [BP-01 ~ BP-04] 性能优化
- [BP-05 ~ BP-08] Hook 设计
- [BP-09 ~ BP-12] 组件模式
- [BP-13 ~ BP-16] 测试策略
- [BP-17 ~ BP-20] 错误处理与可靠性

---

## 性能优化

### BP-01 避免不必要的重渲染
使用 `React.memo` 包裹接收引用类型 props 的纯展示组件。
对传递给子组件的回调函数使用 `useCallback`，对计算开销大的值使用 `useMemo`。

```tsx
// 推荐 — 纯展示组件用 memo 包裹
const UserCard = React.memo<UserCardProps>(({ name, email, onSelect }) => {
  return (
    <div onClick={onSelect}>
      <h3>{name}</h3>
      <p>{email}</p>
    </div>
  );
});

// 推荐 — 稳定回调引用
const UserList: React.FC = () => {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = useCallback((id: string) => {
    setSelected(id);
  }, []);

  return users.map((u) => (
    <UserCard key={u.id} {...u} onSelect={() => handleSelect(u.id)} />
  ));
};
```

### BP-02 列表虚拟化
渲染超过 50 条数据的长列表时，使用虚拟化库（如 `@tanstack/react-virtual`
或 `react-window`），只渲染视口内可见的元素。

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

const VirtualList: React.FC<{ items: Item[] }> = ({ items }) => {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
  });

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              transform: `translateY(${virtualItem.start}px)`,
              height: `${virtualItem.size}px`,
            }}
          >
            {items[virtualItem.index].name}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### BP-03 代码分割与懒加载
页面级组件使用 `React.lazy` + `Suspense` 实现按需加载，
减少首屏 bundle 体积。

```tsx
// 推荐 — 路由级别懒加载
const Dashboard = React.lazy(() => import('@/pages/Dashboard'));
const Settings = React.lazy(() => import('@/pages/Settings'));

const AppRoutes: React.FC = () => (
  <Suspense fallback={<PageSkeleton />}>
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  </Suspense>
);
```

### BP-04 图片与资源优化
- 使用 `loading="lazy"` 延迟加载非首屏图片
- 提供明确的 `width` 和 `height` 属性避免布局偏移
- 大图使用 WebP/AVIF 等现代格式

```tsx
<img
  src={user.avatar}
  alt={`${user.name} 的头像`}
  width={80}
  height={80}
  loading="lazy"
/>
```

---

## Hook 设计

### BP-05 自定义 Hook 封装副作用
将组件中的数据获取、订阅、定时器等副作用逻辑提取为自定义 Hook，
让组件只关注 UI 渲染。

```tsx
// 推荐 — 副作用逻辑封装在 Hook 中
function useDebounce<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debouncedValue;
}

// 组件只关注 UI
const SearchBox: React.FC = () => {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  const { data } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchAPI(debouncedQuery),
    enabled: debouncedQuery.length > 0,
  });

  return <input value={query} onChange={(e) => setQuery(e.target.value)} />;
};
```

### BP-06 Hook 组合而非嵌套
将多个相关的 Hook 调用组合成一个领域 Hook，降低组件中的 Hook 调用数量。

```tsx
// 推荐 — 组合为领域 Hook
function useUserProfile(userId: string) {
  const userQuery = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateUserRequest) => updateUser(userId, data),
    onSuccess: () => userQuery.refetch(),
  });

  return {
    user: userQuery.data,
    isLoading: userQuery.isLoading,
    error: userQuery.error,
    updateUser: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
  };
}

// 组件使用简洁
const ProfilePage: React.FC<{ userId: string }> = ({ userId }) => {
  const { user, isLoading, updateUser } = useUserProfile(userId);
  // ...
};
```

### BP-07 useReducer 处理复杂状态
当组件状态包含多个相关字段且状态转换逻辑复杂时，
使用 `useReducer` 替代多个 `useState`。

```tsx
// 推荐 — 复杂表单状态使用 useReducer
interface FormState {
  values: Record<string, string>;
  errors: Record<string, string>;
  isSubmitting: boolean;
  isDirty: boolean;
}

type FormAction =
  | { type: 'SET_FIELD'; field: string; value: string }
  | { type: 'SET_ERROR'; field: string; error: string }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_SUCCESS' }
  | { type: 'SUBMIT_ERROR'; errors: Record<string, string> }
  | { type: 'RESET' };

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'SET_FIELD':
      return {
        ...state,
        values: { ...state.values, [action.field]: action.value },
        isDirty: true,
      };
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true };
    case 'SUBMIT_SUCCESS':
      return { ...state, isSubmitting: false, isDirty: false };
    // ...
  }
}
```

### BP-08 Hook 返回值使用对象而非数组
自定义 Hook 返回超过 2 个值时，使用对象而非数组，提升可读性。

```tsx
// 推荐 — 对象解构，字段语义清晰
function usePagination(totalItems: number, pageSize: number) {
  // ...
  return {
    currentPage,
    totalPages,
    goToPage,
    nextPage,
    prevPage,
    hasNext,
    hasPrev,
  };
}
const { currentPage, nextPage, hasNext } = usePagination(100, 10);

// 不推荐 — 数组解构，位置依赖，含义不直观
function usePagination(totalItems: number, pageSize: number) {
  return [currentPage, totalPages, goToPage, nextPage, prevPage];
}
const [page, total, goTo, next, prev] = usePagination(100, 10);
```

---

## 组件模式

### BP-09 组合优于继承
使用 `children` prop 和 Render Props 实现组件组合，避免深层嵌套 wrapper。

```tsx
// 推荐 — 组合模式
const Card: React.FC<{ title: string; children: React.ReactNode }> = ({
  title,
  children,
}) => (
  <div className={styles.card}>
    <h3>{title}</h3>
    <div className={styles.body}>{children}</div>
  </div>
);

// 使用
<Card title="用户信息">
  <UserDetails user={user} />
  <UserActions userId={user.id} />
</Card>
```

### BP-10 受控组件与表单
表单元素优先使用受控模式。复杂表单推荐使用 React Hook Form 库。

```tsx
// 推荐 — React Hook Form
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const loginSchema = z.object({
  email: z.string().email('请输入有效邮箱'),
  password: z.string().min(8, '密码至少 8 位'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const LoginForm: React.FC = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (data: LoginFormValues) => {
    // ...
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      <input type="password" {...register('password')} />
      {errors.password && <span>{errors.password.message}</span>}
      <button type="submit">登录</button>
    </form>
  );
};
```

### BP-11 Compound Component 模式
对于逻辑内聚的多部分 UI（如 Tab、Accordion），使用复合组件模式：

```tsx
// 推荐 — 复合组件
const Tabs: React.FC<{ children: React.ReactNode }> & {
  Tab: typeof Tab;
  Panel: typeof Panel;
} = ({ children }) => {
  const [activeIndex, setActiveIndex] = useState(0);
  return (
    <TabsContext.Provider value={{ activeIndex, setActiveIndex }}>
      <div className={styles.tabs}>{children}</div>
    </TabsContext.Provider>
  );
};

// 使用
<Tabs>
  <Tabs.Tab index={0}>概览</Tabs.Tab>
  <Tabs.Tab index={1}>详情</Tabs.Tab>
  <Tabs.Panel index={0}><Overview /></Tabs.Panel>
  <Tabs.Panel index={1}><Details /></Tabs.Panel>
</Tabs>
```

### BP-12 错误边界
为独立的功能模块设置错误边界，防止局部错误导致整个页面白屏。

```tsx
// 推荐 — 为每个独立功能区域设置错误边界
import { ErrorBoundary } from 'react-error-boundary';

const DashboardPage: React.FC = () => (
  <div>
    <ErrorBoundary fallback={<ChartError />}>
      <SalesChart />
    </ErrorBoundary>
    <ErrorBoundary fallback={<TableError />}>
      <OrderTable />
    </ErrorBoundary>
  </div>
);
```

---

## 测试策略

### BP-13 测试金字塔
按照测试金字塔分配测试投入：

| 层级 | 比例 | 工具 | 测试内容 |
|------|------|------|---------|
| 单元测试 | 60% | Vitest / Jest | 工具函数、自定义 Hook、纯逻辑 |
| 组件测试 | 30% | Testing Library | 组件渲染、用户交互、集成行为 |
| E2E 测试 | 10% | Playwright / Cypress | 关键用户流程（登录、下单） |

### BP-14 以用户视角编写组件测试
使用 `@testing-library/react`，通过用户可见的文本和角色查询元素，
而非内部实现细节（如 class 名、组件实例）。

```tsx
// 推荐 — 基于用户行为测试
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('提交表单后显示成功消息', async () => {
  render(<ContactForm />);

  await userEvent.type(screen.getByLabelText('邮箱'), 'test@example.com');
  await userEvent.type(screen.getByLabelText('内容'), 'Hello');
  await userEvent.click(screen.getByRole('button', { name: '提交' }));

  expect(await screen.findByText('发送成功')).toBeInTheDocument();
});

// 不推荐 — 依赖实现细节
test('提交表单', () => {
  const wrapper = render(<ContactForm />);
  wrapper.find('.email-input').simulate('change', { target: { value: 'test@example.com' } });
  wrapper.find('.submit-btn').simulate('click');
  expect(wrapper.find('.success-message')).toHaveLength(1);
});
```

### BP-15 Mock 外部依赖
测试中 mock API 请求和第三方库，保持测试的确定性和速度。
推荐使用 MSW（Mock Service Worker）拦截网络请求。

```tsx
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const server = setupServer(
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: 1, name: 'Alice' },
      { id: 2, name: 'Bob' },
    ]);
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### BP-16 自定义 Hook 测试
使用 `@testing-library/react` 的 `renderHook` 测试自定义 Hook。

```tsx
import { renderHook, act } from '@testing-library/react';

test('useCounter 增加计数', () => {
  const { result } = renderHook(() => useCounter(0));

  act(() => {
    result.current.increment();
  });

  expect(result.current.count).toBe(1);
});
```

---

## 错误处理与可靠性

### BP-17 API 请求统一错误处理
在 API 服务层统一拦截和转换错误，组件中只处理业务层面的错误逻辑。

```typescript
// 推荐 — services/api.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 统一跳转登录页
      window.location.href = '/login';
    }
    return Promise.reject(
      new AppError(
        error.response?.data?.code ?? 'UNKNOWN_ERROR',
        error.response?.data?.message ?? '请求失败，请稍后重试',
        error.response?.status,
      ),
    );
  },
);
```

### BP-18 加载与空状态
每个数据展示组件都必须处理三种状态：加载中、空数据、有数据。

```tsx
// 推荐 — 完整的状态处理
const UserList: React.FC = () => {
  const { data: users, isLoading, error } = useQuery({ queryKey: ['users'], queryFn: fetchUsers });

  if (isLoading) return <ListSkeleton count={5} />;
  if (error) return <ErrorCard message="加载用户列表失败" onRetry={refetch} />;
  if (!users?.length) return <EmptyState icon="users" message="暂无用户" />;

  return (
    <ul>
      {users.map((user) => (
        <UserCard key={user.id} user={user} />
      ))}
    </ul>
  );
};
```

### BP-19 乐观更新
对于用户体感敏感的操作（如点赞、收藏），使用乐观更新提升交互流畅度。

```tsx
const useLikePost = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (postId: string) => likePostAPI(postId),
    onMutate: async (postId) => {
      await queryClient.cancelQueries({ queryKey: ['posts'] });
      const previous = queryClient.getQueryData<Post[]>(['posts']);
      queryClient.setQueryData<Post[]>(['posts'], (old) =>
        old?.map((p) =>
          p.id === postId ? { ...p, liked: true, likeCount: p.likeCount + 1 } : p,
        ),
      );
      return { previous };
    },
    onError: (_err, _postId, context) => {
      queryClient.setQueryData(['posts'], context?.previous);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });
};
```

### BP-20 可访问性（a11y）基础
组件开发时遵循 WAI-ARIA 基本要求：

- 交互元素必须可通过键盘操作
- 图片提供有意义的 `alt` 文本
- 表单 `input` 关联 `label`
- 颜色对比度符合 WCAG AA 标准（最低 4.5:1）
- 使用语义化 HTML 标签（`button`, `nav`, `main`, `article`）

```tsx
// 推荐
<button aria-label="关闭对话框" onClick={onClose}>
  <CloseIcon aria-hidden="true" />
</button>

<img src={user.avatar} alt={`${user.name} 的头像`} />

<label htmlFor="email">邮箱</label>
<input id="email" type="email" aria-required="true" />

// 不推荐
<div onClick={onClose} className="close-btn">×</div>
<img src={user.avatar} />
<input type="email" placeholder="邮箱" />
```
