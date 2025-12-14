from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import requests
import threading
import time
import os
import heapq

app = FastAPI()

N_PROCS = int(os.getenv("N_PROCS", "3"))
raw = os.getenv("PROC_ID", "0")

try:
    if "-" in raw:
        PROC_ID = int(raw.split("-")[-1])
    else:
        PROC_ID = int(raw)
except:
    PROC_ID = 0

PORT = int(os.getenv("PORT", "8000"))
PEERS = os.getenv("PEERS", "").split(",") if os.getenv("PEERS") else []

# RELÓGIO DE LAMPORT
clock = 0
clock_lock = threading.Lock()

def inc_clock_on_send():
    global clock
    with clock_lock:
        clock += 1
        return clock

def update_clock_on_receive(ts):
    global clock
    with clock_lock:
        clock = max(clock, ts) + 1
        return clock

# FILA DE PRIORIDADE
pq = []  # (timestamp, sender, msgId, payload)
pq_lock = threading.Lock()

# CONTROLE DE ACKS
acks = {}  # msgId -> set()
acks_lock = threading.Lock()

msgs = {}

# SIMULAÇÃO DE ATRASO
DELAY_PROCESS_ID = os.getenv("DELAY_PROCESS_ID")   # ex: "1"
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "5"))

# AUXILIARES
def multicast(path, data):
    for p in PEERS:
        try:
            requests.post(f"{p}{path}", json=data, timeout=2)
        except:
            print(f"[PROC {PROC_ID}] Falha ao enviar para {p}")

def try_deliver():
    while True:
        with pq_lock:
            if not pq:
                return
            ts, sender, msgId, payload = pq[0]

        with acks_lock:
            if msgId in acks and len(acks[msgId]) == N_PROCS:
                with pq_lock:
                    heapq.heappop(pq)
                print(f"[PROC {PROC_ID}] >>> ENTREGOU mensagem {msgId} de {sender}: {payload}")
                msgs.pop(msgId, None)
                acks.pop(msgId, None)
                continue
        return

# MODELOS
class Msg(BaseModel):
    msg: str

class Incoming(BaseModel):
    msgId: str
    sender: int
    ts: int
    payload: str

class Ack(BaseModel):
    msgId: str
    sender: int
    ts: int

# ENDPOINTS
@app.post("/send")
def send_message(m: Msg):
    ts = inc_clock_on_send()
    msgId = str(uuid.uuid4())
    payload = m.msg

    msgs[msgId] = (ts, PROC_ID, payload)

    with pq_lock:
        heapq.heappush(pq, (ts, PROC_ID, msgId, payload))

    with acks_lock:
        acks[msgId] = {PROC_ID}

    body = {
        "msgId": msgId,
        "sender": PROC_ID,
        "ts": ts,
        "payload": payload
    }

    threading.Thread(target=multicast, args=("/receive", body)).start()
    try_deliver()

    return {"status": "sent", "id": msgId, "ts": ts}

    def send_ack():
        if DELAY_PROCESS_ID:
            try:
                if int(DELAY_PROCESS_ID) == PROC_ID:
                    print(f"[PROC {PROC_ID}] DELAYING ACK por {DELAY_SECONDS}s")
                    time.sleep(DELAY_SECONDS)
            except:
                pass

        multicast("/ack", ack_body)

    threading.Thread(target=send_ack).start()
    return {"ok": True}

@app.post("/ack")
def ack_msg(a: Ack):
    update_clock_on_receive(a.ts)

    with acks_lock:
        if a.msgId not in acks:
            acks[a.msgId] = set()
        acks[a.msgId].add(a.sender)

    try_deliver()
    return {"ack": "received"}

@app.get("/state")
def get_state():
    return {
        "proc": PROC_ID,
        "clock": clock,
        "queue": pq,
        "acks": {k: list(v) for k, v in acks.items()}
    }
