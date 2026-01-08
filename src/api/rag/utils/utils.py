# src/api/rag/utils/utils.py
import yaml
from jinja2 import Template
from langsmith import Client

ls_client = Client()


def prompt_template_config(path, template_name):
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    prompts = config.get("prompts", {})
    template_content = prompts.get(template_name)

    if isinstance(template_content, str):
        # old style → single string template
        return Template(template_content)

    elif isinstance(template_content, dict):
        # new style → dict with system/user
        return {
            key: Template(val) for key, val in template_content.items()
        }

    else:
        raise ValueError(f"Unexpected template type for {template_name}: {type(template_content)}")



def prompt_template_registry(prompt_name):

    template_content = ls_client.pull_prompt(prompt_name).messages[1].prompt.template

    template = Template(template_content)

    return template