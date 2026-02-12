#!/bin/bash
# =======================
# 🌐 Guia Rápido - Alternativas Gratuitas ao Ngrok
# =======================

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════════╗
║                   🌐 ALTERNATIVAS GRATUITAS AO NGROK                        ║
║           Para expor seu serviço site com HTTPS (OAuth + Webhooks)          ║
╚══════════════════════════════════════════════════════════════════════════════╝


┌──────────────────────────────────────────────────────────────────────────────┐
│ 🏆 OPÇÃO 1: CLOUDFLARE TUNNEL (RECOMENDADO)                                 │
└──────────────────────────────────────────────────────────────────────────────┘

✅ Vantagens:
   • Completamente GRATUITO
   • Sem limites de tempo ou conexões
   • URL estável (não muda)
   • Perfeito para produção
   • HTTPS automático

📦 Setup (executar apenas uma vez):
   make setup-cloudflare

🚀 Usar:
   make serve-cloudflare

🛑 Parar:
   Ctrl+C ou make stop-cloudflare

📝 URL: https://[random].trycloudflare.com (gerada automaticamente)


┌──────────────────────────────────────────────────────────────────────────────┐
│ 🥈 OPÇÃO 2: LOCALTUNNEL (MAIS SIMPLES)                                      │
└──────────────────────────────────────────────────────────────────────────────┘

✅ Vantagens:
   • Setup super rápido
   • Subdomínio personalizado
   • HTTPS automático

⚠️  Limitação:
   • Pode pedir verificação no navegador na primeira vez (só clicar)

📦 Setup (executar apenas uma vez):
   make setup-localtunnel

🚀 Usar:
   make serve-localtunnel

🛑 Parar:
   Ctrl+C ou make stop-localtunnel

📝 URL: https://vm-site.loca.lt (sempre a mesma!)


┌──────────────────────────────────────────────────────────────────────────────┐
│ 🥉 OPÇÃO 3: SERVEO (MAIS RÁPIDO)                                            │
└──────────────────────────────────────────────────────────────────────────────┘

✅ Vantagens:
   • Não precisa instalar NADA (usa SSH nativo)
   • Funciona imediatamente
   • Subdomínio personalizado

⚠️  Limitação:
   • Pode cair se conexão SSH for perdida

📦 Setup:
   Nenhum! Já está pronto.

🚀 Usar:
   make serve-serveo

🛑 Parar:
   Ctrl+C ou make stop-serveo

📝 URL: https://vmsite.serveo.net (sempre a mesma!)


┌──────────────────────────────────────────────────────────────────────────────┐
│ 📋 COMO CONFIGURAR NO MERCADO LIVRE                                          │
└──────────────────────────────────────────────────────────────────────────────┘

1️⃣  Escolha uma das opções acima e inicie o túnel

2️⃣  Copie a URL HTTPS que aparecer (ex: https://abc123.trycloudflare.com)

3️⃣  Acesse o painel do Mercado Livre:
    https://developers.mercadolivre.com.br/devcenter

4️⃣  Na sua aplicação, adicione o Redirect URI:
    <URL_DO_TUNNEL>/auth/mercadolivre/callback
    
    Exemplos:
    https://abc123.trycloudflare.com/auth/mercadolivre/callback
    https://vm-site.loca.lt/auth/mercadolivre/callback
    https://vmsite.serveo.net/auth/mercadolivre/callback

5️⃣  Atualize o arquivo .env:
    ML_REDIRECT_URI=<URL_DO_TUNNEL>/auth/mercadolivre/callback

6️⃣  Teste o OAuth:
    make test-oauth


┌──────────────────────────────────────────────────────────────────────────────┐
│ 💡 RECOMENDAÇÃO                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Para desenvolvimento:
  👉 Serveo (mais rápido, não precisa instalar nada)

Para produção/testes longos:
  👉 Cloudflare Tunnel (mais estável, sem limites)


┌──────────────────────────────────────────────────────────────────────────────┐
│ ❓ COMPARAÇÃO                                                                │
└──────────────────────────────────────────────────────────────────────────────┘

                     Cloudflare  LocalTunnel  Serveo    Ngrok Free
────────────────────────────────────────────────────────────────────
Instalação           Média       Fácil        Nenhuma   Fácil
Cadastro             Sim         Não          Não       Sim
Limite de tempo      ❌ Não      ❌ Não       ❌ Não    ✅ Sim (2h)
URL fixa             ✅ Sim      ✅ Sim       ✅ Sim    ❌ Não
Estabilidade         ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐     ⭐⭐⭐      ⭐⭐⭐⭐⭐
Para produção        ✅ Sim      ⚠️  Talvez   ❌ Não    ❌ Não


┌──────────────────────────────────────────────────────────────────────────────┐
│ 🐛 TROUBLESHOOTING                                                           │
└──────────────────────────────────────────────────────────────────────────────┘

Problema: "Túnel não inicia"
Solução: Verifique se os containers estão rodando:
         docker ps

Problema: "URL não abre no navegador"
Solução: Verifique se o site está respondendo localmente:
         curl -k https://localhost:5000

Problema: "OAuth retorna erro 'redirect_uri mismatch'"
Solução: A URL no painel do ML deve ser EXATAMENTE igual à do .env
         (incluindo https://, sem espaços, com /auth/mercadolivre/callback)

Problema: "LocalTunnel pede verificação sempre"
Solução: Normal na primeira vez. Depois não pede mais.


EOF
