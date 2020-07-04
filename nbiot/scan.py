import click
import tabulate
from .module import SaraN211Module, PingError


def connect_module(module: SaraN211Module, app_ctx):
    click.echo(click.style(f"Connecting to network...", fg="yellow", bold=True))
    module.read_module_status()
    if app_ctx.apn:
        module.set_pdp_context(apn=app_ctx.apn)

    module.enable_signaling_connection_urc()
    module.enable_network_registration()
    module.enable_radio_functions()
    if app_ctx.psm:
        module.enable_psm_mode()
    else:
        module.disable_psm_mode()

    module.connect(app_ctx.mno)
    click.echo(click.style(f"Connected!", fg="yellow", bold=True))


@click.command()
@click.pass_obj
def connect(app_ctx):
    """
    Connect to the network and get general info on module and network
    """
    module: SaraN211Module = app_ctx.module
    connect_module(module, app_ctx)
    header = ["IMEI", "IMSI", "ICCID", "IP", "APN"]
    data = [[module.imei, module.imsi, module.iccid, module.ip, module.apn]]
    click.echo(
        click.style(
            tabulate.tabulate(
                data, header, tablefmt="github", numalign="left", stralign="left"
            ),
            fg="red",
        )
    )


@click.command()
@click.argument("ip")
@click.option("--runs", "-r", default=1, help="How many times should we ping")
@click.pass_obj
def ping(app_ctx, ip, runs):
    """
    Ping an IP address
    """
    module: SaraN211Module = app_ctx.module
    connect_module(module, app_ctx)
    click.echo(click.style(f"Pinging IP {ip}", fg="blue"))

    results = []
    for i in range(0, runs):
        try:
            ttl, rtt = module.ping(ip)
            results.append((rtt, ttl))
            click.echo(click.style(f"Success: rtt: {rtt}, ttl: {ttl}", fg="red"))
        except PingError as e:
            click.echo(click.style(f"**\t{e.args[0]}\t**", fg="red", bold=True))
    click.echo("\nResults:")
    click.echo(
        click.style(
            tabulate.tabulate(
                results,
                headers=["Round trip time (ms)", "Time to live (ms)"],
                tablefmt="github",
                numalign="left",
                stralign="left",
            ),
            fg="red",
        )
    )


@click.command()
@click.pass_obj
def stats(app_ctx):
    """
    Print statistics from the module.
    """
    module: SaraN211Module = app_ctx.module
    connect_module(module, app_ctx)
    click.echo(click.style(f"Collecting statistics...", fg="blue"))
    module.update_radio_statistics()

    header = ["Stat", "Value"]
    data = list()
    data.append(("ECL", f"{module.radio_ecl}"))
    data.append(("Signal power", f"{module.radio_signal_power} dBm"))
    data.append(("Total power", f"{module.radio_total_power} dBm"))
    data.append(("Signal power", f"{module.radio_signal_power} dBm"))
    data.append(("Tx power", f"{module.radio_tx_power} dBm"))
    data.append(("Tx time", f"{module.radio_tx_time} ms"))
    data.append(("Rx time", f"{module.radio_rx_time} ms"))
    data.append(("Cell id", f"{module.radio_cell_id}"))
    data.append(("Physical cell id", f"{module.radio_pci}"))
    data.append(("SNR", f"{module.radio_snr}"))
    data.append(("RSRQ", f"{module.radio_rsrq} dBm"))
    click.echo(
        click.style(
            tabulate.tabulate(
                data, header, tablefmt="github", numalign="left", stralign="left"
            ),
            fg="red",
        )
    )


@click.command()
@click.pass_obj
def reboot(app_ctx):
    """
    Reboot the module
    """
    module: SaraN211Module = app_ctx.module
    click.echo(click.style(f"Rebooting module {module}...", fg="red", bold=True))
    module.reboot()
    click.echo(click.style(f"Module rebooted", fg="red", bold=True))
