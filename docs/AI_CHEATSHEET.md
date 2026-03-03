# AI开发快速参考卡

## 🚨 开始开发前（必须！）

```markdown
1. 输出设计文档
2. 用户确认 ✅
3. 写接口定义
4. 用户确认 ✅
5. 写测试（红）
6. 用户确认 ✅
7. 实现代码（绿）
8. 用户确认 ✅
9. 重构优化
10. 完成 ✅
```

---

## 📏 数字红线（不能超过）

| 类型 | 最大行数 |
|------|---------|
| Python文件 | 150行 |
| Vue文件 | 200行 |
| TypeScript工具 | 100行 |
| 函数/方法 | 50行 |

**检查：**
```bash
wc -l backend/app/services/cascade_engine.py  # 应该 < 150
wc -l frontend/src/views/VideoPlayback.vue     # 应该 < 200
```

---

## ✅ 三步确认法

### 每完成一步必须说：
"第X步完成，输出：...
请检查并确认是否继续？"

**用户说"继续"才能下一步！**

---

## 🚫 绝对禁止

- ❌ 文件超过行数限制
- ❌ 不写测试就提交
- ❌ 直接改已有接口
- ❌ 复制粘贴代码
- ❌ 硬编码配置
- ❌ any类型滥用
- ❌ 遗留注释代码
- ❌ 空catch块

---

## 📋 代码审查清单（每次提交前）

```markdown
□ 文件大小符合规范
□ 有类型注解
□ 有单元测试
□ 有错误处理
□ 无重复代码
□ 相关功能测试通过
□ 数据格式未破坏API
```

---

## 🔄 如果改错了

```bash
# 1. 立即停止
# 2. 查看修改
 git diff --name-only

# 3. 回滚文件
 git checkout HEAD -- <file-path>

# 4. 报告分析
# 5. 等待用户确认重新开发
```

---

## 🏗️ 正确代码结构

### Vue组件拆分
```
views/FeaturePage/
├── index.vue           # <100行，只组装
├── composables/
│   ├── useFeature.ts   # 业务逻辑
│   └── useUtils.ts     # 工具函数
└── components/
    ├── Header.vue      # 子组件
    ├── Main.vue
    └── Sidebar.vue
```

### Python服务拆分
```
services/feature/
├── __init__.py         # 统一导出
├── engine.py           # 主引擎（调度）
├── processor.py        # 业务逻辑
└── utils.py            # 工具函数
```

---

## 🧪 测试要求

**每个功能必须有：**
1. 单元测试（70%）
2. 集成测试（20%）
3. E2E测试（10%）

**运行命令：**
```bash
pytest backend/tests/ -x          # 失败停止
npm run test:unit -- --bail      # 失败停止
```

---

## 📞 沟通模板

### 开发前
"我计划实现[功能名]，影响文件：
- backend/app/services/xxx.py
- frontend/src/views/xxx.vue

数据格式会改变吗？[是/否]
请先确认设计文档。"

### 开发中
"第2步完成，已创建接口定义：
- types/defect.ts
- schemas/defect.py

请检查是否正确，确认后继续？"

### 开发后
"功能完成，测试证据：
- [截图]
- 测试通过率：100%
- 代码审查清单：[全部勾选]

请验收。"

---

## 💡 常见错误

| 错误 | 正确 |
|------|------|
| 直接改 cascade_engine.py | 先拆分为多个小文件 |
| bbox.x1（对象） | bbox[0]（数组） |
| import { useStore } from '..' | import { useStore } from '@/stores' |
| 硬编码 8001 | 从 config.API_BASE_URL 读取 |
| catch(e) {} | catch(e) { logger.error(e) } |

---

## 📚 完整文档

详细规范见：
`docs/AI_DEVELOPMENT_GUIDELINES.md`

**承诺：**
我已阅读并遵守以上所有规范。

AI代理ID: ____________
日期: ____________
