# 11x.ai — Alice & Jordan (AI SDR di riferimento)

## Cosa fa concretamente

11x.ai è la piattaforma di AI SDR più avanzata sul mercato. **Alice** è il digital worker per outbound sales: individua lead, li arricchisce, scrive email personalizzate e gestisce le sequenze di follow-up. **Jordan** è un agente voice-enabled (30+ lingue) per chiamate inbound e outbound. Il sistema dichiara ~2M lead sourced, ~3M messaggi inviati, ~21.000 reply generate con un reply rate intorno al 2% (pari agli SDR umani).

I canali coperti sono: email, telefono, SMS, WhatsApp, LinkedIn + integrazione CRM (Salesforce).

## Architettura inferita

**Multi-agent gerarchico con supervisor node** — la scelta finale dopo aver abbandonato sia il pattern ReAct (troppo imprevedibile) sia il workflow rigido (troppo infllessibile).

```
Supervisor Agent
├── Researcher Agent       ← deep lead analysis
├── Positioning Agent      ← sceglie angolo di pitch
├── LinkedIn Writer Agent  ← messaggi LinkedIn
└── Email Writer Agent     ← email personalizzate
(Audience Module)          ← sourcing + qualification (separato)
```

- **Orchestrazione**: LangGraph (state machine espliciti)
- **Filosofia**: "tools over skills" — ogni sub-agent ha tool specifici (DB, API) invece di skill embedded in prompt
- **Navigazione non lineare**: l'utente può saltare tra step della campagna senza seguire un flusso rigido
- **Auto-learning**: il sistema raffina le strategie di engagement nel tempo basandosi sulle interazioni reali
- **LLM**: non dichiarato pubblicamente, probabilmente mix di GPT-4/Claude

## Punti di forza

- Architettura multi-agent matura con anni di iterazione (3 architetture provate prima)
- Dati di prospect aggregati da 21+ provider con verifica al momento dell'invio (non cache statica)
- Canale voice (Jordan) — differenziante unico nel settore
- Self-optimization delle strategie di messaging nel tempo
- SOC 2 Type II per mercato enterprise

## Limiti / cosa NON fa bene

- Pricing enterprise: $5.000+/month — completamente fuori range per un freelancer
- Black box: l'utente non controlla i prompt né l'architettura
- Nessuna gestione post-outbound (pipeline, onboarding, ecc.)
- Focalizzato su mercato US/EN — personalizzazione per mercato italiano assente
- No approval gate umano granulare per ogni messaggio

## Cosa rubare per il nostro progetto

1. **Pattern supervisor + sub-agent specializzati** → implementare con LangGraph esattamente come Alice
2. **"Tools over skills"** → ogni agent ha tool Python dedicati, non skill generiche nei prompt
3. **Navigazione non lineare** → il dashboard deve permettere di entrare in qualsiasi step del workflow senza ricominciare
4. **Verifica contatti al momento dell'invio** → non affidarsi a dati statici cached
5. **Auto-learning da replies** → il feedback delle risposte torna come few-shot examples al Writer Agent
