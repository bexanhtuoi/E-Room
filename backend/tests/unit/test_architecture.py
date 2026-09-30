import ast
import io
import pathlib

BACKEND_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def read_module(relative: str) -> ast.Module:
    return ast.parse(io.open(BACKEND_ROOT / relative, encoding="utf-8-sig").read())


def module_imports(tree: ast.Module, top_level_only: bool = False) -> list:
    nodes = tree.body if top_level_only else ast.walk(tree)
    names = []
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


def router_files() -> list:
    return sorted((BACKEND_ROOT / "app" / "api" / "routers").glob("*.py"))


class TestRouterLayer:
    def test_no_http_exception_in_routers(self):
        for path in router_files():
            tree = read_module("app/api/routers/" + path.name)
            for node in ast.walk(tree):
                assert not (
                    isinstance(node, ast.Name) and node.id == "HTTPException"
                ), path.name

    def test_no_direct_db_access_in_routers(self):
        for path in router_files():
            tree = read_module("app/api/routers/" + path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    target = node.func
                    assert not (
                        isinstance(target.value, ast.Name)
                        and target.value.id == "db"
                        and target.attr in ("exec", "add", "commit", "delete")
                    ), (path.name, target.attr)

    def test_no_ai_imports_in_routers(self):
        for path in router_files():
            for module in module_imports(read_module("app/api/routers/" + path.name)):
                assert module != "app.ai" and not module.startswith("app.ai."), (path.name, module)


class TestLayerDirections:
    def test_repositories_do_not_import_upper_layers(self):
        for path in sorted((BACKEND_ROOT / "app" / "repositories").glob("*.py")):
            for module in module_imports(read_module("app/repositories/" + path.name)):
                assert not module.startswith(("app.services", "app.api", "app.tasks")), (path.name, module)

    def test_services_do_not_import_api(self):
        for path in sorted((BACKEND_ROOT / "app" / "services").glob("*.py")):
            for module in module_imports(read_module("app/services/" + path.name)):
                assert not module.startswith("app.api"), (path.name, module)

    def test_schemas_do_not_import_logic_layers(self):
        for path in sorted((BACKEND_ROOT / "app" / "schemas").glob("*.py")):
            tree = read_module("app/schemas/" + path.name)
            for module in module_imports(tree, top_level_only=True):
                assert not module.startswith(
                    ("app.ai", "app.services", "app.repositories", "app.tasks")
                ), (path.name, module)

    def test_shared_is_leaf(self):
        for path in sorted((BACKEND_ROOT / "app" / "shared").glob("*.py")):
            tree = read_module("app/shared/" + path.name)
            for module in module_imports(tree, top_level_only=True):
                assert module == "app.shared" or module.startswith("app.shared."), (path.name, module)


class TestCeleryTaskNames:
    def test_expected_tasks_registered(self):
        from app.integration.celery import celery_app
        from app.tasks import maintenance, room_jobs, scoring

        assert maintenance.check_room_heartbeats is not None
        assert room_jobs.stream_ai_response is not None
        assert scoring.score_room_utterances is not None

        expected = {
            "app.tasks.room_jobs.stream_ai_response",
            "app.tasks.room_jobs.observe_room_audio",
            "app.tasks.room_jobs.transcribe_room_audio",
            "app.tasks.maintenance.ensure_room_workers",
            "app.tasks.maintenance.check_room_heartbeats",
            "app.tasks.scoring.score_single_utterance",
            "app.tasks.scoring.score_room_utterances",
        }
        assert expected <= set(celery_app.tasks.keys())


class TestFacadeSurfaces:
    def test_repositories_surface(self):
        from app import repositories

        for name in (
            "document_crud",
            "message_crud",
            "notification_crud",
            "pronunciation_score_crud",
            "room_crud",
            "session_crud",
            "user_crud",
        ):
            assert getattr(repositories, name, None) is not None, name

    def test_tasks_surface(self):
        from app import tasks

        for name in (
            "enqueue_ai_job",
            "score_room_utterance",
            "check_room_heartbeats",
            "mark_room_activity",
        ):
            assert getattr(tasks, name, None) is not None, name

    def test_shared_surface(self):
        from app import shared

        assert shared.SESSION_CHAT_KEY == "session_chat"
        assert shared.AI_IDENTITY_PREFIX == "ai_"
        assert shared.room_presence_key(7) == "room:7:participants"
        assert issubclass(shared.AppException, Exception)
