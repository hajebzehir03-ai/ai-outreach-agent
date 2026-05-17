# Claude Computer Use / Operator — Browsing-Based Agent

## Cosa fa concretamente

Claude Computer Use è una feature beta di Anthropic che permette a Claude di controllare un computer come farebbe un umano: guarda screenshot, clicca, scrive, naviga il browser. In contesto di outreach, è stato usato per automatizzare LinkedIn outreach (legge profili, valuta rilevanza, decide se connettere, invia messaggi personalizzati) e per navigare siti senza API (Pagine Gialle, form di contatto, registri pubblici). Claude Operator (OpenAI equivalente) è il concorrente diretto.

## Architettura inferita

**Vision-based action loop** — vede screenshot → decide azione → esegue → vede nuovo screenshot.

```
Screenshot Capture
    ↓
Claude Vision (legge lo stato dello schermo)
    ↓
Reasoning (cosa devo fare per avanzare verso il goal?)
    ↓
Action (click / type / scroll / navigate)
    ↓
Osserva nuovo stato
    ↓ (loop fino a completamento)
Output (testo, file, dati estratti)
```

- **Tool**: `computer_use` tool nell'Anthropic API con tre azioni: `screenshot`, `click`, `type`
- **Modello**: Claude Sonnet/Opus (vision required) — Haiku non supporta computer use
- **Ambiente**: container Docker con browser virtuale (Playwright/Chromium) o desktop reale
- **Costo**: più lento e costoso rispetto ad automazioni code-based, ma resiliente a cambi UI

## Punti di forza

- **No API required**: funziona su qualsiasi sito, anche quelli senza API pubblica (Pagine Gialle, CCIAA, Registro Imprese)
- **Resiliente a cambi UI**: non dipende da selettori CSS fragili
- **Judgement at each step**: Claude valuta ogni situazione invece di seguire script rigidi
- **LinkedIn outreach** senza API ufficiale (LinkedIn non ha API per messaggistica pubblica)
- **Personalizzazione dinamica**: legge il profilo e genera messaggi unici

## Limiti / cosa NON fa bene

- **Lento**: ogni step richiede screenshot + LLM call — 10-50x più lento di Playwright diretto
- **Costoso**: ogni screenshot è un'API call con immagine allegata (token alti)
- **Non scalabile per volumi**: 30 email/giorno è gestibile, 300 no
- **Fragile su CAPTCHA e anti-bot**: i siti riconoscono il pattern automatizzato
- **Non adatto come primary tool**: usare solo come fallback per siti senza API

## Cosa rubare per il nostro progetto

1. **Playwright headless come alternativa leggera** → per lo Scout Agent usare Playwright diretto (più veloce/economico) con Computer Use come fallback solo per siti problematici
2. **Pattern "leggi prima di agire"** → il Researcher Agent deve leggere l'intera pagina prima di estrarre dati, non affidarsi a selettori fragili
3. **Personalizzazione da lettura diretta** → il Writer Agent legge la pagina "about" e le recensioni Google prima di scrivere, come Claude farebbe con Computer Use
4. **Judgement at each step** → ogni agent node deve avere un check esplicito "ha senso continuare?" prima di procedere allo step successivo
