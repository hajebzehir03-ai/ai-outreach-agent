# Artisan AI — Ava (AI SDR)

## Cosa fa concretamente

Artisan è il concorrente diretto di 11x. **Ava** è il loro AI SDR: trova prospect, fa enrichment, scrive email personalizzate e gestisce le sequenze. Database integrato di 300M+ contatti. Canali: email + LinkedIn (nessuna capacità phone, a differenza di 11x/Jordan). Focus sulla qualità della personalizzazione: Ava mina segnali personali (post LinkedIn, job change, funding news, news aziendali) per scegliere l'angolo di pitch più rilevante. Pricing più accessibile di 11x: ~$999/mese vs $5.000+/mese.

## Architettura inferita

**Multi-signal personalization engine + sequencing** — architettura centrata sul data mining di segnali personali.

```
Lead Sourcing
├── Database interno: 300M+ contatti
└── Filtri: settore, ruolo, dimensione, geo

Signal Mining (differenziante Ava)
├── LinkedIn posts recenti
├── Job changes (Ava = trigger di cambio ruolo)
├── Funding news (Crunchbase / Pitchbook signals)
├── Company news (press release, eventi)
└── Ranking segnali per richness → sceglie il più forte

Personalization Engine
├── Seleziona angolo dal segnale più ricco
├── Genera opening line da segnale specifico
└── Adatta tono e CTA al contesto

Sequence Engine
├── Email multi-step
├── LinkedIn connection + message
└── No phone/SMS

CRM integrations: HubSpot, Salesforce
```

- **LLM**: non dichiarato, probabilmente GPT-4 con fine-tuning su dataset outbound
- **Segnali**: approccio più sofisticato di 11x sulla qualità della personalizzazione per segnale
- **No phone**: gap competitivo vs 11x (Jordan)

## Punti di forza

- **Signal-based personalization** — il sistema più avanzato per scegliere l'angolo giusto basandosi su segnali reali
- **Pricing 5x inferiore a 11x** — $999/mese rende Artisan più accessibile (anche se ancora fuori range freelancer)
- **300M database** — buona copertura, anche se ancora US-centric
- **LinkedIn nativo** — gestisce connessioni + messaggi senza tool esterni
- **Transparenza del processo**: l'utente vede perché Ava ha scelto quel segnale

## Limiti / cosa NON fa bene

- Nessuna capacità voice/phone
- Database carente su PMI italiane (struttura dati pensata per mercato anglosassone)
- Approval gate limitato — controllo umano granulare assente
- Nessun warmup email interno (si affida a strumenti terzi)
- Non adatto per singolo freelancer (minimo contrattuale alto)

## Cosa rubare per il nostro progetto

1. **Signal-based pitch angle selection** → il Writer Agent deve scegliere l'angolo di pitch dal segnale più forte trovato dal Researcher (non angolo generico sempre uguale)
2. **Ranking dei segnali** → il Qualifier Agent assegna peso a ogni signal di dolore trovato; il Writer usa il segnale con peso più alto
3. **Transparenza dell'angolo scelto** → nel dashboard di approval, mostrare quale segnale ha motivato la scelta del pitch
4. **LinkedIn come canale secondario** → nella v0.2, integrare LinkedIn via Computer Use per follow-up su lead non rispondenti
