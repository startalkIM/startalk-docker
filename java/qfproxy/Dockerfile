FROM tomcat:8.5.60-jdk8-openjdk-slim-buster as base
WORKDIR /usr/local/tomcat
COPY ${PWD}/code/qfproxy.war /usr/local/tomcat/webapps/
EXPOSE 8006 8010 8082
