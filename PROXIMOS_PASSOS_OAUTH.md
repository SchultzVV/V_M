# 🔐 Configuração OAuth Mercado Livre - Próximos Passos

## ✅ O que já foi feito

1. ✅ App criado no Mercado Livre Developers
2. ✅ URL cadastrada: `https://2af6e203b111.ngrok-free.app/`
3. ✅ Variáveis de ambiente configuradas
4. ✅ Container reiniciado com nova configuração

## 🎯 Próximos Passos

### 1. Testar Fluxo de Autenticação OAuth

Acesse no navegador:
```
https://2af6e203b111.ngrok-free.app/auth/mercadolivre/login
```

**O que deve acontecer:**
1. Você será redirecionado para página de autorização do Mercado Livre
2. Faça login com sua conta ML (se necessário)
3. Autorize o aplicativo
4. Será redirecionado de volta para `/auth/mercadolivre/callback`
5. O sistema salvará seus tokens automaticamente

### 2. Verificar Tokens Salvos

Após autorizar, verifique se os tokens foram salvos:
```bash
# Ver tokens no .env
cat .env | grep ML_ACCESS_TOKEN

# Ou verificar no banco de dados (se estiver salvando lá)
```

### 3. Testar Webhooks

#### a) Verificar se a rota de webhook existe
```bash
curl https://2af6e203b111.ngrok-free.app/webhooks/mercadolivre
```

#### b) Cadastrar webhook no Mercado Livre

Acesse o painel do seu app:
- https://developers.mercadolivre.com.br/devcenter

Configure o webhook:
- **URL de notificação:** `https://2af6e203b111.ngrok-free.app/webhooks/mercadolivre`
- **Tópicos:** `items`, `orders`, `questions`

### 4. Testar API do Mercado Livre

Após obter o access token, teste fazer chamadas:

```bash
# Buscar informações da sua conta
curl -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  https://api.mercadolibre.com/users/me

# Buscar seus produtos
curl -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  https://api.mercadolibre.com/users/YOUR_USER_ID/items/search
```

### 5. Atualizar Script de Preparação de Produtos

Agora que temos acesso à API, podemos melhorar o `auto_prepare_ml.py`:

```python
# Usar token OAuth para acessar API com mais permissões
headers = {
    'Authorization': f'Bearer {ML_ACCESS_TOKEN}'
}

# Acessar dados privados (seus próprios produtos)
response = requests.get(
    'https://api.mercadolibre.com/users/me/items/search',
    headers=headers
)
```

## 🔍 Troubleshooting

### Erro: "Invalid redirect_uri"
- Verifique se a URL cadastrada no painel ML está **exatamente igual** à do .env
- Deve incluir o protocolo (https://)
- Não pode ter barra no final

### Erro: "Invalid client_id or client_secret"
- Confirme os valores no painel do Mercado Livre
- ML_APP_ID deve ser o Application ID
- ML_CLIENT_SECRET deve ser o Secret Key

### Erro: "Connection refused" no webhook
- Verifique se o ngrok está rodando
- Confirme se a URL está correta
- Teste manualmente com curl

### URL do ngrok mudou
Se a URL do ngrok mudar (plano free), você precisa:
1. Atualizar `ML_REDIRECT_URI` no `.env`
2. Atualizar URL no painel do Mercado Livre
3. Reiniciar container: `make restart-site`
4. Fazer o fluxo OAuth novamente

## 📝 Checklist

- [ ] Acessar `https://2af6e203b111.ngrok-free.app/auth/mercadolivre/login`
- [ ] Autorizar o aplicativo no Mercado Livre
- [ ] Verificar se tokens foram salvos
- [ ] Cadastrar webhook no painel ML
- [ ] Testar recebimento de notificações
- [ ] Testar chamadas à API com token
- [ ] Atualizar `auto_prepare_ml.py` para usar API autenticada

## 🎉 Resultado Esperado

Após completar todos os passos, você terá:
- ✅ Autenticação OAuth funcionando
- ✅ Access token válido salvo
- ✅ Webhooks recebendo notificações
- ✅ Capacidade de acessar API com permissões completas
- ✅ Sistema totalmente integrado com Mercado Livre

## 🔗 Links Úteis

- [Painel do App](https://developers.mercadolivre.com.br/devcenter)
- [Documentação OAuth](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)
- [Documentação Webhooks](https://developers.mercadolivre.com.br/pt_br/produto-receba-notificacoes)
- [Seu site (ngrok)](https://2af6e203b111.ngrok-free.app)
