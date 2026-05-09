resource "huaweicloud_obs_bucket" "main" {
  bucket        = "${var.prefix}-artifacts"
  storage_class = "STANDARD"
  region        = var.region

  tags = {
    "managed-by" = "aiops-agent"
    "purpose"    = "runbooks-reports-state"
  }
}
