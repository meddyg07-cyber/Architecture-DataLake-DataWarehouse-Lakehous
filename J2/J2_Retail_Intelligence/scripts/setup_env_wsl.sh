#!/usr/bin/env bash
# Installation Hadoop 3.5.0 + NiFi 2.12.0 dans Ubuntu 24.04 (WSL2), mode pseudo-distribué.
# Prérequis (en root) : apt install openjdk-17-jdk-headless openjdk-21-jdk-headless openssh-server ...
# Archives téléchargées au préalable dans ~/downloads.
set -euo pipefail

DL="$HOME/downloads"
J17=/usr/lib/jvm/java-17-openjdk-amd64
J21=/usr/lib/jvm/java-21-openjdk-amd64

# --- Vérification des sommes de contrôle ---------------------------------------
cd "$DL"
for f in hadoop-3.5.0.tar.gz nifi-2.12.0-bin.zip; do
  expected=$(awk '{print $1}' "$f.sha512" | head -1)
  [ ${#expected} -lt 100 ] && expected=$(grep -oE '[0-9a-fA-F]{128}' "$f.sha512" | head -1)
  actual=$(sha512sum "$f" | awk '{print $1}')
  [ "${expected,,}" = "$actual" ] && echo "SHA512 OK : $f" || { echo "SHA512 KO : $f"; exit 1; }
done

# --- Hadoop -----------------------------------------------------------------------
# /opt/hadoop et /opt/nifi sont créés au préalable en root et donnés à l'utilisateur
[ -x /opt/hadoop/bin/hadoop ] || tar -xzf hadoop-3.5.0.tar.gz -C /opt/hadoop --strip-components=1
HC=/opt/hadoop/etc/hadoop
grep -q "^export JAVA_HOME=$J17" $HC/hadoop-env.sh || echo "export JAVA_HOME=$J17" >> $HC/hadoop-env.sh

cat > $HC/core-site.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
</configuration>
EOF

cat > $HC/hdfs-site.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <property><name>dfs.replication</name><value>1</value></property>
  <property><name>dfs.namenode.name.dir</name><value>file://$HOME/hadoop-data/namenode</value></property>
  <property><name>dfs.datanode.data.dir</name><value>file://$HOME/hadoop-data/datanode</value></property>
</configuration>
EOF
mkdir -p "$HOME/hadoop-data/namenode" "$HOME/hadoop-data/datanode"

# --- Variables d'environnement ---------------------------------------------------
if ! grep -q HADOOP_HOME ~/.bashrc; then
cat >> ~/.bashrc <<'EOF'
# --- TP J2 : Hadoop / NiFi ---
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export JAVA_HOME_HADOOP=/usr/lib/jvm/java-17-openjdk-amd64
export JAVA_HOME_NIFI=/usr/lib/jvm/java-21-openjdk-amd64
export JAVA_HOME=$JAVA_HOME_HADOOP
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$JAVA_HOME/bin
EOF
fi

# --- SSH local sans mot de passe (requis par start-dfs.sh) ------------------------
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -q
grep -qf ~/.ssh/id_ed25519.pub ~/.ssh/authorized_keys 2>/dev/null || cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys
ssh-keyscan -H localhost 0.0.0.0 >> ~/.ssh/known_hosts 2>/dev/null

# --- NiFi --------------------------------------------------------------------------
if [ ! -x /opt/nifi/bin/nifi.sh ]; then
  unzip -q nifi-2.12.0-bin.zip -d /tmp/nifi-unzip
  mv /tmp/nifi-unzip/nifi-2.12.0/* /opt/nifi/ && rm -rf /tmp/nifi-unzip
fi
# NiFi 2.x ne livre plus PutHDFS par défaut : ajout des NAR Hadoop officiels (Maven Central)
cp -n nifi-hadoop-nar-2.12.0.nar nifi-hadoop-libraries-nar-2.12.0.nar /opt/nifi/lib/
grep -q "^export JAVA_HOME=$J21" /opt/nifi/bin/nifi-env.sh || echo "export JAVA_HOME=$J21" >> /opt/nifi/bin/nifi-env.sh

# Spécifique WSL : forcer l'écoute IPv4, sinon l'UI n'est pas joignable depuis le navigateur Windows
grep -q preferIPv4Stack /opt/nifi/conf/bootstrap.conf || echo 'java.arg.ipv4=-Djava.net.preferIPv4Stack=true' >> /opt/nifi/conf/bootstrap.conf

# Dossiers d'entrée NiFi /data/nifi/{input,archive,error} : créés en root puis donnés à l'utilisateur
echo "Configuration terminée."
