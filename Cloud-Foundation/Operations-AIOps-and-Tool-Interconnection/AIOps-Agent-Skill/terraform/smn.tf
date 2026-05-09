resource "huaweicloud_smn_topic" "approval" {
  name         = "${var.prefix}-approval"
  display_name = "AIOps Agent Approval Notifications"

  tags = {
    "managed-by" = "aiops-agent"
    "purpose"    = "approval-notifications"
  }
}

resource "huaweicloud_smn_subscription" "email" {
  topic_urn = huaweicloud_smn_topic.approval.id
  protocol  = "email"
  endpoint  = var.approval_email
}
