"""Huawei Cloud SDK tool registry for the AIOps Agent.

Unified registry wrapping AOM, CES, CTS, CSS, ECS, CCE, FunctionGraph,
VPN, and CBR SDKs. Reuses css-testing/huawei_css_api.py builder pattern.
"""

from typing import Callable, Optional

from ops_agent_config import OpsAgentConfig
from action_policy import ActionPolicy


def _build_sdk_client(service_module: str, client_class_name: str,
                      region: str, credentials) -> object:
    """Generic SDK client builder following css-testing pattern."""
    import importlib
    from huaweicloudsdkcore.http.http_config import HttpConfig

    module = importlib.import_module(service_module)
    client_class = getattr(module, client_class_name)
    region_class = getattr(module, f"{client_class_name.replace('Client', 'Region')}")

    http_config = HttpConfig.get_default_config()
    http_config.timeout = (30, 60)

    return (
        client_class.new_builder()
        .with_http_config(http_config)
        .with_credentials(credentials)
        .with_region(region_class.value_of(region))
        .build()
    )


def _get_credentials(config: OpsAgentConfig):
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    return BasicCredentials(
        ak=config.hwc_ak,
        sk=config.hwc_sk,
        project_id=config.hwc_project_id,
    )


class AOMTools:
    """Huawei Cloud AOM (Application Operations Management) SDK tools."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkaom.v1", "AomClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def list_alarms(self, alarm_name: Optional[str] = None,
                    severity: Optional[list[str]] = None) -> list:
        from huaweicloudsdkaom.v1 import ListAlarmsRequest
        req = ListAlarmsRequest()
        if alarm_name:
            req.alarm_name = alarm_name
        if severity:
            req.severity = ",".join(severity)
        resp = self.client.list_alarms(req)
        return resp.alarms or []

    def show_alarm_history(self, alarm_id: str) -> dict:
        from huaweicloudsdkaom.v1 import ShowAlarmHistoryRequest
        req = ShowAlarmHistoryRequest(alarm_id=alarm_id)
        return self.client.show_alarm_history(req)

    def list_components(self, app_id: str) -> list:
        from huaweicloudsdkaom.v1 import ListComponentsRequest
        req = ListComponentsRequest(app_id=app_id)
        resp = self.client.list_components(req)
        return resp.components or []

    def show_component_metrics(self, component_id: str, metric_names: list) -> dict:
        from huaweicloudsdkaom.v1 import ShowComponentMetricsRequest
        req = ShowComponentMetricsRequest(component_id=component_id)
        req.metric_names = metric_names
        return self.client.show_component_metrics(req)


class CESTools:
    """Huawei Cloud CES (Cloud Eye Service) SDK tools."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkces.v1", "CesClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def list_metrics(self, namespace: str, dim_name: str, dim_id: str) -> list:
        from huaweicloudsdkces.v1 import ListMetricsRequest
        req = ListMetricsRequest(namespace=namespace, dim_name=dim_name, dim_id=dim_id)
        resp = self.client.list_metrics(req)
        return resp.metrics or []

    def show_metric_data(self, metric_name: str, namespace: str,
                         dim_name: str, dim_id: str, period: int,
                         _from: int, to: int) -> dict:
        from huaweicloudsdkces.v1 import ShowMetricDataRequest, ShowMetricDataRequestBody
        body = ShowMetricDataRequestBody(
            namespace=namespace, metric_name=metric_name,
            dim_name=dim_name, dim_id=dim_id,
            period=period, filter="average", _from=_from, to=to,
        )
        req = ShowMetricDataRequest(body=body)
        return self.client.show_metric_data(req)

    def list_alarms(self, alarm_name: Optional[str] = None) -> list:
        from huaweicloudsdkces.v1 import ListAlarmsRequest
        req = ListAlarmsRequest()
        if alarm_name:
            req.alarm_name = alarm_name
        resp = self.client.list_alarms(req)
        return resp.alarms or []

    def show_alarm_history(self, alarm_id: str) -> dict:
        from huaweicloudsdkces.v1 import ShowAlarmHistoryRequest
        req = ShowAlarmHistoryRequest(alarm_id=alarm_id)
        return self.client.show_alarm_history(req)


