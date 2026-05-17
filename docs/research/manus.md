# Manus AI — General-Purpose Autonomous Agent

## Cosa fa concretamente

Manus (sviluppato da Monica.im, Cina) è un agente AI general-purpose che esegue task complessi end-to-end con minima supervisione umana. Non è specializzato in outreach, ma dimostra cosa è possibile con un'architettura agente completa: browsing web, esecuzione codice, manipolazione file, analisi dati, generazione contenuto. Supera GPT-4 Deep Research su GAIA benchmark (practical task execution). Il nome richiama "dalla mente alla mano" — pensa, pianifica, esegue, consegna.

## Architettura inferita

**Multi-model iterative agent loop con CodeAct** — usa esecuzione di codice Python come meccanismo di azione primario.

```
Foundation Models
├── Claude 3.5/3.7 (reasoning principale)
├── Alibaba Qwen (task specifici)
└── Selezione dinamica in base al task

Agent Loop (iterativo)
├── Analyze: comprende il goal
├── Plan: decompone in sub-task
├── Execute: esegue via tool (browser, shell, code)
├── Observe: legge output
└── Iterate: fino a completamento

Cloud Computing Environment
├── Browser virtuale (Playwright)
├── Shell execution
├── File system
└── Code runner (Python)

Memory / Knowledge
├── Planning module
├── Knowledge retrieval (RAG)
└── Memory management cross-step
```

- **Approccio CodeAct**: invece di usare tool pre-definiti, genera ed esegue codice Python per azioni complesse
- **Multi-model**: sceglie il modello migliore per ogni step, non usa sempre lo stesso
- **Ambiente isolato**: opera in un container cloud, non sul PC dell'utente (a meno di computer use)

## Punti di forza

- **Benchmark-leading** su task di esecuzione pratica (GAIA)
- **Generalista**: può fare qualsiasi cosa abbia senso fare su un computer
- **CodeAct** — approccio più flessibile dei tool predefiniti per task nuovi
- **Multi-model** — usa il modello più economico/veloce quando possibile

## Limiti / cosa NON fa bene

- **Non specializzato**: nessuna conoscenza di dominio su outreach B2B, GDPR, mercato italiano
- Lento e costoso per task ripetitivi ad alto volume (1 agente per N lead non scala)
- Stato ancora beta / in sviluppo rapido — instabilità
- Non gestisce deliverability, warming, tracking email
- Privacy non chiara (ambiente cloud cinese)

## Cosa rubare per il nostro progetto

1. **CodeAct per il Researcher Agent** → invece di avere tool hardcoded per ogni fonte, permettere all'agent di scrivere codice di scraping ad-hoc per siti non previsti
2. **Iterative loop esplicito** → LangGraph implementa già questo pattern — ogni agent node segue analyze→plan→execute→observe
3. **Multi-model routing** → usare claude-haiku-4-5 per step cheap (classificazione), claude-sonnet-4-5 per reasoning profondo (scoring, writing)
4. **Planning module** → il Qualifier Agent deve esplicitare il reasoning del suo score in testo (trasparenza, come da spec)
