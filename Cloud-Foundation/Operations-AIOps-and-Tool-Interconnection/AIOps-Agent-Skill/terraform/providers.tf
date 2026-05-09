terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.60"
    }
  }

  required_version = ">= 1.5"
}

provider "huaweicloud" {
  region = var.region
}
