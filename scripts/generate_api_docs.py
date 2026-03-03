#!/usr/bin/env python3
"""
FabricEye API 文档自动生成脚本

该脚本从 FastAPI 应用提取 OpenAPI 规范并生成 Markdown 文档。

用法:
    python scripts/generate_api_docs.py

输出:
    docs/api-auto-generated.md - 自动生成的 API 文档
"""

import json
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.main import app


def generate_markdown_docs():
    """生成 Markdown 格式的 API 文档"""
    
    openapi_schema = app.openapi()
    
    lines = []
    lines.append("# FabricEye API 文档（自动生成）\n")
    lines.append(f"> **版本**: {openapi_schema.get('info', {}).get('version', '1.0.0')}\n")
    lines.append(f"> **生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append("> **说明**: 本文档由 FastAPI 自动生成，与代码实时同步\n\n")
    
    lines.append("---\n\n")
    lines.append("## 目录\n\n")
    
    # 生成目录
    paths = openapi_schema.get('paths', {})
    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete']:
                summary = details.get('summary', '')
                anchor = f"{method}-{path.replace('/', '-').replace('{', '').replace('}', '')}"
                lines.append(f"- [{method.upper()} {path}](#{anchor}) - {summary}\n")
    
    lines.append("\n---\n\n")
    
    # 生成详细接口文档
    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method not in ['get', 'post', 'put', 'delete']:
                continue
            
            summary = details.get('summary', '')
            description = details.get('description', '')
            anchor = f"{method}-{path.replace('/', '-').replace('{', '').replace('}', '')}"
            
            lines.append(f"### {method.upper()} {path}\n")
            lines.append(f"<div id=\"{anchor}\"></div>\n\n")
            
            if summary:
                lines.append(f"**{summary}**\n\n")
            if description:
                lines.append(f"{description}\n\n")
            
            # 请求参数
            parameters = details.get('parameters', [])
            if parameters:
                lines.append("**参数**:\n\n")
                lines.append("| 名称 | 类型 | 位置 | 必填 | 说明 |\n")
                lines.append("|------|------|------|------|------|\n")
                for param in parameters:
                    name = param.get('name', '')
                    param_type = param.get('schema', {}).get('type', 'string')
                    location = param.get('in', '')
                    required = '是' if param.get('required') else '否'
                    desc = param.get('description', '')
                    lines.append(f"| {name} | {param_type} | {location} | {required} | {desc} |\n")
                lines.append("\n")
            
            # 请求体
            request_body = details.get('requestBody', {})
            if request_body:
                lines.append("**请求体**:\n\n")
                content = request_body.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    if 'properties' in schema:
                        lines.append("```json\n")
                        example = {}
                        for prop_name, prop_schema in schema['properties'].items():
                            prop_type = prop_schema.get('type', 'string')
                            if prop_type == 'string':
                                example[prop_name] = 'string'
                            elif prop_type == 'integer':
                                example[prop_name] = 0
                            elif prop_type == 'number':
                                example[prop_name] = 0.0
                            elif prop_type == 'boolean':
                                example[prop_name] = True
                            elif prop_type == 'array':
                                example[prop_name] = []
                            elif prop_type == 'object':
                                example[prop_name] = {}
                        lines.append(json.dumps(example, indent=2, ensure_ascii=False))
                        lines.append("\n```\n\n")
            
            # 响应
            responses = details.get('responses', {})
            if '200' in responses or '201' in responses:
                success_code = '200' if '200' in responses else '201'
                lines.append(f"**响应 ({success_code})**:\n\n")
                lines.append("```json\n")
                response = responses[success_code]
                content = response.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    lines.append(json.dumps({"code": 0, "message": "success", "data": {}}, indent=2, ensure_ascii=False))
                lines.append("\n```\n\n")
            
            lines.append("---\n\n")
    
    return ''.join(lines)


def main():
    """主函数"""
    docs_dir = Path(__file__).parent.parent / "docs"
    output_file = docs_dir / "api-auto-generated.md"
    
    print("🔄 正在生成 API 文档...")
    
    try:
        markdown_content = generate_markdown_docs()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ API 文档已生成: {output_file}")
        print(f"📊 共生成 {len(markdown_content)} 字符")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
