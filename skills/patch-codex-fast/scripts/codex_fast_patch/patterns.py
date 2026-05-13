"""Minified bundle patterns used by patch-codex-fast."""

FUSE_FLAGS = (
    "OnlyLoadAppFromAsar=off",
    "EnableEmbeddedAsarIntegrityValidation=off",
    "GrantFileProtocolExtraPrivileges=off",
    "EnableCookieEncryption=off",
)

FAST_AUTH_PATTERNS = (
    "return!(r?.authMethod!==`chatgpt`||i?.requirements?.featureRequirements?.fast_mode===!1)",
    "return!(r?.authMethod!==`chatgpt`||a)",
)

FAST_HOOK_AUTH_PATTERNS = (
    ("if(i?.authMethod!==`chatgpt`||s){", "if(false){"),
)

FAST_MODELS_PATTERNS = (
    ("l?.modelsByType.models.some(F)??!1", "true"),
    ("l?.modelsByType.models.some(F)??false", "true"),
    ("u?.models.some(M)??!1", "true"),
    ("u?.models.some(M)??false", "true"),
)

APIKEY_GATE_PATTERNS = (
    "function e(e){return e===`apikey`}",
)

CONNECTOR_PATTERNS = (
    ("(i=`connector-unavailable`)", "false&&(i=`connector-unavailable`)"),
)
