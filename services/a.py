    def record_metric(self, name: str, value: float, description: str = ""):
        """
        Registra uma métrica customizada (counter).
        """
        counter = self.meter.create_counter(name, description=description)
        counter.add(value)

    def log_info(self, message: str):
        self.logger.info(message)

    def log_error(self, message: str):
        self.logger.error(message)
        # opcional: também mandar pro Teams
        self.send_teams_message(f"❗[{self.service_name}] {message}", level="error")

    # =========================
    # Webhook (Teams / LogicApp)
    # =========================
    def _post_to_webhook(self, payload: dict, max_retries: int = 3, backoff_s: float = 0.8):
        """
        Envia um payload para o webhook com tentativas e backoff exponencial simples.
        """
        if not self.webhook_url:
            return False, "WEBHOOK_URL não configurada"

        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    self.webhook_url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=self.webhook_timeout_s,
                )
                if 200 <= resp.status_code < 300:
                    return True, None
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                last_err = str(e)
            # backoff antes da próxima tentativa
            if attempt < max_retries:
                time.sleep(backoff_s * (2 ** (attempt - 1)))
        return False, last_err

    def send_teams_message(self, text: str, level: str = "info", extra: Optional[dict] = None):
        """
        Envia uma mensagem simples para o Teams. Nível pode ser: info|warning|error.
        """
        if not self.webhook_url:
            return False, "WEBHOOK_URL não configurada"

        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❗"}.get(level, "ℹ️")
        now = datetime.utcnow().isoformat() + "Z"

        base = {
            "text": f"{emoji} **{self.service_name}** @ {now}\n\n{self._safe_text(text)}",
        }

        if extra:
            pretty = json.dumps(extra, ensure_ascii=False, indent=2)
            base["text"] += f"\n\n```\n{pretty}\n```"

        ok, err = self._post_to_webhook(base)
        if not ok:
            self.logger.error(f"Falha ao enviar webhook: {err}")
        return ok, err

    def send_exception_to_teams(self, err: Exception, context_msg: str = ""):
        """
        Captura stacktrace + trace_id/span_id e envia pro Teams.
        """
        current_span = trace.get_current_span()
        ctx = current_span.get_span_context() if current_span else None
        trace_id = f"{ctx.trace_id:032x}" if ctx and ctx.trace_id else "na"
        span_id = f"{ctx.span_id:016x}" if ctx and ctx.span_id else "na"

        payload_extra = {
            "service": self.service_name,
            "host": socket.gethostname(),
            "trace_id": trace_id,
            "span_id": span_id,
            "error_type": type(err).__name__,
            "error_message": str(err),
            "stacktrace": traceback.format_exc(),
            "context": context_msg,
        }
        return self.send_teams_message(
            "Exceção capturada e correlacionada ao trace atual.",
            level="error",
            extra=payload_extra,
        )

    def _send_startup_test_message(self):
        """
        Envia uma mensagem de teste de ERRO no startup para validar o canal.
        """
        test_err = RuntimeError("Teste de erro de inicialização (OpenTelemetry + Teams)")
        self.send_exception_to_teams(
            test_err,
            context_msg="Mensagem de teste automática ao iniciar o serviço. Pode ser ignorada.",
        )

    @staticmethod
    def _safe_text(text: str) -> str:
        # Evita mensagens gigantes ou com caracteres estranhos (ajuste conforme necessidade)
        text = text or ""
        return text.strip()[:5000]  # limite simples
