# ------------------------------------------------------------------
# VPC: 2 AZs, 2 subnets públicas (jobs ECS, NAT) e 2 privadas
# (Lambda, RDS, EFS, ElastiCache).
# ------------------------------------------------------------------
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name}-vpc" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name}-igw" }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${local.name}-public-${count.index}", Tier = "public" }
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 10 + count.index)
  availability_zone = local.azs[count.index]

  tags = { Name = "${local.name}-private-${count.index}", Tier = "private" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${local.name}-rt-public" }
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name}-rt-private" }
}

resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# S3 por endpoint de gateway: grátis e tira o tráfego de imagens do NAT.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id, aws_route_table.private.id]

  tags = { Name = "${local.name}-vpce-s3" }
}

# ------------------------------------------------------------------
# NAT: fck-nat (instância t4g.nano) | NAT Gateway | nenhum
# ------------------------------------------------------------------
data "aws_ami" "fck_nat" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  most_recent = true
  owners      = ["568608671756"] # fck-nat (https://fck-nat.dev)

  filter {
    name   = "name"
    values = ["fck-nat-al2023-*-arm64-*"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

resource "aws_security_group" "nat" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  name        = "${local.name}-nat"
  description = "fck-nat: aceita tudo da VPC, sai para a internet"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${local.name}-nat" }
}

resource "aws_vpc_security_group_ingress_rule" "nat_from_vpc" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  security_group_id = aws_security_group.nat[0].id
  cidr_ipv4         = var.vpc_cidr
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "nat_all" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  security_group_id = aws_security_group.nat[0].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_instance" "fck_nat" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  ami                         = data.aws_ami.fck_nat[0].id
  instance_type               = var.fck_nat_instance_type
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.nat[0].id]
  source_dest_check           = false
  associate_public_ip_address = true

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required"
  }

  tags = { Name = "${local.name}-fck-nat" }

  lifecycle {
    ignore_changes = [ami]
  }
}

resource "aws_eip" "fck_nat" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  domain = "vpc"
  tags   = { Name = "${local.name}-fck-nat" }
}

resource "aws_eip_association" "fck_nat" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  instance_id   = aws_instance.fck_nat[0].id
  allocation_id = aws_eip.fck_nat[0].id
}

resource "aws_route" "private_fck_nat" {
  count = var.nat_mode == "fck-nat" ? 1 : 0

  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = aws_instance.fck_nat[0].primary_network_interface_id
}

resource "aws_eip" "nat_gw" {
  count = var.nat_mode == "gateway" ? 1 : 0

  domain = "vpc"
  tags   = { Name = "${local.name}-natgw" }
}

resource "aws_nat_gateway" "this" {
  count = var.nat_mode == "gateway" ? 1 : 0

  allocation_id = aws_eip.nat_gw[0].id
  subnet_id     = aws_subnet.public[0].id

  tags       = { Name = "${local.name}-natgw" }
  depends_on = [aws_internet_gateway.this]
}

resource "aws_route" "private_nat_gw" {
  count = var.nat_mode == "gateway" ? 1 : 0

  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[0].id
}

# ------------------------------------------------------------------
# Security groups
# ------------------------------------------------------------------
resource "aws_security_group" "lambda" {
  name        = "${local.name}-lambda"
  description = "Lambda do site (so egress)"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${local.name}-lambda" }
}

resource "aws_vpc_security_group_egress_rule" "lambda_all" {
  security_group_id = aws_security_group.lambda.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "jobs" {
  name        = "${local.name}-jobs"
  description = "Tasks ECS dos jobs (so egress)"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${local.name}-jobs" }
}

resource "aws_vpc_security_group_egress_rule" "jobs_all" {
  security_group_id = aws_security_group.jobs.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL: 5432 a partir do Lambda e dos jobs"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${local.name}-rds" }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_lambda" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.lambda.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_jobs" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.jobs.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_security_group" "efs" {
  name        = "${local.name}-efs"
  description = "EFS: NFS 2049 a partir do Lambda e dos jobs"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${local.name}-efs" }
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_lambda" {
  security_group_id            = aws_security_group.efs.id
  referenced_security_group_id = aws_security_group.lambda.id
  from_port                    = 2049
  to_port                      = 2049
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_jobs" {
  security_group_id            = aws_security_group.efs.id
  referenced_security_group_id = aws_security_group.jobs.id
  from_port                    = 2049
  to_port                      = 2049
  ip_protocol                  = "tcp"
}

resource "aws_security_group" "redis" {
  count = var.redis_mode == "serverless" ? 1 : 0

  name        = "${local.name}-redis"
  description = "ElastiCache: 6379 a partir do Lambda e dos jobs"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${local.name}-redis" }
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_lambda" {
  count = var.redis_mode == "serverless" ? 1 : 0

  security_group_id            = aws_security_group.redis[0].id
  referenced_security_group_id = aws_security_group.lambda.id
  from_port                    = 6379
  to_port                      = 6380
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_jobs" {
  count = var.redis_mode == "serverless" ? 1 : 0

  security_group_id            = aws_security_group.redis[0].id
  referenced_security_group_id = aws_security_group.jobs.id
  from_port                    = 6379
  to_port                      = 6380
  ip_protocol                  = "tcp"
}
