FROM node:22-alpine

WORKDIR /app
COPY package.json ./
COPY agent ./agent
COPY web ./web

ENV NODE_ENV=production
ENV PORT=3000
ENV HOST=0.0.0.0
EXPOSE 3000

CMD ["node", "web/server.mjs"]
