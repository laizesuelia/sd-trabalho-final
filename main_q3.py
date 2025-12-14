from fastapi import FastAPI
import requests
import os
import threading
import time

app = FastAPI()

# Configuração do Processo
N_PROCS = int(os.getenv("N_PROCS", "3"))

try:
    # Obtém o ID do nome do pod (ex: bully-0 -> 0)
    PROC_ID = int(os.getenv("PROC_ID", "0").split("-")[-1]) 
except:
    PROC_ID = 0

raw_peers = os.getenv("PEERS", "")
PEERS = [p.strip() for p in raw_peers.split(",") if p.strip()]

# Estado local
coordinator = None
is_participating = False
lock = threading.Lock()

def log(msg):
    print(f"[PROC {PROC_ID}] {msg}")

# Auxiliares
def send_election(url):
    """
    Envia a mensagem ELECTION para um processo maior.
    Retorna True se o processo responder dentro do timeout.
    """
    try:
        # Timeout curto é crucial para detectar falhas rapidamente
        r = requests.post(
            f"{url}/election",
            json={"from": PROC_ID},
            timeout=0.5 
        )
        return r.json().get("alive", False)
    except:
        return False

def bigger_processes():
    """Retorna a lista de URLs dos processos com ID maior que o meu."""
    return [p for i, p in enumerate(PEERS) if i > PROC_ID]

# Lógica do Algoritmo do Valentão 
def start_election():
    global is_participating, coordinator

    with lock:
        if is_participating: 
            return # Evita iniciar múltiplas eleições
        is_participating = True
        coordinator = None

    log(">>> INICIOU ELEIÇÃO")

    higher = bigger_processes()

    # 1. Se não existe ninguém maior, EU sou o líder.
    if not higher:
        become_leader()
        return

    someone_answered = False

    # 2. Envia ELECTION para processos maiores.
    for url in higher:
        if send_election(url):
            someone_answered = True
            log(f"Processo maior em {url} respondeu.")

    # 3. Se ninguém maior respondeu, eu assumo imediatamente (Regra do Valentão).
    if not someone_answered:
        log("Ninguém maior respondeu. Assumindo liderança AGORA.")
        become_leader()
        return

    # 4. Se alguém respondeu, eu espero ele se tornar o novo líder.
    log("Alguém maior respondeu. Aguardando anúncio do coordenador...")
    
    wait_time = 0.0
    while wait_time < 2.0: # Espera 2 segundos pelo anúncio
        time.sleep(0.1)
        wait_time += 0.1

        with lock:
            if coordinator is not None:
                log("Coordenador anunciado. Encerrando minha tentativa.")
                is_participating = False
                return

    # 5. Se o tempo esgotou e o processo maior falhou em se anunciar, reinicia a eleição.
    log("Timeout! O processo maior respondeu mas não assumiu. Reiniciando eleição...")
    with lock:
        is_participating = False 
    start_election()


def become_leader():
    global coordinator, is_participating

    with lock:
        coordinator = PROC_ID
        is_participating = False

    log("🎉 EU SOU O NOVO COORDENADOR!")

    # Anuncia a todos os peers
    for url in PEERS:
        if url != PEERS[PROC_ID]:
            try:
                requests.post(
                    f"{url}/coordinator",
                    json={"leader": PROC_ID},
                    timeout=0.5
                )
            except:
                pass

# Endpoints da API
@app.post("/election")
def receive_election():
    """Recebe mensagem de Eleição, responde "alive" e inicia a própria eleição."""
    threading.Thread(target=start_election).start()
    return {"alive": True}


@app.post("/coordinator")
def receive_coordinator(body: dict):
    """Recebe o anúncio do novo coordenador."""
    global coordinator, is_participating

    with lock:
        coordinator = body["leader"]
        is_participating = False

    log(f"Novo coordenador anunciado: {coordinator}")
    return {"ok": True}


@app.get("/crash_coordinator")
def crash_coordinator():
    """Simula a detecção de falha no líder para forçar uma nova eleição."""
    global coordinator, is_participating

    log("Detectada falha no coordenador! Iniciando eleição...")

    with lock:
        coordinator = None
        is_participating = False # Reseta o estado para garantir que a eleição comece

    threading.Thread(target=start_election).start()
    return {"ok": True}


@app.get("/state")
def state():
    """Retorna o estado atual do processo."""
    return {
        "proc": PROC_ID,
        "coordinator": coordinator,
        "participating": is_participating
    }