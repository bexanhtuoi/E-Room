# Build React bang node, serve bang nginx (static + proxy /api ve api).
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Clean any stale dev-server artifacts before production build
RUN rm -rf build
RUN npm run build


FROM nginx:1.27-alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
