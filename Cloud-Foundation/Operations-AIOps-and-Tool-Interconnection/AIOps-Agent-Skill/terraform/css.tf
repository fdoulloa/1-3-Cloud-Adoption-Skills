resource "huaweicloud_css_cluster" "main" {
  name     = "${var.prefix}-css"
  version  = var.css_engine_version

  node_config {
    flavor   = var.css_flavor
    number   = var.css_node_count
    availability_zone = "${var.region}a"

    volume {
      size = var.css_volume_size
    }
  }

  vpc_id            = huaweicloud_vpc.main.id
  subnet_id         = huaweicloud_vpc_subnet.main.id
  security_group_id = huaweicloud_networking_secgroup.main.id

  tags = {
    "managed-by" = "aiops-agent"
    "purpose"    = "ops-log-analytics"
  }
}
