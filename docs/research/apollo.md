# Apollo.io — AI Features + Sequencing

## Cosa fa concretamente

Apollo è la piattaforma all-in-one per outbound B2B: database di 265M+ contatti, sequencing multi-step (email + call + LinkedIn + custom), e AI layer per personalizzazione e automazione. L'AI Assistant è il componente più rilevante: genera email personalizzate addestrato su dataset reali di campagne outbound, integra variabili dinamiche (azienda, titolo, attività recente), e supporta l'intero workflow dalla list building all'analytics. Il sequencing combina step automatizzati e task manuali in una UI visuale.

## Architettura inferita

**Database-first + AI layer sovrapposto** — Apollo è fondamentalmente un database (265M contatti) con AI embedded nel workflow, non un agente autonomo.

```
Lead Database
├── 265M+ contatti verificati
├── Filtri avanzati: technografia, segnali intento, funding
└── Apollo-native enrichment

AI Assistant (powered by Claude 3.5 Haiku)
├── Email generation da contesto prospect
├── Subject line optimization
├── Personalization variables injection
└── Sequence step suggestion

Sequence Engine
├── Multi-step: email automatica + call task + LinkedIn + custom
├── Visual sequence builder
├── A/B test su subject e body
└── Timing intelligente

Agentic Features (2025)
├── Pre-meeting insights (AI summary)
├── Auto follow-up post-call
└── CRM auto-population da recording
```

- **LLM**: Claude 3.5 Haiku per AI writing (dichiarato), probabilmente GPT-4 per task più complessi
- **Memoria**: storico interazioni per prospect nel CRM nativo; no memoria cross-campaign
- **Integrazione**: Salesforce, HubSpot, Outreach, Salesloft, e 200+ via Zapier

## Punti di forza

- **Database enorme** (265M contatti) — il migliore sul mercato per qualità/prezzo
- **Tutto in uno**: sourcing + sequencing + analytics in una piattaforma
- **Claude 3.5 Haiku** per writing — buona qualità per personalizzazione standard
- **Piano gratuito** con 50 email/mese — ideale per testare
- **Agentic features** in crescita rapida (2025 roadmap aggressiva)

## Limiti / cosa NON fa bene

- Database US-centric — copertura PMI italiane molto limitata (dati spesso mancanti o errati)
- AI writing di qualità media — personalizzazione basata su variabili semplici, non narrative
- Nessun approval gate umano granulare
- Reply handler assente — gestione risposte solo manuale
- Costo cresce rapidamente con i contatti (piano pro $99+/mese per 2.000 email)

## Cosa rubare per il nostro progetto

1. **Claude 3.5 Haiku per classificazione cheap** → conferma la scelta di Haiku per task binari (positivo/negativo, interessato/non interessato)
2. **Visual sequence builder** → il Streamlit dashboard deve visualizzare la sequenza in modo chiaro
3. **Multi-step con mix automatico/manuale** → alcuni step (risposta a domanda specifica) devono essere task manuali passati a me
4. **Pre-meeting insights pattern** → quando un lead diventa "caldo", generare automaticamente un brief per la chiamata
