# Smartlead AI — Deliverability + AI Personalization

## Cosa fa concretamente

Smartlead è una piattaforma per cold email outbound focalizzata su due pilastri: **deliverability** (email che arrivano in inbox, non spam) e **personalizzazione AI** (messaggi che sembrano scritti da un umano). Gestisce il warming progressivo delle caselle email, la rotazione multi-sender, la classificazione automatica delle risposte per intento, e ha un'integrazione diretta con ChatGPT API per generazione contenuto. Dati dichiarati: 85%+ inbox placement rate, utenti che inviano 2.1M+ email con questo stack.

## Architettura inferita

**Infrastruttura email + AI layer** — non è un agente autonomo, è uno strumento di esecuzione con AI embedded.

```
Warm-up Engine
├── Simula aperture/click/reply umane su rete privata
├── Reputation building progressivo per dominio
└── SPF/DKIM/DMARC checker automatico

Campaign Engine
├── Multi-sender rotation (infiniti mailbox per piano)
├── Dynamic IP rotation
├── ESP matching dinamico (sceglie il provider email ottimale)
└── Timing intelligente (finestra oraria configurabile)

AI Personalization Layer
├── Dynamic variables (nome, azienda, settore, ruolo)
├── AI opening lines personalizzate
├── ChatGPT API integration per body generation
└── A/B test automatici su subject + body

Reply Handler
├── Classificazione intento: interested / not interested / OOO / unsubscribe
├── Unibox: tutti i canali in un'unica inbox
└── Auto-reply rules configurabili
```

- **LLM**: ChatGPT API (integrazione diretta), non usa modelli propri
- **Memoria**: stateless per campaign; storico reply per classificazione
- **Scaling**: illimitati mailbox per account — ottimo per agenzie

## Punti di forza

- **Deliverability best-in-class**: sistema di warmup più robusto del mercato
- **Multi-sender rotation**: distribuisce il rischio su N domini
- **Classificazione reply automatica** — la killer feature per automation B2B
- **Unibox centralizzata** per gestire risposte da tutti i canali
- **API aperta** per integrare qualsiasi LLM

## Limiti / cosa NON fa bene

- **Non fa sourcing né enrichment**: devi portare i tuoi lead
- **Non è un agente autonomo**: nessuna logica di decisione, solo esecuzione
- Personalizzazione AI superficiale (variabili dinamiche + opening line, non narrative complesse)
- UI non intuitiva per utenti non tecnici
- Pricing cresce rapidamente con i volumi

## Cosa rubare per il nostro progetto

1. **Pattern warmup progressivo** → documentare e implementare via Resend con incremento graduale (5→10→20→30 email/giorno nell'arco di 4 settimane)
2. **Classificazione reply per intento** → il nostro Reply Handler usa Haiku esattamente per questo (interested/not_now/not_interested/unsubscribe/ooo/question)
3. **Multi-sender strategy** → documentare nel README la strategia dominio dedicato outreach + warming
4. **Timing intelligente** → invio distribuito random in finestra 9:00-18:00 lun-gio come da spec
5. **SPF/DKIM/DMARC come requirement** → non opzionali, obbligatori nella Fase 2 setup
