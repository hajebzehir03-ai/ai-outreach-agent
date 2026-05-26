# Auto-fix Patterns

Pattern ricorrenti osservati durante l'audit ADH v0.1.1 → base per costruire un bot auto-fix futuro.

## Pattern 1 — Import patologico da mypy.state
- **Detect**: `from mypy.state import state` (o qualunque `from mypy.*`) in file di adh/ runtime
- **Rule**: mypy è dev-only; ogni import da `mypy.*` in production code è codice morto che crasha in ambienti senza mypy installato
- **Fix**: rimuovere l'import senza altre modifiche (la variabile `state` nel file è tipicamente il parametro funzione, non quello di mypy)

## Pattern 2 — datetime.utcnow() deprecato
- **Detect**: `datetime.utcnow()` ovunque nel codebase
- **Rule**: deprecato in Python 3.12+, in Python 3.13 sarà rimosso
- **Fix**: sostituire con `datetime.now(UTC)`, importare `UTC` da `datetime` (Python 3.11+)
- **Edge case**: in `Field(default_factory=...)` usare `lambda: datetime.now(UTC)` perché `datetime.now` richiede argomento

## Pattern 3 — asyncio.get_event_loop().run_until_complete()
- **Detect**: `asyncio.get_event_loop().run_until_complete(coro)` in qualunque file
- **Rule**: pattern deprecato in Python 3.10+, fa RuntimeError in contesti con loop già attivo (FastAPI, Streamlit, pytest-asyncio)
- **Fix**: convertire la funzione caller in `async def`, usare `await coro` direttamente

## Pattern 4 — Coroutine never awaited
- **Detect**: warning runtime `RuntimeWarning: coroutine 'X' was never awaited`
- **Rule**: funzione async chiamata senza `await` o senza `asyncio.create_task`
- **Fix**: aggiungere `await` se la funzione caller è async; se non lo è, convertirla o usare `asyncio.run` (mai in handler webhook)

## Pattern 5 — Enum incompleto vs produttori
- **Detect**: enum X usato come tipo di campo persistito, ma codice che produce valori non presenti nell'enum
- **Rule**: SQLModel/Pydantic solleva ValueError silente o crash su save
- **Fix**: completare l'enum + aggiungere fallback `try/except ValueError: return ENUM.other`

## Pattern 6 — Blind exception catch in test
- **Detect**: `with pytest.raises(Exception):`
- **Rule**: cattura troppo larga, nasconde bug genuini (es. TypeError per parametri sbagliati passa il test invece di fallire)
- **Fix**: specificare l'eccezione attesa (`pytest.raises(ValueError)`, `pytest.raises(httpx.TimeoutException)`, ecc.)

## Pattern 7 — _in_region match senza word boundary
- **Detect**: ricerca substring di toponimi/keyword (`if "Torino" in address`)
- **Rule**: matcha sottostringhe accidentali ("Torino" matcha "Bertorino")
- **Fix**: usare `re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)`

## Pattern 8 — Webhook handler senza try/except globale
- **Detect**: handler FastAPI/Flask di webhook esterno senza try/except che ritorni 200
- **Rule**: payload mal formato → eccezione → HTTP 500 → provider retry storm
- **Fix**: wrap dell'intero handler in try/except con log dell'eccezione e ritorno HTTP 200 sempre

## Pattern 9 — Unused variable in test
- **Detect**: variabile locale assegnata e mai usata in test
- **Rule**: residuo di refactoring, code smell
- **Fix**: rimuovere se inutile, usare in una assertion se serviva a documentare uno stato

## Pattern 10 — Whitespace in blank lines
- **Detect**: ruff W293
- **Rule**: code smell, fix automatico
- **Fix**: rimuovere gli spazi (ruff --fix lo fa, ma alcuni editor li reintroducono — configurare .editorconfig)
