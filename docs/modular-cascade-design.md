# FabricEye 模块化级联检测系统架构文档

## 1. 设计哲学 (Design Philosophy)
FabricEye 旨在提供一个**高度可配置**的视觉检测流水线。系统将“初次扫描”与“二次验证”完全解耦，允许用户根据业务场景自由定义模型组合与逻辑流程。

## 2. 核心架构设计 (System Architecture)

### 2.1 梯度检测流水线 (The Pipeline)
1.  **初次扫描 (Primary Scan)**：由 `PRIMARY_MODEL` 执行，目标是快速定位疑似瑕疵。
2.  **逻辑闸门 (Decision Gate)**：
    *   若 `ENABLE_SECONDARY` 为 `False`：直接输出初扫结果。
    *   若 `ENABLE_SECONDARY` 为 `True`：
        *   `Confidence >= SKIP_THRESHOLD`：**免检通行**，直接输出结论。
        *   `MIN_THRESHOLD <= Confidence < SKIP_THRESHOLD`：**进入验证**，触发二次精检。
3.  **二次验证 (Secondary Verification)**：由 `SECONDARY_MODEL` 执行，对初扫切出的 ROI 区域进行像素级复核。

---

## 3. 配置规范 (Configuration Specification)

在 `backend/app/core/config.py` 或 `.env` 中定义以下变量：

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PRIMARY_MODEL` | `qwen3.5-flash` | 负责第一遍全帧扫描的模型 |
| `SECONDARY_MODEL` | `qwen3.5-plus` | 负责第二遍 ROI 复核的模型 |
| `ENABLE_SECONDARY` | `True` | 是否开启二次验证开关 |
| `FLASH_THRESHOLD` | `0.4` | 触发任何动作的最低门槛 |
| `SKIP_VERIFY_THRESHOLD`| `0.8` | 超过此值则认为初扫已足够准确，跳过复核 |

---

## 4. 开发实施细节 (Implementation Details)

### 4.1 核心服务层 (`ai_analyzer.py`)
*   **通用接口化**：重构 `analyze_with_flash` 和 `analyze_with_plus` 为更通用的 `analyze_image(image, model_name, prompt_type)`。
*   **Prompt 动态化**：针对初扫（侧重定位）和复核（侧重分类与确认）设计两套不同的提示词。

### 4.2 引擎逻辑层 (`cascade_engine.py`)
```python
# 逻辑伪代码示例
detections = self.analyzer.call_model(frame, settings.PRIMARY_MODEL)

for det in detections:
    if det.confidence >= settings.SKIP_VERIFY_THRESHOLD or not settings.ENABLE_SECONDARY:
        # 路径 A: 直接确认并广播
        self.confirm_and_broadcast(det)
    elif det.confidence >= settings.FLASH_THRESHOLD:
        # 路径 B: 提交复核队列
        self.verification_queue.put(det)
```

---

## 5. 典型应用场景组合 (Use Cases)

| 场景 | PRIMARY_MODEL | ENABLE_SECONDARY | SECONDARY_MODEL | 优势 |
| :--- | :--- | :--- | :--- | :--- |
| **追求极致速度** | `qwen3.5-flash` | `False` | - | 延迟 < 1s，成本最低 |
| **标准工业检测** | `qwen3.5-flash` | `True` | `qwen3.5-plus` | 平衡成本与准确率（默认） |
| **高精实验室模式** | `qwen3.5-plus` | `True` | `qwen3.5-plus` | 采用最高规格进行双重交叉验证 |
| **专家复核模式** | `qwen3.5-flash` | `True` | `qwen3.5-plus` | 用 Plus 的细节识别能力去校准 Flash |

---

## 6. 后续维护建议
*   **影子测试**：在修改模式前，建议开启日志记录 Flash 与 Plus 的判定差异率，以微调 `SKIP_VERIFY_THRESHOLD`。
*   **成本预警**：当开启 `plus` 作为 Primary 模型时，应在前端给出成本消耗预警。

---
*文档版本：v2.0*
*更新日期：2026-03-02*
