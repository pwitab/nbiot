import click
import sys
from .module import SaraN211Module, PingError
import time

import itertools
import sys
import time
import threading


def connect_module(module: SaraN211Module, app_ctx):
    click.echo(click.style(f'Connecting to network...', fg='yellow', bold=True))
    module.read_module_status()
    module.enable_signaling_connection_urc()
    module.enable_network_registration()
    module.enable_radio_functions()
    if app_ctx.psm:
        module.enable_psm_mode()
    else:
        module.disable_psm_mode()

    module.connect(app_ctx.mno)
    click.echo(click.style(f'Connected!', fg='yellow', bold=True))


@click.command()
@click.pass_obj
def connect(app_ctx):
    """
    The scan command enables you to connect and get information of the network
    """
    module: SaraN211Module = app_ctx.module
    connect_module(module, app_ctx)
    #print(module._at_action('AT+CPSMS?', capture_urc=True))
    header = f'IMEI\t\t\tIMSI\t\t\tICCID\t\t\t\tIP\t\tAPN'
    click.echo(header)
    click.echo(click.style(
        f'{module.imei}\t\t{module.imsi}\t\t{module.iccid}\t\t{module.ip}\t{module.apn}',
        fg='red'))


@click.command()
@click.argument('ip')
@click.option('--runs', '-r', default=1, help='How many times should we ping')
@click.pass_obj
def ping(app_ctx, ip, runs):
    module: SaraN211Module = app_ctx.module
    connect_module(module, app_ctx)
    click.echo(click.style(f'Pinging IP {ip}', fg='blue'))
    click.echo('Round Trip Time\t\t\tTime To Live')
    for i in range(0, runs):
        try:
            ttl, rtt = module.ping(ip)
            click.echo(click.style(f'{rtt}\t\t\t\t{ttl}', fg='red'))
        except PingError as e:
            click.echo(click.style(f'**\t{e.args[0]}\t**', fg='red', bold=True))


@click.command()
@click.pass_obj
def stats(app_ctx):
    module: SaraN211Module = app_ctx.module
    connect_module(module, app_ctx)
    click.echo(click.style(f'Collecting statistics...', fg='blue'))
    module.update_radio_statistics()
    click.echo(click.style(
        f'ECL: \t\t\t{module.radio_ecl} '
        f'(Extended Coverage Level (0=good, 2=worst))'))
    click.echo(
        click.style(f'Signal Power: \t\t{module.radio_signal_power} dBm'))
    click.echo(click.style(f'Total Power: \t\t{module.radio_total_power} dBm'))
    click.echo(click.style(f'TX Power: \t\t{module.radio_tx_power} dBm'))
    click.echo(click.style(f'TX Time: \t\t{module.radio_tx_time} ms'))
    click.echo(click.style(f'RX Time: \t\t{module.radio_rx_time} ms'))
    click.echo(click.style(f'Cell ID: \t\t{module.radio_cell_id}'))
    click.echo(click.style(f'Physical Cell ID: \t{module.radio_pci}'))
    click.echo(click.style(f'Channel (EARFNC): \t{module.radio_earfcn}'))
    click.echo(click.style(f'SNR: \t\t\t{module.radio_snr} '))
    click.echo(click.style(f'RSRQ: \t\t\t{module.radio_rsrq} dBm'))


@click.command()
@click.pass_obj
def reboot(app_ctx):
    module: SaraN211Module = app_ctx.module
    click.echo(click.style(f'Rebooting module {module}...', fg='red', bold=True))
    module.reboot()
    click.echo(click.style(f'Module rebooted', fg='red', bold=True))
