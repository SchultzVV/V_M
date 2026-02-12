#!/usr/bin/env python3
"""
Proxy HTTP simples para redirecionar para HTTPS local
Necessário para LocalTunnel que só aceita HTTP
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import ssl

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.proxy_request()
    
    def do_HEAD(self):
        self.proxy_request()
    
    def do_POST(self):
        self.proxy_request()
    
    def do_PUT(self):
        self.proxy_request()
    
    def do_DELETE(self):
        self.proxy_request()
    
    def proxy_request(self):
        try:
            # URL do serviço local HTTPS
            target_url = f"https://localhost:5000{self.path}"
            
            # Criar contexto SSL que ignora verificação de certificado
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # Copiar headers
            headers = {}
            for key, value in self.headers.items():
                if key.lower() not in ['host', 'connection']:
                    headers[key] = value
            
            # Ler corpo da requisição se houver
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Fazer requisição para o serviço HTTPS
            req = urllib.request.Request(target_url, data=body, headers=headers, method=self.command)
            
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                # Enviar resposta
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in ['connection', 'transfer-encoding']:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
        
        except Exception as e:
            print(f"Erro ao fazer proxy: {e}")
            self.send_error(502, f"Bad Gateway: {str(e)}")
    
    def log_message(self, format, *args):
        # Suprimir logs padrão (muito verboso)
        pass

if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f"🔄 Proxy HTTP rodando na porta {port}")
    print(f"   HTTP :8000 → HTTPS :5000")
    print(f"   Pressione Ctrl+C para parar")
    server.serve_forever()
