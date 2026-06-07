import json
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from shipmybox.client import ShipMyBoxClient
from shipmybox.exceptions import ShipMyBoxException
from shipmybox.notifications import get_notification_config, get_notifier
from shipmybox.state import load_state, save_state

app = typer.Typer(help="ShipMyBox CLI tool for extracting personal parcels and address info.")
console = Console()

def get_client() -> ShipMyBoxClient:
    return ShipMyBoxClient()

@app.command()
def login(
    email: str = typer.Option(..., prompt=True, help="Your ShipMyBox email address"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Your ShipMyBox password")
):
    """Log in to ShipMyBox and save session."""
    client = get_client()
    try:
        with console.status("[bold green]Logging in..."):
            client.login(email, password)
        console.print("[bold green]✓[/bold green] logged in successfully. Session saved.")
    except ShipMyBoxException as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def info(
    as_json: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Get your shipping address and unique codes."""
    client = get_client()
    try:
        data = client.get_address_and_codes()
        if as_json:
            print(json.dumps(data, indent=2))
        else:
            console.print(Panel.fit(
                f"[bold cyan]Customer ID:[/bold cyan] {data.get('customer_id', 'N/A')}\n"
                f"[bold cyan]Alternative ID:[/bold cyan] {data.get('alternative_id', 'N/A')}\n\n"
                f"[bold yellow]Shipping Address:[/bold yellow]\n{data.get('shipping_address', 'N/A')}\n\n"
                f"[bold yellow]Alternative Address:[/bold yellow]\n{data.get('alternative_address', 'N/A')}",
                title="[bold green]ShipMyBox Info[/bold green]"
            ))
    except ShipMyBoxException as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def parcels(
    as_json: bool = typer.Option(False, "--json", help="Output in JSON format"),
    last: bool = typer.Option(False, "--last", help="Output only the last parcel info")
):
    """List your parcels."""
    client = get_client()
    try:
        parcels = client.get_parcels()
        
        if last and parcels:
            parcels = [parcels[-1]]
            
        if as_json:
            print(json.dumps(parcels, indent=2))
        else:
            if not parcels:
                console.print("[yellow]No parcels found.[/yellow]")
                return

            table = Table(title="My Parcels")
            table.add_column("Number", style="cyan", no_wrap=True)
            table.add_column("Dimensions (LxWxH)", style="magenta")
            table.add_column("Weight (kg)", justify="right", style="green")
            table.add_column("Status", style="blue")
            table.add_column("Price (EUR)", justify="right", style="green")
            table.add_column("Payment", style="yellow")

            for p in parcels:
                dimensions = f"{p.get('length_cm', '')}x{p.get('width_cm', '')}x{p.get('height_cm', '')}"
                table.add_row(
                    p.get("number", "N/A"),
                    dimensions,
                    p.get("weight_kg", "N/A"),
                    p.get("status", "N/A"),
                    p.get("price_eur", "N/A"),
                    p.get("payment_status", "N/A")
                )

            console.print(table)
    except ShipMyBoxException as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def check(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate check and print notifications without sending them or saving state"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print detailed execution logs to stdout")
):
    """Check the status of the last parcel. Notify if status changes or a new parcel arrives."""
    client = get_client()
    try:
        if verbose:
            console.print("[bold blue]Retrieving parcels...[/bold blue]")
        parcels = client.get_parcels()
        
        if not parcels:
            if verbose:
                console.print("[yellow]No parcels found on your account. Exiting.[/yellow]")
            return

        # Last parcel is parcels[-1]
        last_parcel = parcels[-1]
        parcel_num = last_parcel.get("number", "N/A")
        parcel_status = last_parcel.get("status", "N/A")
        
        if verbose:
            console.print(f"Current last parcel: [cyan]{parcel_num}[/cyan] with status: [magenta]{parcel_status}[/magenta]")

        # Load state
        old_state = load_state()
        
        # Determine notifications
        notification_msg = None
        
        if old_state is None:
            # First run behavior: Send notification about the current last parcel
            if verbose:
                console.print("[green]First run detected. Sending initial notification for last parcel.[/green]")
            notification_msg = f"New parcel has appeared!\nNumber: {parcel_num}\nStatus: {parcel_status}"
        else:
            old_num = old_state.get("number")
            old_status = old_state.get("status")
            
            if verbose:
                console.print(f"Loaded previous state: [cyan]{old_num}[/cyan] with status: [magenta]{old_status}[/magenta]")
                
            if old_num != parcel_num:
                # New parcel appeared
                notification_msg = f"New parcel has appeared!\nNumber: {parcel_num}\nStatus: {parcel_status}"
            elif old_status != parcel_status:
                # Status changed
                notification_msg = f"Parcel {parcel_num} status changed: {old_status} -> {parcel_status}"
            else:
                if verbose:
                    console.print("[green]No changes detected since last check.[/green]")

        if notification_msg:
            method, notifier_config = get_notification_config()
            if verbose:
                console.print(f"[bold blue]Sending notification using '{method}'...[/bold blue]")
                
            if dry_run:
                console.print(Panel.fit(
                    f"[bold yellow]DRY RUN: Notification would be sent via {method}[/bold yellow]\n\n{notification_msg}",
                    title="Notification Simulation"
                ))
            else:
                notifier = get_notifier(method, notifier_config)
                notifier.send(notification_msg)
                if verbose:
                    console.print("[bold green]Notification sent successfully.[/bold green]")
        
        # Save state if not a dry run
        if not dry_run:
            new_state = {
                "number": parcel_num,
                "status": parcel_status
            }
            save_state(new_state)
            if verbose:
                console.print("[green]State updated.[/green]")
            
    except ShipMyBoxException as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
