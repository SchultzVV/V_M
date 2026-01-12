# 🔧 Troubleshooting OAuth - Mercado Livre

## ❌ Erro: "não foi possível conectar o aplicativo à sua conta"

Este erro acontece quando há problemas na configuração do painel do Mercado Livre.

## ✅ Checklist de Configuração no Painel ML

Acesse: https://developers.mercadolivre.com.br/devcenter

### 1️⃣ **Redirect URI DEVE estar EXATAMENTE assim:**

```
https://2af6e203b111.ngrok-free.app/auth/mercadolivre/callback
```

**❗ IMPORTANTE:**
- ✅ COM https://
- ✅ SEM barra (/) no final
- ✅ SEM espaços
- ✅ Caminho completo: `/auth/mercadolivre/callback`

### 2️⃣ **Verificar Estado do Aplicativo**

No painel, verifique se:
- [ ] App está **ativo** (não suspenso)
- [ ] Modo: **Teste** ou **Produção**
- [ ] Redirect URI cadastrado corretamente

### 3️⃣ **Scopes/Permissões**

Verifique se o app tem permissões para:
- [ ] `read` - Leitura de dados
- [ ] `offline_access` - Acesso offline (refresh token)

### 4️⃣ **Configurações Adicionais**

Algumas contas podem precisar:
- [ ] Domínio verificado
- [ ] Aplicativo aprovado pelo ML (para produção)
- [ ] Certificado HTTPS válido (não self-signed em produção)

## 🧪 Teste Manual no Painel ML

1. No painel, vá em **"Testar autenticação"**
2. Cole a Redirect URI exatamente como está no .env
3. Clique em "Autorizar"
4. Deve funcionar no painel antes de testar via código

## 🔄 URL Corrigida para Teste

```
https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=3186869212482819&redirect_uri=https://2af6e203b111.ngrok-free.app/auth/mercadolivre/callback
```

## 🆘 Se ainda não funcionar

### Opção A: Usar localhost temporariamente

1. Pare o ngrok
2. Atualize .env:
   ```
   ML_REDIRECT_URI=http://localhost:5000/auth/mercadolivre/callback
   ```
3. Cadastre no painel ML: `http://localhost:5000/auth/mercadolivre/callback`
4. Teste localmente

### Opção B: Verificar logs

```bash
# Ver erros detalhados
docker-compose logs -f site | grep -i "error\|auth\|mercado"

# Ver requisições ao callback
docker-compose logs -f site | grep callback
```

### Opção C: Testar com curl

```bash
# Ver resposta do servidor
curl -v "https://2af6e203b111.ngrok-free.app/auth/mercadolivre/callback?code=TESTE"
```

## 📞 Suporte ML

Se nada funcionar, entre em contato:
- Fórum: https://developers.mercadolivre.com.br/support
- Email: developers@mercadolibre.com

## 🎯 Próximo Passo

Após corrigir no painel ML, teste novamente:
```bash
make test-oauth
```

Escolha o **Método 2 (URL Direta)** e autorize no navegador.
