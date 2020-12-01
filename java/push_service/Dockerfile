FROM tomcat:8.5.60-jdk8-openjdk-slim-buster as base
WORKDIR /usr/local/tomcat
COPY ${PWD}/code/push_service.war /usr/local/tomcat/webapps/
EXPOSE 8007 8011 8083
