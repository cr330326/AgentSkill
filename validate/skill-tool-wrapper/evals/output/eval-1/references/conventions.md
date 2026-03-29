# React + TypeScript 编码规范

本文件定义 React + TypeScript 前端项目的硬性编码规则。
所有团队成员和 AI 生成的代码必须遵循这些约定。

## 目录
- [REACT-01 ~ REACT-05] 项目结构
- [REACT-06 ~ REACT-10] 组件设计
- [REACT-11 ~ REACT-15] TypeScript 类型约定
- [REACT-16 ~ REACT-20] 状态管理
- [REACT-21 ~ REACT-24] 样式与命名

---

## 项目结构

### REACT-01 标准目录布局

```
project-name/
├── src/
│   ├── index.tsx               # 应用入口
│   ├── App.tsx                 # 根组件，挂载路由
│   ├── components/             # 通用/共享组件
│   │   └── Button/
│   │       ├── Button.tsx
│   │       ├── Button.styles.ts
│   │       ├── Button.test.tsx
│   │       └── index.ts
│   ├── pages/                  # 页面级组件（与路由一一对应）
│   ├── hooks/                  # 自定义 Hook
│   ├── services/               # API 请求层
│   ├── stores/                 # 状态管理（全局状态）
│   ├── types/                  # 全局 TypeScript 类型定义
│   ├── utils/                  # 工具函数
│   ├── constants/              # 常量定义
│   └── assets/                 # 静态资源（图片、字体等）
├── public/
├── tsconfig.json
└── package.json
```

### REACT-02 组件目录结构
每个组件使用独立目录，包含组件文件、样式、测试和导出入口。
禁止将多个无关组件定义在同一文件中。

```
# 正确
components/
├── UserCard/
│   ├── UserCard.tsx
│   ├── UserCard.styles.ts
│   ├── UserCard.test.tsx
│   └── index.ts

# 错误
components/
├── UserCard.tsx
├── UserList.tsx
├── OrderCard.tsx        # 所有组件平铺，无独立目录
```

### REACT-03 导出规范
每个组件目录通过 `index.ts` 统一导出，外部引用时使用目录路径。
禁止在 `index.ts` 中包含组件实现逻辑。

```typescript
// 正确 — components/Button/index.ts
export { Button } from './Button';
export type { ButtonProps } from './Button';

// 错误 — 直接在 index.ts 写组件实现
export const Button = ({ children }: ButtonProps) => { ... };
```

### REACT-04 路径别名
使用 `@/` 作为 `src/` 的路径别名，避免深层相对路径。

```typescript
// 正确
import { Button } from '@/components/Button';
import { useAuth } from '@/hooks/useAuth';

// 错误
import { Button } from '../../../components/Button';
import { useAuth } from '../../hooks/useAuth';
```

### REACT-05 页面与路由对应
`pages/` 目录下的每个组件对应一个路由。页面组件只负责组合通用组件和调用 Hook，
不包含可复用的 UI 逻辑。

---

## 组件设计

### REACT-06 函数组件
所有组件使用函数组件 + Hooks。禁止使用 Class 组件。

```tsx
// 正确
const UserCard: React.FC<UserCardProps> = ({ name, email }) => {
  return (
    <div>
      <h3>{name}</h3>
      <p>{email}</p>
    </div>
  );
};

// 错误
class UserCard extends React.Component<UserCardProps> {
  render() {
    return (
      <div>
        <h3>{this.props.name}</h3>
        <p>{this.props.email}</p>
      </div>
    );
  }
}
```

### REACT-07 Props 定义
组件的 Props 使用 `interface` 定义，命名为 `组件名Props`。
必须为每个 prop 添加 JSDoc 注释。

```tsx
// 正确
interface UserCardProps {
  /** 用户显示名称 */
  name: string;
  /** 用户邮箱地址 */
  email: string;
  /** 头像 URL，不传则使用默认头像 */
  avatarUrl?: string;
  /** 点击卡片时的回调 */
  onClick?: (userId: string) => void;
}

// 错误 — 使用 type 而非 interface，缺少注释
type Props = {
  name: string;
  email: string;
  avatarUrl?: string;
  onClick?: (userId: string) => void;
};
```

