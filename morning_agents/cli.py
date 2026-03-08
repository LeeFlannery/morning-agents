import typer

app = typer.Typer()


@app.command()
def main():
    """Morning Agents - coming soon."""
    typer.echo("morning-agents: nothing to run yet. Session 2 builds the first agent.")


if __name__ == "__main__":
    app()
