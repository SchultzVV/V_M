# DEF Frontend

Frontend moderno em React + TypeScript para o catálogo DEF — equipamento para ambientes hostis.

## Stack Tecnológico

- **React 18** — UI framework
- **TypeScript** — Type safety
- **Vite** — Build tool (fast!)
- **Tailwind CSS** — Styling (com cores neon DEF)
- **React Router** — Routing
- **Zustand** — State management (auth)
- **Axios** — HTTP client

## Estrutura de Pastas

```
src/
├── components/        # Componentes reutilizáveis
│   ├── ProductCard.tsx
│   ├── ProductGrid.tsx
│   ├── Layout.tsx
│   ├── AdminLayout.tsx
│   └── ProtectedRoute.tsx
├── pages/            # Páginas
│   ├── Home.tsx
│   ├── ProductDetail.tsx
│   └── admin/
│       ├── Login.tsx
│       └── Dashboard.tsx
├── services/         # API clients + utilities
│   ├── api.ts
│   ├── productService.ts
│   ├── authService.ts
│   └── imageUtils.ts
├── stores/          # Zustand stores
│   └── authStore.ts
├── styles/
│   └── index.css    # Tailwind + custom CSS
├── App.tsx          # Root component
└── main.tsx         # Entry point
```

## Development

### Setup

```bash
# Install dependencies
npm install

# Create .env.local (copy from .env.example)
cp .env.example .env.local
```

### Dev Server

```bash
# Start Vite dev server (http://localhost:5173)
npm run dev

# The server proxies API calls to http://localhost:5000 (Flask backend)
```

### Build for Production

```bash
npm run build

# Output goes to ./dist/
```

### Preview Production Build

```bash
npm run preview
```

## API Integration

O frontend faz proxy de requisições para o backend Flask:
- `/api/*` → `http://localhost:5000/api/*`
- `/auth/*` → `http://localhost:5000/auth/*`
- `/webhook/*` → `http://localhost:5000/webhook/*`

Veja `vite.config.ts` para configuração.

## Design System

**Cores** (Tailwind custom):
- `text-neon-green` — #00ff41 (preço em oferta, destaque)
- `text-neon-red` — #ff004d (preço original, urgência)
- `bg-dark-gray` — #1a1a1a (card background)
- `bg-black-deep` — #0a0a0a (page background)

**Componentes reutilizáveis**:
- `.btn-primary` — CTA verde neon
- `.btn-secondary` — CTA cinza
- `.card-def` — Card padrão DEF
- `.price-display` — Price typography (3rem, mono)
- `.grid-def` — Grid 4/2/1 responsivo

## Testing

```bash
# Run tests
npm run test

# Watch mode
npm run test

# UI
npm run test:ui
```

## Build for Docker

The Dockerfile in the root project includes a multi-stage build:
1. `npm install && npm run build` → gera `/dist/`
2. Copia `/dist/` para `/app/static/frontend/` no container Python

Flask então serve `index.html` como SPA root.

## Authentication

- Login: `POST /auth/admin/login` (username + password)
- Valida token: `Authorization: Bearer {token}`
- Store: Zustand (`useAuthStore`)
- Logout: Limpa localStorage + redirect

## Next Steps

- [ ] Adicionar lazy loading de imagens
- [ ] Code splitting por rota
- [ ] PWA (service worker, manifest)
- [ ] Analytics/tracking
- [ ] Error boundary
- [ ] 404 page

## License

© 2026 DEF. Equipamento de sobrevivência pós-sistema.
