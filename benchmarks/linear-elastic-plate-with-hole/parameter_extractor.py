import json
import os
from snakemake_report_plugin_metadata4ing.interfaces import (
    ParameterExtractorInterface,
)
import yaml
import re

class ParameterExtractor(ParameterExtractorInterface):
    def extract_params(self, rule_name: str, file_path: str) -> dict:
        results = {}
        file_name = os.path.basename(file_path)
        if (
            file_name.startswith("summary")
            and rule_name == "summary"
        ):
            with open(file_path) as f:
                data = json.load(f)
            for experiment in data:
                config = experiment['configuration']
                results.setdefault(config, {})
                results[config].setdefault('has parameter', [])
                results[config].setdefault('investigates', [])
                for key, val in experiment['parameters'].items():
                    if isinstance(val, dict):
                        results[config]["has parameter"].append({key: {
                            "value": val["value"],
                            "unit": self._get_unit(key),
                            "json-path": f"/{key}/value",
                            "data-type": self._get_type(val["value"]),
                        }})
                    else:
                        results[config]["has parameter"].append({key: {
                            "value": val,
                            "unit": None,
                            "json-path": f"/{key}",
                            "data-type": self._get_type(val),
                        }})
                for key, val in experiment['metrics'].items():
                    if isinstance(val, dict):
                        results[config]["investigates"].append({key: {
                            "value": val["value"],
                            "unit": self._get_unit(key),
                            "json-path": f"/{key}/value",
                            "data-type": self._get_type(val["value"]),
                        }})
                    else:
                        results[config]["investigates"].append({key: {
                            "value": val,
                            "unit": None,
                            "json-path": f"/{key}",
                            "data-type": self._get_type(val),
                        }})        
        return results

    def extract_tools(self, rule_name: str, env_file_content: str,) -> dict:
        results = {}
        parsed = yaml.safe_load(env_file_content)
        dependencies = parsed.get("dependencies", [])

        for dep in dependencies:
           if isinstance(dep, str):
               match = re.match(r'^([a-zA-Z0-9_\-]+)([=<>!].*)?$', dep)
               if match:
                   name, version = match.groups()
                   results[name] = version if version else None
           elif isinstance(dep, dict):
               for _, pkgs in dep.items():
                   for pkg in pkgs:
                       match = re.match(r'^([a-zA-Z0-9_\-]+)([=<>!].*)?$', pkg)
                       if match:
                           name, version = match.groups()
                           results[name] = version if version else None
        rename_map = {
            "fenics-dolfinx": "FEniCS",
            "KratosMultiphysics-all": "Kratos Multiphysics"
        }

        filtered_results = {
            rename_map[k]: v for k, v in results.items() if k in rename_map
        }
        
        return filtered_results

    def _get_unit(self, name: str):
        return {
            "young-modulus": "units:PA",
            "load": "units:MegaPA",
            "length": "units:m",
            "radius": "units:m",
            "element-size": "units:m",
        }.get(name)

    def _get_type(self, val):
        if isinstance(val, float):
            return "schema:Float"
        elif isinstance(val, int):
            return "schema:Integer"
        elif isinstance(val, str):
            return "schema:Text"
        return None
