"""Pure routing decision for config.wsgi (testable without Django). Every /api/v1/* path, including the spec's health operations
(API-SYS-001/002, which the application implements and which touch the database through the request transaction), is served by the API app."""


def goes_to_api(path: str, dev_content: bool) -> bool:
    return path.startswith("/api/v1/") or (path == "/" and dev_content)
