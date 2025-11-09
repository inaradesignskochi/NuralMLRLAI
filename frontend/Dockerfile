FROM nginx:alpine

LABEL maintainer="smc-bot@trading.com"
LABEL description="SMC Trading Bot Frontend"

# Copy frontend files
COPY index.html /usr/share/nginx/html/
COPY static /usr/share/nginx/html/static

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]