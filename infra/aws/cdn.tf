# ------------------------------------------------------------------
# CloudFront: uma distribuição, três origens.
#   /            → S3 frontend (React; rotas do SPA reescritas p/ index.html)
#   /media/*     → S3 media (prefixo /media removido; chave = <plataforma>/<arq>)
#   rotas Flask  → Lambda Function URL (OAC sigv4 ou header secreto)
# TLS pelo ACM (us-east-1), HSTS via response headers policy.
# ------------------------------------------------------------------
resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${local.name}-s3"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "lambda" {
  count = var.lambda_url_auth_type == "AWS_IAM" ? 1 : 0

  name                              = "${local.name}-lambda"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "${local.name}-spa-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rotas do React (/produto/123, /admin/...) → /index.html"
  publish = true
  code    = file("${path.module}/cloudfront/spa_rewrite.js")
}

resource "aws_cloudfront_function" "media_strip" {
  name    = "${local.name}-media-strip"
  runtime = "cloudfront-js-2.0"
  comment = "/media/<plataforma>/<arq> → /<plataforma>/<arq> no bucket"
  publish = true
  code    = file("${path.module}/cloudfront/media_strip.js")
}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_cache_policy" "api" {
  name        = "${local.name}-api-short-ttl"
  comment     = "/api/*: cache curto por query string"
  min_ttl     = 0
  default_ttl = var.api_cache_ttl
  max_ttl     = max(var.api_cache_ttl * 5, 1)

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${local.name}-security-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "SAMEORIGIN"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }
}

# ------------------------------------------------------------------
# Certificado (us-east-1). Sem Route 53, crie os CNAMEs de validação no
# Cloudflare durante o apply (a validação espera até 75 min).
# ------------------------------------------------------------------
resource "aws_acm_certificate" "this" {
  provider = aws.us_east_1

  domain_name               = var.domain
  subject_alternative_names = var.create_www_alias ? ["www.${var.domain}"] : []
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "acm_validation" {
  for_each = var.manage_dns_route53 ? {
    for dvo in aws_acm_certificate.this.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id         = var.route53_zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 300
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "this" {
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.this.arn
  validation_record_fqdns = var.manage_dns_route53 ? [for r in aws_route53_record.acm_validation : r.fqdn] : null

  timeouts {
    create = "75m"
  }
}

# ------------------------------------------------------------------
# Distribuição
# ------------------------------------------------------------------
locals {
  lambda_paths_no_cache = [
    "/auth/*", "/webhook/*", "/ai/*", "/instagram/*", "/sync/*",
    "/validate-prices*", "/add_product", "/catalogo", "/secao*",
    "/sitemap.xml", "/robots.txt",
  ]
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  comment             = "${local.name}: React + Flask (Lambda) + imagens"
  aliases             = local.aliases
  price_class         = var.cloudfront_price_class
  http_version        = "http2and3"
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  origin {
    origin_id                = "frontend"
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  origin {
    origin_id                = "media"
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  origin {
    origin_id                = "lambda"
    domain_name              = local.lambda_origin_domain
    origin_access_control_id = var.lambda_url_auth_type == "AWS_IAM" ? aws_cloudfront_origin_access_control.lambda[0].id : null

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "https-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 5
    }

    dynamic "custom_header" {
      for_each = var.lambda_url_auth_type == "NONE" ? [1] : []

      content {
        name  = "x-origin-verify"
        value = random_password.origin_verify.result
      }
    }
  }

  # React (SPA)
  default_cache_behavior {
    target_origin_id           = "frontend"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
  }

  # Imagens
  ordered_cache_behavior {
    path_pattern               = "/media/*"
    target_origin_id           = "media"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.media_strip.arn
    }
  }

  # API com cache curto
  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "lambda"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = var.api_cache_ttl > 0 ? aws_cloudfront_cache_policy.api.id : data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  # Demais rotas Flask, sem cache
  dynamic "ordered_cache_behavior" {
    for_each = local.lambda_paths_no_cache

    content {
      path_pattern               = ordered_cache_behavior.value
      target_origin_id           = "lambda"
      viewer_protocol_policy     = "redirect-to-https"
      allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods             = ["GET", "HEAD"]
      compress                   = true
      cache_policy_id            = data.aws_cloudfront_cache_policy.caching_disabled.id
      origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
      response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.this.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = { Name = "${local.name}-cdn" }
}

# DNS no Route 53 (opcional). Sem isso: CNAME <domain> → <cloudfront_domain> no Cloudflare, "DNS only".
resource "aws_route53_record" "alias" {
  for_each = var.manage_dns_route53 ? toset(local.aliases) : toset([])

  zone_id = var.route53_zone_id
  name    = each.value
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_v6" {
  for_each = var.manage_dns_route53 ? toset(local.aliases) : toset([])

  zone_id = var.route53_zone_id
  name    = each.value
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}
