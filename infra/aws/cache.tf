# ------------------------------------------------------------------
# ElastiCache Serverless (Valkey): só quando redis_mode = serverless.
# Mínimo cobrado ~100 MB (≈ US$ 6/mês). TLS obrigatório → rediss://.
# ------------------------------------------------------------------
resource "aws_elasticache_serverless_cache" "this" {
  count = var.redis_mode == "serverless" ? 1 : 0

  name                 = "${local.name}-cache"
  engine               = "valkey"
  major_engine_version = "8"
  description          = "Cache do DEF (price_validator, memoria dos agentes)"

  cache_usage_limits {
    data_storage {
      maximum = 1
      unit    = "GB"
    }
    ecpu_per_second {
      maximum = 1000
    }
  }

  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.redis[0].id]

  tags = { Name = "${local.name}-cache" }
}

locals {
  redis_url = var.redis_mode == "serverless" ? "rediss://${aws_elasticache_serverless_cache.this[0].endpoint[0].address}:${aws_elasticache_serverless_cache.this[0].endpoint[0].port}/0" : ""
}
