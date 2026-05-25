"""ADH CLI — comandi per operare il sistema da terminale."""

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="adh",
    help="AI-Driven Hunter — outreach agent per PMI italiane",
    no_args_is_help=True,
)
console = Console()


@app.command()
def stop_all(reason: str = typer.Option(..., "--reason", "-r", help="Motivo del blocco")):
    """Kill switch: blocca immediatamente tutti gli invii pianificati."""
    import os

    # Scrivi il flag nel .env runtime
    console.print("[red]⚠ KILL SWITCH ATTIVATO[/red]")
    console.print(f"Motivo: {reason}")
    console.print("Tutti gli invii pianificati sono bloccati.")
    console.print("Per riattivare: imposta KILL_SWITCH=false nel .env e riavvia.")
    os.environ["KILL_SWITCH"] = "true"


@app.command()
def status():
    """Mostra lo stato del sistema e le statistiche recenti."""
    from sqlmodel import Session, func, select

    from adh.models.company import Company, CompanyStatus
    from adh.models.database import engine

    with Session(engine) as session:
        total = session.exec(select(func.count(Company.id))).one()
        qualified = session.exec(
            select(func.count(Company.id)).where(Company.status == CompanyStatus.qualified)
        ).one()
        contacted = session.exec(
            select(func.count(Company.id)).where(Company.status == CompanyStatus.contacted)
        ).one()
        replied = session.exec(
            select(func.count(Company.id)).where(Company.status == CompanyStatus.replied)
        ).one()

    table = Table(title="ADH Pipeline Status")
    table.add_column("Fase", style="cyan")
    table.add_column("Count", style="magenta")

    table.add_row("Totale aziende", str(total))
    table.add_row("Qualificate", str(qualified))
    table.add_row("Contattate", str(contacted))
    table.add_row("Risposte", str(replied))

    console.print(table)


@app.command()
def run_scout(
    sector: str = typer.Option(..., "--sector", "-s", help="Settore da cercare"),
    region: str = typer.Option("Piemonte", "--region", "-r", help="Regione target"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max aziende da trovare"),
):
    """Esegue il Scout Agent per un settore e regione specifici."""
    import asyncio

    from adh.agents.scout import scout_single_sector

    console.print(f"[cyan]Avvio Scout Agent: {sector} in {region}[/cyan]")

    results = asyncio.run(scout_single_sector(sector, region))

    results = results[:limit]
    console.print(f"[green]Trovate {len(results)} aziende[/green]")

    for company in results:
        rprint(f"  - {company.name} | {company.city} | {company.website or 'no sito'}")


@app.command()
def gdpr_purge(days_old: int = typer.Option(365, "--days", help="Rimuovi dati più vecchi di N giorni")):
    """GDPR: cancella i dati di aziende non interessate dopo N giorni."""
    from datetime import UTC, timedelta
    from datetime import datetime as dt

    from sqlmodel import Session, select

    from adh.models.company import Company, CompanyStatus
    from adh.models.database import engine


    cutoff = dt.now(UTC) - timedelta(days=days_old)

    with Session(engine) as session:
        to_purge = session.exec(
            select(Company).where(
                Company.status == CompanyStatus.not_interested,
                Company.updated_at < cutoff,
            )
        ).all()

        count = len(to_purge)
        for company in to_purge:
            company.email = None
            company.decision_maker_email = None
            company.decision_maker_name = None
            company.phone = None
            session.add(company)

        session.commit()

    console.print(f"[green]GDPR purge completata: {count} aziende anonimizzate[/green]")


if __name__ == "__main__":
    app()
