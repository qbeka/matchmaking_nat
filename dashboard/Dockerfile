# syntax=docker/dockerfile:1

FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# This is just a build stage, the output will be mounted as a volume
FROM scratch
COPY --from=build /app/dist /app/dist 