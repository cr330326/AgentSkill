#!/usr/bin/env python3
"""
批量创建 Zadig 项目和服务

从 Excel 文件读取数据，批量创建 Zadig 空项目，并通过模板创建服务。

Usage:
    python batch_create_projects.py <excel_file>

Excel 文件需要包含两个 sheet：
- Projects: 项目信息
- Services: 服务信息

Configuration:
    需要 ~/.zadigrc.json 配置文件或设置环境变量：
    - ZADIG_ENDPOINT: Zadig API endpoint
    - ZADIG_API_TOKEN: Zadig API token
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Add parent directory to path to import zadig_client
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from zadig_client import ZadigClient, ZadigAPIError, load_config


def load_excel_data(excel_file: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    从 Excel 文件加载项目和服务数据。

    Args:
        excel_file: Excel 文件路径

    Returns:
        (projects_df, services_df) 两个 DataFrame 的元组
    """
    xl = pd.ExcelFile(excel_file)

    # 读取 Projects sheet
    if "Projects" not in xl.sheet_names:
        print(f"Error: 'Projects' sheet not found in {excel_file}", file=sys.stderr)
        print(f"Available sheets: {xl.sheet_names}", file=sys.stderr)
        sys.exit(1)
    projects_df = pd.read_excel(excel_file, sheet_name="Projects")

    # 读取 Services sheet
    if "Services" not in xl.sheet_names:
        print(f"Error: 'Services' sheet not found in {excel_file}", file=sys.stderr)
        print(f"Available sheets: {xl.sheet_names}", file=sys.stderr)
        sys.exit(1)
    services_df = pd.read_excel(excel_file, sheet_name="Services")

    return projects_df, services_df


def parse_variable_yaml(var_str: str) -> List[Dict[str, Any]]:
    """
    解析 variable_yaml 字符串。

    Args:
        var_str: JSON 字符串或字典字符串

    Returns:
        变量列表 [{key, value}, ...]
    """
    if pd.isna(var_str) or var_str == "":
        return []

    # 如果已经是字符串格式的 JSON
    if isinstance(var_str, str):
        try:
            data = json.loads(var_str)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [{"key": k, "value": v} for k, v in data.items()]
        except json.JSONDecodeError:
            pass

    return []


