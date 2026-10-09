# ============================================================
# Container Apps Jobs: mesma imagem do Flask, comando por job.
# Trigger: cron (var.schedules, UTC) ou manual (az containerapp job start).
# Volumes: /app/staging, /app/uploads, /app/config (Azure Files).
# ============================================================
resource "azurerm_container_app_job" "jobs" {
  for_each = local.jobs

  name                         = local.job_names[each.key]
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  replica_timeout_in_seconds   = var.job_timeout_seconds
  replica_retry_limit          = var.job_retry_limit
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  dynamic "registry" {
    for_each = local.registries
    content {
      server               = registry.value.server
      username             = registry.value.username
      password_secret_name = registry.value.password_secret_name
      identity             = registry.value.identity
    }
  }

  dynamic "secret" {
    for_each = local.app_secret_names
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.app.id
      key_vault_secret_id = azurerm_key_vault_secret.s[secret.key].versionless_id
    }
  }

  dynamic "secret" {
    for_each = var.ghcr_pat != "" ? ["ghcr-pat"] : []
    content {
      name  = "ghcr-pat"
      value = var.ghcr_pat
    }
  }

  dynamic "schedule_trigger_config" {
    for_each = contains(keys(local.scheduled_jobs), each.key) ? [local.scheduled_jobs[each.key]] : []
    content {
      cron_expression          = schedule_trigger_config.value.cron_utc
      parallelism              = 1
      replica_completion_count = 1
    }
  }

  dynamic "manual_trigger_config" {
    for_each = contains(keys(local.scheduled_jobs), each.key) ? [] : [1]
    content {
      parallelism              = 1
      replica_completion_count = 1
    }
  }

  template {
    container {
      name    = "site"
      image   = local.image_site
      cpu     = var.job_cpu
      memory  = var.job_memory
      command = each.value.command
      args    = each.value.args

      dynamic "env" {
        for_each = each.value.ocr ? local.job_env_ocr : local.job_env_plain
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.site_env_secret
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      volume_mounts {
        name = "staging"
        path = "/app/staging"
      }
      volume_mounts {
        name = "uploads"
        path = "/app/uploads"
      }
      volume_mounts {
        name = "config"
        path = "/app/config"
      }
    }

    dynamic "volume" {
      for_each = ["staging", "uploads", "config"]
      content {
        name         = volume.value
        storage_name = azurerm_container_app_environment_storage.shares[volume.value].name
        storage_type = "AzureFile"
      }
    }
  }

  depends_on = [time_sleep.app_rbac]
}

# ------------------------------------------------------------
# Job por evento: fila `events` (KEDA azure-queue, auth por identidade).
# Mensagem: {"args":["scripts/api_update_ml.py","https://meli.la/xxx"]}
# O wrapper scripts/run_from_queue.py tira UMA mensagem e executa python3 <args>.
# ------------------------------------------------------------
resource "azurerm_container_app_job" "events" {
  name                         = "caj-${local.prefix}-api-update-ml"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  replica_timeout_in_seconds   = 1800
  replica_retry_limit          = 1
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  dynamic "registry" {
    for_each = local.registries
    content {
      server               = registry.value.server
      username             = registry.value.username
      password_secret_name = registry.value.password_secret_name
      identity             = registry.value.identity
    }
  }

  dynamic "secret" {
    for_each = local.app_secret_names
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.app.id
      key_vault_secret_id = azurerm_key_vault_secret.s[secret.key].versionless_id
    }
  }

  dynamic "secret" {
    for_each = var.ghcr_pat != "" ? ["ghcr-pat"] : []
    content {
      name  = "ghcr-pat"
      value = var.ghcr_pat
    }
  }

  event_trigger_config {
    parallelism              = 1
    replica_completion_count = 1

    scale {
      min_executions              = 0
      max_executions              = var.event_job_max_executions
      polling_interval_in_seconds = 30

      rules {
        name             = "events-queue"
        custom_rule_type = "azure-queue"
        identity_id      = azurerm_user_assigned_identity.app.id
        metadata = {
          accountName = azurerm_storage_account.main.name
          queueName   = azurerm_storage_queue.events.name
          queueLength = "1"
          cloud       = "AzurePublicCloud"
        }
      }
    }
  }

  template {
    container {
      name    = "site"
      image   = local.image_site
      cpu     = var.job_cpu
      memory  = var.job_memory
      command = ["python3"]
      args    = ["infra_scripts/run_from_queue.py"]

      dynamic "env" {
        for_each = local.job_env_ocr
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.site_env_secret
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      volume_mounts {
        name = "staging"
        path = "/app/staging"
      }
      volume_mounts {
        name = "uploads"
        path = "/app/uploads"
      }
      volume_mounts {
        name = "config"
        path = "/app/config"
      }
    }

    dynamic "volume" {
      for_each = ["staging", "uploads", "config"]
      content {
        name         = volume.value
        storage_name = azurerm_container_app_environment_storage.shares[volume.value].name
        storage_type = "AzureFile"
      }
    }
  }

  depends_on = [time_sleep.app_rbac]
}
