import importlib
import importlib.util
import inspect
import pkgutil
import sys
import warnings
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Iterator, Tuple

import pytest

from genai._utils.service import BaseService


def _import_submodules(package_name):
    """Import all submodules of a module, recursively (taken from https://stackoverflow.com/a/25083161)

    :param package_name: Package name
    :type package_name: str
    :rtype: dict[types.ModuleType]
    """
    package = sys.modules[package_name]
    return {
        name: importlib.import_module(package_name + "." + name)
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__)
    }


def _get_all_subclasses(cls: type) -> list[type]:
    subclasses = cls.__subclasses__()
    for subclass in subclasses:
        subclasses.extend(_get_all_subclasses(subclass))
    return subclasses


@pytest.mark.unit
def test_services_export_symbols_explicitly():
    """All services export their symbols explicitly under __all__ module attribute."""

    _import_submodules("genai")  # import everything to register all subclasses
    classes_to_check = _get_all_subclasses(BaseService)
    # ignore subclasses classes defined in tests
    classes_to_check = [clazz for clazz in classes_to_check if clazz.__module__.startswith("genai")]

    for clazz in classes_to_check:
        module = inspect.getmodule(clazz)
        assert module and module.__all__
        assert clazz.__name__ in module.__all__


@pytest.mark.unit
def test_backwards_compatibility(propagate_caplog):
    """

    Note: The following schemas were removed without any deprecation warning as they were not part of any public API:
      - FileRetrieveParametersQuery
      - ModelRetrieveParametersQuery
      - RequestRetrieveParametersQuery
      - TuneRetrieveParametersQuery
      - TextGenerationComparisonCreateRequest
    """
    previously_exported_symbols = [
        "AIMessage",
        "BaseMessage",
        "ChatRole",
        "DecodingMethod",
        "FileCreateResponse",
        "FileIdRetrieveResponse",
        "FileListSortBy",
        "FilePurpose",
        "FileRetrieveResponse",
        "HAPOptions",
        "HumanMessage",
        "LengthPenalty",
        "ModelIdRetrieveResponse",
        "ModelIdRetrieveResult",
        "ModelRetrieveResponse",
        "ModelTokenLimits",
        "ModerationHAP",
        "ModerationImplicitHate",
        "ModerationParameters",
        "ModerationPosition",
        "ModerationStigma",
        "ModerationTokens",
        "PromptCreateResponse",
        "PromptIdRetrieveResponse",
        "PromptIdUpdateResponse",
        "PromptRetrieveResponse",
        "PromptTemplateData",
        "PromptType",
        "RequestApiVersion",
        "RequestChatConversationIdRetrieveResponse",
        "RequestEndpoint",
        "RequestOrigin",
        "RequestRetrieveResponse",
        "RequestStatus",
        "SortDirection",
        "StopReason",
        "SystemMessage",
        "TextChatCreateResponse",
        "TextChatStreamCreateResponse",
        "TextEmbeddingCreateResponse",
        "TextEmbeddingLimit",
        "TextEmbeddingParameters",
        "TextGenerationComparisonCreateRequestRequest",
        "TextGenerationComparisonCreateResponse",
        "TextGenerationComparisonParameters",
        "TextGenerationCreateResponse",
        "TextGenerationFeedbackCategory",
        "TextGenerationIdFeedbackCreateResponse",
        "TextGenerationIdFeedbackRetrieveResponse",
        "TextGenerationIdFeedbackUpdateResponse",
        "TextGenerationLimitRetrieveResponse",
        "TextGenerationParameters",
        "TextGenerationResult",
        "TextGenerationReturnOptions",
        "TextGenerationStreamCreateResponse",
        "TextModeration",
        "TextModerationCreateResponse",
        "TextTokenizationCreateResponse",
        "TextTokenizationCreateResults",
        "TextTokenizationParameters",
        "TextTokenizationReturnOptions",
        "TrimMethod",
        "TuneAssetType",
        "TuneCreateResponse",
        "TuneIdRetrieveResponse",
        "TuneParameters",
        "TuneResult",
        "TuneRetrieveResponse",
        "TuneStatus",
        "TuningTypeRetrieveResponse",
        "UserCreateResponse",
        "UserPatchResponse",
        "UserRetrieveResponse",
    ]
    # name is available in schema
    import genai.schema

    for name in previously_exported_symbols:
        with warnings.catch_warnings(record=True) as warning_log:
            result = getattr(genai.schema, name)
            assert not warning_log
            assert result is not None


@pytest.mark.unit
def test_backwards_compatibility_warnings():
    # Try a few imports from services:
    services = [
        "file",
        "model",
        "prompt",
        "request",
        "text.chat",
        "text.embedding",
        "text.embedding.limits",
        "text.generation",
        "text.generation.feedback",
        "text.generation.limit",
        "text.moderation",
        "text.tokenization",
        "tune",
        "user",
    ]
    services = ["file"]
    example_symbol = "DecodingMethod"
    for service in services:
        module = f"genai.{service}"
        with warnings.catch_warnings(record=True) as warning_log:
            exec(f"from {module} import {example_symbol}")
            assert warning_log
            warning = warning_log[0]
            assert f"Deprecated import of {example_symbol} from module {module}" in warning.message.args[0]
            assert warning.category == DeprecationWarning


@pytest.mark.unit
@pytest.mark.parametrize(
    "name_pair",
    [
        ["UserPromptResult", "PromptResult"],
        ["PromptsResponseResult", "PromptResult"],
        ["UserResponseResult", "UserResult"],
        ["UserCreateResultApiKey", "UserApiKey"],
        ["PromptRetrieveRequestParamsSource", "PromptListSource"],
    ],
)
def test_import_renamed_schema_warning(name_pair: Tuple[str, str]):
    module = "genai.schema"
    old_name, new_name = name_pair
    with warnings.catch_warnings(record=True) as warning_log:
        exec(f"from {module} import {old_name}")
        assert warning_log
        warning = warning_log[0]
        assert f"Class has been renamed from '{old_name}' to '{new_name}'." in warning.message.args[0]
        assert warning.category == DeprecationWarning


@pytest.mark.unit
@pytest.mark.parametrize("name", ["TuningType", "PromptTemplate", "ImplicitHateOptions", "StigmaOptions"])
def test_import_removed_schema_warning(name: str):
    module = "genai.schema"
    with warnings.catch_warnings(record=True) as warning_log:
        exec(f"from {module} import {name}")
        warning = warning_log[0]
        assert warning.category == DeprecationWarning


@pytest.mark.unit
def test_schemas_export_symbols_explicitly():
    """All `schema.py` modules export their symbols explicitly under __all__ module attribute."""
    import genai

    path = Path(genai.__file__)
    schemas_files: Iterator[Path] = path.parent.glob("**/schema.py")
    schema_modules = [SourceFileLoader(f.parent.name, str(f)).load_module() for f in schemas_files]
    assert schema_modules
    for module in schema_modules:
        assert module and module.__all__ and len(module.__all__) >= 1
