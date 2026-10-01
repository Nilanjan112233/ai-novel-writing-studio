FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm ci

ENV NEXT_TELEMETRY_DISABLED=1

COPY . .
RUN npm run build

CMD ["npm", "start"]
