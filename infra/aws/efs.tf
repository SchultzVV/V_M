# ------------------------------------------------------------------
# EFS: substitui os bind mounts locais (staging/, uploads/, config/
# ml_tokens.json) para que web e jobs compartilhem o mesmo estado sem
# mudar o código. Um filesystem, três access points.
# ------------------------------------------------------------------
resource "aws_efs_file_system" "this" {
  creation_token   = "${local.name}-efs"
  encrypted        = true
  throughput_mode  = "bursting"
  performance_mode = "generalPurpose"

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle_policy {
    transition_to_primary_storage_class = "AFTER_1_ACCESS"
  }

  tags = { Name = "${local.name}-efs" }
}

resource "aws_efs_mount_target" "this" {
  count = 2

  file_system_id  = aws_efs_file_system.this.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "this" {
  for_each = toset(["staging", "uploads", "config"])

  file_system_id = aws_efs_file_system.this.id

  posix_user {
    uid = 1000
    gid = 1000
  }

  root_directory {
    path = "/${each.key}"

    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "0755"
    }
  }

  tags = { Name = "${local.name}-efs-${each.key}" }
}
