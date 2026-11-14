
import json
import logging
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from py_mini_racer import MiniRacer

from .exceptions import SessionExpiredError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JavaScript runtime
# ---------------------------------------------------------------------------

_RUNTIME = r"""
var __registry = {};
var __cache = {};

function __d(name, deps, factory, flag) {
    __registry[name] = { deps, factory, flag };
    delete __cache[name];
}

function require(name) {
    if (__cache[name]) return __cache[name].exports;

    var definition = __registry[name];
    if (!definition) return undefined;

    var module = { exports: {} };
    var defaultSlot = {};

    __cache[name] = module;

    definition.factory(
        globalThis, require, require, require,
        module, module.exports, defaultSlot
    );

    if (defaultSlot.default !== undefined) {
        module.exports = defaultSlot.default;
    } else {
        Object.assign(module.exports, defaultSlot); // promote .get
    }

    return module.exports;
}

var babelHelpers = {
    extends: Object.assign,

    inheritsLoose: function(sub, sup) {
        sub.prototype = Object.create(sup.prototype);
        sub.prototype.constructor = sub;
    },

    objectWithoutPropertiesLoose: function(obj, keys) {
        var result = {};
        for (var key in obj) {
            if (keys.indexOf(key) === -1) result[key] = obj[key];
        }
        return result;
    },

    taggedTemplateLiteralLoose: function(strings) {
        return strings;
    },

    assertThisInitialized: function(self) {
        return self;
    }
};

var gkx = function() { return false; };

var justknobx = {
    _: function() { return false; },
    _bool: function() { return false; },
    _num: function() { return 0; }
};

var qex = { _: function() { return false; } };
var requireLazy = function() {};
var __dyn = function() {};
var __r = function() {};
var __s = function() {};
var _bt = function() { return ""; };

var console = {
    log: function() {},
    warn: function() {},
    error: function() {},
    info: function() {},
    debug: function() {}
};

var performance = {
    now: function() { return Date.now(); },
    mark: function() {},
    measure: function() {}
};

var self = globalThis;
var window = globalThis;


// ---------------------------------------------------------------------------
// Default module stubs
// ---------------------------------------------------------------------------

__d("gkx", [], function(t,n,r,o,a,i,l) {
    l.default = function() { return false; };
}, 0);

__d("justknobx", [], function(t,n,r,o,a,i,l) {
    l.default = {
        _: function() { return false; },
        _bool: function() { return false; },
        _num: function() { return 0; }
    };
}, 0);

__d("qex", [], function(t,n,r,o,a,i,l) {
    l.default = { _: function() { return false; } };
}, 0);

__d("WebPixelRatio", [], function(t,n,r,o,a,i,l) {
    l.default = { get: function() { return 1; } };
}, 0);

__d("JSResourceForInteraction", [], function(t,n,r,o,a,i,l) {
    l.default = function(name) {
        return {
            __setRef: function(ref) {
                return {
                    moduleName: name,
                    ref: ref,
                    load: function() {
                        return Promise.resolve();
                    }
                };
            }
        };
    };
}, 0);

__d("relay-runtime", [], function(t,n,r,o,a,i,l) {
    l.default = {
        PreloadableQueryRegistry: {
            set: function() {},
            get: function() { return undefined; },
            has: function() { return false; }
        }
    };
}, 0);

__d("MetaConfig", [], function(t,n,r,o,a,i,l) {
    l.default = {
        _: function() { return false; },
        _num: function() { return 0; },
        _bool: function() { return false; }
    };
}, 0);


__d("XPlatReactEnvironment", [], function(t,n,r,o,a,i,l){
    l.default = {
        isWeb: function() { return true; },
        isAndroid: function() { return false; },
        isIOS: function() { return false; },
        isReactVR: function() { return false; },
        isDesktop: function() { return false; }
    };
}, 0);
"""


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

class _ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "script":
            return

        src = dict(attrs).get("src")
        if src:
            self.urls.append(src)


# ---------------------------------------------------------------------------
# Facebook operation discovery
# ---------------------------------------------------------------------------

