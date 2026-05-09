resource "huaweicloud_fgs_function" "css_scale_out" {
  name        = "${var.prefix}-css-scale-out"
  app         = "default"
  description = "AIOps remediation: scale out CSS data nodes"
  handler     = "index.handler"
  memory_size = 256
  timeout     = 300
  runtime     = "Python3.9"

  functiongraph_code {
    zip_file = filebase64("${path.module}/functions/css_scale_out.zip")
  }
}

resource "huaweicloud_fgs_function" "ecs_reboot" {
  name        = "${var.prefix}-ecs-reboot"
  app         = "default"
  description = "AIOps remediation: reboot ECS instance"
  handler     = "index.handler"
  memory_size = 256
  timeout     = 120
  runtime     = "Python3.9"

  functiongraph_code {
    zip_file = filebase64("${path.module}/functions/ecs_reboot.zip")
  }
}

resource "huaweicloud_fgs_function" "cce_restart_pod" {
  name        = "${var.prefix}-cce-restart-pod"
  app         = "default"
  description = "AIOps remediation: restart CCE pod/deployment"
  handler     = "index.handler"
  memory_size = 256
  timeout     = 120
  runtime     = "Python3.9"

  functiongraph_code {
    zip_file = filebase64("${path.module}/functions/cce_restart_pod.zip")
  }
}

resource "huaweicloud_fgs_function" "vpn_reconnect" {
  name        = "${var.prefix}-vpn-reconnect"
  app         = "default"
  description = "AIOps remediation: recreate VPN connection"
  handler     = "index.handler"
  memory_size = 256
  timeout     = 120
  runtime     = "Python3.9"

  functiongraph_code {
    zip_file = filebase64("${path.module}/functions/vpn_reconnect.zip")
  }
}
