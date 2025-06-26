import os
import json
import logging
from typing import Optional
from datetime import datetime
from qdrant_client import QdrantClient
import joblib

logger = logging.getLogger(__name__)


class CollectionRouter:
    def __init__(self, client: QdrantClient, embedding_model, model_path="models/router_classifier.joblib", log_path="logs/reranker_log.jsonl"):
        self.client = client
        self.embedding_model = embedding_model
        self.model_path = model_path
        self.log_path = log_path
        self.model = self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            logger.info(f"📦 Modelo supervisionado carregado de: {self.model_path}")
            return joblib.load(self.model_path)
        logger.warning("⚠️ Nenhum modelo supervisionado encontrado.")
        return None

    def heuristic(self, question: str) -> Optional[str]:
        q = question.lower()
        if any(x in q for x in ["curso", "oferece", "matrícula", "nota de corte", "existe"]):
            return "ufsm_faqs"
        if any(x in q for x in ["ensino", "metodologia", "roteiro", "atividade", "didático", "projeto"]):
            return "ufsm_knowledge"
        return None

    def decide(self, question: str, max_results_per_collection: int = 3) -> Optional[str]:
        # 1. Heurística
        heuristica = self.heuristic(question)
        if heuristica:
            logger.info(f"🔀 Heurística aplicável → usando coleção `{heuristica}`")
            return heuristica

        # 2. Modelo supervisionado
        if self.model:
            try:
                predicted = self.model.predict([question])[0]
                logger.info(f"🧠 Modelo supervisionado escolheu: `{predicted}`")
                return predicted
            except Exception as e:
                logger.warning(f"⚠️ Falha ao usar o modelo supervisionado: {e}")

        # 3. Votação vetorial
        return self._rerank_by_vector_voting(question, max_results_per_collection)

    def _rerank_by_vector_voting(self, question: str, top_k: int) -> Optional[str]:
        question_embedding = self.embedding_model.embed_query(question)
        logger.info(f"🔎 Votação vetorial ativada para: {question}")

        try:
            collections = self.client.get_collections()
            available = [col.name for col in collections.collections]
            if not available:
                logger.warning("❌ Nenhuma coleção disponível.")
                return None

            scores = {}
            for col in available:
                try:
                    results = self.client.search(
                        collection_name=col,
                        query_vector=question_embedding,
                        limit=top_k
                    )
                    if results:
                        avg_score = sum(r.score for r in results if r.score) / len(results)
                        scores[col] = avg_score
                        logger.debug(f"📊 Score médio para `{col}`: {avg_score:.4f}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar na `{col}`: {e}")

            if not scores:
                logger.warning("⚠️ Nenhuma coleção retornou resultados.")
                return None

            best_col = max(scores, key=scores.get)
            logger.info(f"✅ Votação vetorial elegeu: `{best_col}`")
            self._log_decision(question, best_col, scores)
            return best_col

        except Exception as e:
            logger.error(f"❌ Erro no reranking vetorial: {e}")
            return None

    def _log_decision(self, question: str, selected_collection: str, scores: dict):
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "selected_collection": selected_collection,
                "scores": scores
            }
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.debug(f"📝 Log de decisão salvo: {selected_collection}")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao salvar log da decisão: {e}")

# import os
# import json
# import logging
# from typing import Optional
# from datetime import datetime
# from qdrant_client import QdrantClient

# logger = logging.getLogger(__name__)



# class CollectionRouter:
#     def __init__(self, client: QdrantClient, embedding_model, log_path="logs/reranker_log.jsonl"):
#         self.client = client
#         self.embedding_model = embedding_model
#         self.log_path = log_path

#     def heuristic(self, question: str) -> Optional[str]:
#         q = question.lower()
        
#         if any(x in q for x in ["curso", "oferece", "matrícula", "nota de corte", "existe"]):
#             return "ufsm_faqs"
#         if any(x in q for x in ["ensino", "metodologia", "roteiro", "atividade", "didático", "projeto"]):
#             return "ufsm_knowledge"
#         return None

#     def decide(self, question: str, max_results_per_collection: int = 3) -> Optional[str]:
#         # 1. Heurística
#         heuristica = self.heuristic(question)
#         if heuristica:
#             logger.info(f"🔀 Heurística aplicável → usando coleção `{heuristica}`")
#             return heuristica

