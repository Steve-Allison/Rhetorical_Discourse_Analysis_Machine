import ast
import json
from pathlib import Path
from typing import Any

import _jsonnet


class ConfigReader:
    def __init__(self, config_file: str | Path, ext_vars: dict[str, str] | None = None) -> None:
        self.config = json.loads(_jsonnet.evaluate_file(str(config_file), ext_vars=ext_vars))

    def read(self, cls: type) -> Any:
        init_params: dict[str, Any] = {}
        stack: list[tuple[str, Any]] = [("", self.config)]

        while stack:
            prefix, value = stack.pop()

            if isinstance(value, dict):
                for key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        if sub_value == "true":
                            sub_value = True
                        elif sub_value == "false":
                            sub_value = False
                        elif sub_value.replace("-", "").isnumeric():
                            sub_value = int(sub_value)
                        elif sub_value[0] == "(" and sub_value[-1] == ")":
                            sub_value = ast.literal_eval(sub_value)
                        elif "." in sub_value and sub_value.replace("-", "").replace(".", "").isnumeric():
                            sub_value = float(sub_value)

                    stack.append((f"{prefix}{key}__", sub_value))
            else:
                param_name = prefix[:-2]
                init_params[param_name] = value

        init_params["trainer__config"] = self.config
        return cls(**init_params)
