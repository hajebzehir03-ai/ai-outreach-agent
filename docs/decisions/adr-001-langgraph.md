# ADR-001: Uso di LangGraph come Agent Framework

**Data**: 2025-05-17
**Stato**: Accettato
**Autore**: Zehir

## Contesto

Il progetto richiede un sistema multi-agent orchestrato con: stato condiviso tra agenti, retry su errori, navigazione non lineare tra step, e human-in-the-loop (approval gate). Sono state valutate le seguenti alternative:

| Framework | Tipo | Pro | Contro |
|---|---|---|---|
| LangGraph | State machine | Stato esplicito, retry nativi, human-in-the-loop, usato da 11x | Curva apprendimento |
| CrewAI | Multi-agent sequenziale | Semplice, template predefiniti | Stato implicito, difficile debug |
| AutoGen | Conversational multi-agent | Flessibile | Verbose, difficile da deployare |
| Custom (solo Anthropic SDK) | Nessun framework | Zero dipendenze | Da costruire da zero, niente retry/state |
| n8n / Make | Low-code workflow | Rapido setup | Non adatto a logica complessa in Python |

## Decisione

**LangGraph** come framework di orchestrazione per tutti gli agenti.

## Motivazione

1. **Stato esplicito**: ogni nodo del grafo riceve e restituisce uno `AgentState` tipizzato. Nessuna magia implicita — è chiaro cosa entra e cosa esce da ogni agente.

2. **Human-in-the-loop nativo**: LangGraph supporta `interrupt_before` e `interrupt_after` su qualsiasi nodo. L'approval gate del Writer Agent è implementabile in 5 righe.

3. **Retry e error handling**: i nodi falliti possono essere re-eseguiti senza ripartire dall'inizio — fondamentale per pipeline di enrichment che coinvolgono API esterne.

4. **Usato da 11x.ai**: il case study ZenML documenta che 11x ha abbandonato ReAct e workflow rigido per arrivare esattamente a LangGraph — si evita lo stesso percorso di trial-and-error.

5. **Compatibilità**: integrazione nativa con LangSmith per tracing, con LangChain tools, e con Anthropic SDK.

6. **Navigazione non lineare**: un lead può essere re-processato dal Qualifier Agent senza dover ripassare per lo Scout Agent — impossibile con framework sequenziali.

## Conseguenze

- **Positivo**: stato del workflow sempre ispezionabile, retry granulari, approval gate semplice
- **Positivo**: tracing in LangSmith permette debug visuale del grafo
- **Negativo**: dipendenza da `langgraph` e `langchain` — aggiunge ~200ms di overhead al primo import
- **Negativo**: curva di apprendimento per chi non conosce i concetti di StateGraph

## Alternativa non scelta: pattern puro Anthropic SDK

Per la v2, se LangGraph dovesse aggiungere troppa complessità, si può migrare a un pattern tool-calling puro con `anthropic` SDK e gestione manuale dello stato via PostgreSQL. La struttura dei tool Python rimane invariata.