### REACT-08 组件拆分原则
单个组件不超过 200 行（含空行和注释）。超过时必须拆分为子组件。
子组件放在同一目录下：

```
UserProfile/
├── UserProfile.tsx        # 主组件
├── UserProfileHeader.tsx  # 子组件
├── UserProfileStats.tsx   # 子组件
└── index.ts               # 只导出主组件
```

### REACT-09 条件渲染
复杂条件渲染逻辑提取为独立变量或子组件，禁止在 JSX 中嵌套三元表达式。

```tsx
// 正确
const UserStatus: React.FC<{ status: Status }> = ({ status }) => {
  if (status === 'loading') return <Spinner />;
  if (status === 'error') return <ErrorMessage />;
  return <UserContent />;
};

// 错误 — JSX 中嵌套三元
return (
  <div>
    {status === 'loading' ? (
      <Spinner />
    ) : status === 'error' ? (
      <ErrorMessage />
    ) : (
      <UserContent />
    )}
  </div>
);
```

### REACT-10 事件处理命名
事件处理函数使用 `handle` + 动作命名。Props 中的回调使用 `on` + 动作命名。

```tsx
// 正确
interface ButtonProps {
  onPress?: () => void;     // prop 回调用 on 前缀
}

const Form: React.FC = () => {
  const handleSubmit = () => { ... };  // 处理函数用 handle 前缀
  return <form onSubmit={handleSubmit}>...</form>;
};

// 错误
const Form: React.FC = () => {
  const submitForm = () => { ... };     // 缺少 handle 前缀
  const clickHandler = () => { ... };   // Handler 后缀风格不一致
};
```

---

## TypeScript 类型约定

### REACT-11 严格模式
`tsconfig.json` 必须启用 `strict: true`。禁止使用 `@ts-ignore`，
如确需绕过类型检查，使用 `@ts-expect-error` 并附带注释说明原因。

```json
// 正确 — tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true
  }
}
```

```typescript
// 正确 — 附带原因说明
// @ts-expect-error 第三方库缺少类型定义，已提交 PR
import { legacyUtil } from 'untyped-lib';

// 错误
// @ts-ignore
import { legacyUtil } from 'untyped-lib';
```

### REACT-12 禁止 any
禁止使用 `any` 类型。使用 `unknown` + 类型收窄替代。

```typescript
// 正确
const parseResponse = (data: unknown): User => {
  if (isUser(data)) {
    return data;
  }
  throw new Error('Invalid data');
};

// 错误
const parseResponse = (data: any): User => {
  return data as User;
};
```

### REACT-13 API 响应类型
所有 API 响应必须定义对应的 TypeScript 类型，放在 `types/` 目录下。
类型名称使用 `接口名 + Response/Request` 后缀。

```typescript
// 正确 — types/user.ts
export interface GetUserResponse {
  id: number;
  name: string;
  email: string;
  createdAt: string;
}

export interface CreateUserRequest {
  name: string;
  email: string;
  password: string;
}
```

### REACT-14 枚举使用 const enum 或联合类型
优先使用联合类型（union type）而非 `enum`。如需用 enum 必须使用 `const enum`。

```typescript
// 正确 — 优先使用联合类型
type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'cancelled';

// 可接受 — const enum
const enum HttpMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  DELETE = 'DELETE',
}

// 错误 — 普通 enum（编译产物体积大）
enum OrderStatus {
  Pending = 'pending',
  Confirmed = 'confirmed',
}
```

### REACT-15 泛型组件
可复用组件如列表、表格、选择器，必须使用泛型支持不同数据类型：

```tsx
// 正确
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string;
}

function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return (
    <ul>
      {items.map((item) => (
        <li key={keyExtractor(item)}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

// 错误 — 使用 any 代替泛型
interface ListProps {
  items: any[];
  renderItem: (item: any) => React.ReactNode;
}
```

---

## 状态管理

### REACT-16 状态分层
状态按作用域分为三层，禁止混用：

| 层级 | 用途 | 工具 |
|------|------|------|
| 组件本地状态 | UI 交互状态（开关、输入值） | `useState`, `useReducer` |
| 跨组件共享状态 | 多组件共享的业务状态 | Context 或状态管理库（如 Zustand） |
| 服务端状态 | API 数据、缓存、加载状态 | TanStack Query (React Query) |

