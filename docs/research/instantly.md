# Instantly.ai — Outbound Infrastructure + AI Features

## Cosa fa concretamente

Instantly è l'infrastruttura outbound per eccellenza: gestisce il ciclo completo di cold email con focus su deliverability e volume. Punti salienti: rete di warmup da 4.2M+ account, invio illimitato per piano, SuperSearch con 450M+ lead verificati, e AI Copilot per creazione campagne + AI Reply Agent per gestione automatica risposte entro 5 minuti. Il modello di business è flat-fee per unlimited accounts — ideale per agenzie che gestiscono N domini.

## Architettura inferita

**Infrastruttura distribuita + AI layer sovrapposto** — molto simile a Smartlead, ma con database di lead proprio e AI Reply Agent più avanzato.

```
Lead Database (SuperSearch)
├── 450M+ contatti verificati
├── Filtri: settore, ruolo, dimensione, technografia
└── Verifica email in real-time

Deliverability Engine
├── Warmup network: 4.2M+ account reali
├── Unlimited sending accounts (flat fee)
├── SISR (Sender Infrastructure Score Rating)
└── Private deliverability network

Campaign Engine
├── AI Copilot: genera campagna da prompt
├── Template adaptativi: subject, opener, body
├── Reply rate ottimizzazione: +18% vs controllo
└── Sequence multi-step configurabile

AI Reply Agent
├── Classifica risposte in <5 minuti
├── Auto-risponde secondo regole configurabili
└── Handoff umano per lead caldi

Unibox
└── Centralizza tutte le risposte da tutti i domini
```

- **LLM**: non dichiarato, probabilmente GPT-4 con fine-tuning su dataset di campagne outbound
- **AI Copilot**: genera intera campagna da un prompt testuale
- **Memoria**: storico campagne per ottimizzazione A/B; nessuna memoria prospect individuale

## Punti di forza

- **Flat-fee unlimited**: gestisci 100 domini senza pagare per account
- **Rete warmup enorme** — 4.2M+ account, deliverability industry-leading
- **SuperSearch integrato** — lead + invio nello stesso tool
- **AI Reply Agent** che risponde entro 5 minuti — differenziante significativo
- **Pricing aggressivo** per il volume che offre

## Limiti / cosa NON fa bene

- SuperSearch è focalizzato US/EN — scarsissimi dati su PMI italiane
- AI Copilot genera campagne generiche — personalizzazione superficiale
- Nessun sourcing da fonti italiane (Google Maps, Pagine Gialle, CCIAA)
- Non fa enrichment profondo (solo variabili di base)
- Reply Agent autonomo senza approval gate — rischio per brand personale

## Cosa rubare per il nostro progetto

1. **AI Reply Agent pattern** → il nostro Reply Handler deve rispondere in tempo reale via webhook (non polling batch)
2. **Flat-fee infrastructure thinking** → scegliere Resend con pricing flat per non scalare i costi con i volumi
3. **Unlimited sending accounts** → strategia multi-dominio documentata (dominio principale vs dominio outreach dedicato)
4. **5-minute reply SLA** → il webhook Resend → FastAPI deve avere latency <1 min in risposta
