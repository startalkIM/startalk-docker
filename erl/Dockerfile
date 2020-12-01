FROM erlang:19.3.6.13-slim as base
RUN mkdir -p /startalk/ejabberd && apt-get update && apt-get install -y libssl-dev libyaml-dev && apt-get clean autoclean

FROM base as builder
RUN mkdir -p /startalk/openssl1.0.2l && mkdir /builder
COPY build/ejabberd /builder/ejabberd
WORKDIR /builder/ejabberd

RUN apt-get update && apt-get install -y wget make gcc libssl-dev libyaml-dev libexpat1-dev zlib1g zlib1g-dev perl g++ && \
wget https://www.openssl.org/source/openssl-1.0.2l.tar.gz && \
tar -zxvf openssl-1.0.2l.tar.gz && \
cd openssl-1.0.2l/ && \
./config --prefix=/openssl1.0.2l && \
sed -i '0,/CFLAG=/s//CFLAG= -fPIC /' /builder/ejabberd/openssl-1.0.2l/Makefile && \
make install && \
cd /builder/ejabberd && \
./configure --prefix=/startalk/ejabberd --enable-pgsql --enable-full-xml && \
make && \
make install 

From base
COPY --from=builder /startalk/ejabberd /startalk/ejabberd
WORKDIR /startalk/ejabberd
EXPOSE 5202 5280 10050
CMD [ "/startalk/ejabberd/sbin/ejabberdctl", "foreground" ]

