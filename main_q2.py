from fastapi import FastAPI, Request
import os, requests, threading, time

app = FastAPI()

# Configuração do Processo
N_PROCS = int(os.getenv("N_PROCS", "3"))
try:
    PROC_ID = int(os.getenv("PROC_ID", "0").split("-")[-1])
except:
    PROC_ID = 0

raw_peers = os.getenv("PEERS", "")
PEERS = raw_peers.split(",") if raw_peers else []

# Estado da Exclusão Mútua
has_token = False
want_cs = False
in_cs = False
lock = threading.Lock()

def log(msg):
    print(f"[PROC {PROC_ID}] {msg}")

# Lógica Auxiliar
def next_proc(idx):
    return (idx + 1) % N_PROCS

def send_post(url, endpoint, body=None):
    try:
        requests.post(f"{url}{endpoint}", json=body or {}, timeout=3)
    except:
        pass

def pass_token():
    """Passa o token para o próximo processo no anel."""
    global has_token
    nxt = next_proc(PROC_ID)
    
    time.sleep(1.5) # Delay para visualização dos logs

    if PEERS and len(PEERS) > nxt:
        send_post(PEERS[nxt], "/pass_token", {"from": PROC_ID})
    
    with lock:
        has_token = False

def process_token():
    """Lógica executada ao receber o token."""
    global has_token, want_cs, in_cs
    
    with lock:
        if not has_token: return
        should_enter = want_cs
    
    if should_enter:
        # Entra na Seção Crítica
        in_cs = True
        log(">>> ENTROU NA SEÇÃO CRÍTICA (Bloqueando token por 2s...)")
        
        time.sleep(2) # Simulação de trabalho
        
        log("<<< SAIU DA SEÇÃO CRÍTICA")
        in_cs = False
        with lock:
            want_cs = False
            
        pass_token()
    else:
        # Apenas repassa o token
        pass_token()

# Endpoints da API
@app.post("/init_token")
def init_token():
    """Inicializa o token neste processo."""
    global has_token
    with lock:
        has_token = True
    log("Token inicializado neste processo.")
    threading.Thread(target=process_token).start()
    return {"ok": True}

@app.post("/pass_token")
def receive_token(req: Request):
    """Recebe o token de um processo anterior."""
    global has_token
    with lock:
        if has_token: return {"ok": False}
        has_token = True
        
    log("Recebeu token.")
    threading.Thread(target=process_token).start()
    return {"ok": True}

@app.get("/request_cs")
def request_cs():
    """Faz a requisição para entrar na Seção Crítica."""
    global want_cs
    with lock:
        want_cs = True
    log("REQUISIÇÃO RECEBIDA: Quero entrar na Seção Crítica!")
    return {"status": "request_accepted"}

@app.get("/state")
def state():
    """Retorna o estado interno do processo."""
    return {
        "proc": PROC_ID,
        "has_token": has_token,
        "want_cs": want_cs, 
        "peers": PEERS
    }