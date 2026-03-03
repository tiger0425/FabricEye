# FabricEye AI开发规范 v1.0

> **适用范围**: 所有AI代理（AI Developers）在FabricEye项目中的代码开发  
> **目标**: 从快速交付转向高质量、可维护的代码  
> **核心原则**: **单一职责、接口隔离、测试驱动**

---

## 📋 目录

1. [架构原则](#1-架构原则)
2. [代码结构规范](#2-代码结构规范)
3. [开发流程规范](#3-开发流程规范)
4. [代码质量标准](#4-代码质量标准)
5. [测试规范](#5-测试规范)
6. [AI开发行为准则](#6-ai开发行为准则)
7. [检查清单](#7-检查清单)
8. [违规处理](#8-违规处理)

---

## 1. 架构原则

### 1.1 单一职责原则（SRP）

**每个文件、每个类、每个函数只做一件事。**

```
❌ 错误示例：
   cascade_engine.py (400+行)
   ├── 数据定义
   ├── 去重算法
   ├── 图像处理
   ├── 视频写入
   └── 主业务逻辑

✅ 正确示例：
   services/
   ├── cascade/
   │   ├── __init__.py          # 统一导出
   │   ├── engine.py            # 主引擎（只负责调度）
   │   ├── deduplicator.py      # 去重算法
   │   ├── video_writer.py      # 视频写入
   │   └── utils.py             # 工具函数
   └── cascade_engine.py        # 兼容入口（导入新模块）
```

### 1.2 接口隔离原则

**前后端通过明确的接口契约交互，任何格式转换必须在隔离层完成。**

```typescript
// 后端返回格式 (snake_case)
interface BackendDefect {
  id: number;
  timestamp: number | null;
  bbox_x1: number;
  bbox_y2: number;
  type_cn: string;
}

// 前端使用格式 (CamelCase)
interface Defect {
  id: number;
  timestamp: number;
  bbox: [number, number, number, number];
  typeCn: string;
}

// ✅ 隔离层：数据转换函数
function normalizeDefect(raw: BackendDefect): Defect {
  return {
    id: raw.id,
    timestamp: raw.timestamp ?? 0,
    bbox: [raw.bbox_x1, raw.bbox_y1, raw.bbox_x2, raw.bbox_y2],
    typeCn: raw.type_cn || '未知'
  };
}
```

### 1.3 依赖注入原则

**不要内部创建依赖，通过构造函数/参数传入。**

```python
❌ 错误示例：
class CascadeEngine:
    def __init__(self):
        self.deduplicator = DetectionDeduplicator()  # 硬编码
        self.video_writer = AsyncVideoWriter()       # 硬编码

✅ 正确示例：
class CascadeEngine:
    def __init__(self, 
                 deduplicator: DetectionDeduplicator,
                 video_writer: AsyncVideoWriter):
        self.deduplicator = deduplicator
        self.video_writer = video_writer

# 组装时使用
engine = CascadeEngine(
    deduplicator=DetectionDeduplicator(),
    video_writer=AsyncVideoWriter()
)
```

---

## 2. 代码结构规范

### 2.1 文件大小限制

| 文件类型 | 最大行数 | 超过时的处理方式 |
|---------|---------|----------------|
| Vue单文件组件 | **200行** | 拆分：逻辑→composable，模板→子组件 |
| Python模块 | **150行** | 拆分：按职责拆分为多个模块 |
| TypeScript工具函数 | **100行** | 拆分：按功能拆分为多个文件 |
| API路由文件 | **100行** | 拆分：按资源拆分为多个路由文件 |

**检查命令：**
```bash
# 后端
find backend/app -name "*.py" -exec wc -l {} + | awk '$1 > 150 {print $1, $2}'

# 前端
find frontend/src -name "*.vue" -exec wc -l {} + | awk '$1 > 200 {print $1, $2}'
```

### 2.2 目录结构规范

#### 后端 (Python/FastAPI)

```
backend/app/
├── api/                    # API层：路由定义，无业务逻辑
│   ├── v1/
│   │   ├── endpoints/      # 路由端点
│   │   │   ├── videos.py       # 视频相关路由
│   │   │   ├── defects.py      # 缺陷相关路由
│   │   │   └── rolls.py        # 布卷相关路由
│   │   └── deps.py         # 依赖注入
├── core/                   # 核心配置
│   ├── config.py
│   └── database.py
├── models/                 # 数据模型（SQLAlchemy）
│   ├── defect.py
│   ├── video.py
│   └── roll.py
├── schemas/                # Pydantic模型（API序列化）
│   ├── defect.py
│   └── video.py
├── services/               # 业务逻辑层（核心）
│   ├── cascade/            # 级联检测相关
│   │   ├── __init__.py
│   │   ├── engine.py       # 主引擎（调度）
│   │   ├── deduplicator.py # 去重逻辑
│   │   ├── video_writer.py # 视频写入
│   │   └── utils.py        # 工具函数
│   ├── defect_service.py   # 缺陷业务逻辑
│   ├── video_service.py    # 视频业务逻辑
│   └── export_service.py   # 导出业务逻辑
└── utils/                  # 通用工具
    └── helpers.py
```

#### 前端 (Vue3 + TypeScript)

```
frontend/src/
├── api/                    # API客户端层
│   ├── videos.ts           # 只负责HTTP请求
│   ├── defects.ts
│   └── rolls.ts
├── types/                  # 类型定义（单一真相源）
│   ├── defect.ts           # Defect接口 + normalize函数
│   ├── video.ts
│   └── index.ts
├── stores/                 # 状态管理（Pinia）
│   ├── videos.ts           # 视频store
│   ├── defects.ts
│   └── rolls.ts
├── views/                  # 页面级组件
│   ├── VideoPlayback/      # 视频回放页面（目录）
│   │   ├── index.vue       # 主页面（<100行，只组装）
│   │   ├── composables/    # 组合式函数
│   │   │   ├── useVideoPlayer.ts
│   │   │   ├── useDefectMarkers.ts
│   │   │   └── useTimeline.ts
│   │   └── components/     # 子组件
│   │       ├── VideoPlayer.vue
│   │       ├── DefectOverlay.vue
│   │       ├── DefectTimeline.vue
│   │       └── DefectList.vue
│   └── ...
├── components/             # 全局共享组件
│   ├── common/             # 通用组件（Layout, Header等）
│   └── ui/                 # UI组件库封装
└── utils/                  # 工具函数
    └── formatters.ts       # 日期、时间格式化
```

### 2.3 命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 文件/目录 | 小写 + 下划线 | `video_writer.py`, `use_video_player.ts` |
| Vue组件 | PascalCase | `DefectOverlay.vue`, `VideoPlayer.vue` |
| Python类 | PascalCase | `class CascadeEngine:` |
| 函数/方法 | snake_case | `def save_to_db():` |
| 常量 | UPPER_SNAKE_CASE | `MAX_BUFFER_SIZE = 100` |
| 接口/类型 | PascalCase | `interface Defect {}` |
| Composable | camelCase + use前缀 | `useVideoPlayer()`, `useDefectMarkers()` |

---

## 3. 开发流程规范

### 3.1 强制流程：开发前必须完成

**任何人（包括AI代理）在开始开发前，必须输出以下文档：**

```markdown
## 功能开发文档

### 基本信息
- 功能名称：
- 需求来源：
- 预计修改文件：
- 影响范围：

### 1. 接口契约
#### 后端API
```
GET /api/videos/{id}/defects
Response: {
  "defects": [{
    "id": number,
    "timestamp": number,      // 相对于视频开始的秒数
    "bbox": [x1,y1,x2,y2],    // 数组格式
    "type_cn": string
  }]
}
```

#### 前端使用
```typescript
interface Defect {
  id: number;
  timestamp: number;
  bbox: [number, number, number, number];
  typeCn: string;  // 转换后
}
```

### 2. 数据流图
```
后端API返回 -> normalizeDefect() -> Store -> 组件渲染
(snake_case)     (格式转换层)      (CamelCase)
```

### 3. 文件变更计划
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| | 新增/修改/删除 | |

### 4. 测试计划
- [ ] 单元测试：...
- [ ] 集成测试：...
- [ ] E2E测试：...

### 5. 回滚方案
如果出现问题，执行：
```bash
git checkout <commit-hash> -- <file-path>
```
```

### 3.2 开发步骤（TDD）

**严禁跳过步骤！每一步必须得到用户确认后再继续。**

```
步骤1: 写设计文档（必须）
  └─> 输出：功能开发文档.md
  └─> 用户确认：✅ 通过 / ❌ 修改

步骤2: 写接口定义
  └─> 输出：types/*.ts 或 schemas/*.py
  └─> 输出：数据转换函数（normalizeXxx）
  └─> 用户确认：✅ 通过 / ❌ 修改

步骤3: 写测试（必须）
  └─> 单元测试：测试单个函数
  └─> 集成测试：测试API端点
  └─> E2E测试：测试完整流程
  └─> 运行测试：必须失败（红）
  └─> 用户确认：✅ 通过 / ❌ 修改

步骤4: 实现功能
  └─> 最小代码实现
  └─> 运行测试：必须通过（绿）
  └─> 用户确认：✅ 通过 / ❌ 修改

步骤5: 重构优化
  └─> 提取函数、优化结构
  └─> 运行测试：必须通过
  └─> 用户确认：✅ 完成
```

### 3.3 代码提交规范

**每次提交必须满足：**

```bash
# 1. 代码格式化
black backend/app/
npx prettier --write frontend/src/

# 2. 类型检查
cd backend && mypy app/
cd frontend && npx vue-tsc --noEmit

# 3. 运行测试
pytest backend/tests/
npm run test:unit

# 4. 检查文件大小
# （不能超过2.1节规定的限制）

# 5. 提交信息格式
git commit -m "feat: 添加视频回放缺陷标记功能

- 新增 DefectOverlay 组件渲染SVG标记
- 添加 bbox 坐标转换函数
- 修复时间戳计算逻辑

相关文件:
- frontend/src/views/VideoPlayback/components/DefectOverlay.vue
- frontend/src/views/VideoPlayback/composables/useDefectMarkers.ts
- backend/app/services/cascade/timestamp_calculator.py

测试:
- tests/e2e/video-playback.spec.ts
- tests/unit/test_timestamp.py"
```

---

## 4. 代码质量标准

### 4.1 禁止项（绝对不允许）

| 禁止项 | 示例 | 正确做法 |
|--------|------|---------|
| 文件超过限制行数 | `videos.py` 480行 | 拆分多个文件 |
| 函数超过50行 | 一个函数处理多个逻辑 | 拆分为多个小函数 |
| 直接修改已有接口 | 改`bbox`从数组变对象 | 新增字段，兼容旧格式 |
| 复制粘贴代码 | 3处相同的格式化代码 | 提取到utils |
| 注释掉的代码残留 | `# old_code = ...` | 直接删除 |
| 硬编码配置 | `port = 8001` | 写到config.py |
| any类型滥用 | `data: any` | 定义具体接口 |
| 空catch块 | `catch(e) {}` | 至少记录日志 |

### 4.2 必须项（强制要求）

- [ ] **所有函数必须有类型注解**（Python: type hints, TS: 接口）
- [ ] **所有复杂逻辑必须有注释**（为什么这么做，不是做什么）
- [ ] **所有API必须有文档字符串**
- [ ] **所有边界情况必须处理**（null, 空数组, 异常）
- [ ] **所有修改必须有测试覆盖**

### 4.3 代码审查标准

**审查清单（必须逐项确认）：**

```markdown
## 代码审查清单

### 基础检查
- [ ] 代码格式化正确（Black/Prettier）
- [ ] 类型检查通过（mypy/vue-tsc）
- [ ] 文件大小符合规范
- [ ] 无语法错误

### 架构检查
- [ ] 单一职责：每个文件/函数只做一件事
- [ ] 接口隔离：格式转换在隔离层完成
- [ ] 依赖注入：无硬编码依赖
- [ ] 无重复代码

### 质量检查
- [ ] 有类型注解
- [ ] 有单元测试
- [ ] 有错误处理
- [ ] 无魔法数字（都有常量定义）
- [ ] 无遗留注释代码

### 回归检查
- [ ] 相关功能测试通过
- [ ] 数据格式未破坏已有API
- [ ] 数据库迁移（如有）向后兼容
```

---

## 5. 测试规范

### 5.1 测试金字塔

```
        /\
       /  \       E2E测试 (10%) - 关键用户流程
      /----\         tests/e2e/
     /      \      
    /--------\   集成测试 (20%) - API端点
   /          \     tests/integration/
  /------------\
 /              \ 单元测试 (70%) - 函数/类
/----------------\   tests/unit/
```

### 5.2 必须编写的测试

**任何修改必须包含：**

1. **单元测试** - 测试修改的函数
2. **集成测试** - 测试API端点
3. **E2E测试** - 测试完整用户流程

```python
# backend/tests/unit/test_timestamp.py
def test_timestamp_calculation():
    """测试时间戳计算：必须是相对于视频开始的秒数"""
    engine = CascadeEngine()
    engine.recording_start_time = time.time()
    
    # 等待0.1秒
    time.sleep(0.1)
    
    # 计算时间戳
    timestamp = engine._calculate_timestamp()
    
    # 验证：0.1秒左右
    assert 0.09 <= timestamp <= 0.11
```

```typescript
// frontend/tests/e2e/video-playback.spec.ts
test('缺陷标记正确显示', async ({ page }) => {
  await page.goto('/playback/5?videoId=19');
  
  // 等待视频加载
  await page.waitForSelector('video');
  
  // 跳转到20秒（有缺陷的时间点）
  await page.click('text=跳转');
  
  // 验证SVG标记显示
  const svg = await page.locator('svg.defect-overlay');
  await expect(svg).toBeVisible();
  
  // 验证有2个缺陷标记
  const rects = await page.locator('svg.defect-overlay rect');
  await expect(rects).toHaveCount(2);
});
```

### 5.3 测试运行要求

**本地开发时：**
```bash
# 每次提交前
pytest backend/tests/ -x          # 任一失败停止
npm run test:unit -- --bail      # 任一失败停止
npm run test:e2e -- --spec video  # 相关E2E测试
```

**CI/CD中：**
- 所有测试必须通过
- 覆盖率不能低于70%
- 类型检查必须通过

---

## 6. AI开发行为准则

### 6.1 AI代理必须遵守

1. **不擅自修改配置文件**
   - 禁止修改：package.json, requirements.txt, vite.config.ts等
   - 如需修改，必须明确告知用户并获得同意

2. **不擅自删除代码**
   - 删除任何函数/类前，必须确认无调用方
   - 使用`grep`或LSP查找所有引用

3. **不硬编码假设**
   - 所有配置必须从config文件读取
   - 所有魔法数字必须定义为常量

4. **必须保持兼容性**
   - 不修改已有接口（除非用户明确要求）
   - 新增功能通过新增接口实现
   - 数据格式变更必须通过适配器层

5. **必须写测试**
   - 任何功能必须有对应的单元测试
   - 任何API必须有对应的集成测试
   - 任何用户流程必须有对应的E2E测试

6. **必须文档化**
   - 所有函数必须有文档字符串
   - 所有复杂逻辑必须有注释
   - 所有API必须有契约文档

### 6.2 AI代理被质疑时的回应

**如果用户说"你改错了"，AI必须：**

1. 立即停止当前修改
2. 回滚到上一版本：
   ```bash
   git diff --name-only  # 查看修改的文件
   git checkout HEAD -- <file>  # 恢复文件
   ```
3. 分析报告：
   - 哪部分理解错了？
   - 影响了哪些功能？
   - 如何修复？
4. 提出修复方案，等待用户确认后再执行

### 6.3 AI代理的沟通原则

**开发前必须询问：**
- 这个功能影响哪些已有功能？
- 数据格式会变吗？
- 如何测试验证？

**开发中必须报告：**
- 修改了哪些文件？
- 每完成一步，请求确认
- 发现设计问题时，立即提出

**开发后必须提供：**
- 测试证据（截图、日志）
- 代码审查清单（逐项勾选）
- 回滚方案

---

## 7. 检查清单

### 7.1 开发前检查清单

- [ ] 已阅读相关需求文档
- [ ] 已分析影响范围（改哪些文件）
- [ ] 已确定数据格式（是否需要转换层）
- [ ] 已编写功能设计文档
- [ ] 用户已确认设计文档

### 7.2 开发中检查清单

- [ ] 文件大小未超过限制
- [ ] 函数长度未超过50行
- [ ] 已添加类型注解
- [ ] 已添加单元测试
- [ ] 运行测试通过

### 7.3 开发后检查清单

- [ ] 代码格式化正确
- [ ] 类型检查通过
- [ ] 所有测试通过
- [ ] 相关功能回归测试通过
- [ ] 已更新文档
- [ ] 用户已验收

---

## 8. 违规处理

### 8.1 违规定义

以下情况视为违规：
1. 文件超过规定行数
2. 未写测试就提交功能
3. 直接修改已有接口导致不兼容
4. 未获得用户确认就修改核心代码
5. 复制粘贴代码而不提取公共函数

### 8.2 违规处理流程

```
发现违规
  ↓
立即停止开发
  ↓
回滚所有修改
  ↓
分析报告原因
  ↓
按规范重新开发
  ↓
用户确认
```

### 8.3 预防措施

1. **代码审查工具**
   ```bash
   # 添加pre-commit钩子
   pip install pre-commit
   pre-commit install
   ```

2. **CI/CD检查**
   ```yaml
   # .github/workflows/ci.yml
   - name: Check File Size
     run: |
       find . -name "*.py" -exec wc -l {} + | awk '$1 > 150 {exit 1}'
       find . -name "*.vue" -exec wc -l {} + | awk '$1 > 200 {exit 1}'
   
   - name: Run Tests
     run: pytest --cov=app --cov-fail-under=70
   ```

3. **类型检查**
   ```bash
   mypy --strict backend/app/
   npx vue-tsc --noEmit
   ```

---

## 📎 附录

### A. 常用命令速查

```bash
# 检查文件大小
find backend/app -name "*.py" -exec wc -l {} + | sort -n | tail -10
find frontend/src -name "*.vue" -exec wc -l {} + | sort -n | tail -10

# 运行测试
pytest backend/tests/ -v --tb=short
npm run test:unit
npm run test:e2e

# 代码格式化
black backend/app/
npx prettier --write frontend/src/

# 类型检查
mypy backend/app/
npx vue-tsc --noEmit

# 查找重复代码
jscpd frontend/src/ --min-lines 5 --min-tokens 50
```

### B. 快速参考：文件拆分模板

#### Vue组件拆分模板

```vue
<!-- views/FeatureName/index.vue -->
<template>
  <div class="feature-page">
    <FeatureHeader :title="title" />
    <FeatureMain :data="data" @action="handleAction" />
    <FeatureSidebar v-model:visible="showSidebar" />
  </div>
</template>

<script setup lang="ts">
import FeatureHeader from './components/FeatureHeader.vue'
import FeatureMain from './components/FeatureMain.vue'
import FeatureSidebar from './components/FeatureSidebar.vue'
import { useFeature } from './composables/useFeature'

const { title, data, handleAction, showSidebar } = useFeature()
</script>
```

#### Python服务拆分模板

```python
# services/feature/__init__.py
from .engine import FeatureEngine
from .processor import FeatureProcessor
from .utils import feature_helper

__all__ = ['FeatureEngine', 'FeatureProcessor', 'feature_helper']

# services/feature/engine.py
class FeatureEngine:
    """主引擎，负责调度"""
    def __init__(self, processor: FeatureProcessor):
        self.processor = processor
    
    def process(self, data: dict) -> dict:
        return self.processor.process(data)

# services/feature/processor.py
class FeatureProcessor:
    """具体处理逻辑"""
    def process(self, data: dict) -> dict:
        # 实现逻辑
        pass
```

---

## ✅ 确认签字

**所有AI代理在参与本项目前，必须阅读并同意遵守本规范。**

> 我已阅读并理解FabricEye AI开发规范，承诺在开发过程中严格遵守以上所有条款。
> 
> AI代理ID: _______________  
> 日期: _______________

---

**文档版本**: v1.0  
**最后更新**: 2026-03-02  
**维护者**: 项目技术负责人  
**适用范围**: 所有AI代理及开发人员
