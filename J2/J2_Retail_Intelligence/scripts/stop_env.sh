#!/usr/bin/env bash
# Arrêt (ordre du sujet §1.8) : arrêter les flux dans l'UI NiFi, puis NiFi, puis HDFS.
export HADOOP_HOME=/opt/hadoop HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$PATH:/opt/hadoop/bin:/opt/hadoop/sbin
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 /opt/nifi/bin/nifi.sh stop
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 stop-dfs.sh
jps
