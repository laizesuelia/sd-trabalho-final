# Trabalho de Sistemas Distribuídos: Multicast, Exclusão Mútua e Eleição de Líder

Implementação de algoritmos clássicos de sistemas distribuídos utilizando Python (FastAPI) e orquestração via Kubernetes (Minikube).

-> Q1 — Multicast com Ordenação Total

Implementação de multicast confiável com ordenação total usando:

Relógios lógicos de Lamport

Fila de prioridade para ordenação global

Confirmações (ACKs) de todos os processos antes da entrega

Simulação de atrasos para validar o comportamento do algoritmo

 Garantia: todas as mensagens são entregues na mesma ordem em todos os processos.

->  Q2 — Exclusão Mútua (Token Ring)

Implementação do algoritmo de Token Ring para controle de acesso à região crítica:

Apenas o processo que possui o token pode entrar na região crítica

O token circula entre os processos em ordem lógica

Comunicação realizada via mensagens HTTP

Garantia: exclusão mútua sem starvation.

->  Q3 — Eleição de Líder (Algoritmo do Valentão)

Implementação do Algoritmo do Valentão (Bully Algorithm):

Cada processo possui um identificador único

Ao detectar falha do coordenador, inicia-se uma eleição

O processo com maior ID ativo torna-se o novo líder

O líder anuncia sua coordenação aos demais processos
