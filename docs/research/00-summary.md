# Research Summary — AI Outreach Agent per PMI Italiane

## Pattern ricorrenti nei 10 agenti analizzati

### 1. Multi-agent gerarchico con supervisor node
Il pattern più maturo (11x, Lindy Societies) prevede un orchestratore centrale che delega a sub-agent specializzati. Il supervisor non esegue task: coordina, controlla il flusso, aggrega i risultati. Ogni sub-agent ha responsabilità singola e tool dedicati.

### 2. Separazione enrichment da messaging
Clay, Apollo e Artisan separano sempre la fase di raccolta dati dalla fase di generazione contenuto. I dati vengono prima accumulati, poi usati. Questo permette retry, caching, e debug indipendenti.

### 3. Signal-based pitch selection (Artisan)
Il sistema più avanzato non sceglie un template generico, ma identifica il segnale di dolore più forte e lo usa come angolo di pitch. La personalizzazione è narrativa, non solo di variabili.

### 4. Deliverability come fondamenta (Smartlead, Instantly)
La qualità dell'outreach è inutile se le email finiscono in spam. Il warmup progressivo, SPF/DKIM/DMARC, la rotazione multi-sender, e il timing intelligente non sono optional.

### 5. Reply classification con LLM cheap (Apollo, Instantly)
Tutti usano un modello leggero (Haiku o equivalente) per classificare le risposte per intento. È una task binaria/multi-class, non richiede reasoning profondo.

### 6. CRM come memoria persistente (HubSpot Breeze)
I migliori sistemi usano il database come fonte di verità e memoria dell'agente. Non file temporanei, non session state: tutto scritto su DB con timestamp.

### 7. Approval gate umano (pattern assente nei tool enterprise)
Nessuno dei tool analizzati offre un approval gate granulare per messaggio. Questa è una **opportunità differenziante**: per un freelancer italiano che cura il brand personale, l'approval gate è la feature più importante.

### 8. Tool over skills (11x, Manus)
Gli agenti più affidabili hanno tool Python specifici invece di skill generiche nei prompt. Il reasoning dell'LLM si occupa della logica; i tool si occupano dell'esecuzione.

---

## Agente di riferimento scelto: 11x.ai (Alice)

### Motivazione
11x è l'unico tra i 10 analizzati che:
1. Ha iterato su 3 architetture diverse (ReAct → workflow → multi-agent) e ha scelto il multi-agent gerarchico con LangGraph — esattamente ciò che vogliamo usare
2. Ha pubblicato dettagli tecnici sufficienti per replicarne i principi (case study ZenML)
3. Dimostra che l'architettura scala da 0 a 2M+ lead con lo stesso pattern
4. Usa "tools over skills" come filosofia esplicita — facile da implementare in Python

Clay è il secondo riferimento per la fase di enrichment (pattern waterfall, Claygent come ispirazione per il Researcher Agent).

Artisan è il riferimento per la personalizzazione (signal-based pitch selection).

---

## Architettura del nostro agente — adattamento per freelancer italiano

### Principi di adattamento
- **Qualità > quantità**: 20 email iper-personalizzate al giorno, non 200 generiche
- **Approval gate obbligatorio nella v1**: niente invio autonomo senza OK umano
- **Fonti italiane native**: Google Maps Places API, Pagine Gialle, CCIAA — non Apollo/ZoomInfo
- **GDPR by design**: base giuridica documentata per ogni invio, opt-out facile
- **Costo zero / low-cost**: solo API pay-per-use, nessun SaaS mensile da $999+

### Schema architetturale scelto

