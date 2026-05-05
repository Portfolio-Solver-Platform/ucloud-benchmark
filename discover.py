from pathlib import Path

EXCLUDED_PREFIXES = ("license", "readme")
INSTANCE_EXTENSIONS = (".dzn", ".json")


def discover_problems(base: Path, start_from_instance: str) -> list[tuple[Path, Path | None]]:
    problems = []

    found_instance=False
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():
            continue

        models = sorted(folder.glob("*.mzn"))
        instances = sorted(
            f for f in folder.rglob("*")
            if f.is_file()
            and f.suffix in INSTANCE_EXTENSIONS
            and not f.name.lower().startswith(EXCLUDED_PREFIXES)
        )

        if not models:
            continue

        # Skip (model, instance) pairs until start point found. The start
        # name is matched first against .dzn/.json instance filenames; if no
        # match, we fall back to matching .mzn model filenames (needed for
        # "models-only" problem dirs like connect/, where each .mzn file is
        # itself an instance).
        if start_from_instance is not None and not found_instance:
            skip_i = None
            for i, instance in enumerate(instances):
                if start_from_instance in instance.name:
                    skip_i = i
                    found_instance = True
                    break
            skip_m = None
            if not found_instance:
                for i, model in enumerate(models):
                    if start_from_instance in model.name:
                        skip_m = i
                        found_instance = True
                        break
            if not found_instance:
                continue
            if skip_i is not None:
                instances = instances[skip_i:]
            if skip_m is not None:
                models = models[skip_m:]

        if len(models) == 1 and instances:
            for instance in instances:

                problems.append((models[0], instance))
        elif not instances:
            for model in models:
                problems.append((model, None))
        else:
            for model in models:
                for instance in instances:
                    problems.append((model, instance))

    return problems
