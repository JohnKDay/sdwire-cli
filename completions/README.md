# SDWire CLI Bash Completion

This directory contains bash completion scripts for the SDWire CLI tool.

## Overview

The bash completion script provides intelligent tab completion for:
- Main commands (`list`, `benchmark`, `switch`)
- Command options (`--debug`, `--version`, `--serial`, etc.)
- SDWire device serial numbers (dynamically retrieved)
- Switch subcommands (`ts`, `host`, `dut`, `target`, `off`)

## Installation

### Method 1: Source directly in your shell

```bash
# Add to your ~/.bashrc or ~/.bash_profile
source /path/to/sdwire-cli/completions/bash_completions
```

### Method 2: System-wide installation

```bash
# Copy to system bash completion directory (requires sudo)
sudo cp bash_completions /etc/bash_completion.d/sdwire

# Or for newer systems:
sudo cp bash_completions /usr/share/bash-completion/completions/sdwire
```

### Method 3: User-specific installation

```bash
# Create user completion directory if it doesn't exist
mkdir -p ~/.local/share/bash-completion/completions

# Copy the completion script
cp bash_completions ~/.local/share/bash-completion/completions/sdwire
```

## Usage

After installation, restart your shell or source your shell configuration:

```bash
source ~/.bashrc
```

Now you can use tab completion with the `sdwire` command:

```bash
# List available commands
sdwire <TAB>

# Complete device serials for benchmark
sdwire benchmark <TAB>

# Complete switch options and subcommands
sdwire switch <TAB>
sdwire switch --serial <TAB>
sdwire switch ts <TAB>
```

## Examples

```bash
# Tab completion for main commands
$ sdwire <TAB>
benchmark  list  switch  --debug  --version  --help

# Tab completion for benchmark with device serials
$ sdwire benchmark <TAB>
SD12345678  SD87654321  SD11223344

# Tab completion for switch subcommands
$ sdwire switch <TAB>
ts  host  dut  target  off  -s  --serial  --help

# Tab completion for switch with serial option
$ sdwire switch --serial <TAB>
SD12345678  SD87654321  SD11223344
```

## Features

- **Dynamic serial completion**: Automatically fetches available SDWire device serials
- **Context-aware completion**: Provides relevant options based on current command context
- **Error handling**: Gracefully handles cases where SDWire devices are not available
- **Comprehensive coverage**: Supports all commands, options, and subcommands

## Troubleshooting

### Completion not working

1. Ensure bash completion is installed on your system:
   ```bash
   # On Ubuntu/Debian
   sudo apt install bash-completion
   
   # On CentOS/RHEL
   sudo yum install bash-completion
   ```

2. Verify the completion script is properly sourced:
   ```bash
   complete -p sdwire
   ```

3. Check if the `sdwire` command is in your PATH:
   ```bash
   which sdwire
   ```

### Serial numbers not completing

If device serial numbers are not being completed:

1. Ensure SDWire devices are connected and detected:
   ```bash
   sdwire list
   ```

2. Check if you have proper permissions to access SDWire devices

3. Verify the `sdwire list` command works without errors

## Requirements

- Bash 4.0 or later
- `sdwire` command available in PATH
- bash-completion package (for system-wide installation)

## Contributing

If you find issues with the completion script or want to add new features:

1. Test your changes thoroughly
2. Ensure compatibility with different bash versions
3. Update this README if adding new functionality