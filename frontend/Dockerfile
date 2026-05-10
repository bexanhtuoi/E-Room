FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Clean any stale dev-server artifacts before production build
RUN rm -rf build
RUN npm run build
RUN npm install -g serve

EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000", "--no-clipboard"]
