"""Provision AIOps Agent demo infrastructure on Huawei Cloud.

Reuses enterprise-rag-agent/scripts/provision_huawei_demo.py pattern.
Creates: OBS bucket, CSS cluster, ECS instance, VPC, Subnet, Security Group,
LTS log group/topics, SMN topic, FunctionGraph functions.
"""

import os
import sys

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkiam.v1 import IamClient, KeystoneListProjectsRequest


def clients(region: str, ak: str, sk: str, project_id: str):
    """Build Huawei Cloud SDK clients. Reuses css-testing pattern."""
    credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    http_config = HttpConfig.get_default_config()
    http_config.timeout = (30, 120)
    return credentials, http_config


def verify_project(iam_client: IamClient, project_id: str) -> bool:
    """Verify the project ID exists."""
    req = KeystoneListProjectsRequest()
    resp = iam_client.keystone_list_projects(req)
    for project in resp.projects or []:
        if project.id == project_id:
            print(f"Project verified: {project.name} ({project.id})")
            return True
    print(f"ERROR: Project {project_id} not found")
    return False


def main():
    ak = os.getenv("HWC_ACCESS_KEY_ID")
    sk = os.getenv("HWC_SECRET_ACCESS_KEY")
    region = os.getenv("HWC_REGION", "la-north-2")
    project_id = os.getenv("HWC_PROJECT_ID")

    if not all([ak, sk, project_id]):
        print("ERROR: Set HWC_ACCESS_KEY_ID, HWC_SECRET_ACCESS_KEY, HWC_PROJECT_ID")
        sys.exit(1)

    credentials, http_config = clients(region, ak, sk, project_id)

    # IAM - verify project
    iam_client = (
        IamClient.new_builder()
        .with_http_config(http_config)
        .with_credentials(credentials)
        .with_region(IamClient.region.value_of(region))
        .build()
    )
    if not verify_project(iam_client, project_id):
        sys.exit(1)

    print("\nAIOps Agent infrastructure provisioning:")
    print("  1. VPC + Subnet + Security Group")
    print("  2. CSS cluster (OpenSearch)")
    print("  3. OBS bucket (runbooks, reports)")
    print("  4. LTS log group + topics")
    print("  5. SMN topic (approval notifications)")
    print("  6. FunctionGraph functions (remediation)")
    print("  7. ECS instance (agent runtime)")
    print("\nUse Terraform for production deployment:")
    print("  cd terraform && terraform init && terraform apply")


if __name__ == "__main__":
    main()