class CTSTools:
    """Huawei Cloud CTS (Cloud Trace Service) SDK tools."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkcts.v3", "CtsClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def list_traces(self, resource_type: Optional[str] = None,
                    resource_id: Optional[str] = None,
                    from_time: Optional[int] = None,
                    to_time: Optional[int] = None) -> list:
        from huaweicloudsdkcts.v3 import ListTracesRequest
        req = ListTracesRequest(tracker_name=self.config.cts_tracker_name)
        if resource_type:
            req.resource_type = resource_type
        if resource_id:
            req.resource_id = resource_id
        if from_time:
            req.from_time = from_time
        if to_time:
            req.to_time = to_time
        resp = self.client.list_traces(req)
        return resp.traces or []

    def list_trace_quotas(self) -> dict:
        from huaweicloudsdkcts.v3 import ListTraceQuotasRequest
        req = ListTraceQuotasRequest()
        return self.client.list_trace_quotas(req)


class CSSTools:
    """Huawei Cloud CSS (Cloud Search Service) SDK tools.

    Reuses css-testing/huawei_css_api.py pattern.
    """

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkcss.v1", "CssClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def get_cluster_info(self, cluster_id: str) -> dict:
        from huaweicloudsdkcss.v1 import ShowClusterDetailRequest
        req = ShowClusterDetailRequest(cluster_id=cluster_id)
        return self.client.show_cluster_detail(req)

    def get_cluster_status(self, cluster_id: str) -> str:
        info = self.get_cluster_info(cluster_id)
        return getattr(info, "status", "unknown")

    def get_data_node_count(self, cluster_id: str) -> int:
        info = self.get_cluster_info(cluster_id)
        return getattr(info, "data_node_num", 0)

    def scale_out_data_nodes(self, cluster_id: str, node_count: int) -> dict:
        from huaweicloudsdkcss.v1 import ExtendClusterRequest, ExtendClusterRequestBody
        body = ExtendClusterRequestBody(type="ess", nodes=node_count)
        req = ExtendClusterRequest(cluster_id=cluster_id, body=body)
        return self.client.extend_cluster(req)

    def scale_in_data_nodes(self, cluster_id: str, node_count: int) -> dict:
        from huaweicloudsdkcss.v1 import ShrinkClusterRequest, ShrinkClusterRequestBody
        body = ShrinkClusterRequestBody(type="ess", nodes=node_count)
        req = ShrinkClusterRequest(cluster_id=cluster_id, body=body)
        return self.client.shrink_cluster(req)


class ECSTools:
    """Huawei Cloud ECS SDK tools (read + change)."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkecs.v2", "EcsClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def list_servers(self) -> list:
        from huaweicloudsdkecs.v2 import ListServersDetailsRequest
        req = ListServersDetailsRequest()
        resp = self.client.list_servers_details(req)
        return resp.servers or []

    def show_server(self, server_id: str) -> dict:
        from huaweicloudsdkecs.v2 import ShowServerRequest
        req = ShowServerRequest(server_id=server_id)
        return self.client.show_server(req)

    def resize_server(self, server_id: str, flavor_ref: str) -> dict:
        from huaweicloudsdkecs.v2 import ResizeServerRequest
        req = ResizeServerRequest(server_id=server_id)
        req.body = {"resize": {"flavor_ref": flavor_ref}}
        return self.client.resize_server(req)

    def reboot_server(self, server_id: str, reboot_type: str = "SOFT") -> dict:
        from huaweicloudsdkecs.v2 import RebootServerRequest
        req = RebootServerRequest(server_id=server_id)
        req.body = {"reboot": {"type": reboot_type}}
        return self.client.reboot_server(req)


class CCETools:
    """Huawei Cloud CCE (Cloud Container Engine) SDK tools."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkcce.v3", "CceClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def list_pods(self, cluster_id: str, namespace: str = "default") -> list:
        from huaweicloudsdkcce.v3 import ListPodsRequest
        req = ListPodsRequest(cluster_id=cluster_id, namespace=namespace)
        resp = self.client.list_pods(req)
        return resp.items or []

    def show_pod(self, cluster_id: str, namespace: str, pod_name: str) -> dict:
        from huaweicloudsdkcce.v3 import ShowPodRequest
        req = ShowPodRequest(cluster_id=cluster_id, namespace=namespace, name=pod_name)
        return self.client.show_pod(req)

    def restart_pod(self, cluster_id: str, namespace: str, deployment_name: str) -> dict:
        from huaweicloudsdkcce.v3 import CreateAddonInstanceRequest
        # Restart via deployment rollout restart
        req = CreateAddonInstanceRequest(cluster_id=cluster_id)
        return self.client.create_addon_instance(req)

    def scale_deployment(self, cluster_id: str, namespace: str,
                         deployment_name: str, replicas: int) -> dict:
        from huaweicloudsdkcce.v3 import UpdateDeploymentRequest
        req = UpdateDeploymentRequest(
            cluster_id=cluster_id, namespace=namespace,
            name=deployment_name,
        )
        return self.client.update_deployment(req)


class FunctionGraphTools:
    """Huawei Cloud FunctionGraph SDK tools for remediation."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _build_sdk_client(
                "huaweicloudsdkfunctiongraph.v2", "FunctionGraphClient",
                self.config.hwc_region, _get_credentials(self.config),
            )
        return self._client

    def invoke_function(self, function_urn: str, payload: dict) -> dict:
        from huaweicloudsdkfunctiongraph.v2 import InvokeFunctionRequest
        import json
        req = InvokeFunctionRequest(function_urn=function_urn)
        req.body = json.dumps(payload)
        return self.client.invoke_function(req)


class HuaweiCloudToolRegistry:
    """Registry of all Huawei Cloud SDK tools with action level classification."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self.policy = ActionPolicy(config.policy_dir)
        self.aom = AOMTools(config)
        self.ces = CESTools(config)
        self.cts = CTSTools(config)
        self.css = CSSTools(config)
        self.ecs = ECSTools(config)
        self.cce = CCETools(config)
        self.fg = FunctionGraphTools(config)

    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """Get a tool function by name (e.g., 'aom.list_alarms')."""
        service, method = tool_name.split(".", 1) if "." in tool_name else (tool_name, "")
        tools_map = {
            "aom": self.aom,
            "ces": self.ces,
            "cts": self.cts,
            "css": self.css,
            "ecs": self.ecs,
            "cce": self.cce,
            "functiongraph": self.fg,
            "fg": self.fg,
        }
        obj = tools_map.get(service)
        if obj and method:
            return getattr(obj, method, None)
        return None

    def classify_action_level(self, tool_name: str) -> str:
        """Classify tool into L0/L1/L2/L3 based on action_levels.json."""
        return self.policy.classify(tool_name)

    def dry_run(self, tool_name: str, params: dict) -> dict:
        """Preview what a tool would do without executing it."""
        level = self.classify_action_level(tool_name)
        enforcement = self.policy.enforce(tool_name)
        return {
            "tool": tool_name,
            "params": params,
            "level": level,
            "would_execute": enforcement["allowed"],
            "requires_approval": enforcement["requires_approval"],
            "reason": enforcement["reason"],
        }
