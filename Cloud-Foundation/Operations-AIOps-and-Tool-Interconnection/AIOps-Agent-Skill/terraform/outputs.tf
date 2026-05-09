output "css_cluster_id" {
  description = "CSS cluster ID"
  value       = huaweicloud_css_cluster.main.id
}

output "css_endpoint" {
  description = "CSS cluster endpoint"
  value       = huaweicloud_css_cluster.main.nodes[0].ip
}

output "ecs_id" {
  description = "ECS instance ID for agent runtime"
  value       = huaweicloud_compute_instance.agent.id
}

output "ecs_eip" {
  description = "ECS elastic IP"
  value       = huaweicloud_vpc_eip.agent.address
}

output "obs_bucket" {
  description = "OBS bucket name"
  value       = huaweicloud_obs_bucket.main.bucket
}

output "smn_topic_urn" {
  description = "SMN topic URN for approval notifications"
  value       = huaweicloud_smn_topic.approval.id
}

output "lts_group_id" {
  description = "LTS log group ID"
  value       = huaweicloud_lts_group.ops.id
}

output "vpc_id" {
  description = "VPC ID"
  value       = huaweicloud_vpc.main.id
}
