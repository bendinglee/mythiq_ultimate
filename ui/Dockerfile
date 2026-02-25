FROM node:20-alpine
RUN apk add --no-cache curl

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm","run","dev","--","-H","0.0.0.0","-p","3000"]
