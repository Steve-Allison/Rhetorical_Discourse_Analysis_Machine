"""Build-only compiler: traverse Central manifests and LinkML inline resource slots."""

import argparse
from pathlib import Path
from typing import Any, cast

import yaml

from rdam._canonical import sha256_bytes
from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("expected a string-keyed mapping")
    if any(not isinstance(key, str) for key in cast(dict[object, object], value)):
        raise ValueError("expected a string-keyed mapping")
    return cast(dict[str, Any], value)


def compile_distribution(root: Path) -> IndexProjection:
    """Compile an authored distribution; no Central resource is modified."""
    root = root.resolve()
    inputs: dict[str, str] = {}

    def read(relative: str) -> dict[str, Any]:
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"declared path escapes distribution: {relative}")
        data = path.read_bytes()
        inputs[path.relative_to(root).as_posix()] = sha256_bytes(data)
        return _mapping(yaml.safe_load(data))

    manifest = read("ontology/data/distribution.yaml")
    classes: dict[str, Any] = {}
    slots: dict[str, Any] = {}
    enums: dict[str, Any] = {}
    loaded: set[str] = set()

    def schema(relative: str) -> None:
        if relative in loaded:
            return
        loaded.add(relative)
        value = read(relative)
        for imported in value.get("imports", []):
            if imported == "linkml:types":
                continue
            location = (Path(relative).parent / f"{imported}.yaml").as_posix()
            schema(location)
        classes.update(value.get("classes", {}))
        slots.update(value.get("slots", {}))
        enums.update(value.get("enums", {}))

    schema(manifest["schema_path"])
    read(manifest["evidence_catalog_path"])

    def ancestors(name: str) -> tuple[str, ...]:
        parent = classes[name].get("is_a")
        return (name, *ancestors(parent)) if parent else (name,)

    def fields(name: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for ancestor in reversed(ancestors(name)):
            value = classes[ancestor]
            for slot in value.get("slots", []):
                result[slot] = dict(slots[slot])
            result.update(value.get("attributes", {}))
            for slot, usage in value.get("slot_usage", {}).items():
                result[slot] = {**result.get(slot, {}), **usage}
        return result

    identifiers: set[str] = set()
    resources: list[SemanticResource] = []
    entries: list[LexicalEntry] = []

    def walk(value: dict[str, Any], name: str, path: str, domain: str, term: dict[str, Any] | None = None) -> None:
        definitions = fields(name)
        unknown = value.keys() - definitions.keys()
        if unknown:
            raise ValueError(f"unknown {name} fields in {path}: {sorted(unknown)}")
        for key, definition in definitions.items():
            if definition.get("required") and key not in value:
                raise ValueError(f"missing {name}.{key} in {path}")
            if definition.get("identifier"):
                identifier = value[key]
                if identifier in identifiers:
                    raise ValueError(f"duplicate identifier: {identifier}")
                identifiers.add(identifier)
        if "SemanticResource" in ancestors(name):
            resource = SemanticResource.model_validate({
                "identifier": value["id"], "label": value["label"],
                "description": value.get("description", value.get("definition", "")),
                "domain": value["home_domain"], "status": value["status"],
                "resource_type": name, "source_path": path,
            })
            resources.append(resource)
            if name in {"Concept", "OntologyEntity"}:
                entries.append(LexicalEntry(literal=resource.label, target=resource.identifier, method="label", status=resource.status))
        if name == "TermSense":
            if term is None:
                raise ValueError("TermSense must belong to a Term")
            base = {
                "target": value["denotes"], "term_id": term["id"], "sense_id": value["id"],
                "definition": value["definition"], "distinguished_from": tuple(value.get("distinguished_from", [])),
                "usage_note": value.get("usage_note"), "status": value["status"],
            }
            entries.append(LexicalEntry.model_validate({**base, "literal": term["surface_form"], "method": "term"}))
            for synonym in value.get("synonyms", []):
                entries.append(LexicalEntry.model_validate({
                    **base, "literal": synonym["literal"], "method": "synonym",
                    "scope": synonym["synonym_scope"], "synonym_id": synonym["synonym_id"],
                }))
        for key, content in value.items():
            definition = definitions[key]
            target = definition.get("range")
            if target not in classes or not (definition.get("inlined") or definition.get("inlined_as_list")):
                continue
            children = content if definition.get("multivalued") else [content]
            for child in children:
                walk(_mapping(child), target, path, domain, value if name == "Term" else term)

    modules: dict[str, tuple[str, dict[str, Any]]] = {}
    for path in manifest["domain_module_paths"]:
        module = read(path)
        identifier = module["module_id"]
        if identifier in modules:
            raise ValueError(f"duplicate module: {identifier}")
        modules[identifier] = (path, module)
    domains: set[str] = set()
    declared: set[str] = set()
    for path in manifest["domain_bundle_paths"]:
        bundle = read(path)
        domain = bundle["domain"]
        if domain in domains:
            raise ValueError(f"duplicate domain: {domain}")
        domains.add(domain)
        walk(bundle, "DomainBundle", path, domain)
        for identifier in bundle["modules"]:
            if identifier in declared or identifier not in modules:
                raise ValueError(f"duplicate or missing declared module: {identifier}")
            declared.add(identifier)
            location, module = modules[identifier]
            if module["domain"] != domain:
                raise ValueError(f"module domain differs from bundle: {identifier}")
            walk(module, "DomainModule", location, domain)
    if declared != modules.keys():
        raise ValueError("distribution contains modules absent from domain manifests")
    return IndexProjection(
        distribution_id=manifest["distribution_id"], version=manifest["version"],
        domains=tuple(sorted(domains)), source_files=tuple(sorted(inputs.items())),
        resources=tuple(sorted(resources, key=lambda item: item.identifier)),
        entries=tuple(sorted(entries, key=lambda item: (item.literal, item.target, item.method, item.sense_id or "", item.synonym_id or ""))),
        authorable_predicates=tuple(sorted(enums["AuthoredPredicateEnum"]["permissible_values"])),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("distribution", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    projection = compile_distribution(args.distribution)
    payload = projection.model_dump_json(indent=2) + "\n"
    if args.check:
        if args.output.read_text() != payload:
            raise ValueError("generated concept projection is stale")
    else:
        args.output.write_text(payload, encoding="utf-8")
    print(f"{len(projection.domains)} domains; {len(projection.resources)} resources; {len(projection.entries)} lexical entries; {projection.content_digest}")


if __name__ == "__main__":
    main()
