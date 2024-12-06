#!/bin/bash

# 检查Redis是否已经运行
if pgrep redis-server > /dev/null
then
    echo "Redis is already running"
else
    # 启动Redis服务器
    redis-server /etc/redis/redis.conf &
    echo "Started Redis server"
fi 