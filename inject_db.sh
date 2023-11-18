#!/bin/bash

# Load configuration values
username=$(cat config.json | jq -r .username)
password=$(cat config.json | jq -r .password)
server=$(cat config.json | jq -r .server)
port=$(cat config.json | jq -r .port)
database=$(cat config.json | jq -r .database)

mysql -u ${username} -p ${password} -P ${port} -h ${server} ${database} < resume_structure.sql