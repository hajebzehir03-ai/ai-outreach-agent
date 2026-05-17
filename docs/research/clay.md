# Clay.com — Enrichment + Claygent + Workflow

## Cosa fa concretamente

Clay è una piattaforma GTM (Go-To-Market) che combina enrichment dati e AI research. Il cuore è il sistema **Waterfall Enrichment**: sequenza di provider dati (Hunter, Apollo, Clearbit, ecc.) consultati in cascata fino a completare il profilo prospect. **Claygent** è l'AI research assistant che va oltre i database statici: naviga siti web, legge pagine, estrae insights che i database tradizionali non catturano. Gli output alimentano workflow di outreach personalizzato via n8n, Make o integrazioni native (Salesforce, HubSpot, Lemlist, ecc.).

## Architettura inferita

**Tool-augmented single agent + waterfall pipeline** — non è un sistema multi-agent puro, ma un orchestratore di tool con AI al centro.

```
Input (CSV / CRM / source list)
    ↓
Waterfall Enrichment
├── Provider 1 (Hunter)   ← email
├── Provider 2 (Apollo)   ← firmographics
├── Provider 3 (Clearbit) ← tech stack
└── Provider N ...
    ↓
Claygent (AI Research Agent)
├── Naviga sito web aziendale
├── Legge LinkedIn pubblico
├── Estrae segnali di dolore
└── Genera testo personalizzato
    ↓
Output → CRM / Email tool / Google Sheets
```

- **Modelli**: GPT-5 (recente migrazione) + accesso MCP a Salesforce, Gong, Google Docs
- **Memoria**: stateless per sessione, i dati vengono salvati nelle tabelle Clay
- **Versioning agenti**: gli utenti possono creare e versionare più Claygent per use case diversi
- **No multi-agent nativo**: l'orchestrazione tra agenti richiede costruzione manuale via workflow

## Punti di forza

- **Waterfall enrichment** — il miglior sistema di completamento dati del mercato (costo ottimizzato, massima copertura)
- Flessibilità enorme: si integra con qualsiasi tool via HTTP
- Claygent può fare ricerche molto specifiche (es. "trova il nome del responsabile HR di questa azienda")
- Community enorme + library di template predefiniti
- Prezzi accessibili per utenti individuali ($149+/mese piano base)

## Limiti / cosa NON fa bene

- **Non è un agente autonomo end-to-end**: richiede configurazione manuale di ogni workflow
- Nessuna gestione reply, follow-up, o tracking risposte
- Claygent è solo enrichment + scrittura — non gestisce invio email, warming, ecc.
- Curva di apprendimento alta per utenti non tecnici
- Dati su mercato italiano (PMI, Registro Imprese) limitati — ottimizzato per US

## Cosa rubare per il nostro progetto

1. **Pattern waterfall per enrichment** → nel Researcher Agent, consultare più fonti in cascata (Google Places → sito web → LinkedIn → annunci)
2. **Claygent come ispirazione per il Researcher Agent** → un agent che naviga siti web e estrae segnali di dolore invece di consultare solo database
3. **Separazione enrichment da messaging** → i dati vengono prima raccolti e archiviati, poi usati per la personalizzazione (non tutto in un unico step)
4. **Versioning dei template** → il Writer Agent deve supportare varianti di prompt testabili
