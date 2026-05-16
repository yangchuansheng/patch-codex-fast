"""Minified bundle patterns used by patch-codex-fast."""

FUSE_FLAGS = (
    "OnlyLoadAppFromAsar=off",
    "EnableEmbeddedAsarIntegrityValidation=off",
    "GrantFileProtocolExtraPrivileges=off",
    "EnableCookieEncryption=off",
)

STOCK_FUSE_FLAGS = (
    "OnlyLoadAppFromAsar=on",
    "EnableEmbeddedAsarIntegrityValidation=on",
    "EnableCookieEncryption=on",
    "GrantFileProtocolExtraPrivileges=off",
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

# The gate function exported from gradient-*.js tells the rest of the bundle
# "is the current user NOT signed in via ChatGPT?". When it returns true the
# renderer disables the Plugins sidebar entry, hides the Plugins label, and
# greys out other ChatGPT-only surfaces. Neutralising it to a constant `false`
# makes the app treat API-key users as if they were signed in with ChatGPT
# for UI-gating purposes only.
#
# Known variants across Codex releases:
#   - `return e===`apikey``  (older builds; gate based on apikey)
#   - `return e!==`chatgpt``  (current builds; gate based on not-chatgpt)
APIKEY_GATE_PATTERNS = (
    "function e(e){return e===`apikey`}",
    "function e(e){return e!==`chatgpt`}",
)

CONNECTOR_PATTERNS = (
    ("(i=`connector-unavailable`)", "false&&(i=`connector-unavailable`)"),
)
