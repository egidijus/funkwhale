#!/bin/bash -eux

SWAGGER_VERSION="3.13.6"
TARGET_PATH=${TARGET_PATH-"swagger"}
rm -rf $TARGET_PATH /tmp/swagger-ui
git clone --branch="v$SWAGGER_VERSION" --depth=1 "https://github.com/swagger-api/swagger-ui.git" /tmp/swagger-ui
mv /tmp/swagger-ui/dist $TARGET_PATH
cp swagger.yml $TARGET_PATH
cp -r api $TARGET_PATH/api
sed -i "s,http://petstore.swagger.io/v2/swagger.json,swagger.yml,g" $TARGET_PATH/index.html