def merge_service_variables(
    variable_yaml: List[Dict[str, Any]],
    service_row: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    将服务行中的预留字段合并到 variable_yaml 中。

    预留字段包括：
    - language
    - port
    - COMPONENT
    - NAMESPACE
    - team
    - TYPE

    Args:
        variable_yaml: 原始变量列表
        service_row: 服务数据行

    Returns:
        合并后的变量列表
    """
    # 转换为字典便于处理
    var_dict = {v["key"]: v["value"] for v in variable_yaml}

    # 需要合并的预留字段映射（字段名 -> 变量名）
    reserved_fields = {
        "language": "language",
        "port": "port",
        "COMPONENT": "COMPONENT",
        "NAMESPACE": "NAMESPACE",
        "team": "team",
        "TYPE": "TYPE",
    }

    # 合并非空的预留字段
    for field, var_name in reserved_fields.items():
        value = service_row.get(field)
        if not pd.isna(value) and value != "":
            # port 可能是浮点数，需要转换
            if field == "port" and isinstance(value, float):
                value = int(value) if value == int(value) else value
            var_dict[var_name] = value

    # 转换回列表格式
    return [{"key": k, "value": v} for k, v in var_dict.items()]


def create_projects_and_services(
    client: ZadigClient,
    projects_df: pd.DataFrame,
    services_df: pd.DataFrame,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    批量创建项目和服务。

    Args:
        client: Zadig API 客户端
        projects_df: 项目数据 DataFrame
        services_df: 服务数据 DataFrame
        dry_run: 是否为试运行（不实际创建）

    Returns:
        结果统计字典
    """
    results = {
        "projects": {"success": [], "failed": [], "skipped": []},
        "services": {"success": [], "failed": [], "skipped": []},
    }

    # 按 project_key 对服务进行分组
    services_by_project: Dict[str, List[Dict[str, Any]]] = {}
    for _, row in services_df.iterrows():
        project_key = row.get("project_key（app_domain）")
        if pd.isna(project_key):
            continue

        if project_key not in services_by_project:
            services_by_project[project_key] = []

        services_by_project[project_key].append(row.to_dict())

    # 创建项目
    for _, row in projects_df.iterrows():
        project_key = row.get("project_key（app_domain）")
        project_name = row.get("project_name")
        project_type = row.get("project_type", "yaml")
        is_public = row.get("is_public", False)
        description = row.get("description", "")

        # 跳过无效数据
        if pd.isna(project_key) or pd.isna(project_name):
            print(f"  ! Skipping invalid project data: {row.to_dict()}", file=sys.stderr)
            results["projects"]["skipped"].append(row.to_dict())
            continue

        # 处理 is_public 布尔值
        if isinstance(is_public, str):
            is_public = is_public.lower() in ("true", "1", "yes")
        elif pd.isna(is_public):
            is_public = False

        print(f"\n→ Creating project: {project_key} ({project_name})", file=sys.stderr)

        if dry_run:
            print(f"  [DRY RUN] Would create project", file=sys.stderr)
            results["projects"]["success"].append({"project_key": project_key, "project_name": project_name})
        else:
            try:
                response = client.create_project(
                    project_name=project_name,
                    project_key=project_key,
                    project_type=project_type,
                    is_public=bool(is_public),
                    description=description if not pd.isna(description) else "",
                )
                print(f"  ✓ Project created successfully", file=sys.stderr)
                results["projects"]["success"].append({
                    "project_key": project_key,
                    "project_name": project_name,
                    "response": response,
                })
            except ZadigAPIError as e:
                print(f"  ✗ Failed to create project: {e}", file=sys.stderr)
                results["projects"]["failed"].append({
                    "project_key": project_key,
                    "project_name": project_name,
                    "error": str(e),
                })
                continue

        # 创建该项目的服务
        if project_key in services_by_project:
            for service_row in services_by_project[project_key]:
                service_name = service_row.get("NAME")
                source = service_row.get("source", "template")
                template_name = service_row.get("template_name")
                variable_yaml_str = service_row.get("variable_yaml", "{}")
                auto_sync = service_row.get("auto_sync", True)

                # 跳过无效服务数据
                if pd.isna(service_name) or pd.isna(template_name):
                    print(f"    ! Skipping invalid service data", file=sys.stderr)
                    results["services"]["skipped"].append(service_row)
                    continue

                # 只处理 template 类型的服务
                if source != "template":
                    print(f"    ! Skipping service '{service_name}' with source '{source}'", file=sys.stderr)
                    results["services"]["skipped"].append(service_row)
                    continue

                # 处理 auto_sync 布尔值
                if isinstance(auto_sync, str):
                    auto_sync = auto_sync.lower() in ("true", "1", "yes")
                elif pd.isna(auto_sync):
                    auto_sync = True

                # 解析变量
                variable_yaml = parse_variable_yaml(variable_yaml_str)

                # 合并预留字段到 variable_yaml
                variable_yaml = merge_service_variables(variable_yaml, service_row)

                # 打印变量信息（调试用）
                if variable_yaml:
                    var_str = ", ".join([f"{v['key']}={v['value']}" for v in variable_yaml])
                    print(f"    → Variables: {var_str}", file=sys.stderr)

                print(f"    → Creating service: {service_name} from template '{template_name}'", file=sys.stderr)

                if dry_run:
                    print(f"      [DRY RUN] Would create service", file=sys.stderr)
                    results["services"]["success"].append({
                        "project_key": project_key,
                        "service_name": service_name,
                    })
                else:
                    try:
                        response = client.create_service_from_template(
                            project_key=project_key,
                            service_name=service_name,
                            template_name=template_name,
                            variable_yaml=variable_yaml,
                            auto_sync=bool(auto_sync),
                        )
                        print(f"      ✓ Service created successfully", file=sys.stderr)
                        results["services"]["success"].append({
                            "project_key": project_key,
                            "service_name": service_name,
                            "response": response,
                        })
                    except ZadigAPIError as e:
                        print(f"      ✗ Failed to create service: {e}", file=sys.stderr)
                        results["services"]["failed"].append({
                            "project_key": project_key,
                            "service_name": service_name,
                            "error": str(e),
                        })

    return results


def print_summary(results: Dict[str, Any]):
    """打印结果摘要。"""
    print("\n" + "=" * 60, file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    print(f"\nProjects:", file=sys.stderr)
    print(f"  ✓ Success: {len(results['projects']['success'])}", file=sys.stderr)
    print(f"  ✗ Failed:  {len(results['projects']['failed'])}", file=sys.stderr)
    print(f"  ⊘ Skipped: {len(results['projects']['skipped'])}", file=sys.stderr)

    print(f"\nServices:", file=sys.stderr)
    print(f"  ✓ Success: {len(results['services']['success'])}", file=sys.stderr)
    print(f"  ✗ Failed:  {len(results['services']['failed'])}", file=sys.stderr)
    print(f"  ⊘ Skipped: {len(results['services']['skipped'])}", file=sys.stderr)

    if results["projects"]["failed"]:
        print(f"\nFailed Projects:", file=sys.stderr)
        for item in results["projects"]["failed"]:
            print(f"  - {item.get('project_key')}: {item.get('error')}", file=sys.stderr)

    if results["services"]["failed"]:
        print(f"\nFailed Services:", file=sys.stderr)
        for item in results["services"]["failed"]:
            print(f"  - {item.get('project_key')}/{item.get('service_name')}: {item.get('error')}", file=sys.stderr)

    print("\n" + "=" * 60, file=sys.stderr)


def main():
    """CLI 入口点。"""
    parser = argparse.ArgumentParser(
        description="批量创建 Zadig 项目和服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 批量创建项目和服务
  python batch_create_projects.py projects.xlsx

  # 试运行（不实际创建）
  python batch_create_projects.py projects.xlsx --dry-run

  # 指定自定义配置
  python batch_create_projects.py projects.xlsx --endpoint https://zadig.example.com --token YOUR_TOKEN
        """
    )

    parser.add_argument("excel_file", help="Excel 文件路径")
    parser.add_argument("--endpoint", help="Zadig API endpoint URL")
    parser.add_argument("--token", help="Zadig API token")
    parser.add_argument("--no-verify-ssl", action="store_true", help="禁用 SSL 验证")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际创建")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时时间（秒）")
    parser.add_argument("--output", choices=["json", "pretty"], default="pretty", help="结果输出格式")

    args = parser.parse_args()

    # 检查文件是否存在
    if not Path(args.excel_file).exists():
        print(f"Error: File not found: {args.excel_file}", file=sys.stderr)
        sys.exit(1)

    # 加载配置
    config = load_config()

    try:
        # 创建客户端
        client = ZadigClient(
            endpoint=args.endpoint,
            api_token=args.token,
            verify_ssl=not args.no_verify_ssl,
            timeout=args.timeout,
            config=config,
        )

        # 加载 Excel 数据
        print(f"Loading data from: {args.excel_file}", file=sys.stderr)
        projects_df, services_df = load_excel_data(args.excel_file)

        print(f"  - Projects: {len(projects_df)} rows", file=sys.stderr)
        print(f"  - Services: {len(services_df)} rows", file=sys.stderr)

        # 批量创建
        results = create_projects_and_services(
            client,
            projects_df,
            services_df,
            dry_run=args.dry_run,
        )

        # 打印摘要
        print_summary(results)

        # 输出完整结果（可选）
        if args.output == "json":
            print(json.dumps(results, indent=2, ensure_ascii=False))

        # 如果有失败，返回非零退出码
        if results["projects"]["failed"] or results["services"]["failed"]:
            sys.exit(1)

    except ZadigAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