```tsx
// 正确 — API 数据使用 React Query
const { data: users, isLoading } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
});

// 错误 — 手动用 useState + useEffect 管理 API 数据
const [users, setUsers] = useState<User[]>([]);
const [loading, setLoading] = useState(false);
useEffect(() => {
  setLoading(true);
  fetchUsers().then(setUsers).finally(() => setLoading(false));
}, []);
```

### REACT-17 全局状态最小化
只有真正需要跨页面/跨组件共享的状态才放入全局 store。
能通过 props 传递或 React Query 管理的数据，禁止放入全局状态。

### REACT-18 Store 按领域拆分
全局状态按业务领域拆分为独立 store 文件，禁止使用单一巨型 store。

```typescript
// 正确 — stores/ 目录按领域拆分
// stores/useAuthStore.ts
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  login: async (credentials) => { ... },
  logout: () => set({ user: null }),
}));

// stores/useThemeStore.ts
export const useThemeStore = create<ThemeState>((set) => ({
  mode: 'light',
  toggle: () => set((s) => ({ mode: s.mode === 'light' ? 'dark' : 'light' })),
}));

// 错误 — 单一巨型 store
export const useStore = create((set) => ({
  user: null,
  theme: 'light',
  cartItems: [],
  notifications: [],
  // ... 所有状态混在一起
}));
```

### REACT-19 禁止直接修改状态
状态更新必须使用不可变方式。数组使用展开运算符或 `map`/`filter`，
对象使用展开运算符。禁止使用 `push`、`splice` 等可变方法。

```typescript
// 正确
setItems((prev) => [...prev, newItem]);
setItems((prev) => prev.filter((item) => item.id !== targetId));
setUser((prev) => ({ ...prev, name: newName }));

// 错误
items.push(newItem);
setItems(items);
items.splice(index, 1);
setItems(items);
```

### REACT-20 useEffect 依赖完整性
`useEffect` 必须声明所有依赖项。禁止使用 `// eslint-disable-next-line` 跳过
exhaustive-deps 检查。如果 effect 依赖过多，重构逻辑而非忽略警告。

```tsx
// 正确
useEffect(() => {
  fetchData(userId, filters);
}, [userId, filters]);

// 错误 — 忽略依赖警告
useEffect(() => {
  fetchData(userId, filters);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [userId]);
```

---

## 样式与命名

### REACT-21 组件命名
- 组件文件和组件名使用 PascalCase：`UserCard.tsx` / `UserCard`
- Hook 使用 camelCase 且以 `use` 开头：`useAuth.ts` / `useAuth`
- 工具函数使用 camelCase：`formatDate.ts` / `formatDate`
- 常量使用 UPPER_SNAKE_CASE：`MAX_PAGE_SIZE`
- 类型/接口使用 PascalCase：`UserResponse`、`ButtonProps`

### REACT-22 CSS 方案
使用 CSS Modules 或 CSS-in-JS（如 styled-components / Emotion）。
禁止使用全局 CSS 类名（除 reset/normalize 外）。

```tsx
// 正确 — CSS Modules
import styles from './Button.module.css';
const Button = () => <button className={styles.primary}>Click</button>;

// 正确 — styled-components
const StyledButton = styled.button`
  background: var(--color-primary);
  padding: 8px 16px;
`;

// 错误 — 全局类名
import './Button.css';  // .btn-primary { ... } 可能与其他组件冲突
const Button = () => <button className="btn-primary">Click</button>;
```

### REACT-23 Magic Number 禁止
禁止在组件中使用未命名的魔法数字和字符串。提取为常量并给予语义化命名。

```tsx
// 正确
const MAX_VISIBLE_TAGS = 5;
const DEBOUNCE_DELAY_MS = 300;

const TagList: React.FC<{ tags: string[] }> = ({ tags }) => {
  const visibleTags = tags.slice(0, MAX_VISIBLE_TAGS);
  // ...
};

// 错误
const TagList: React.FC<{ tags: string[] }> = ({ tags }) => {
  const visibleTags = tags.slice(0, 5);  // 5 是什么？
  // ...
};
```

### REACT-24 文件长度限制
单个文件不超过 300 行。超过时拆分为多个文件。
自定义 Hook 提取到 `hooks/` 目录，工具函数提取到 `utils/` 目录。
