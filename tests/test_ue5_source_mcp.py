"""Integration tests for ue5_source_mcp.py.

These tests hit the real filesystem and require:
  D:/Games/UE_5.7                                              (engine root)
  D:/projects/Pegasus-Engine/PegasusGame/Samples/Games/Lyra   (lyra root)
  ripgrep (rg) in PATH
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import ue5_source_mcp as srv

ENGINE_PATH = Path(r"D:\Games\UE_5.7")
LYRA_PATH = Path(r"D:\projects\Pegasus-Engine\PegasusGame\Samples\Games\Lyra")

skip_no_engine = pytest.mark.skipif(
    not ENGINE_PATH.exists(), reason="Engine root not found at D:/Games/UE_5.7"
)
skip_no_lyra = pytest.mark.skipif(
    not LYRA_PATH.exists(), reason="Lyra root not found"
)


@pytest.fixture(autouse=True)
def reset_roots():
    """Each test starts with a clean ROOTS dict."""
    srv.ROOTS.clear()
    yield
    srv.ROOTS.clear()


@pytest.fixture
def with_engine():
    """Seed the engine root for tests that need it."""
    if not ENGINE_PATH.exists():
        pytest.skip("Engine root not found")
    srv.ROOTS["engine"] = ENGINE_PATH


@pytest.fixture
def with_lyra():
    """Seed the lyra root for tests that need it."""
    if not LYRA_PATH.exists():
        pytest.skip("Lyra root not found")
    srv.ROOTS["lyra"] = LYRA_PATH


class TestSetRoot:
    def test_set_valid_root(self, tmp_path):
        result = srv._set_root_impl("test", str(tmp_path))
        assert "test" in result
        assert str(tmp_path) in result
        assert srv.ROOTS["test"] == tmp_path

    def test_set_root_nonexistent_path(self):
        result = srv._set_root_impl("engine", r"Z:\does\not\exist")
        assert "Error" in result
        assert "engine" not in srv.ROOTS

    def test_set_root_empty_label(self, tmp_path):
        result = srv._set_root_impl("", str(tmp_path))
        assert "Error" in result

    def test_overwrite_existing_root(self, tmp_path):
        other = tmp_path / "sub"
        other.mkdir()
        srv._set_root_impl("engine", str(tmp_path))
        srv._set_root_impl("engine", str(other))
        assert srv.ROOTS["engine"] == other

    @skip_no_engine
    def test_set_engine_root(self):
        result = srv._set_root_impl("engine", str(ENGINE_PATH))
        assert "engine" in result
        assert srv.ROOTS["engine"] == ENGINE_PATH


class TestListRoots:
    def test_empty_returns_helpful_message(self):
        result = srv._list_roots_impl()
        assert "No roots" in result
        assert "set_root" in result

    @skip_no_engine
    def test_shows_configured_roots(self):
        srv.ROOTS["engine"] = ENGINE_PATH
        result = srv._list_roots_impl()
        assert "engine" in result
        assert str(ENGINE_PATH) in result
        assert "ok" in result

    def test_shows_missing_root(self, tmp_path):
        missing = tmp_path / "gone"
        srv.ROOTS["ghost"] = missing  # set directly, bypassing validation
        result = srv._list_roots_impl()
        assert "ghost" in result
        assert "MISSING" in result


class TestGetRoot:
    def test_no_roots_raises_helpful_error(self):
        with pytest.raises(ValueError, match="No roots configured"):
            srv._get_root("engine")

    @skip_no_engine
    def test_engine_root_resolves(self):
        srv.ROOTS["engine"] = ENGINE_PATH
        root = srv._get_root("engine")
        assert root == ENGINE_PATH

    @skip_no_lyra
    def test_lyra_root_resolves(self):
        srv.ROOTS["lyra"] = LYRA_PATH
        root = srv._get_root("lyra")
        assert root == LYRA_PATH

    def test_unknown_root_raises(self):
        srv.ROOTS["engine"] = ENGINE_PATH  # at least one root present
        with pytest.raises(ValueError, match="Unknown root"):
            srv._get_root("nonexistent")


class TestSearchImpl:
    def test_finds_known_class_in_engine(self, with_engine):
        result = srv._search_impl("class UAbilitySystemComponent", "engine")
        assert "[engine]" in result
        assert "AbilitySystemComponent" in result

    def test_no_results_returns_message(self, with_engine):
        result = srv._search_impl("ZZZNOMATCH_UNIQUE_9999_ZZZ", "engine")
        assert "No matches" in result

    def test_cpp_file_pattern(self, with_engine):
        result = srv._search_impl("UAbilitySystemComponent", "engine", "*.cpp")
        assert "[engine]" in result

    def test_lyra_root_returns_lyra_label(self, with_lyra):
        result = srv._search_impl("CommonGame", "lyra")
        assert "[lyra]" in result

    def test_unknown_root_raises(self, with_engine):
        with pytest.raises(ValueError, match="Unknown root"):
            srv._search_impl("anything", "bogus")


class TestReadFileImpl:
    def test_reads_known_header(self, with_engine):
        path = "Engine/Plugins/Runtime/GameplayAbilities/Source/GameplayAbilities/Public/AbilitySystemComponent.h"
        result = srv._read_file_impl(path, "engine")
        assert "[engine]" in result
        assert "UAbilitySystemComponent" in result

    def test_missing_file_returns_not_found(self, with_engine):
        result = srv._read_file_impl("Engine/Source/Nonexistent/Fake.h", "engine")
        assert "not found" in result.lower()

    def test_path_traversal_blocked(self, with_engine):
        result = srv._read_file_impl("../../Windows/System32/cmd.exe", "engine")
        assert "not found" in result.lower() or "escapes" in result.lower()

    def test_reads_lyra_header(self, with_lyra):
        sample = next(LYRA_PATH.rglob("*.h"), None)
        if sample is None:
            pytest.skip("No .h files found in lyra root")
        rel = str(sample.relative_to(LYRA_PATH)).replace("\\", "/")
        result = srv._read_file_impl(rel, "lyra")
        assert "[lyra]" in result
        assert "=" * 10 in result

    def test_unknown_root_raises(self, with_engine):
        with pytest.raises(ValueError, match="Unknown root"):
            srv._read_file_impl("anything.h", "bogus")


class TestListModuleImpl:
    def test_finds_gameplay_abilities(self, with_engine):
        result = srv._list_module_impl("GameplayAbilities", "engine")
        assert "[engine]" in result
        assert "AbilitySystemComponent.h" in result

    def test_finds_umg_module(self, with_engine):
        result = srv._list_module_impl("UMG", "engine")
        assert "[engine]" in result
        assert ".h" in result

    def test_unknown_module_returns_message(self, with_engine):
        result = srv._list_module_impl("ZZZNoSuchModule999", "engine")
        assert "No module" in result

    def test_finds_common_game_in_lyra(self, with_lyra):
        result = srv._list_module_impl("CommonGame", "lyra")
        assert "[lyra]" in result
        assert ".h" in result

    def test_unknown_root_raises(self, with_engine):
        with pytest.raises(ValueError, match="Unknown root"):
            srv._list_module_impl("GameplayAbilities", "bogus")


class TestFindPluginsImpl:
    def test_finds_gameplay_abilities_plugin(self, with_engine):
        result = srv._find_plugins_impl("GameplayAbilities", "engine")
        assert "[engine]" in result
        assert "GameplayAbilities" in result

    def test_no_query_returns_multiple_results(self, with_engine):
        result = srv._find_plugins_impl(None, "engine")
        assert "[engine]" in result
        assert "plugins" in result

    def test_no_match_returns_message(self, with_engine):
        result = srv._find_plugins_impl("ZZZNoPluginZZZ999", "engine")
        assert "No plugins" in result

    def test_finds_shooter_core_in_lyra(self, with_lyra):
        result = srv._find_plugins_impl("ShooterCore", "lyra")
        assert "[lyra]" in result
        assert "ShooterCore" in result

    def test_lyra_no_query_returns_all_lyra_plugins(self, with_lyra):
        result = srv._find_plugins_impl(None, "lyra")
        assert "[lyra]" in result
        assert "CommonGame" in result

    def test_unknown_root_raises(self, with_engine):
        with pytest.raises(ValueError, match="Unknown root"):
            srv._find_plugins_impl(None, "bogus")
