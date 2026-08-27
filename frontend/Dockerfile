# Stage 1: build the static bundle. Node and the whole npm toolchain are
# only needed to produce that bundle — none of it belongs in the image that
# actually serves the site.
FROM node:24-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: serve the built static files with nginx — a tiny, purpose-built
# static file server, instead of shipping Node (or Vite's dev server, which
# isn't meant for anything but local development) in the final image.
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
