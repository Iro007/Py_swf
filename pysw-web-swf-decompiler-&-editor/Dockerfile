# Multi-stage Dockerfile for PySW Web SWF Decompiler

# Builder: install deps and build assets
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --silent
COPY . .
RUN npm run build

# Runtime
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./package.json
RUN npm ci --production --silent
EXPOSE 3000
CMD ["node", "dist/server.cjs"]
