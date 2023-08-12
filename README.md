# llm-mlc

[![PyPI](https://img.shields.io/pypi/v/llm-mlc.svg)](https://pypi.org/project/llm-mlc/)
[![Changelog](https://img.shields.io/github/v/release/simonw/llm-mlc?include_prereleases&label=changelog)](https://github.com/simonw/llm-mlc/releases)
[![Tests](https://github.com/simonw/llm-mlc/workflows/Test/badge.svg)](https://github.com/simonw/llm-mlc/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/llm-mlc/blob/main/LICENSE)

[LLM](https://llm.datasette.io/) plugin for running models using [MLC](https://mlc.ai/mlc-llm/docs/)

## Installation

Install this plugin in the same environment as `llm`.
```bash
llm install llm-mlc
```
Next, run the `llm mlc setup` command to complete the installation:
```bash
llm mlc setup
```
This will setup `git lfs` and use it to install some extra dependencies:

```
Git LFS is not installed. Should I run 'git lfs install' for you?
Install Git LFS? [y/N]: y
Updated Git hooks.
Git LFS initialized.
Downloading prebuilt binaries...
Cloning into '/Users/simon/Library/Application Support/io.datasette.llm/mlc/dist/prebuilt/lib'...
remote: Enumerating objects: 221, done.
remote: Counting objects: 100% (86/86), done.
remote: Compressing objects: 100% (54/54), done.
remote: Total 221 (delta 59), reused 56 (delta 32), pack-reused 135
Receiving objects: 100% (221/221), 52.06 MiB | 9.13 MiB/s, done.
Resolving deltas: 100% (152/152), done.
Updating files: 100% (60/60), done.
Ready to install models in /Users/simon/Library/Application Support/io.datasette.llm/mlc
```

Finally, install the `mlc_chat` package. This is a few extra steps, which are [described in detail on the mlc.ai/package](https://mlc.ai/package/) site.

If you are on an Apple Silicon M1/M2 Mac you can run this command:
```bash
llm mlc pip install --pre --force-reinstall \
  mlc-ai-nightly \
  mlc-chat-nightly \
  -f https://mlc.ai/wheels
```
The `llm mlc pip` command ensures that `pip` will run in the same virtual environment as `llm` itself.

For other systems, [follow the instructions here](https://mlc.ai/package/).

## Installing models

After installation you will need to download a model using the `llm mlc download-model` command.

Here's how to download and install Llama 2:

```bash
llm mlc download-model Llama-2-7b-chat
```
This will download around 8GB of content.

You can also use `Llama-2-13b-chat` or `Llama-2-70b-chat`, though these files are a lot larger.

You can see a list of models you have installed this way using:
```bash
llm mlc models
```
This will also show the name of the model you should use to activate it, e.g.:

```
MlcModel: mlc-chat-Llama-2-7b-chat-hf-q4f16_1
```
## Running a prompt through a model

Once you have downloaded and added a model, you can run a prompt like this:
```bash
llm -m mlc-chat-Llama-2-7b-chat-hf-q4f16_1 \
  'five names for a cute pet ferret'
```

> Great! Here are five cute and creative name suggestions for a pet ferret:
>
> 1. Ferbie - a playful and affectionate name for a friendly and outgoing ferret.
> 2. Mr. Whiskers - a suave and sophisticated name for a well-groomed and dignified ferret.
> 3. Luna - a celestial and dreamy name for a curious and adventurous ferret.
> 4. Felix - a cheerful and energetic name for a lively and mischievous ferret.
> 5. Sprinkles - a fun and playful name for a happy and energetic ferret with a sprinkle of mischief.
>
> Remember, the most important thing is to choose a name that you and your ferret will love and enjoy!


## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-mlc
python3 -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
pytest
```
