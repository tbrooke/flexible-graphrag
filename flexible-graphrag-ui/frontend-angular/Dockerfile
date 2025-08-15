FROM node:24-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Replace proxy config with Docker-specific version
RUN mv proxy.docker.conf.json proxy.conf.json

# Build the application with Docker-specific configuration and base href for nginx routing  
RUN npm run build:docker -- --base-href=/ui/angular/

# Expose port
EXPOSE 4200

# Install serve to serve built files
RUN npm install -g serve

# Serve the built static files
CMD ["serve", "-s", "dist/cmis-graphrag-ui", "-l", "4200"]