#         # 2. Reranking vetorial entre coleções
#         return self._rerank_by_vector_voting(question, max_results_per_collection)

#     def _rerank_by_vector_voting(self, question: str, top_k: int) -> Optional[str]:
#         question_embedding = self.embedding_model.embed_query(question)
#         logger.info(f"🔎 Votação vetorial ativada para: {question}")

#         try:
#             collections = self.client.get_collections()
#             available = [col.name for col in collections.collections]
#             if not available:
#                 logger.warning("❌ Nenhuma coleção disponível.")
#                 return None

#             scores = {}
#             for col in available:
#                 try:
#                     results = self.client.search(
#                         collection_name=col,
#                         query_vector=question_embedding,
#                         limit=top_k
#                     )
#                     if results:
#                         avg_score = sum(r.score for r in results if r.score) / len(results)
#                         scores[col] = avg_score
#                         logger.debug(f"📊 Score médio para `{col}`: {avg_score:.4f}")
#                 except Exception as e:
#                     logger.warning(f"⚠️ Erro ao buscar na `{col}`: {e}")

#             if not scores:
#                 logger.warning("⚠️ Nenhuma coleção retornou resultados.")
#                 return None

#             best_col = max(scores, key=scores.get)
#             logger.info(f"✅ Votação vetorial elegeu: `{best_col}`")

#             self._log_decision(question, best_col, scores)
#             return best_col

#         except Exception as e:
#             logger.error(f"❌ Erro no reranking vetorial: {e}")
#             return None

#     def _log_decision(self, question: str, selected_collection: str, scores: dict):
#         try:
#             os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
#             log_entry = {
#                 "timestamp": datetime.now().isoformat(),
#                 "question": question,
#                 "selected_collection": selected_collection,
#                 "scores": scores
#             }
#             with open(self.log_path, "a", encoding="utf-8") as f:
#                 f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
#             logger.debug(f"📝 Decisão logada: {selected_collection}")
#         except Exception as e:
#             logger.warning(f"⚠️ Falha ao salvar log da decisão: {e}")
# ############################################################################################

# # import logging
# # from typing import Optional
# # from qdrant_client import QdrantClient

# # logger = logging.getLogger(__name__)


# # class CollectionRouter:
# #     def __init__(self, client: QdrantClient, embedding_model):
# #         self.client = client
# #         self.embedding_model = embedding_model

# #     def heuristic(self, question: str) -> Optional[str]:
# #         q = question.lower()
        
# #         # 🎯 Regras simples (expanda conforme necessário)
# #         if "curso" in q or "oferece" in q or "tem curso de" in q or "existe" in q:
# #             return "ufsm_faqs"
# #         else:
# #             return "ufsm_knowledge"
# #         return None

# #     def decide(self, question: str, max_results_per_collection: int = 3) -> Optional[str]:
# #         # 1. Heurística simples
# #         heuristica = self.heuristic(question)
# #         if heuristica:
# #             logger.info(f"🔀 Heurística aplicável → usando coleção `{heuristica}`")
# #             return heuristica

# #         # 2. Busca vetorial (fallback)
# #         # question_embedding = self.embedding_model.encode(question).tolist()
# #         question_embedding = self.embedding_model.embed_query(question)
# #         try:
# #             collections = self.client.get_collections()
# #             available = [col.name for col in collections.collections]
# #             if not available:
# #                 logger.warning("❌ Nenhuma coleção disponível.")
# #                 return None

# #             scores = {}
# #             for col in available:
# #                 try:
# #                     results = self.client.search(
# #                         collection_name=col,
# #                         query_vector=question_embedding,
# #                         limit=max_results_per_collection
# #                     )
# #                     if results:
# #                         avg_score = sum([r.score for r in results if r.score]) / len(results)
# #                         scores[col] = avg_score
# #                         logger.debug(f"📊 Média de score na `{col}`: {avg_score:.3f}")
# #                 except Exception as e:
# #                     logger.warning(f"Erro ao buscar na `{col}`: {e}")

# #             if scores:
# #                 best = max(scores, key=scores.get)
# #                 logger.info(f"✅ Vetorial escolheu coleção `{best}`")
# #                 return best

# #             logger.warning("⚠️ Nenhuma coleção retornou resultado relevante.")
# #             return None

# #         except Exception as e:
# #             logger.error(f"❌ Erro ao decidir coleção: {e}")
# #             return None
