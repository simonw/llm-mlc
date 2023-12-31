import click
import contextlib
import json
import llm
import os
from pydantic import Field
import subprocess
import sys
import textwrap
from typing import Optional


MODEL_URLS = {
    "Llama-2-7b-chat": "https://huggingface.co/mlc-ai/mlc-chat-Llama-2-7b-chat-hf-q4f16_1",
    "Llama-2-13b-chat": "https://huggingface.co/mlc-ai/mlc-chat-Llama-2-13b-chat-hf-q4f16_1",
    "Llama-2-70b-chat": "https://huggingface.co/mlc-ai/mlc-chat-Llama-2-70b-chat-hf-q4f16_1",
}

MLC_INSTALL = (
    "You must install mlc_chat first. "
    "See https://github.com/simonw/llm-mlc for instructions."
)


def is_git_lfs_command_available():
    try:
        subprocess.run(
            ["git", "lfs"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def is_git_lfs_installed():
    try:
        # Run the git lfs status command
        result = subprocess.check_output(
            ["git", "lfs", "status"], encoding="utf-8"
        ).strip()

        # If the result contains the result of object to be pushed or that it's
        # not a git repo, it's likely that Git LFS is installed
        if "Objects to be pushed" in result:
            return True
        elif "Objects to be committed" in result:
            return True
        elif "Not in a Git repository" in result:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        # If the command fails, it's likely that the configuration option isn't set
        return False


def _ensure_models_dir():
    directory = llm.user_dir() / "llama-cpp" / "models"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _ensure_models_file():
    directory = llm.user_dir() / "llama-cpp"
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / "models.json"
    if not filepath.exists():
        filepath.write_text("{}")
    return filepath


@llm.hookimpl
def register_models(register):
    directory = llm.user_dir() / "mlc"
    models_dir = directory / "dist" / "prebuilt"
    if not models_dir.exists():
        return
    for child in models_dir.iterdir():
        if child.is_dir() and child.name != "lib":
            # It's a model! Register it
            register(
                MlcModel(
                    model_id=child.name,
                    model_path=str(child.absolute()),
                )
            )


@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def mlc():
        "Commands for managing MLC models"

    @mlc.command()
    def setup():
        "Finish setting up MLC, step by step"
        directory = llm.user_dir() / "mlc"
        directory.mkdir(parents=True, exist_ok=True)
        if not is_git_lfs_command_available():
            raise click.ClickException(
                "Git LFS is not installed. You should run 'brew install git-lfs' or similar."
            )
        if not is_git_lfs_installed():
            click.echo(
                "Git LFS is not installed. Should I run 'git lfs install' for you?"
            )
            if click.confirm("Install Git LFS?"):
                subprocess.run(["git", "lfs", "install"], check=True)
            else:
                raise click.ClickException(
                    "Git LFS is not installed. You should run 'git lfs install'."
                )
        # Now we have git-lfs installed, ensure we have cloned the repo
        dist_dir = directory / "dist"
        if not dist_dir.exists():
            click.echo("Downloading prebuilt binaries...")
            # mkdir -p dist/prebuilt
            (dist_dir / "prebuilt").mkdir(parents=True, exist_ok=True)
            # git clone
            git_clone_command = [
                "git",
                "clone",
                "https://github.com/mlc-ai/binary-mlc-llm-libs.git",
                str((dist_dir / "prebuilt" / "lib").absolute()),
            ]
            subprocess.run(git_clone_command, check=True)
        click.echo("Ready to install models in {}".format(directory))
        # Do we have mlc_chat installed?
        try:
            import mlc_chat
        except ImportError:
            raise click.ClickException(MLC_INSTALL)

    @mlc.command(
        help=textwrap.dedent(
            """
        Download and register a model from a URL

        Try one of these names:
        
        \b
        {}
        """
        ).format("\n".join("- {}".format(key) for key in MODEL_URLS.keys()))
    )
    @click.argument("name_or_url")
    @click.option(
        "aliases", "-a", "--alias", multiple=True, help="Alias to use for this model"
    )
    def download_model(name_or_url, aliases):
        url = MODEL_URLS.get(name_or_url) or name_or_url
        if name_or_url in MODEL_URLS:
            # Set that up as an alias too
            aliases = list(aliases) + [name_or_url]
        if not url.startswith("https://"):
            raise click.BadParameter("Invalid model name or URL")
        directory = llm.user_dir() / "mlc"
        prebuilt_dir = directory / "dist" / "prebuilt"
        if not prebuilt_dir.exists():
            raise click.ClickException("You must run 'llm mlc setup' first")
        # Run git clone URL dist/prebuilt
        last_bit = url.split("/")[-1]
        git_clone_command = [
            "git",
            "clone",
            url,
            str((prebuilt_dir / last_bit).absolute()),
        ]
        subprocess.run(git_clone_command, check=True)
        if aliases:
            aliases_path = llm.user_dir() / "aliases.json"
            if not aliases_path.exists():
                aliases_path.write_text("{}")
            aliases_data = json.loads(aliases_path.read_text())
            for alias in aliases:
                aliases_data[alias] = last_bit
            aliases_path.write_text(json.dumps(aliases_data, indent=2))

    @mlc.command()
    def models():
        "List installed MLC models"

        for model_alias in llm.get_models_with_aliases():
            if isinstance(model_alias.model, MlcModel):
                aliases = ", ".join(model_alias.aliases)
                if aliases:
                    aliases = " (aliases: {})".format(aliases)
                click.echo(
                    "{}{}".format(
                        model_alias.model,
                        aliases,
                    )
                )

    @mlc.command()
    def models_dir():
        "Display the path to the directory holding downloaded models"
        directory = llm.user_dir() / "mlc" / "dist" / "prebuilt"
        click.echo(directory.absolute())

    @mlc.command(
        context_settings={
            "ignore_unknown_options": True,
            "allow_extra_args": True,
        }
    )
    @click.pass_context
    def pip(ctx, **kwargs):
        "Run pip in the LLM virtual environment"
        cmd = [sys.executable, "-m", "pip"] + ctx.args
        subprocess.run(cmd)


class MlcModel(llm.Model):
    can_stream = True

    class Options(llm.Options):
        temperature: Optional[float] = Field(
            description=(
                "A higher temperature encourages more diverse outputs, while a "
                "lower temperature produces more deterministic outputs"
            ),
            ge=0,
            le=1,
            default=None,
        )
        top_p: Optional[float] = Field(
            description=(
                "At each step, we select tokens from the minimal set that has a "
                "cumulative probability exceeding this value"
            ),
            ge=0,
            le=1,
            default=None,
        )
        repetition_penalty: Optional[float] = Field(
            description=(
                "Controls the likelihood of the model generating repeated texts"
            ),
            ge=0,
            le=1,
            default=None,
        )
        max_gen_len: Optional[int] = Field(
            description="The maximum length of the output text",
            gt=0,
            default=None,
        )

    def __init__(self, model_id, model_path):
        self.model_id = model_id
        self.model_path = model_path
        self.chat_mod = None  # Lazy loading

    def execute(self, prompt, stream, response, conversation):
        try:
            import mlc_chat
            from mlc_chat.base import get_delta_message
            import mlc_chat.chat_module
        except ImportError:
            raise click.ClickException(MLC_INSTALL)

        # Disable print() in that module
        def noop(*args, **kwargs):
            pass

        mlc_chat.chat_module.__dict__["print"] = noop

        class StreamingChatModule(mlc_chat.ChatModule):
            def generate_iter(self, prompt):
                curr_message = ""
                self._prefill(prompt)
                while not self._stopped():
                    self._decode()
                    new_msg = self._get_message()
                    delta = get_delta_message(curr_message, new_msg)
                    curr_message = new_msg
                    yield delta

        with SuppressOutput():
            config_kwargs = {}

            system_prompt = None
            if conversation:
                messages = []
                # Populate messages from the conversation history
                for prev_response in conversation.responses:
                    if prev_response.prompt.system:
                        # Use the last set system prompt in that sequence
                        system_prompt = prev_response.prompt.system
                    messages.extend(
                        [
                            ["USER", prev_response.prompt.prompt],
                            ["ASSISTANT", prev_response.text()],
                        ]
                    )
                if messages:
                    config_kwargs["messages"] = messages
                    config_kwargs["offset"] = len(messages)

            if self.chat_mod is None:
                with temp_chdir(llm.user_dir() / "mlc"):
                    self.chat_mod = StreamingChatModule(model=self.model_path)

            if prompt.system:
                system_prompt = prompt.system

            if system_prompt is not None:
                config_kwargs["system"] = system_prompt

            chat_config_kwargs = {
                "max_gen_len": prompt.options.max_gen_len or 512,
                "conv_config": mlc_chat.ConvConfig(**config_kwargs),
            }
            if prompt.options.temperature is not None:
                chat_config_kwargs["temperature"] = prompt.options.temperature
            if prompt.options.top_p is not None:
                chat_config_kwargs["top_p"] = prompt.options.top_p
            if prompt.options.repetition_penalty is not None:
                chat_config_kwargs[
                    "repetition_penalty"
                ] = prompt.options.repetition_penalty

            self.chat_mod.reset_chat(mlc_chat.ChatConfig(**chat_config_kwargs))

            if stream:
                yield from self.chat_mod.generate_iter(prompt=prompt.prompt)
            else:
                # All in one go
                yield self.chat_mod.generate(prompt=prompt.prompt)


@contextlib.contextmanager
def temp_chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)


class SuppressOutput:
    def __enter__(self):
        # Save a copy of the current file descriptors for stdout and stderr
        self.stdout_fd = os.dup(1)
        self.stderr_fd = os.dup(2)

        # Open a file to /dev/null
        self.devnull_fd = os.open(os.devnull, os.O_WRONLY)

        # Replace stdout and stderr with /dev/null
        os.dup2(self.devnull_fd, 1)
        os.dup2(self.devnull_fd, 2)

        # Writes to sys.stdout and sys.stderr should still work
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = os.fdopen(self.stdout_fd, "w")
        sys.stderr = os.fdopen(self.stderr_fd, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore stdout and stderr to their original state
        os.dup2(self.stdout_fd, 1)
        os.dup2(self.stderr_fd, 2)

        # Close the saved copies of the original stdout and stderr file descriptors
        os.close(self.stdout_fd)
        os.close(self.stderr_fd)

        # Close the file descriptor for /dev/null
        os.close(self.devnull_fd)

        # Restore sys.stdout and sys.stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
