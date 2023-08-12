from llm.plugins import pm


def test_plugin_is_installed():
    plugins = pm.get_plugins()
    assert "llm_mlc" in {mod.__name__ for mod in plugins}
