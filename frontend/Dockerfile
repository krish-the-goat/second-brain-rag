# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# We must pass the API URL at build time so the Vite app can talk to the backend.
# In a real setup, you might use relative paths if Nginx proxies /api to the backend.
# Here we'll configure Vite to hit /api, and Nginx will reverse proxy it to the backend container.
RUN echo "VITE_API_URL=/api" > .env.production
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy static assets from builder stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy our custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
