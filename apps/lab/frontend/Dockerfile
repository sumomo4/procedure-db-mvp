FROM node:22.23.4-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS build

WORKDIR /app

COPY package*.json ./
RUN node -e "const { rootCertificates } = require('node:tls'); const { X509Certificate } = require('node:crypto'); if (rootCertificates.some(pem => new X509Certificate(pem).subject.includes('CN=emSign ECC Root CA - G3'))) throw new Error('Outdated Node.js CA bundle');" \
    && npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

RUN apk add --no-cache --upgrade ca-certificates

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
