"""UC-04 – Flux NiFi GetFile → PutHDFS (+ LogAttribute sur failure), via l'API REST NiFi 2.12.

Usage (Ubuntu/WSL) : python3 uc04_nifi.py build|run|erreur_dossier|erreur_conflit|provenance|export
Chaque phase écrit sa preuve dans ../04_UC04_nifi/preuves/.
Les objets créés sont identiques à ceux construits à la main dans l'interface (visibles sur le canvas).
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

from nifi_api import NiFi

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "04_UC04_nifi" / "preuves"
PG_NAME = "UC04_ingestion_tpcxbb"
HADOOP_CONF = "/opt/hadoop/etc/hadoop/core-site.xml,/opt/hadoop/etc/hadoop/hdfs-site.xml"
HDFS_DEST = "/retail-lake/raw/nifi"
INPUT = "/data/nifi/input"
KIT_FILE = Path.home() / "tpcxbb_kit/data/store/store.dat"
STD = {"group": "org.apache.nifi", "artifact": "nifi-standard-nar", "version": "2.12.0"}
HDP = {"group": "org.apache.nifi", "artifact": "nifi-hadoop-nar", "version": "2.12.0"}

n = NiFi()
log_file = None


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_file.write(s + "\n")


def sh(cmd):
    env = "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 PATH=$PATH:/opt/hadoop/bin; "
    r = subprocess.run(["bash", "-c", env + cmd], capture_output=True, text=True)
    log(f"[{now()}] $ {cmd}\n{(r.stdout + r.stderr).rstrip()}\n→ code retour : {r.returncode}\n")
    return r


# --- accès aux objets ---------------------------------------------------------------
def pg():
    root = n.get("/flow/process-groups/root")["processGroupFlow"]
    for g in root["flow"]["processGroups"]:
        if g["component"]["name"] == PG_NAME:
            return g["component"]["id"]
    return None


def procs():
    f = n.get(f"/flow/process-groups/{pg()}")["processGroupFlow"]["flow"]
    return {p["component"]["name"]: p for p in f["processors"]}


def conns():
    return n.get(f"/flow/process-groups/{pg()}")["processGroupFlow"]["flow"]["connections"]


def set_state(name, state):
    p = n.get(f"/processors/{procs()[name]['id']}")
    n.put(f"/processors/{p['id']}/run-status", {"revision": p["revision"], "state": state})
    log(f"[{now()}] {name} → {state}")


def update_props(name, props):
    p = n.get(f"/processors/{procs()[name]['id']}")
    n.put(f"/processors/{p['id']}", {"revision": p["revision"],
                                     "component": {"id": p["id"], "config": {"properties": props}}})
    log(f"[{now()}] {name} : propriétés modifiées {props}")


def describe(name):
    p = n.get(f"/processors/{procs()[name]['id']}")
    c = p["component"]
    st = n.get(f"/flow/processors/{p['id']}/status")["processorStatus"]["aggregateSnapshot"]
    log(f"--- {name} ({c['type'].split('.')[-1]}) id={c['id']}")
    log(f"    état={c['state']}  validation={c.get('validationStatus')}  "
        f"planification={c['config']['schedulingPeriod']}  auto-terminate={c['config'].get('autoTerminatedRelationships')}")
    for k in ("Input Directory", "Keep Source File", "Recurse Subdirectories", "Hadoop Configuration Resources",
              "Directory", "Conflict Resolution Strategy", "Log Level"):
        if k in c["config"]["properties"]:
            log(f"    {k} = {c['config']['properties'][k]}")
    for e in c.get("validationErrors") or []:
        log(f"    ERREUR DE VALIDATION : {e}")
    log(f"    compteurs (5 min) : in={st['flowFilesIn']} out={st['flowFilesOut']} "
        f"lus={st['bytesRead']} o, écrits={st['bytesWritten']} o, tâches={st['taskCount']}")


def queues():
    for c in conns():
        s = c["status"]["aggregateSnapshot"]
        log(f"    file {c['component']['source']['name']} -[{','.join(c['component']['selectedRelationships'])}]-> "
            f"{c['component']['destination']['name']} : {s['queued']}")


def bulletins(since_id=0):
    bs = n.get(f"/flow/bulletin-board?after={since_id}&limit=50")["bulletinBoard"]["bulletins"]
    for b in bs:
        if b.get("bulletin"):
            bb = b["bulletin"]
            log(f"    BULLETIN [{bb['level']}] {bb['timestamp']} {bb['sourceName']} : {bb['message'][:400]}")
    return max([b["id"] for b in bs], default=since_id)


def wait(cond, timeout=90, step=3):
    t = time.time()
    while time.time() - t < timeout:
        if cond():
            return True
        time.sleep(step)
    return False


# --- phases --------------------------------------------------------------------------
def build():
    if pg():
        log(f"Process Group {PG_NAME} déjà présent ({pg()}) : rien à créer.")
        return
    root_id = n.get("/flow/process-groups/root")["processGroupFlow"]["id"]
    g = n.post(f"/process-groups/{root_id}/process-groups",
               {"revision": {"version": 0}, "component": {"name": PG_NAME, "position": {"x": 0, "y": 0},
                "comments": "UC-04 : ingestion d'un fichier TPCx-BB local vers HDFS (zone raw/nifi)"}})
    gid = g["id"]
    log(f"[{now()}] Process Group créé : {PG_NAME} ({gid})")

    def add(name, typ, bundle, x, y, props, sched="0 sec", auto=()):
        p = n.post(f"/process-groups/{gid}/processors", {"revision": {"version": 0}, "component": {
            "name": name, "type": typ, "bundle": bundle, "position": {"x": x, "y": y},
            "config": {"properties": props, "schedulingPeriod": sched,
                       "autoTerminatedRelationships": list(auto)}}})
        log(f"[{now()}] Processeur créé : {name} ({p['id']})")
        return p

    gf = add("GetFile", "org.apache.nifi.processors.standard.GetFile", STD, 0, 0,
             {"Input Directory": INPUT, "Keep Source File": "false", "Recurse Subdirectories": "false"},
             sched="10 sec")
    ph = add("PutHDFS", "org.apache.nifi.processors.hadoop.PutHDFS", HDP, 0, 260,
             {"Hadoop Configuration Resources": HADOOP_CONF, "Directory": HDFS_DEST,
              "Conflict Resolution Strategy": "fail"}, auto=("success",))
    la = add("LogAttribute (échecs)", "org.apache.nifi.processors.standard.LogAttribute", STD, 520, 260,
             {"Log Level": "warn", "Log Payload": "false"}, auto=("success",))

    def link(src, dst, rels):
        n.post(f"/process-groups/{gid}/connections", {"revision": {"version": 0}, "component": {
            "source": {"id": src["id"], "groupId": gid, "type": "PROCESSOR"},
            "destination": {"id": dst["id"], "groupId": gid, "type": "PROCESSOR"},
            "selectedRelationships": rels}})
        log(f"[{now()}] Connexion : {src['component']['name']} -[{','.join(rels)}]-> {dst['component']['name']}")

    link(gf, ph, ["success"])
    link(ph, la, ["failure"])
    time.sleep(2)
    for name in procs():
        describe(name)


def run():
    sh(f"ls -l {INPUT}; md5sum {INPUT}/* {KIT_FILE}")
    sh(f"hdfs dfs -ls {HDFS_DEST}")
    set_state("PutHDFS", "RUNNING")
    set_state("LogAttribute (échecs)", "RUNNING")
    set_state("GetFile", "RUNNING")
    ok = wait(lambda: subprocess.run(["bash", "-c", f"/opt/hadoop/bin/hdfs dfs -test -e {HDFS_DEST}/store.dat"],
                                     env={"JAVA_HOME": "/usr/lib/jvm/java-17-openjdk-amd64", "PATH": "/usr/bin:/bin"}
                                     ).returncode == 0)
    log(f"[{now()}] Fichier présent dans HDFS : {ok}")
    set_state("GetFile", "STOPPED")       # pas de relance en boucle
    time.sleep(3)
    for name in procs():
        describe(name)
    queues()
    sh(f"hdfs dfs -ls -h {HDFS_DEST}")
    sh(f"hdfs dfs -du -h {HDFS_DEST}")
    sh(f"hdfs dfs -cat {HDFS_DEST}/store.dat | md5sum; md5sum {KIT_FILE}")
    sh(f"ls -l {INPUT}   # vide : GetFile a consommé la copie de travail")
    sh(f"hdfs dfs -ls /retail-lake/raw/tpcxbb/initial/store   # dépôt UC-03 conservé")


def erreur_dossier():
    log("Test A – dossier source inexistant dans GetFile")
    bid = bulletins()
    update_props("GetFile", {"Input Directory": "/data/nifi/input_inexistant"})
    time.sleep(3)
    describe("GetFile")
    try:
        set_state("GetFile", "RUNNING")
        time.sleep(15)
        set_state("GetFile", "STOPPED")
    except RuntimeError as e:
        log(f"[{now()}] Démarrage refusé par NiFi : {e}")
    bulletins(bid)
    log("Rétablissement de la configuration :")
    update_props("GetFile", {"Input Directory": INPUT})
    time.sleep(3)
    describe("GetFile")


def erreur_conflit():
    log("Test B – conflit de nom dans HDFS (Conflict Resolution Strategy = fail)")
    sh(f"cp -p {KIT_FILE} {INPUT}/ && ls -l {INPUT}")
    sh(f"hdfs dfs -ls {HDFS_DEST}")
    bid = bulletins()
    set_state("GetFile", "RUNNING")
    wait(lambda: any(c["status"]["aggregateSnapshot"]["flowFilesQueued"] == 0 for c in conns()) and
         n.get(f"/flow/processors/{procs()['LogAttribute (échecs)']['id']}/status")
         ["processorStatus"]["aggregateSnapshot"]["flowFilesIn"] > 0, timeout=60)
    set_state("GetFile", "STOPPED")
    time.sleep(3)
    for name in procs():
        describe(name)
    queues()
    bulletins(bid)
    sh("grep -n -A14 'LogAttribute' /opt/nifi/logs/nifi-app.log | grep -E 'filename|absolute.path|uuid|Standard FlowFile|WARN' | tail -8")
    sh(f"hdfs dfs -ls {HDFS_DEST}   # toujours 1 seul fichier : pas d'écrasement ni de doublon")


def provenance():
    req = n.post("/provenance", {"provenance": {"request": {
        "maxResults": 100, "summarize": False, "incrementalResults": False,
        "searchTerms": {"Filename": {"value": "store.dat", "inverse": False}}}}})
    pid = req["provenance"]["id"]
    wait(lambda: n.get(f"/provenance/{pid}")["provenance"]["finished"], timeout=30, step=1)
    evs = n.get(f"/provenance/{pid}")["provenance"]["results"]["provenanceEvents"]
    n.call("DELETE", f"/provenance/{pid}")
    evs.sort(key=lambda e: e["eventId"])
    log(f"{len(evs)} événements de provenance pour filename=store.dat\n")
    log("eventId | date | type | composant | FlowFile UUID | taille | détail")
    for e in evs:
        det = e.get("transitUri") or e.get("details") or ""
        log(f"{e['eventId']} | {e['eventTime']} | {e['eventType']} | {e['componentName']} | "
            f"{e['flowFileUuid']} | {e['fileSize']} | {det}")
    (OUT / "provenance_evenements.json").write_text(json.dumps(evs, indent=2, ensure_ascii=False))
    if evs:
        e = evs[0]
        log("\nAttributs du FlowFile (1er événement) :")
        for a in e.get("attributes", []):
            log(f"    {a['name']} = {a.get('value')}")


def export():
    raw = n.call("GET", f"/process-groups/{pg()}/download", raw=True)
    f = HERE.parent / "04_UC04_nifi" / f"{PG_NAME}.json"
    f.write_bytes(raw)
    txt = raw.decode()
    log(f"Flow definition exportée : {f.name} ({len(raw)} octets)")
    log("Recherche de secrets dans l'export :", "aucun" if "assword" not in txt and n.token not in txt else "À VÉRIFIER")


PHASES = {"build": build, "run": run, "erreur_dossier": erreur_dossier,
          "erreur_conflit": erreur_conflit, "provenance": provenance, "export": export}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    phase = sys.argv[1]
    num = list(PHASES).index(phase) + 1
    with open(OUT / f"{num:02d}_{phase}.txt", "w", encoding="utf-8") as log_file:
        log(f"### UC-04 – phase « {phase} » – {now()} – NiFi {n.get('/flow/about')['about']['version']}\n")
        PHASES[phase]()
