# FabricEye 脚本目录

本目录包含项目开发和维护所需的实用脚本。

## 脚本列表

### 1. `generate_api_docs.py`

**用途**：从 FastAPI 应用自动生成 API 文档（Markdown 格式）

**用法**：
```bash
cd scripts
python generate_api_docs.py
```

**输出**：`docs/api-auto-generated.md`

**说明**：
- 自动提取 OpenAPI 规范
- 生成包含所有接口的 Markdown 文档
- 适合作为快速参考，但不包含详细的业务说明
- 完整的业务文档仍需手动维护在 `docs/api-design.md`

---

## 添加新脚本

添加新脚本时请遵循以下规范：

1. **脚本头部注释**：包含用途、用法和输出说明
2. **错误处理**：所有脚本必须有适当的错误处理
3. **日志输出**：使用 print 输出执行状态和结果
4. **路径处理**：使用 `pathlib` 处理文件路径

**示例模板**：

```python
#!/usr/bin/env python3
"""
脚本名称和简要描述

用法:
    python scripts/script_name.py

输出:
    说明输出文件或结果
"""

import sys
from pathlib import Path

# 添加 backend 到路径（如果需要）
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

def main():
    print("🔄 开始执行...")
    # 脚本逻辑
    print("✅ 执行完成")

if __name__ == "__main__":
    main()
```

---

**注意**：本目录下的脚本仅供开发和维护使用，不包含在生产部署中。
