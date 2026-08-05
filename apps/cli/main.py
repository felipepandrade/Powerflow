import typer

app = typer.Typer(help="TaskFlow CLI - Ferramenta de linha de comando para operação do TaskFlow.")


@app.command()
def sync(channels: str = typer.Option("mail,chat,calendar", help="Canais a sincronizar")) -> None:
    """Dispara a sincronização de canais de ingestão."""
    typer.echo(f"Sincronizando canais: {channels}...")


@app.command()
def extract() -> None:
    """Executa a extração de sinais de itens de origem pendentes."""
    typer.echo("Executando extração de sinais por LLM...")


@app.command()
def correlate() -> None:
    """Executa o motor de correlação nos sinais pendentes."""
    typer.echo("Executando motor de correlação...")


if __name__ == "__main__":
    app()
