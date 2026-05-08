#!/usr/bin/env python3
"""
Huawei Cloud CSS API - Interface for data node scaling operations.
Uses the official Huawei Cloud SDK for authentication and API calls.

Based on: https://support.huaweicloud.com/api-css/css_02_0001.html
"""
import warnings
warnings.filterwarnings("ignore")

import time
import logging
from datetime import datetime
from typing import Optional, Any

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkcss.v1 import (
    CssClient,
    RoleExtendGrowReq,
    RoleExtendReq,
    ShrinkClusterReq,
    ShrinkNodeReq,
    ShowClusterDetailRequest,
    UpdateExtendInstanceStorageRequest,
    UpdateShrinkClusterRequest,
)
from huaweicloudsdkcss.v1.region.css_region import CssRegion

from config import config

# Setup logging
logging.basicConfig(level=logging.WARNING)


class HuaweiCSSDataNodeAPI:
    """
    API client for Huawei Cloud CSS data node scaling operations.
    Uses official Huawei Cloud SDK for authentication.
    """

    def __init__(self):
        self.ak = config.hw_access_key
        self.sk = config.hw_secret_key
        self.project_id = config.hw_project_id
        self.region = config.hw_region
        self.cluster_id = config.css_cluster_id

        # Build CSS client using official SDK
        self.client = self._build_client()

        # Track scaling operations
        self.last_operation_id: Optional[str] = None

    def _build_client(self) -> CssClient:
        """Build the Huawei Cloud CSS client with AK/SK authentication."""
        credentials = BasicCredentials(
            ak=self.ak,
            sk=self.sk,
            project_id=self.project_id,
        )

        http_config = HttpConfig.get_default_config()
        http_config.timeout = (30, 60)

        builder = CssClient.new_builder() \
            .with_http_config(http_config) \
            .with_credentials(credentials) \
            .with_region(CssRegion.value_of(self.region))

        return builder.build()

    def _get_cluster_state(self) -> dict[str, Any]:
        """Get cluster runtime state."""
        request = ShowClusterDetailRequest(cluster_id=self.cluster_id)
        response = self.client.show_cluster_detail(request)

        if not response or not getattr(response, "id", None):
            raise RuntimeError(f"CSS cluster is not accessible: {self.cluster_id}")

        instances = []
        for instance in getattr(response, "instances", []) or []:
            instances.append({
                "id": getattr(instance, "id", ""),
                "name": getattr(instance, "name", ""),
                "type": getattr(instance, "type", ""),
                "status": getattr(instance, "status", ""),
                "ip": getattr(instance, "ip", ""),
                "spec_code": getattr(instance, "spec_code", ""),
                "az_code": getattr(instance, "az_code", ""),
            })

        return {
            "cluster_id": getattr(response, "id", self.cluster_id),
            "name": getattr(response, "name", ""),
            "status": getattr(response, "status", ""),
            "instances": instances,
        }

    def get_cluster_info(self) -> dict:
        """Get cluster information including current node count."""
        try:
            state = self._get_cluster_state()
            return {
                "cluster_id": state["cluster_id"],
                "name": state["name"],
                "status": state["status"],
                "instances": state["instances"],
            }
        except Exception as e:
            print(f"❌ Error getting cluster info: {e}", flush=True)
            return {}

    def get_cluster_status(self) -> str:
        """Get current cluster status."""
        try:
            state = self._get_cluster_state()
            return state.get("status", "unknown")
        except Exception as e:
            print(f"❌ Error getting cluster status: {e}", flush=True)
            return "unknown"

    def get_data_node_count(self) -> int:
        """Get current number of data nodes."""
        try:
            state = self._get_cluster_state()
            data_nodes = [
                inst for inst in state.get("instances", [])
                if inst.get("type") == "ess"
            ]
            return len(data_nodes)
        except Exception as e:
            print(f"❌ Error getting data node count: {e}", flush=True)
            return 3  # Default fallback

    def scale_out_data_nodes(self, nodes_to_add: int) -> bool:
        """
        Scale out (add) data nodes.

        Args:
            nodes_to_add: Number of data nodes to add

        Returns:
            True if operation initiated successfully
        """
        print(f"\n🚀 Initiating SCALE OUT: Adding {nodes_to_add} data node(s)...", flush=True)

        try:
            current_count = self.get_data_node_count()
            target_count = current_count + nodes_to_add

            # Build the scale-out request
            grow_req = RoleExtendGrowReq(
                type="ess",  # Data node type
                nodesize=nodes_to_add,
                disksize=0,
            )
            body = RoleExtendReq(
                grow=[grow_req],
                is_auto_pay=1,
            )
            request = UpdateExtendInstanceStorageRequest(
                cluster_id=self.cluster_id,
                body=body,
            )

            # Execute the request
            response = self.client.update_extend_instance_storage(request)

            self.last_operation_id = getattr(response, "order_id", "") or str(response)
            print(f"✅ Scale out operation initiated", flush=True)
            print(f"   Operation ID: {self.last_operation_id}", flush=True)
            print(f"   Target: {current_count} → {target_count} data nodes", flush=True)
            return True

        except exceptions.ClientRequestException as exc:
            print(f"❌ API error: {exc.status_code} - {exc.error_code} - {exc.error_msg}", flush=True)
            return False
        except Exception as e:
            print(f"❌ Error during scale out: {e}", flush=True)
            return False

    def scale_in_data_nodes(self, nodes_to_remove: int) -> bool:
        """
        Scale in (remove) data nodes.

        Args:
            nodes_to_remove: Number of data nodes to remove

        Returns:
            True if operation initiated successfully
        """
        print(f"\n🔻 Initiating SCALE IN: Removing {nodes_to_remove} data node(s)...", flush=True)

        try:
            current_count = self.get_data_node_count()
            target_count = max(current_count - nodes_to_remove, config.min_data_nodes)

            # Build the scale-in request
            shrink_node = ShrinkNodeReq(
                type="ess",
                reduced_node_num=nodes_to_remove,
            )
            body = ShrinkClusterReq(
                shrink=[shrink_node],
                agency_name="",
                operation_type="",
                cluster_load_check=True,
            )
            request = UpdateShrinkClusterRequest(
                cluster_id=self.cluster_id,
                body=body,
            )

            # Execute the request
            response = self.client.update_shrink_cluster(request)

            self.last_operation_id = getattr(response, "order_id", "") or str(response)
            print(f"✅ Scale in operation initiated", flush=True)
            print(f"   Operation ID: {self.last_operation_id}", flush=True)
            print(f"   Target: {current_count} → {target_count} data nodes", flush=True)
            return True

        except exceptions.ClientRequestException as exc:
            print(f"❌ API error: {exc.status_code} - {exc.error_code} - {exc.error_msg}", flush=True)
            return False
        except Exception as e:
            print(f"❌ Error during scale in: {e}", flush=True)
            return False

    def wait_for_scaling_completion(self, timeout_seconds: int = 600) -> bool:
        """
        Wait for scaling operation to complete.

        Args:
            timeout_seconds: Maximum time to wait

        Returns:
            True if scaling completed successfully
        """
        print(f"⏳ Waiting for scaling operation to complete (timeout: {timeout_seconds}s)...", flush=True)

        start_time = time.time()
        check_interval = 30

        while time.time() - start_time < timeout_seconds:
            try:
                state = self._get_cluster_state()
                status = state.get("status", "unknown")
                instances = state.get("instances", [])
                data_nodes = [i for i in instances if i.get("type") == "ess"]

                # Check if all data nodes are stable (status 200)
                all_stable = all(i.get("status") == "200" for i in data_nodes)

                if status == "200" and all_stable:
                    print(f"✅ Cluster is now available with {len(data_nodes)} data nodes", flush=True)
                    return True

                if status in ["303", "400", "500"]:
                    print(f"❌ Cluster in error state: {status}", flush=True)
                    return False

                elapsed = int(time.time() - start_time)
                print(f"   Status: {status} | Data nodes: {len(data_nodes)} | Elapsed: {elapsed}s", flush=True)
                time.sleep(check_interval)

            except Exception as e:
                print(f"⚠️  Error checking status: {e}", flush=True)
                time.sleep(check_interval)

        print(f"⚠️  Timeout waiting for scaling completion", flush=True)
        return False

    def get_scaling_history(self) -> list:
        """Get history of scaling operations."""
        # Not implemented in this version
        return []


if __name__ == "__main__":
    print("🚀 Testing Huawei Cloud CSS API with official SDK...", flush=True)

    api = HuaweiCSSDataNodeAPI()

    print(f"\nCluster ID: {api.cluster_id}", flush=True)
    print(f"Region: {api.region}", flush=True)
    print(f"AK: {api.ak[:8]}...", flush=True)

    print("\n📊 Getting cluster info...", flush=True)
    info = api.get_cluster_info()
    print(f"Cluster info: {info}", flush=True)

    count = api.get_data_node_count()
    print(f"Current data nodes: {count}", flush=True)
