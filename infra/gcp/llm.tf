# ------------------------------------------------------------------
# LLM gerenciado (Vertex AI / Gemini) no lugar de Ollama + hsmart + Qdrant.
# Vetores: `CREATE EXTENSION vector` no Cloud SQL (pgvector).
# ------------------------------------------------------------------
resource "google_project_iam_member" "runtime_vertex" {
  count = var.enable_llm ? 1 : 0

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"

  depends_on = [google_project_service.apis]
}
