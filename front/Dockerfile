FROM node:12-buster

# needed to compile translations
RUN curl -L -o /usr/local/bin/jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64 && chmod +x /usr/local/bin/jq

EXPOSE 8080
WORKDIR /app/
COPY scripts/ ./scripts/
ADD package.json yarn.lock  ./
RUN yarn install

COPY . .

CMD ["yarn", "serve"]
