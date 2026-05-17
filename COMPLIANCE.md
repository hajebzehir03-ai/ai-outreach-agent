# COMPLIANCE.md — DPIA-lite e base giuridica GDPR

## Base giuridica

Il trattamento dei dati personali in questo sistema si basa su **legittimo interesse** (GDPR art. 6.1.f) per le seguenti ragioni:

- Le comunicazioni sono inviate esclusivamente a **indirizzi email aziendali pubblici** (info@, contatti@, nome.cognome@dominio-aziendale.it)
- Il contenuto è **rilevante per l'attività professionale** del destinatario (servizi B2B)
- È ragionevolmente prevedibile che un'azienda possa ricevere proposte commerciali pertinenti
- Il **test di bilanciamento** è soddisfatto: il trattamento non prevale sui diritti fondamentali del destinatario

**Non è lecito e il sistema non tratterà mai:**
- Email personali (Gmail, Libero, Yahoo, Hotmail)
- Dati sensibili (salute, politica, religione)
- Dati di persone fisiche al di fuori del contesto professionale

---

## Dati trattati

| Categoria | Dato | Base giuridica | Retention |
|---|---|---|---|
| Azienda | Nome, P.IVA, settore, regione | Legittimo interesse | 12 mesi da ultimo contatto |
| Contatto aziendale | Email aziendale, nome, ruolo | Legittimo interesse | 12 mesi |
| Comunicazioni | Testo email inviata, subject | Legittimo interesse | 24 mesi |
| Risposte | Testo risposta, intento classificato | Legittimo interesse | 24 mesi |
| Opt-out | Email, data richiesta | Obbligo legale | Permanente (blacklist) |

---

## Misure di sicurezza

- Dati archiviati su PostgreSQL locale o cloud privato (non condiviso)
- API key gestite via `.env` (mai committate su git)
- Accesso al dashboard protetto da autenticazione locale
- Backup cifrati

---

## Diritti degli interessati

Ogni email include la frase:
> "Se preferisci non ricevere ulteriori email, rispondi STOP e ti rimuoverò immediatamente."

Il sistema gestisce automaticamente l'opt-out:
1. Reply classificata come `unsubscribe` → blacklist permanente in `companies.blacklisted_until = NULL`
2. Conferma di rimozione inviata entro 24h (manuale nella v1)
3. Log in `processing_log` con `action = "unsubscribe_permanent"`

---

## Trasparenza della fonte

Ogni email include una clausola del tipo:
> "Ti scrivo dopo aver visto il vostro profilo su Google / il vostro annuncio su Indeed / il vostro sito aziendale."

Questo soddisfa il requisito di trasparenza del GDPR art. 13/14.

---

## Kill switch

Il comando `adh stop-all --reason "..."` blocca immediatamente tutti gli invii pianificati impostando `KILL_SWITCH=true` nell'ambiente. Nessun invio avviene se questo flag è attivo.

---

## Retention e cancellazione

- Aziende con status `not_interested` vengono anonimizzate dopo 12 mesi (comando: `adh gdpr-purge`)
- I dati vengono anonimizzati (non cancellati) per mantenere l'integrità referenziale del DB
- L'anonimizzazione rimuove: email, telefono, nome decisore, email decisore

---

## Registro dei trattamenti

La tabella `processing_log` traccia ogni operazione con:
- `company_id`, `message_id`
- `action` (sourced, enriched, contacted, unsubscribed, purged)
- `legal_basis` (default: `legittimo_interesse_gdpr_6_1_f`)
- `data_processed` (lista dei campi trattati)
- `performed_at`, `retention_until`

---

## Note sul dominio di outreach

Usare un **dominio dedicato** per il cold outreach (es. `zehir-automation.it`) separato dal dominio principale del business. Questo protegge la reputazione del dominio principale in caso di segnalazioni spam.

Il dominio di outreach deve avere configurati:
- **SPF**: `v=spf1 include:amazonses.com include:resend.com ~all`
- **DKIM**: chiave pubblica pubblicata nel DNS (fornita da Resend)
- **DMARC**: `v=DMARC1; p=quarantine; rua=mailto:dmarc@tuodominio.it`