```
                    ┌─────────────────────┐
                    │    Orchestrator      │  ← LangGraph StateMachine
                    │  (LangGraph state)  │     gestisce il flow globale
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                       ▼
┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Scout Agent  │    │ Researcher Agent │    │  Writer Agent   │
│ (trova ICP)  │    │ (enrich + pain   │    │ (personalizza   │
│              │    │  points)         │    │  messaggio)     │
└──────────────┘    └──────────────────┘    └─────────────────┘
                               │                       │
                               ▼                       ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │ Qualifier Agent  │    │  Sender Agent   │
                    │ (score 0-100)    │    │  + Tracker      │
                    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Reply Handler  │
                                               │  + Follow-up    │
                                               └─────────────────┘
```

**[UMANO NEL LOOP]** tra Writer e Sender: Streamlit dashboard con approval gate.

### Stack tecnologico confermato dalla research

| Componente | Scelta | Motivazione |
|---|---|---|
| Agent framework | LangGraph | Usato da 11x, state machine espliciti, ottimo per workflow con retry |
| LLM reasoning | claude-sonnet-4-5 | Migliore per writing italiano, scoring, reasoning |
| LLM cheap | claude-haiku-4-5 | Classificazione reply, check anti-spam, task binari |
| Email sending | Resend | Deliverability, webhook reply, pricing flat |
| Database | PostgreSQL + pgvector | CRM nativo + embeddings (ispirato a HubSpot Breeze) |
| ORM | SQLModel | Type-safe, compatibile con FastAPI/Pydantic |
| Enrichment | Playwright + Google Places API | Fonti italiane native (no Apollo/ZoomInfo) |
| Dashboard | Streamlit | Rapido da implementare, sufficiente per v1 |
| Tracing | LangSmith | Gratis per uso personale, ottimo per debug agent |
| Scheduling | APScheduler | Semplice, non richiede infrastruttura Temporal |
| Webhook | FastAPI | Leggerissimo per endpoint Resend webhook |

### Sourcing fonti italiane (non presente in nessun tool analizzato)

Questo è il **vantaggio competitivo principale** del nostro agente: accesso a fonti di dati italiane che nessun tool US gestisce.

```
Fonte primaria:    Google Places API (gratis fino a 17.000 chiamate/mese)
                   → Cerca per categoria + regione + dimensione
Fonte secondaria:  Pagine Gialle scraping (Playwright, rate-limit rispettoso)
                   → Copertura PMI locali non presenti su Google
Fonte terziaria:   Registro Imprese / OpenCorporates IT
                   → P.IVA, anno fondazione, settore ATECO
Signal di dolore:  Google Reviews scraping + Indeed/InfoJobs annunci
                   → Conferma dei pain point in modo oggettivo
```

### Agent di riferimento per ogni modulo

| Modulo | Ispirazione principale | Cosa prendere |
|---|---|---|
| Scout Agent | Clay (sourcing) | Waterfall multi-source, deduplication |
| Researcher Agent | Artisan Ava + Claygent | Signal mining, web navigation, pain points |
| Qualifier Agent | 11x Alice | Score 0-100 con reasoning testuale esplicito |
| Writer Agent | Artisan Ava | Signal-based pitch selection, tono italiano |
| Sender Agent | Smartlead + Instantly | Warmup, timing, multi-sender, SPF/DKIM |
| Reply Handler | Apollo + Instantly | Haiku classification, 5 intenti, fast response |
| Dashboard | HubSpot Breeze (concetto) | CRM context, approval gate, funnel view |

### Innovazioni rispetto ai tool analizzati

1. **Approval gate granulare per messaggio** — nessun tool lo offre, è la nostra killer feature per brand personale
2. **Sourcing da fonti italiane native** — vantaggio competitivo insuperabile vs tool US
3. **GDPR by design** — base giuridica per ogni invio, opt-out automatico, retention documentata
4. **Feedback loop Writer Agent** — le email rifiutate al gate tornano come few-shot examples negativi
5. **Kill switch CLI** — `adh stop-all` ferma tutto istantaneamente, nessun tool competitor lo ha
6. **Scoring trasparente** — il reasoning testuale del Qualifier Agent è visibile nel dashboard
