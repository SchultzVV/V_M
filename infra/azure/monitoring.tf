# ------------------------------------------------------------
# Orçamento mensal (alerta em 50/90/100 % do gasto real)
# ------------------------------------------------------------
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-${local.prefix}"
  resource_group_id = azurerm_resource_group.main.id
  amount            = var.budget_monthly_usd
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-'01T00:00:00Z'", plantimestamp())
  }

  dynamic "notification" {
    for_each = [50, 90, 100]
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThan"
      threshold_type = "Actual"
      contact_emails = var.alert_email != "" ? [var.alert_email] : []
      contact_roles  = ["Owner"]
    }
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}

# ------------------------------------------------------------
# Alertas de métrica (e-mail)
# ------------------------------------------------------------
resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = substr("def${var.environment}", 0, 12)
  tags                = local.tags

  dynamic "email_receiver" {
    for_each = var.alert_email != "" ? [var.alert_email] : []
    content {
      name                    = "operador"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }
}

# Site: > 20 respostas 5xx em 5 min
resource "azurerm_monitor_metric_alert" "web_5xx" {
  name                = "alert-${local.prefix}-web-5xx"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.web.id]
  description         = "Site DEF devolvendo 5xx"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT5M"
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "Requests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 20

    dimension {
      name     = "statusCodeCategory"
      operator = "Include"
      values   = ["5xx"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
}

# Jobs: qualquer execução com state=Failed na última hora
resource "azurerm_monitor_metric_alert" "job_failed" {
  for_each = var.enable_job_alerts ? merge(
    { for k, j in azurerm_container_app_job.jobs : k => j.id },
    { "api-update-ml" = azurerm_container_app_job.events.id }
  ) : {}

  name                = "alert-${local.prefix}-job-${each.key}-failed"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [each.value]
  description         = "Job ${each.key} falhou"
  severity            = 3
  frequency           = "PT15M"
  window_size         = "PT1H"
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.App/jobs"
    metric_name      = "Executions"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0

    dimension {
      name     = "state"
      operator = "Include"
      values   = ["Failed"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
}
