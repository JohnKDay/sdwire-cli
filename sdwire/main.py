#!/usr/bin/env python
"""SDWire CLI main entry point.

This module provides the command-line interface for controlling SDWire devices,
including listing devices and switching between host and DUT modes.
"""
import logging
from typing import Optional
import importlib.metadata
import click
from sdwire.backend import utils
from sdwire.backend import detect


@click.group()
@click.option("--debug", required=False, is_flag=True, help="Enable debug output")
@click.version_option(version=importlib.metadata.version("sdwire"), prog_name="sdwire")
def main(debug: Optional[bool] = None) -> None:
    """SDWire CLI - Control SDWire devices from command line."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)


@main.command()
def list() -> None:
    """List all connected SDWire devices with their block device information."""
    print("Serial\t\t\tProduct Info\t\tBlock Dev")
    for sdwire in detect.get_sdwire_devices():
        print(sdwire)


@main.command()
@click.argument("serial", required=True)
def benchmark(serial: str) -> None:
    """Run benchmark tests on the specified SDWire device.

    SERIAL: Serial number of the SDWire device to benchmark.
    Use 'sdwire list' to see available devices.
    """
    devices = detect.get_sdwire_devices()

    # Find the device by serial number
    target_device = None
    for device in devices:
        if device.serial_string == serial:
            target_device = device
            break

    if target_device is None:
        click.echo(f"Error: No SDWire device found with serial '{serial}'")
        click.echo("Use 'sdwire list' to see available devices.")
        import sys
        sys.exit(1)

    # Import and run benchmark
    try:
        from sdwire.backend.benchmark import run_benchmark
        run_benchmark(target_device)
    except ImportError:
        click.echo("Error: Benchmark module not available")
        import sys
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error running benchmark: {e}")
        import sys
        sys.exit(1)


@main.group()
@click.pass_context
@click.option(
    "-s",
    "--serial",
    required=False,
    help="Serial number of the sdwire device, if there is only one sdwire connected then it will be used by default",
)
def switch(ctx: click.Context, serial=None):
    """
    dut/target => connects the sdcard interface to target device

    ts/host => connects the sdcard interface to host machine

    off => disconnects the sdcard interface from both host and target
    """
    ctx.ensure_object(dict)
    utils.handle_switch_command(ctx, serial)


@switch.command()
@click.pass_context
def ts(ctx: click.Context):
    """
    ts/host => connects the sdcard interface to host machine
    """
    ctx.ensure_object(dict)
    utils.handle_switch_host_command(ctx)


@switch.command()
@click.pass_context
def host(ctx: click.Context):
    """
    ts/host => connects the sdcard interface to host machine
    """
    ctx.ensure_object(dict)
    utils.handle_switch_host_command(ctx)


@switch.command()
@click.pass_context
def dut(ctx: click.Context):
    """
    dut/target => connects the sdcard interface to target device
    """
    ctx.ensure_object(dict)
    utils.handle_switch_target_command(ctx)


@switch.command()
@click.pass_context
def target(ctx: click.Context):
    """
    dut/target => connects the sdcard interface to target device
    """
    ctx.ensure_object(dict)
    utils.handle_switch_target_command(ctx)


@switch.command()
@click.pass_context
def off(ctx: click.Context):
    """
    off => disconnects the sdcard interface from both host and target
    """
    ctx.ensure_object(dict)
    utils.handle_switch_off_command(ctx)


if __name__ == "__main__":
    main()
