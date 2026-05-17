# Lindy.ai — Agent Builder + Lead Generation Templates

## Cosa fa concretamente

Lindy è una piattaforma no-code per costruire AI agent. Il concetto chiave è "vibe coding" degli agenti: descrivi cosa vuoi fare in linguaggio naturale e Lindy genera l'agente in pochi minuti. Per lead generation offre template predefiniti: Lead Generator (trova prospect via criteri settore/ruolo/location), Lead Generation & Evaluation (trova + score su Google Sheet), Email Responder, Support Slackbot. Il modello di default è Claude Sonnet 4 per bilanciare velocità e qualità.

## Architettura inferita

**Agent-as-a-service con memoria persistente + network di agenti ("Societies")**

```
Lindy Agent
├── Memory (persistente cross-sessione)
│   ├── Short-term: contesto della task corrente
│   └── Long-term: storico interazioni per continuità
├── Tools (configurabili: email, calendar, CRM, API)
└── Trigger (email ricevuta / schedule / webhook / manuale)

Societies (multi-agent)
├── Agent A: trova lead
├── Agent B: enrichment
└── Agent C: write + send
    └── condivisione memoria tra agenti
```

- **LLM**: Claude Sonnet 4 (default), altri disponibili
- **Memoria**: persistente long-term — un agente "ricorda" l'ultima interazione con un lead
- **Trigger**: email, schedule, webhook, manuale
- **Tool**: email nativa, Google Calendar, HubSpot, Slack, API HTTP generica

## Punti di forza

- **Onboarding immediato**: da zero a agente funzionante in minuti, nessun codice
- **Societies**: collaborazione tra più agenti con memoria condivisa — ottimo per workflow sequenziali
- **Memoria persistente**: il concetto di "agente che ricorda" è la killer feature per outreach continuato
- **Pricing accessibile**: piani da $49/mese per uso individuale
- **Template predefiniti** per lead gen pronti all'uso

## Limiti / cosa NON fa bene

- Personalizzazione profonda limitata: il no-code impone vincoli quando serve logica complessa
- Nessuna deliverability email nativa (si affida a SMTP/Resend esterni)
- Dati di sourcing dipendono da PeopleDataLabs (US-centric, scarso per PMI italiane)
- Il warming delle email non è gestito
- Control granulare sulle prompt difficile da mantenere a lungo termine

## Cosa rubare per il nostro progetto

1. **Pattern memoria persistente** → usare pgvector per embeddings delle aziende e storico interazioni per agent che "ricordano" ogni lead
2. **Societies → multi-agent con shared context** → il nostro Orchestrator LangGraph passa lo stato condiviso tra tutti i sub-agent invece di passarlo via file
3. **Trigger multipli** → il Reply Handler deve rispondere a eventi (webhook reply) non solo a schedule
4. **Approccio "agent-first"**: ogni funzionalità è un agente con responsabilità singola, non un monolite
