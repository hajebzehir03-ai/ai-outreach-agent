# HubSpot Breeze AI — CRM-Native Agent

## Cosa fa concretamente

Breeze è il layer AI di HubSpot introdotto a INBOUND 2024 e significativamente espanso nel 2025. Non è un prodotto standalone ma AI embedded direttamente nel CRM. I quattro agenti core: **Customer Agent** (supporto clienti / first-line concierge), **Prospecting Agent** (BDR AI 24/7 che monitora segnali di acquisto, fa research, personalizza outreach), **Content Agent** (genera contenuto marketing), e **Report Agent** (analytics). Il Prospecting Agent è il più rilevante per il nostro use case.

## Architettura inferita

**CRM-native agent con Breeze Context Layer** — la differenza fondamentale rispetto ai competitor è l'accesso a dati strutturati del CRM (storico contatti, email, chiamate, deal) come contesto per ogni decisione.

```
Breeze Context Layer
├── Structured data (CRM: contacts, deals, companies)
├── Unstructured data (email, call recordings, support tickets)
├── External data (Breeze Intelligence: enrichment terze parti)
└── Role-aware context (cosa sa fare questo utente nel CRM?)

Prospecting Agent
├── Monitora prospect per buying signals
├── Research account target
├── Personalizza outreach usando contesto CRM
└── Engage al momento ottimale

Agent Loop
├── Trigger (segnale di acquisto / schedule)
├── Research (usa Breeze Context Layer)
├── Write (personalizza da contesto CRM)
└── Send + Track

LLM: GPT-5 (marketplace agents, gen 2026), GPT-4.x (core agents)
MCP connections: Google Workspace, Slack, Salesforce, Gong
```

## Punti di forza

- **CRM context nativo** — nessun competitor ha questo: l'agente sa già tutto del prospect perché vive nel CRM
- **Breeze Intelligence** — enrichment dati integrato senza configurazione
- **Marketplace di agenti** — ecosistema in crescita di agent pre-costruiti
- **Memory**: il CRM è di fatto la memoria persistente dell'agente
- Adatto per chi ha già HubSpot — zero friction di adoption

## Limiti / cosa NON fa bene

- **Lock-in totale in HubSpot** — inutile senza abbonamento HubSpot ($800+/mese enterprise)
- Prospecting Agent non fa sourcing da fonti italiane
- Personalizzazione limitata ai dati nel CRM — se il CRM è vuoto, l'agente è cieco
- Nessun controllo sui prompt o sull'architettura interna
- Non adatto per freelancer (pricing enterprise)

## Cosa rubare per il nostro progetto

1. **CRM come memoria persistente** → PostgreSQL con SQLModel è il nostro "CRM nativo" — tutti gli agent leggono e scrivono lì, non da file temporanei
2. **Buying signals come trigger** → il Scout Agent deve cercare segnali attivi (annunci di lavoro recenti, news, recensioni negative recenti) non solo profili statici
3. **Role-aware context** → ogni prompt deve includere il contesto rilevante del prospect estratto dal DB, non dati generici
4. **Unstructured data enrichment** → il Researcher Agent salva testo grezzo (recensioni, paragrafi sito web) che diventa embedding ricercabile via pgvector
