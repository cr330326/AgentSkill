#!/usr/bin/env python3
"""
Zadig API Client

A Python client for interacting with Zadig OpenAPI endpoints.
Supports workflow execution, project management, and common DevOps operations.

Usage:
    python zadig_client.py list-workflows --project-key <project_key>
    python zadig_client.py trigger-workflow --project-key <project_key> --workflow-name <name>
    python zadig_client.py get-task-status --task-id <task_id>

Configuration:
    Set environment variables:
    - ZADIG_ENDPOINT: Zadig API endpoint (default: from config or https://zadig.example.com)
    - ZADIG_API_TOKEN: Your Zadig API token (required)
    Or use --endpoint and --token flags
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Default config file locations
CONFIG_FILE_PATHS = [
    "~/.zadigrc.json",
    "~/.config/zadig/config.json",
    "./.zadigrc.json",
]


def load_config() -> Dict[str, str]:
    """Load Zadig configuration from config file."""
    for config_path in CONFIG_FILE_PATHS:
        expanded_path = Path(config_path).expanduser()
        if expanded_path.exists():
            try:
                with open(expanded_path, "r") as f:
                    config = json.load(f)
                print(f"Loaded configuration from: {expanded_path}", file=sys.stderr)
                return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config from {expanded_path}: {e}", file=sys.stderr)
    return {}


class ZadigClient:
    """Client for Zadig OpenAPI interactions."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
        debug: bool = False,
        config: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize Zadig API client.

        Args:
            endpoint: Zadig API endpoint URL (e.g., https://zadig.example.com)
            api_token: Zadig API token for authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            debug: Enable debug output
            config: Configuration dict (from config file)
        """
        # Priority: command line args > config file > environment variables
        if config:
            self.endpoint = endpoint or config.get("endpoint") or os.environ.get("ZADIG_ENDPOINT", "")
            self.api_token = api_token or config.get("api_token") or os.environ.get("ZADIG_API_TOKEN", "")
        else:
            self.endpoint = endpoint or os.environ.get("ZADIG_ENDPOINT", "")
            self.api_token = api_token or os.environ.get("ZADIG_API_TOKEN", "")

        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.debug = debug

        if not self.endpoint:
            raise ValueError("Zadig endpoint is required. Set ZADIG_ENDPOINT or use --endpoint")
        if not self.api_token:
            raise ValueError("Zadig API token is required. Set ZADIG_API_TOKEN or use --token")

        # Ensure endpoint doesn't end with slash
        self.endpoint = self.endpoint.rstrip("/")

        # Create requests session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default Authorization header (Content-Type will be set per request)
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
        })

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to Zadig API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            path: API path (e.g., /openapi/workflows)
            params: Query parameters
            json_data: JSON request body

        Returns:
            Parsed JSON response
        """
        url = urljoin(self.endpoint + "/", path.lstrip("/"))

        # Prepare headers - only set Content-Type for methods with request body
        headers = {}
        if json_data is not None:
            headers["Content-Type"] = "application/json"

        if self.debug:
            print(f"\n=== HTTP Request Debug ===", file=sys.stderr)
            print(f"Method: {method.upper()}", file=sys.stderr)
            print(f"URL: {url}", file=sys.stderr)
            print(f"Query Params: {params}", file=sys.stderr)
            print(f"Request Body: {json.dumps(json_data, indent=2) if json_data else None}", file=sys.stderr)
            print(f"Headers: Authorization: Bearer {self.api_token[:20]}...", file=sys.stderr)
            print(f"SSL Verify: {self.verify_ssl}", file=sys.stderr)
            print(f"Timeout: {self.timeout}s", file=sys.stderr)
            print(f"========================\n", file=sys.stderr)

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                headers=headers if headers else None,
                verify=self.verify_ssl,
                timeout=self.timeout,
            )

            if self.debug:
                print(f"\n=== HTTP Response Debug ===", file=sys.stderr)
                print(f"Status Code: {response.status_code}", file=sys.stderr)
                print(f"Response Headers: {dict(response.headers)}", file=sys.stderr)
                print(f"Response Body: {response.text[:1000] if response.text else '(empty)'}", file=sys.stderr)
                print(f"=========================\n", file=sys.stderr)

            # Try to parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {"raw_response": response.text}

            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = data.get("message", data.get("error", "Unknown error"))
                # Print detailed error information for debugging
                print(f"\n=== API Error Details ===", file=sys.stderr)
                print(f"Status Code: {response.status_code}", file=sys.stderr)
                print(f"Error Message: {error_msg}", file=sys.stderr)
                print(f"Full Response: {json.dumps(data, indent=2, ensure_ascii=False)}", file=sys.stderr)
                print(f"=== End Error Details ===\n", file=sys.stderr)
                raise ZadigAPIError(
                    f"API request failed: {response.status_code} - {error_msg}",
                    status_code=response.status_code,
                    response=data,
                )

            return data

        except requests.exceptions.RequestException as e:
            if self.debug:
                import traceback
                print(f"\n=== Request Exception ===", file=sys.stderr)
                print(f"Exception Type: {type(e).__name__}", file=sys.stderr)
                print(f"Exception Message: {e}", file=sys.stderr)
                print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
                print(f"========================\n", file=sys.stderr)
            raise ZadigAPIError(f"HTTP error: {e}")
        except Exception as e:
            if self.debug:
                import traceback
                print(f"\n=== Unexpected Exception ===", file=sys.stderr)
                print(f"Exception Type: {type(e).__name__}", file=sys.stderr)
                print(f"Exception Message: {e}", file=sys.stderr)
                print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
                print(f"============================\n", file=sys.stderr)
            raise ZadigAPIError(f"Request failed: {e}")

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", path, params=params)

    def post(self, path: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", path, json_data=json_data)

    def put(self, path: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        return self._request("PUT", path, json_data=json_data)

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._request("DELETE", path, params=params)

    def patch(self, path: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PATCH request."""
        return self._request("PATCH", path, json_data=json_data)

    # ==================== Workflow API Methods ====================

    def list_workflows(self, project_key: str) -> Dict[str, Any]:
        """
        Get list of workflows in a project.

        Args:
            project_key: Project identifier

        Returns:
            Dictionary containing workflow list
        """
        return self.get("/openapi/workflows", params={"projectKey": project_key})

    def get_workflow_detail(self, workflow_name: str, project_key: str) -> Dict[str, Any]:
        """
        Get workflow details.

        Args:
            workflow_name: Workflow name/identifier
            project_key: Project identifier

        Returns:
            Workflow details
        """
        return self.get(
            f"/openapi/workflows/custom/{workflow_name}/detail",
            params={"projectKey": project_key}
        )

    def trigger_workflow(
        self,
        workflow_key: str,
        project_key: str,
        inputs: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        registry: Optional[str] = None,
        env_name: Optional[str] = None,
        auto_detect_registry: bool = True,
    ) -> Dict[str, Any]:
        """
        Trigger a workflow execution.

        Args:
            workflow_key: Workflow key/identifier
            project_key: Project identifier
            inputs: Optional input parameters for workflow jobs
            parameters: Optional global parameters for the workflow
            registry: Optional registry address (format: https://registry.com/namespace)
            env_name: Optional environment name to auto-detect registry from
            auto_detect_registry: Auto-detect registry from environment if not provided (default: true)

        Returns:
            Task execution response with task ID
        """
        # Auto-detect registry from environment if not provided
        if registry is None and auto_detect_registry:
            registry = self.get_env_registry(project_key, env_name)
            if registry:
                print(f"Auto-detected registry: {registry}", file=sys.stderr)

        # Inject registry into build job inputs if registry is provided
        if registry and inputs:
            for job_input in inputs:
                if job_input.get("job_type") == "zadig-build":
                    params = job_input.get("parameters", {})
                    # Check if registry is not already set
                    if "registry" not in params:
                        # Support both service_list and service_and_builds formats
                        if "service_list" in params or "service_and_builds" in params:
                            params["registry"] = registry
                            print(f"Injected registry into job: {job_input.get('job_name')}", file=sys.stderr)

        payload = {
            "project_key": project_key,
            "workflow_key": workflow_key,
        }
        if inputs:
            payload["inputs"] = inputs
        if parameters:
            payload["parameters"] = parameters

        return self.post("/openapi/workflows/custom/task", json_data=payload)

    def get_workflow_task(self, task_id: str, workflow_key: str) -> Dict[str, Any]:
        """
        Get workflow task status.

        Args:
            task_id: Task identifier
            workflow_key: Workflow key/identifier

        Returns:
            Task status and details
        """
        return self.get(
            "/openapi/workflows/custom/task",
            params={"taskId": task_id, "workflowKey": workflow_key}
        )

    def list_workflow_tasks(
        self,
        workflow_key: str,
        project_key: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List workflow task history.

        Args:
            workflow_key: Workflow key/identifier
            project_key: Project identifier
            page: Page number
            page_size: Items per page

        Returns:
            List of workflow tasks
        """
        return self.get(
            f"/openapi/workflows/custom/{workflow_key}/tasks",
            params={
                "projectKey": project_key,
                "page": page,
                "pageSize": page_size,
            }
        )

    def cancel_workflow_task(self, task_id: str, workflow_key: str) -> Dict[str, Any]:
        """
        Cancel a running workflow task.

        Args:
            task_id: Task identifier
            workflow_key: Workflow key/identifier

        Returns:
            Cancellation response
        """
        return self.delete(
            "/openapi/workflows/custom/task",
            params={"taskId": task_id, "workflowKey": workflow_key}
        )

    # ==================== Project API Methods ====================

    def list_projects(
        self,
        page_num: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Get list of all projects.

        Args:
            page_num: Page number (default: 1)
            page_size: Items per page (default: 20)

        Returns:
            List of projects
        """
        return self.get(
            "/openapi/projects/project",
            params={"pageNum": page_num, "pageSize": page_size}
        )

    def get_project(self, project_key: str) -> Dict[str, Any]:
        """
        Get project details.

        Args:
            project_key: Project identifier

        Returns:
            Project details
        """
        return self.get(
            "/openapi/projects/project/detail",
            params={"projectKey": project_key}
        )

    def create_project(
        self,
        project_name: str,
        project_key: str,
        project_type: str,
        is_public: bool,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Create an empty Zadig project.

        Official API: POST /openapi/projects/project
        Reference: references/02.project.md - 创建空项目

        Args:
            project_name: Project display name (required)
            project_key: Project identifier, lowercase letters/numbers/hyphens only (required)
            project_type: Project type - yaml/helm/loaded (required)
            is_public: Whether project is public (required)
            description: Project description (optional)

        Returns:
            API response
        """
        data = {
            "project_name": project_name,
            "project_key": project_key,
            "project_type": project_type,
            "is_public": is_public,
        }
        if description:
            data["description"] = description

        return self.post("/openapi/projects/project", json_data=data)

    def create_service_from_template(
        self,
        project_key: str,
        service_name: str,
        template_name: str,
        variable_yaml: Optional[List[Dict[str, Any]]] = None,
        auto_sync: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a service from a template (测试服务).

        Official API: POST /openapi/service/template/load/yaml
        Reference: references/05.service.md - 使用模板新建服务（测试服务）

        Args:
            project_key: Project identifier (required)
            service_name: Service name (required)
            template_name: K8s Yaml template name (required)
            variable_yaml: Template variables as list of {key, value} dicts (optional)
            auto_sync: Whether to auto-sync from template (default: true)

        Returns:
            API response
        """
        data = {
            "project_key": project_key,
            "service_name": service_name,
            "template_name": template_name,
            "auto_sync": auto_sync,
        }
        if variable_yaml:
            data["variable_yaml"] = variable_yaml

        return self.post("/openapi/service/template/load/yaml", json_data=data)

    def create_service_from_yaml(
        self,
        project_key: str,
        service_name: str,
        yaml_content: str,
    ) -> Dict[str, Any]:
        """
        Create a service with raw YAML content.

        Args:
            project_key: Project identifier
            service_name: Service name
            yaml_content: YAML configuration content

        Returns:
            API response
        """
        data = {
            "project_key": project_key,
            "service_name": service_name,
            "yaml": yaml_content,
        }

        return self.post("/openapi/service/yaml/raw", json_data=data)

    # ==================== Environment API Methods ====================

    def list_environments(self, project_key: str) -> Dict[str, Any]:
        """
        Get list of environments in a project.

        Args:
            project_key: Project identifier

        Returns:
            List of environments with registry information
        """
        return self.get(
            "/openapi/environments",
            params={"projectKey": project_key}
        )

    def get_env_registry(self, project_key: str, env_name: str = None) -> Optional[str]:
        """
        Get registry address from environment. If env_name is not specified,
        returns the registry from the first environment.

        Args:
            project_key: Project identifier
            env_name: Optional environment name/filter

        Returns:
            Registry address (including namespace), or None if not found
        """
        envs = self.list_environments(project_key)
        if not envs:
            return None

        # Filter by env_name if specified
        target_env = None
        if env_name:
            for env in envs:
                if env.get("env_key") == env_name or env.get("envName") == env_name:
                    target_env = env
                    break
        else:
            # Use first environment
            target_env = envs[0]

        if not target_env:
            return None

        # Get registry details
        registry_id = target_env.get("registry_id")
        if not registry_id:
            return None

        # Get registry info to build full address
        registries = self.get("/openapi/system/registry")
        if not registries:
            return None

        for reg in registries:
            if reg.get("registry_id") == registry_id:
                address = reg.get("address", "").rstrip("/")
                namespace = reg.get("namespace", "")
                if namespace:
                    return f"{address}/{namespace}"
                return address

        return None

    def _should_skip_job(self, job: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if a job should be skipped from the inputs array.

        Only approval/notification jobs are skipped as they use workflow config.
        Jobs with source="fromjob" still need to be in inputs (with empty/minimal params).

        Args:
            job: Job definition from workflow

        Returns:
            Tuple of (should_skip, reason)
        """
        job_type = job.get("type", "")
        job_name = job.get("name", "")

        # Approval/notification jobs use workflow config, no inputs needed
        if job_type in ["approval", "notification"]:
            return True, f"{job_type} job uses workflow configuration, no inputs needed"

        return False, ""

    def _build_build_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for zadig-build job."""
        spec = job.get("spec", {})
        service_and_builds = spec.get("service_and_builds_options", spec.get("default_service_and_builds", []))
        service_list = []
        for sb in service_and_builds:
            service_list.append({
                "service_name": sb.get("service_name"),
                "service_module": sb.get("service_module")
            })

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "service_list": service_list
            }
        }

    def _build_deploy_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for zadig-deploy job."""
        spec = job.get("spec", {})
        service_and_images = spec.get("service_and_images", [])
        service_list = []
        for si in service_and_images:
            service_list.append({
                "service_name": si.get("service_name"),
                "service_module": si.get("service_module"),
                "value": si.get("value")
            })

        deploy_params = {
            "service_list": service_list
        }

        # Add env_name for runtime source
        if spec.get("env_source") == "runtime":
            deploy_params["env_name"] = spec.get("env")

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": deploy_params
        }

    def _build_scanning_job_input(self, job: Dict[str, Any], build_repos: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Build input for zadig-scanning job."""
        spec = job.get("spec", {})
        service_scanning_options = spec.get("service_scanning_options", [])
        scanning_list = []
        for ss in service_scanning_options:
            scanning_entry = {
                "scanning_name": ss.get("name")
            }

            # Try to get repos from build_repos first, then from service_scanning_options
            repos = []
            service_key = f"{ss.get('service_name')}.{ss.get('service_module')}"
            if build_repos and service_key in build_repos:
                repos = build_repos[service_key]
            else:
                repos = ss.get("repos", [])

            # Add repo_info if available
            if repos:
                repo_info = []
                for repo in repos:
                    repo_info.append({
                        "codehost_name": repo.get("source", ""),
                        "repo_namespace": repo.get("repo_namespace", ""),
                        "repo_name": repo.get("repo_name", ""),
                        "branch": repo.get("branch", "")
                    })
                scanning_entry["repo_info"] = repo_info

            scanning_list.append(scanning_entry)

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "scanning_list": scanning_list
            }
        }

    def _build_test_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for zadig-test job."""
        spec = job.get("spec", {})
        test_modules = spec.get("test_modules", [])
        testing_list = []
        for tm in test_modules:
            testing_list.append({
                "testing_name": tm.get("test_name"),
            })

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "testing_list": testing_list
            }
        }

    def _build_custom_deploy_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for custom-deploy (K8s deploy) job."""
        spec = job.get("spec", {})
        targets = spec.get("targets", [])
        target_list = []
        for target in targets:
            target_list.append({
                "workload_type": target.get("workload_type"),
                "workload_name": target.get("workload_name"),
                "container_name": target.get("container_name"),
                "image_name": target.get("image")
            })

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "target_list": target_list
            }
        }

    def _build_update_k8s_yaml_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for update-k8s-yaml job."""
        spec = job.get("spec", {})
        items = spec.get("items", [])
        target_list = []
        for item in items:
            target_list.append({
                "resource_kind": item.get("resource_kind"),
                "resource_name": item.get("resource_name"),
                "patch_strategy": item.get("patch_strategy"),
                "patch_content": item.get("patch_content")
            })

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "target_list": target_list
            }
        }

    def _build_freestyle_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for freestyle/plugin job."""
        spec = job.get("spec", {})
        properties = spec.get("properties", {})
        params = properties.get("params", [])

        kv = []
        for param in params:
            if param.get("default"):
                kv.append({
                    "key": param.get("name"),
                    "value": param.get("default")
                })

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "kv": kv
            }
        }

    def _build_sql_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for SQL job."""
        spec = job.get("spec", {})
        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "database_name": spec.get("db_name"),
                "sql": spec.get("sql_scripts", [""])[0] if spec.get("sql_scripts") else ""
            }
        }

    def _build_distribute_image_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for distribute-image job."""
        spec = job.get("spec", {})
        service_and_images = spec.get("service_and_images", [])
        service_list = []
        for si in service_and_images:
            service_list.append({
                "service_name": si.get("service_name"),
                "service_module": si.get("service_module")
            })

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "service_list": service_list,
                "target_registry_id": spec.get("target_registry_id")
            }
        }

    def _build_jira_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for JIRA job."""
        spec = job.get("spec", {})
        jira_spec = spec.get("jira_spec", {})

        kv = []
        if jira_spec.get("target_status"):
            kv.append({"key": "TargetStatus", "value": jira_spec.get("target_status")})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "kv": kv
            }
        }

    def _build_lark_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for Lark job."""
        spec = job.get("spec", {})
        lark_spec = spec.get("lark_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "work_item_id": lark_spec.get("work_item_id", ""),
                "target_status": lark_spec.get("target_status", "")
            }
        }

    def _build_pingcode_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for PingCode job."""
        spec = job.get("spec", {})
        pingcode_spec = spec.get("pingcode_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "work_item_id": pingcode_spec.get("work_item_id", ""),
                "target_status": pingcode_spec.get("target_status", "")
            }
        }

    def _build_tapd_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for Tapd job."""
        spec = job.get("spec", {})
        tapd_spec = spec.get("tapd_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "project_id": tapd_spec.get("project_id", ""),
                "project_name": tapd_spec.get("project_name", ""),
                "status": tapd_spec.get("status", ""),
                "iteration_ids": tapd_spec.get("iteration_ids", [])
            }
        }

    def _build_apollo_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for Apollo job."""
        spec = job.get("spec", {})
        apollo_spec = spec.get("apollo_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "namespace": apollo_spec.get("namespace", "")
            }
        }

    def _build_nacos_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for Nacos job."""
        spec = job.get("spec", {})
        nacos_spec = spec.get("nacos_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "namespace": nacos_spec.get("namespace", ""),
                "group": nacos_spec.get("group_name", "")
            }
        }

    def _build_jenkins_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for Jenkins job."""
        spec = job.get("spec", {})
        jenkins_spec = spec.get("jenkins_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "job_name": jenkins_spec.get("job_name", "")
            }
        }

    def _build_blueking_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for BlueKing job."""
        spec = job.get("spec", {})
        bk_spec = spec.get("blueking_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "job_name": bk_spec.get("job_name", "")
            }
        }

    def _build_grafana_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for Grafana job."""
        spec = job.get("spec", {})
        grafana_spec = spec.get("grafana_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "monitors": grafana_spec.get("monitors", [])
            }
        }

    def _build_offline_service_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for offline-service job."""
        spec = job.get("spec", {})
        env = spec.get("env", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "env_name": env.get("env_name", "")
            }
        }

    def _build_dms_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for DMS job."""
        spec = job.get("spec", {})
        dms_spec = spec.get("dms_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "db_list": dms_spec.get("db_list", []),
                "affect_rows": dms_spec.get("affect_rows", 0),
                "exec_sql": dms_spec.get("exec_sql", "")
            }
        }

    def _build_trigger_workflow_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for trigger-workflow job."""
        spec = job.get("spec", {})
        trigger_spec = spec.get("trigger_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "service_and_workflow_list": trigger_spec.get("service_and_workflow_list", [])
            }
        }

    def _build_custom_task_job_input(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build input for custom-task job."""
        spec = job.get("spec", {})
        custom_task_spec = spec.get("custom_task_spec", {})

        return {
            "job_name": job.get("name"),
            "job_type": job.get("type"),
            "parameters": {
                "kv": custom_task_spec.get("params", [])
            }
        }

    # Job handler registry - maps job types to their handler methods
    # Note: Only job types supported by Zadig OpenAPI should be listed here
    _JOB_HANDLERS = {
        "zadig-build": "_build_build_job_input",
        "zadig-deploy": "_build_deploy_job_input",
        "zadig-scanning": "_build_scanning_job_input",
        "zadig-test": "_build_test_job_input",
        "custom-deploy": "_build_custom_deploy_job_input",
        "update-k8s-yaml": "_build_update_k8s_yaml_job_input",
        "freestyle": "_build_freestyle_job_input",
        "plugin": "_build_freestyle_job_input",
        "sql": "_build_sql_job_input",
        "distribute-image": "_build_distribute_image_job_input",
        "jira": "_build_jira_job_input",
        "lark": "_build_lark_job_input",
        "pingcode": "_build_pingcode_job_input",
        "tapd": "_build_tapd_job_input",
        "apollo": "_build_apollo_job_input",
        "nacos": "_build_nacos_job_input",
        "jenkins": "_build_jenkins_job_input",
        "blueking": "_build_blueking_job_input",
        "offline-service": "_build_offline_service_job_input",
        "dms": "_build_dms_job_input",
        "trigger-workflow": "_build_trigger_workflow_job_input",
        "custom-task": "_build_custom_task_job_input",
        # Note: grafana, notification jobs are not supported by OpenAPI
    }

    def build_workflow_inputs(self, workflow_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build complete inputs for all stages in a workflow.

        This helper method constructs the inputs array needed to trigger all stages
        in a workflow. It uses default values from the workflow definition and
        supports all Zadig job types.

        Jobs with "source": "fromjob" still need to be in inputs, and their
        dependent job's information (like repos) will be used.

        Args:
            workflow_detail: Workflow detail from get_workflow_detail()

        Returns:
            List of input dictionaries for all stages
        """
        inputs = []
        print(f"\n=== Building workflow inputs ===", file=sys.stderr)

        # First pass: collect build job repos for scanning jobs to use
        build_repos = {}
        for stage in workflow_detail.get("stages", []):
            for job in stage.get("jobs", []):
                if job.get("type") == "zadig-build":
                    spec = job.get("spec", {})
                    # Try both service_and_builds_options and default_service_and_builds
                    service_and_builds = spec.get("service_and_builds_options") or spec.get("default_service_and_builds", [])
                    for sb in service_and_builds:
                        repos = sb.get("repos", [])
                        if repos:
                            key = f"{sb.get('service_name')}.{sb.get('service_module')}"
                            build_repos[key] = repos
                            print(f"  → Found {len(repos)} repo(s) for {key}", file=sys.stderr)

        if not build_repos:
            print(f"  ! No repos found in build jobs, scanning jobs will not have repo_info", file=sys.stderr)

        # Second pass: build inputs for all jobs
        for stage in workflow_detail.get("stages", []):
            stage_name = stage.get("name", "Unnamed Stage")
            print(f"Processing stage: {stage_name}", file=sys.stderr)

            for job in stage.get("jobs", []):
                job_type = job.get("type", "")
                job_name = job.get("name", "")

                # Check if job should be skipped
                should_skip, skip_reason = self._should_skip_job(job)
                if should_skip:
                    print(f"  ✓ Skipping '{job_name}' ({skip_reason})", file=sys.stderr)
                    continue

                # Look up handler for this job type
                handler_method_name = self._JOB_HANDLERS.get(job_type)

                if handler_method_name:
                    try:
                        handler = getattr(self, handler_method_name)
                        # Pass build_repos only for scanning jobs
                        if job_type == "zadig-scanning":
                            job_input = handler(job, build_repos=build_repos)
                        else:
                            job_input = handler(job)
                        if job_input is not None:
                            inputs.append(job_input)
                            print(f"  + Added input for '{job_name}' (type: {job_type})", file=sys.stderr)
                    except Exception as e:
                        print(f"  ! Warning: Failed to build input for '{job_name}': {e}", file=sys.stderr)
                else:
                    # Unknown job type - log warning but don't fail
                    print(f"  ! Warning: Unknown job type '{job_type}' for '{job_name}', skipping", file=sys.stderr)

        print(f"\n=== Built {len(inputs)} inputs ===\n", file=sys.stderr)
        return inputs

    # ==================== Generic API Method ====================

    def api_call(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a generic API call.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            json_data: Request body

        Returns:
            API response
        """
        return self._request(method, path, params, json_data)


class ZadigAPIError(Exception):
    """Exception raised for Zadig API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


def format_json_output(data: Dict[str, Any], pretty: bool = True) -> str:
    """Format JSON data for output."""
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Zadig API Client - Interact with Zadig OpenAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List workflows in a project
  python zadig_client.py list-workflows --project-key my-project

  # Trigger a workflow
  python zadig_client.py trigger-workflow --project-key my-project --workflow-name build-test

  # Get task status
  python zadig_client.py get-task-status --task-id 12345 --project-key my-project

  # List all projects
  python zadig_client.py list-projects

  # Make a custom API call
  python zadig_client.py api-call GET /openapi/workflows --project-key my-project
        """
    )

    # Global options
    parser.add_argument("--endpoint", help="Zadig endpoint URL", default=os.environ.get("ZADIG_ENDPOINT"))
    parser.add_argument("--token", help="Zadig API token", default=os.environ.get("ZADIG_API_TOKEN"))
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--output", choices=["json", "pretty"], default="pretty", help="Output format")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Workflow commands
    subparsers.add_parser("list-workflows", help="List workflows in a project")
    subparsers.add_parser("list-projects", help="List all projects")

    trigger_parser = subparsers.add_parser("trigger-workflow", help="Trigger a workflow")
    trigger_parser.add_argument("--project-key", required=True, help="Project identifier")
    trigger_parser.add_argument("--workflow-key", required=True, help="Workflow key")
    trigger_parser.add_argument("--inputs", help="JSON string of workflow inputs")
    trigger_parser.add_argument("--parameters", help="JSON string of workflow parameters")
    trigger_parser.add_argument("--registry", help="Registry address (e.g., https://registry.com/namespace). Auto-detected from environment if not specified")
    trigger_parser.add_argument("--env-name", help="Environment name to detect registry from")
    trigger_parser.add_argument("--no-auto-detect-registry", action="store_true", help="Disable automatic registry detection from environment")
    trigger_parser.add_argument("--use-all-stages", action="store_true", help="Automatically build inputs for all stages using workflow definition (overrides --inputs)")

    task_status_parser = subparsers.add_parser("get-task-status", help="Get workflow task status")
    task_status_parser.add_argument("--task-id", required=True, help="Task identifier")
    task_status_parser.add_argument("--workflow-key", required=True, help="Workflow key")

    list_tasks_parser = subparsers.add_parser("list-workflow-tasks", help="List workflow task history")
    list_tasks_parser.add_argument("--project-key", required=True, help="Project identifier")
    list_tasks_parser.add_argument("--workflow-key", required=True, help="Workflow key")
    list_tasks_parser.add_argument("--page", type=int, default=1, help="Page number")
    list_tasks_parser.add_argument("--page-size", type=int, default=20, help="Items per page")

    cancel_parser = subparsers.add_parser("cancel-task", help="Cancel a workflow task")
    cancel_parser.add_argument("--task-id", required=True, help="Task identifier")
    cancel_parser.add_argument("--workflow-key", required=True, help="Workflow key")

    # Generic API call
    api_parser = subparsers.add_parser("api-call", help="Make a custom API call")
    api_parser.add_argument("method", help="HTTP method (GET, POST, PUT, DELETE, PATCH)")
    api_parser.add_argument("path", help="API path (e.g., /openapi/workflows)")
    api_parser.add_argument("--params", help="JSON string of query parameters")
    api_parser.add_argument("--data", help="JSON string of request body")

    # Workflow commands with args
    list_workflows_parser = subparsers.add_parser("list-workflows-full", help="List workflows (with project key)")
    list_workflows_parser.add_argument("--project-key", required=True, help="Project identifier")

    get_workflow_parser = subparsers.add_parser("get-workflow", help="Get workflow details")
    get_workflow_parser.add_argument("--project-key", required=True, help="Project identifier")
    get_workflow_parser.add_argument("--workflow-key", required=True, help="Workflow key")

    get_project_parser = subparsers.add_parser("get-project", help="Get project details")
    get_project_parser.add_argument("--project-key", required=True, help="Project identifier")

    create_project_parser = subparsers.add_parser("create-project", help="Create a new project")
    create_project_parser.add_argument("--project-key", required=True, help="Project identifier")
    create_project_parser.add_argument("--project-name", required=True, help="Project display name")
    create_project_parser.add_argument("--project-type", default="yaml", choices=["yaml", "helm", "loaded"], help="Project type")
    create_project_parser.add_argument("--is-public", action="store_true", help="Whether project is public")
    create_project_parser.add_argument("--description", default="", help="Project description")
    create_project_parser.add_argument("--namespace", default="", help="Kubernetes namespace (for YAML projects)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load config file
    config = load_config()

    try:
        client = ZadigClient(
            endpoint=args.endpoint if args.endpoint != os.environ.get("ZADIG_ENDPOINT") else None,
            api_token=args.token if args.token != os.environ.get("ZADIG_API_TOKEN") else None,
            verify_ssl=not args.no_verify_ssl,
            timeout=args.timeout,
            debug=args.debug if hasattr(args, 'debug') else False,
            config=config,
        )

        result = None

        if args.command == "list-workflows":
            print("Error: --project-key is required for list-workflows", file=sys.stderr)
            print("Use 'list-workflows-full' command instead, or specify --project-key", file=sys.stderr)
            sys.exit(1)

        elif args.command == "list-workflows-full":
            result = client.list_workflows(args.project_key)

        elif args.command == "list-projects":
            result = client.list_projects()

        elif args.command == "trigger-workflow":
            registry = getattr(args, 'registry', None)
            env_name = getattr(args, 'env_name', None)
            auto_detect_registry = not getattr(args, 'no_auto_detect_registry', False)
            use_all_stages = getattr(args, 'use_all_stages', False)

            inputs = None
            if use_all_stages:
                # Get workflow detail and build inputs for all stages
                workflow_detail = client.get_workflow_detail(args.workflow_key, args.project_key)
                inputs = client.build_workflow_inputs(workflow_detail)
                print(f"Auto-built inputs for {len(inputs)} stages", file=sys.stderr)
            elif args.inputs:
                inputs = json.loads(args.inputs)

            parameters = json.loads(args.parameters) if hasattr(args, 'parameters') and args.parameters else None
            result = client.trigger_workflow(
                args.workflow_key,
                args.project_key,
                inputs,
                parameters,
                registry=registry,
                env_name=env_name,
                auto_detect_registry=auto_detect_registry,
            )

        elif args.command == "get-task-status":
            result = client.get_workflow_task(args.task_id, args.workflow_key)

        elif args.command == "list-workflow-tasks":
            result = client.list_workflow_tasks(
                args.workflow_key,
                args.project_key,
                args.page,
                args.page_size,
            )

        elif args.command == "cancel-task":
            result = client.cancel_workflow_task(args.task_id, args.workflow_key)

        elif args.command == "api-call":
            params = json.loads(args.params) if args.params else None
            data = json.loads(args.data) if args.data else None
            result = client.api_call(args.method, args.path, params, data)

        elif args.command == "get-workflow":
            result = client.get_workflow_detail(args.workflow_key, args.project_key)

        elif args.command == "get-project":
            result = client.get_project(args.project_key)

        elif args.command == "create-project":
            result = client.create_project(
                project_name=args.project_name,
                project_key=args.project_key,
                project_type=args.project_type,
                is_public=args.is_public,
                description=args.description,
            )

        # Output result
        if result is not None:
            if args.output == "pretty":
                print(format_json_output(result))
            else:
                print(json.dumps(result))

    except ZadigAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
