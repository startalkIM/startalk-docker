#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/superUser
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/ejabberd 
mkdir -p /etc/postgresql
cp /docker-entrypoint-initdb.d/pg_hba.conf /etc/postgresql/pg_hba.conf
