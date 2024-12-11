# Build Stage
# FROM node:16 AS builder
# WORKDIR /app
# COPY package*.json ./
# RUN npm install
# COPY . .
# RUN npm run build && npm run export

# # NGINX Stage
# FROM nginx:alpine
# COPY nginx.conf /etc/nginx/conf.d/default.conf
# COPY --from=builder /app/out /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]

# Build Stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . . 
RUN npm run build

# Production Stage (Node.js Server)
FROM node:16 AS production
WORKDIR /app
COPY --from=builder /app ./
EXPOSE 3000

# Start the Next.js app on 0.0.0.0
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
