
import json
import logging
from html.parser import HTMLParser
from urllib.parse import urljoin

from py_mini_racer import MiniRacer


logger = logging.getLogger(__name__)


_RUNTIME = r"""
var __registry = {};
var __cache = {};

function __d(name, deps, factory, flag) {
    __registry[name] = {
        deps: deps,
        factory: factory,
        flag: flag
    };
    delete __cache[name];
}

function require(name) {
    if (__cache[name]) return __cache[name].exports;

    var m = __registry[name];
    if (!m) return undefined;

    var module = { exports: {} };
    var defaultSlot = {};
    __cache[name] = module;

    m.factory(
        globalThis, require, require, require,
        module, module.exports, defaultSlot
    );

    if (defaultSlot.default !== undefined) {
        module.exports = defaultSlot.default;
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
        var out = {};
        for (var k in obj) {
            if (keys.indexOf(k) === -1) out[k] = obj[k];
        }
        return out;
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
    log: function() {}, warn: function() {}, error: function() {},
    info: function() {}, debug: function() {}
};
var performance = {
    now: function() { return Date.now(); },
    mark: function() {}, measure: function() {}
};
var self = globalThis;
var window = globalThis;
"""


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


class FacebookOperationDiscovery:
    BUNDLE_DELIMITER = ";/*FB_PKG_DELIM*/"

    def __init__(self, context):
        self.context = context
        self.timeout_sec = 30

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

    def discover_operation(self, page_url: str, operation_name: str,) -> dict[str, str]:
        """
        Fetch the page and its external scripts through FacebookContext.
        """

        response = self.context.get(page_url)
        response.raise_for_status()


        # Try the bootloader JSON response first.
        script_urls = self._get_javascript_links(response.text)


        # If no rsrcMap links were found, treat the response as HTML.
        if not script_urls:
            parser = _ScriptParser()
            parser.feed(response.text)

            script_urls = list(dict.fromkeys(
                urljoin(page_url, src) for src in parser.urls
            ))

        v8 = MiniRacer()
        v8.eval(_RUNTIME)
        script_urls = [
        url for url in script_urls
            if url.startswith("https://") or url.startswith("http://")
        ]

        for script_url in script_urls:
            try:
                script_response = self.context.get(script_url)
                script_response.raise_for_status()

                source = self._prepare_bundle(script_response.text)
                if source.strip():
                    v8.eval(source, timeout_sec=self.timeout_sec)

                # Check whether the target operation is registered and resolvable.
                if self._has_operation(v8, operation_name):
                    break
                
            except Exception:
                logger.warning(
                    "Could not evaluate Facebook script %s",
                    script_url,
                    exc_info=True,
                )

        return self._collect(v8)

    def _has_operation(self, v8, operation_name: str) -> bool:
        return bool(v8.call(
            """function(name) {
                if (!__registry[name]) return false;

                try {
                    var value = require(name);
                    return typeof value === "string" && value.length > 0;
                } catch (e) {
                    return false;
                }
            }""",
            operation_name,
        ))

    def _prepare_bundle(self, source: str) -> str:
        marker = self.BUNDLE_DELIMITER

        if marker in source:
            source = source[source.index(marker) + len(marker):]

        return source

    def _collect(self, v8):
        js = r"""
        (function() {
            var out = {};

            // Pass 1: _facebookRelayOperation modules — export is a bare string doc id
            for (var name in __registry) {
                if (!name.endsWith("_facebookRelayOperation")) continue;
                try { out[name] = require(name); } catch (e) {}
            }

            // Pass 2: .graphql and $Parameters modules — id lives in params.id
            for (var name in __registry) {
                if (!name.endsWith(".graphql") && !name.endsWith("$Parameters")) continue;
                try {
                    var m = require(name);
                    if (m && m.params && typeof m.params.id === "string") {
                        out[name] = m.params.id;
                    }
                } catch (e) {}
            }

            return JSON.stringify(out);
        })()
        """
        raw = v8.eval(js)
        return json.loads(raw)