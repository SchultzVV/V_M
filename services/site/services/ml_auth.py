"""
OAuth do Mercado Livre - Autenticação e gerenciamento de tokens
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
from pathlib import Path


class MercadoLivreAuth:
    """Gerencia autenticação OAuth 2.0 do Mercado Livre"""
    
    def __init__(self):
        self.app_id = os.getenv("ML_APP_ID")
        self.client_secret = os.getenv("ML_CLIENT_SECRET")
        self.redirect_uri = os.getenv("ML_REDIRECT_URI", "http://localhost:5000/auth/mercadolivre/callback")
        
        # Arquivo para salvar tokens
        self.token_file = Path(__file__).parent.parent / "config" / "ml_tokens.json"
        self.token_file.parent.mkdir(exist_ok=True)
        
        # URLs da API
        self.auth_url = "https://auth.mercadolivre.com.br/authorization"
        self.token_url = "https://api.mercadolibre.com/oauth/token"
        
    def get_authorization_url(self) -> str:
        """
        Gera a URL para o usuário autorizar a aplicação
        
        Returns:
            URL de autorização do Mercado Livre
        """
        params = {
            "response_type": "code",
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"
    
    def exchange_code_for_token(self, code: str) -> Dict:
        """
        Troca o código de autorização por access_token e refresh_token
        
        Args:
            code: Código recebido do callback
            
        Returns:
            Dict com access_token, refresh_token, expires_in, etc.
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.app_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        # Debug: Log dos dados enviados
        print(f"🔍 DEBUG - Trocando código por token:", flush=True)
        print(f"   client_id: {self.app_id}", flush=True)
        print(f"   redirect_uri: {repr(self.redirect_uri)}", flush=True)
        print(f"   code: {code[:20]}...", flush=True)
        sys.stdout.flush()
        
        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Adiciona timestamp de expiração
            token_data["expires_at"] = (
                datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600))
            ).isoformat()
            
            # Salva tokens no arquivo
            self._save_tokens(token_data)
            
            print(f"✅ Token obtido com sucesso!", flush=True)
            sys.stdout.flush()
            return token_data
            
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = response.json()
            except:
                error_detail = response.text
            
            print(f"❌ Erro ao trocar código por token:", flush=True)
            print(f"   Status: {response.status_code}", flush=True)
            print(f"   Resposta: {error_detail}", flush=True)
            sys.stdout.flush()
            raise
    
    def refresh_access_token(self, refresh_token: Optional[str] = None) -> Dict:
        """
        Renova o access_token usando o refresh_token
        
        Args:
            refresh_token: Token de refresh (opcional, carrega do arquivo se não fornecido)
            
        Returns:
            Dict com novo access_token
        """
        if not refresh_token:
            tokens = self._load_tokens()
            refresh_token = tokens.get("refresh_token")
            
            if not refresh_token:
                raise ValueError("Nenhum refresh_token disponível. Faça login novamente.")
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }
        
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Adiciona timestamp de expiração
        token_data["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600))
        ).isoformat()
        
        # Mantém o refresh_token antigo se não vier um novo
        if "refresh_token" not in token_data:
            old_tokens = self._load_tokens()
            token_data["refresh_token"] = old_tokens.get("refresh_token")
        
        # Salva tokens atualizados
        self._save_tokens(token_data)
        
        return token_data
    
    def get_valid_access_token(self) -> Optional[str]:
        """
        Retorna um access_token válido, renovando se necessário
        
        Returns:
            Access token válido ou None se não houver tokens
        """
        tokens = self._load_tokens()
        
        if not tokens:
            return None
        
        # Verifica se o token ainda é válido
        expires_at = datetime.fromisoformat(tokens.get("expires_at", "2000-01-01"))
        
        # Se expira em menos de 5 minutos, renova
        if datetime.utcnow() >= expires_at - timedelta(minutes=5):
            print("🔄 Access token expirado, renovando...")
            try:
                tokens = self.refresh_access_token()
            except Exception as e:
                print(f"❌ Erro ao renovar token: {e}")
                return None
        
        return tokens.get("access_token")
    
    def _save_tokens(self, tokens: Dict):
        """Salva tokens no arquivo JSON"""
        try:
            with open(self.token_file, "w") as f:
                json.dump(tokens, f, indent=2)
            print(f"✅ Tokens salvos em: {self.token_file}")
        except Exception as e:
            print(f"⚠️ Erro ao salvar tokens: {e}")
    
    def _load_tokens(self) -> Dict:
        """Carrega tokens do arquivo JSON"""
        try:
            if self.token_file.exists():
                with open(self.token_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao carregar tokens: {e}")
        
        return {}
    
    def is_authenticated(self) -> bool:
        """Verifica se há tokens válidos"""
        return self.get_valid_access_token() is not None
    
    def logout(self):
        """Remove tokens salvos"""
        if self.token_file.exists():
            self.token_file.unlink()
            print("✅ Tokens removidos com sucesso")


# Instância global
ml_auth = MercadoLivreAuth()
