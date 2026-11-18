#!/usr/bin/env bash
# Démarrage de l'environnement TP J2 (ordre du sujet §1.8) : HDFS (Java 17) puis NiFi (Java 21).
# Usage dans Ubuntu (WSL) : bash start_env.sh
export HADOOP_HOME=/opt/hadoop HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$PATH:/opt/hadoop/bin:/opt/hadoop/sbin

echo "== 1. HDFS (Java 17) =="
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
jps | grep -q NameNode || start-dfs.sh
jps
hdfs dfsadmin -report | grep -E "Live datanodes|DFS Remaining"

echo "== 2. NiFi (Java 21) =="
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
if ! /opt/nifi/bin/nifi.sh status 2>&1 | grep -q "Status: UP"; then
  setsid nohup /opt/nifi/bin/nifi.sh start > /tmp/nifi-start.log 2>&1 < /dev/null &
  echo -n "Attente de NiFi"
  until curl -sk -o /dev/null https://localhost:8443/nifi/; do echo -n "."; sleep 5; done; echo
fi
echo "NiFi : https://localhost:8443/nifi   |   NameNode : http://localhost:9870"
