# ------------------------------------------------------------------
# RDS PostgreSQL 16, single-AZ, db.t4g.micro (free tier no 1º ano).
# pgvector está disponível: CREATE EXTENSION vector; (substitui o Qdrant).
# Alternativa: Aurora Serverless v2 com auto-pause (0 ACU) — compensa só
# quando o site fica horas sem tráfego; com o Lambda acordando o banco a
# cada visita, o t4g.micro fixo sai mais barato.
# ------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-db" }
}

resource "aws_db_instance" "this" {
  identifier = "${local.name}-pg"

  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage > 0 ? var.db_max_allocated_storage : null
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "produtos_db"
  username = "def_app"
  password = random_password.db.result
  port     = 5432

  multi_az               = false
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  backup_window           = "06:00-07:00"         # 03:00 BRT
  maintenance_window      = "sun:07:00-sun:08:00" # dom 04:00 BRT
  copy_tags_to_snapshot   = true

  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-pg-final"

  auto_minor_version_upgrade   = true
  performance_insights_enabled = false
  apply_immediately            = true

  tags = { Name = "${local.name}-pg" }
}

locals {
  database_url = "postgresql://${aws_db_instance.this.username}:${urlencode(random_password.db.result)}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${aws_db_instance.this.db_name}?sslmode=require"
}
