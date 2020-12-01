FROM tomcat:8.5.60-jdk8-openjdk-slim-buster as base
WORKDIR /usr/local/tomcat
COPY ${PWD}/code/im_http_service.war /usr/local/tomcat/webapps/
EXPOSE 8081 8005 8009
