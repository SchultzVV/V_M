# ------------------------------------------------------------------
# LLM gerenciado (Bedrock) no lugar de Ollama + hsmart + Qdrant.
# Só IAM: o código escolhe o provedor por LLM_PROVIDER=bedrock (Δ código).
# Vetores do price oracle → pgvector no RDS.
# ------------------------------------------------------------------
data "aws_iam_policy_document" "bedrock" {
  count = var.enable_llm ? 1 : 0

  statement {
    actions = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = concat(
      [for id in var.bedrock_model_ids : "arn:aws:bedrock:*::foundation-model/${id}"],
      ["arn:aws:bedrock:*:${local.account_id}:inference-profile/*"],
    )
  }
}

resource "aws_iam_policy" "bedrock" {
  count = var.enable_llm ? 1 : 0

  name   = "${local.name}-bedrock-invoke"
  policy = data.aws_iam_policy_document.bedrock[0].json
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  count = var.enable_llm ? 1 : 0

  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.bedrock[0].arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_bedrock" {
  count = var.enable_llm ? 1 : 0

  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.bedrock[0].arn
}
