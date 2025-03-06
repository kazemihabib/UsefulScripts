# Useful Scripts

This repository contains various scripts that I find useful for my work. These scripts might not be general-purpose as they were developed specifically for my needs. Most of them are generated using AI tools.

## Introduction

These scripts automate different tasks I encounter in my workflow. Each script is organized into directories based on its functionality.

Feel free to explore and use them as you see fit. However, please note that they may require modifications to suit your specific requirements.

## Contents

- [`EbookMaker`](EbookMaker): Scripts for creating eBooks from various sources.
  - [`HuggingFaceAgents`](EbookMaker/HuggingFaceAgents): Scripts for downloading the HuggingFace agents course and converting it to an eBook. Since Kindle does not support GIF images, the GIFs are converted into 8 key frames and embedded as images.
- More scripts to be added...

## Installation

### Installing UV

Before using these scripts, you'll need to install the UV package manager:

```sh
#Homebrew on macOS
brew install uv
```

For more installation options, visit the [UV documentation](https://github.com/astral-sh/uv).

## Usage

### UV Overview

uv is an extremely fast Python package and project manager, written in Rust and designed as a drop-in replacement for pip and pip-tools workflows.

### Why Use UV for Running Scripts

The Python scripts in this repository use [PEP 723](https://peps.python.org/pep-0723/) (Inline Script Metadata), which allows dependencies to be specified directly within the script. We use uv to properly resolve these inline dependencies.

### How To Run

To execute any script in this repository:

```sh
uv run path/to/script.py
```

For example:

```sh
uv run EbookMaker/HuggingFaceAgents/AgentsCourseEbookMaker.py
```

When you run a script with `uv run`:

The uv run command sets up a temporary virtual environment, installs the dependencies, executes your command within that isolated context, and then cleans up the environment once the command completes.

This approach ensures reproducible execution without cluttering your global Python environment.

Additionally, uv lock secures dependency versions by locking them, ensuring every run uses the exact same package versions for a reproducible and conflict-free environment.

## Contributing

While this repository is primarily for personal use, suggestions and improvements are welcome. Feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

These scripts are provided as-is without any guarantees. Use them at your own risk.
