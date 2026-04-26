# Asset Pulse — frontend image
# Stage 1: build the Vite/React bundle
FROM node:20-alpine AS build

WORKDIR /app

# Install deps using the lockfile for reproducible builds.
COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY vite.config.ts eslint.config.js index.html ./
COPY public ./public
COPY src ./src

# Same-origin API base — Nginx proxies /api to the backend service in compose.
ENV VITE_API_BASE_URL=""
RUN npm run build

# Stage 2: serve static files with nginx and reverse-proxy /api
FROM nginx:1.27-alpine

# Replace default nginx config with our SPA + /api reverse-proxy config.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
