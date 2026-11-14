FROM node:22-alpine
WORKDIR /app
COPY package.json ./
COPY package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install --no-audit --no-fund; fi
COPY . .
# next.config.mjs reads BACKEND_URL at build time to create the /api/v1 rewrite (same-origin cookies, no CORS).
ARG BACKEND_URL=http://api:8000
ENV BACKEND_URL=$BACKEND_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build
USER node
EXPOSE 3000
CMD ["npm", "start"]
