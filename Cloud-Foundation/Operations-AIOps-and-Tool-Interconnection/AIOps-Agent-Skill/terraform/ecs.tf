data "huaweicloud_images_image" "ubuntu" {
  name        = "Ubuntu 22.04"
  image_type  = "ECS"
  most_recent = true
}

resource "huaweicloud_compute_keypair" "agent" {
  name = "${var.prefix}-keypair"
}

resource "huaweicloud_compute_instance" "agent" {
  name               = "${var.prefix}-agent"
  image_id           = var.ecs_image_id != "" ? var.ecs_image_id : data.huaweicloud_images_image.ubuntu.id
  flavor_id          = var.ecs_flavor
  availability_zone  = "${var.region}a"
  key_pair           = huaweicloud_compute_keypair.agent.name
  security_group_ids = [huaweicloud_networking_secgroup.main.id]

  network {
    uuid = huaweicloud_vpc_subnet.main.id
  }

  system_disk_type = "SSD"
  system_disk_size = 50

  tags = {
    "managed-by" = "aiops-agent"
    "purpose"    = "agent-runtime"
  }
}

resource "huaweicloud_vpc_eip" "agent" {
  publicip {
    type = "5_bgp"
  }
  bandwidth {
    name        = "${var.prefix}-agent-eip"
    size        = 5
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

resource "huaweicloud_vpc_eip_associate" "agent" {
  public_ip = huaweicloud_vpc_eip.agent.address
  port_id   = huaweicloud_compute_instance.agent.network[0].port
}