class FacebookOperationDiscovery:

    BUNDLE_DELIMITER = ";/*FB_PKG_DELIM*/"

    OPERATION_SUFFIXES = (
        "_facebookRelayOperation",
        "$Parameters",
        ".graphql",
    )

    PV_PREFIX = "__relay_internal__pv__"
    PV_SUFFIX = "relayprovider"

    PV_COMBINATIONS = (
        (False, False, False),
        (True, True, True),
        (False, False, True),
        (False, True, True),
        (True, False, False),
        (True, True, False),
        (True, False, True),
        (False, True, False),
    )

    def __init__(self, context, timeout_sec=30, diagnostics=False):
        self.context = context
        self.timeout_sec = timeout_sec
        self.diagnostics = diagnostics

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def discover_operation(
        self,
        page_url: str,
        operation_name: str,
    ) -> dict:

        response = self.context.get(page_url)
        response.raise_for_status()

        script_urls = self._get_script_urls(response.text, page_url)

        runtime = MiniRacer()
        runtime.eval(_RUNTIME)

        for script_url in script_urls:
            try:
                source = self._fetch_bundle(script_url, operation_name)

                if not source:
                    continue

                runtime.eval(source, timeout_sec=self.timeout_sec)
            except SessionExpiredError:
                raise

            except Exception:
                
                logger.warning(
                    "Could not evaluate Facebook script %s",
                    script_url,
                    exc_info=True,
                )

        operations = self._collect(runtime)

        if self.diagnostics:
            self._dump_operations(operations)
            self._dump_providers(runtime)

        operation = operations.get(operation_name)

        if not operation:
            return {}

        return self._resolve_pv_domains(runtime, operation)

    # -----------------------------------------------------------------------
    # Page and bundle discovery
    # -----------------------------------------------------------------------

    def _find_rsrcmap(self, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "rsrcMap" and isinstance(value, dict):
                    return value

                result = self._find_rsrcmap(value)
                if result is not None:
                    return result

        elif isinstance(obj, list):
            for item in obj:
                result = self._find_rsrcmap(item)
                if result is not None:
                    return result

        return None

    def _get_javascript_links(self, text: str) -> list[str]:
        text = text.lstrip()

        if text.startswith("for (;;);"):
            text = text[len("for (;;);"):].lstrip()

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return []

        rsrc_map = self._find_rsrcmap(data)

        if not rsrc_map:
            return []

        return list(dict.fromkeys(
            item["src"]
            for item in rsrc_map.values()
            if isinstance(item, dict)
            and item.get("type") == "js"
            and isinstance(item.get("src"), str)
        ))

    def _get_script_urls(self, text: str, page_url: str) -> list[str]:
        urls = self._get_javascript_links(text)

        if not urls:
            parser = _ScriptParser()
            parser.feed(text)
            urls = parser.urls

        result = []

        for url in urls:
            absolute_url = urljoin(page_url, url)

            if urlparse(absolute_url).scheme in ("http", "https"):
                result.append(absolute_url)

        return list(dict.fromkeys(result))

    def _fetch_bundle(self, url: str, operation_name: str) -> str:
        response = self.context.get(url)
        response.raise_for_status()

        source = response.text

        if operation_name not in source and "relayprovider" not in source:
            return ""

        logger.debug("Evaluating Facebook bundle: %s", url)

        return self._prepare_bundle(source)

    def _prepare_bundle(self, source: str) -> str:
        marker = self.BUNDLE_DELIMITER

        if marker in source:
            source = source.split(marker, 1)[1]

        return source

    # -----------------------------------------------------------------------
    # GraphQL operation collection
    # -----------------------------------------------------------------------

    def _collect(self, runtime) -> dict:
        script = r"""
        (function() {
            var R = __registry;
            var req = require;
            var names = Object.keys(R);
            var operations = {};

            function safeRequire(name) {
                try {
                    return R[name] ? req(name) : null;
                } catch (_) {
                    return null;
                }
            }

            function getDocId(op) {
                var id = safeRequire(op + "_facebookRelayOperation");

                if (id) return id;

                var params = safeRequire(op + "$Parameters");

                return params && params.params
                    ? params.params.id
                    : null;
            }

            function getSchemaDefaults(op) {
                var gql = safeRequire(op + ".graphql");
                var defaults = {};

                ["fragment", "operation"].forEach(function(slot) {
                    var definitions = gql && gql[slot]
                        && gql[slot].argumentDefinitions || [];

                    definitions.forEach(function(def) {
                        defaults[def.name] = def.defaultValue;
                    });
                });

                return defaults;
            }

            function getRuntimeArgs(docId) {
                var result = {};

                if (!docId) return result;

                names.forEach(function(name) {
                    if (!name.endsWith(".entrypoint")) return;

                    var entrypoint = safeRequire(name);

                    if (!entrypoint ||
                        typeof entrypoint.getPreloadProps !== "function") {
                        return;
                    }

                    try {
                        var props = entrypoint.getPreloadProps({
                            routeParams: {},
                            routeProps: {},
                            passthroughProps: {}
                        });

                        var queries = props && props.queries || {};

                        Object.keys(queries).forEach(function(key) {
                            var ref = queries[key] || {};
                            var params = ref.parameters
                                && ref.parameters.params;

                            if (!params || params.id !== docId || !ref.variables) {
                                return;
                            }

                            Object.assign(result, ref.variables);
                        });
                    } catch (_) {}
                });

                return result;
            }

            function getProvidedVariables(op) {
                var params = safeRequire(op + "$Parameters");
                var provided = params && params.params
                    && params.params.providedVariables || {};

                var result = {};

                Object.keys(provided).forEach(function(name) {
                    var provider = provided[name];

                    if (!provider || typeof provider.get !== "function") {
                        result[name] = [null];
                        return;
                    }

                    try {
                        result[name] = [provider.get()];
                    } catch (_) {
                        result[name] = [null];
                    }
                });

                return result;
            }

            // Find all operation names from registered modules.
            names.forEach(function(name) {
                for (var suffix of [
                    "_facebookRelayOperation",
                    "$Parameters",
                    ".graphql"
                ]) {
                    if (name.endsWith(suffix)) {
                        operations[name.slice(0, -suffix.length)] = true;
                        break;
                    }
                }
            });

            var output = {};

            Object.keys(operations).forEach(function(op) {
                var docId = getDocId(op);
                var defaults = getSchemaDefaults(op);
                var runtimeArgs = getRuntimeArgs(docId);
                var args = {};

                // Schema defaults, overridden by runtime variables.
                Object.keys(defaults).forEach(function(name) {
                    args[name] = [
                        name in runtimeArgs
                            ? runtimeArgs[name]
                            : defaults[name]
                    ];
                });

                // Runtime variables absent from the schema.
                Object.keys(runtimeArgs).forEach(function(name) {
                    if (!(name in args)) {
                        args[name] = [runtimeArgs[name]];
                    }
                });

                // Relay provided variables.
                var provided = getProvidedVariables(op);

                Object.keys(provided).forEach(function(name) {
                    if (!(name in args)) {
                        args[name] = provided[name];
                    }
                });

                if (docId || Object.keys(args).length) {
                    output[op] = {
                        docId: docId,
                        args: args
                    };
                }
            });

            return JSON.stringify(output);
        })()
        """

        return json.loads(runtime.eval(script))

    # -----------------------------------------------------------------------
    # Relay provider resolution
    # -----------------------------------------------------------------------

    def _resolve_pv_domains(self, runtime, operation: dict) -> dict:
        args = operation.get("args") or {}

        for name in list(args):
            if not name.startswith(self.PV_PREFIX):
                continue

            domain = self._extract_pv_provider_values(runtime, name)

            if domain:
                args[name] = domain

        return operation

    def _set_stub_values(self, runtime, gkx, meta, jk):
        script = f"""
        (function() {{
            __d("gkx", [], function(t,n,r,o,a,i,l) {{
                l.default = function() {{ return {str(gkx).lower()}; }};
            }}, 0);

            __d("MetaConfig", [], function(t,n,r,o,a,i,l) {{
                l.default = {{
                    _: function() {{ return {str(meta).lower()}; }},
                    _num: function() {{ return 0; }},
                    _bool: function() {{ return {str(meta).lower()}; }}
                }};
            }}, 0);

            __d("justknobx", [], function(t,n,r,o,a,i,l) {{
                l.default = {{
                    _: function() {{ return {str(jk).lower()}; }},
                    _bool: function() {{ return {str(jk).lower()}; }},
                    _num: function() {{ return 0; }}
                }};
            }}, 0);
        }})()
        """

        runtime.eval(script)

    def _get_provider_value(self, runtime, module: str):
        script = r"""
        (function(name) {
            if (!__registry[name]) {
                return JSON.stringify({status: "missing"});
            }

            try {
                var provider = require(name);

                if (!provider || typeof provider.get !== "function") {
                    return JSON.stringify({status: "no_get"});
                }

                try {
                    return JSON.stringify({
                        status: "ok",
                        value: provider.get()
                    });
                } catch (e) {
                    return JSON.stringify({
                        status: "get_threw",
                        error: String(e)
                    });
                }
            } catch (e) {
                return JSON.stringify({
                    status: "require_threw",
                    error: String(e)
                });
            }
        })
        """

        result = json.loads(runtime.call(script, module))

        return result.get("status"), result.get("value")

    def _extract_pv_provider_values(self, runtime, name: str) -> list:
        if not name.startswith(self.PV_PREFIX):
            return []

        if not name.endswith(self.PV_SUFFIX):
            return []

        base = name[len(self.PV_PREFIX):-len(self.PV_SUFFIX)]
        module = f"{base}.relayprovider"

        values = {}
        saw_get_threw = False

        try:
            for flags in self.PV_COMBINATIONS:
                self._set_stub_values(runtime, *flags)

                status, value = self._get_provider_value(runtime, module)

                if status == "ok":
                    values[json.dumps(value, sort_keys=True)] = value
                elif status == "get_threw":
                    saw_get_threw = True

        finally:
            self._set_stub_values(runtime, False, False, False)

        if values:
            return list(values.values())

        if saw_get_threw:
            return [False, True]    # provider ran but errored -> Use Guessing as fallback

        return []  
    
    # -----------------------------------------------------------------------
    # Diagnostics
    # -----------------------------------------------------------------------

    def _dump_operations(self, operations: dict):
        if not operations:
            logger.info("No operations discovered")
            return

        lines = []

        for name, record in sorted(operations.items()):
            args = record.get("args") or {}

            user_args = sum(
                not key.startswith(self.PV_PREFIX)
                for key in args
            )

            lines.append(
                f"{name}\t"
                f"docId={record.get('docId')}\t"
                f"args={len(args)} (user={user_args})"
            )

        with open("operations.txt", "w", encoding="utf-8") as file:
            file.write(f"# {len(operations)} operations discovered\n")
            file.write("\n".join(lines) + "\n")

        logger.info("Wrote %d operations to operations.txt", len(operations))

    def _dump_providers(self, runtime):
        script = r"""
        (function() {
            var result = {
                loaded: [],
                resolved: {},
                failed: {}
            };

            Object.keys(__registry).forEach(function(name) {
                if (!name.endsWith(".relayprovider")) return;

                result.loaded.push(name);

                try {
                    var provider = require(name);

                    if (!provider || typeof provider.get !== "function") {
                        result.failed[name] = "no .get";
                        return;
                    }

                    try {
                        result.resolved[name] = provider.get();
                    } catch (e) {
                        result.failed[name] = "get threw: " + String(e);
                    }
                } catch (e) {
                    result.failed[name] = "require threw: " + String(e);
                }
            });

            result.loaded.sort();

            return JSON.stringify(result);
        })()
        """

        data = json.loads(runtime.eval(script))

        with open("providers.txt", "w", encoding="utf-8") as file:
            file.write(
                f"# relayprovider modules loaded: {len(data['loaded'])}\n"
            )

            for name in data["loaded"]:
                if name in data["resolved"]:
                    file.write(
                        f"{name}\tOK\tvalue={data['resolved'][name]!r}\n"
                    )
                else:
                    error = data["failed"].get(name, "unknown")
                    file.write(f"{name}\tFAIL\t{error}\n")

        logger.info(
            "Wrote %d providers (%d successful, %d failed)",
            len(data["loaded"]),
            len(data["resolved"]),
            len(data["failed"]),
        )