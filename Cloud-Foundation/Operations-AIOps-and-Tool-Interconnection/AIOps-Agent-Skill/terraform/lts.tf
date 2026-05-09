resource "huaweicloud_lts_group" "ops" {
  group_name  = "${var.prefix}-ops-logs"
  ttl_in_days = 30

  tags = {
    "managed-by" = "aiops-agent"
    "purpose"    = "ops-log-aggregation"
  }
}

resource "huaweicloud_lts_topic" "css_logs" {
  group_id    = huaweicloud_lts_group.ops.id
  topic_name  = "css-logs"
  ttl_in_days = 30
}

resource "huaweicloud_lts_topic" "ecs_logs" {
  group_id    = huaweicloud_lts_group.ops.id
  topic_name  = "ecs-logs"
  ttl_in_days = 30
}

resource "huaweicloud_lts_topic" "cce_logs" {
  group_id    = huaweicloud_lts_group.ops.id
  topic_name  = "cce-logs"
  ttl_in_days = 30
}

resource "huaweicloud_lts_topic" "audit_logs" {
  group_id    = huaweicloud_lts_group.ops.id
  topic_name  = "audit-logs"
  ttl_in_days = 365

  tags = {
    "compliance" = "pci-dss-10.3"
  }
}
