"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
var _a;
Object.defineProperty(exports, "__esModule", { value: true });
exports.getCachedTransform = getCachedTransform;
exports.setCachedTransform = setCachedTransform;
exports.createCacheKey = createCacheKey;
exports.clearTransformCache = clearTransformCache;
exports.getTransformCacheDirectory = getTransformCacheDirectory;
exports.shouldSkipTransformForRuntimeJs = shouldSkipTransformForRuntimeJs;
const node_fs_1 = __importDefault(require("node:fs"));
const node_path_1 = __importDefault(require("node:path"));
const ts = __importStar(require("typescript"));
const node_os_1 = require("node:os");
const node_path_2 = require("node:path");
const xxhash_1 = require("@node-rs/xxhash");
const debug_1 = __importDefault(require("debug"));
const fast_json_stable_stringify_1 = __importDefault(require("fast-json-stable-stringify"));
const LOOKS_LIKE_ESM_SYNTAX_REGEX = /(?:^|\n)\s*import\s|(?:^|\n)\s*export\s|\bimport\.meta\b/;
// Strong JSX signals: a closing element `</Tag`, a self-closing element
// `<Tag ... />`, or a fragment `<>`. These are rare in plain JS (a `<`/`>`
// comparison matches none of them), so a hit reliably means the file needs the
// JSX transform and must not be skipped.
const LOOKS_LIKE_JSX_REGEX = /<\/[A-Za-z]|<[A-Za-z][^>]*\/>|<>/;
const JS_RUNTIME_EXTENSIONS = new Set([ts.Extension.Js, ts.Extension.Mjs, ts.Extension.Cjs, '.es6', '.es']);
const debug = (0, debug_1.default)('@swc-node');
const CACHE_ENABLED = isEnabled(process.env.SWC_NODE_CACHE, true);
const MEMORY_CACHE_LIMIT = Number((_a = process.env.SWC_NODE_CACHE_MEMORY_LIMIT) !== null && _a !== void 0 ? _a : '2000');
// A stable per-user segment so the on-disk cache is shared across runs by the
// same user. Windows has no getuid(); falling back to the pid there would give
// every process a throwaway directory and defeat the disk cache entirely.
function cacheUserSegment() {
    if (typeof process.getuid === 'function') {
        return String(process.getuid());
    }
    try {
        const name = (0, node_os_1.userInfo)().username;
        if (name) {
            return name.replace(/[^a-zA-Z0-9_-]/g, '_');
        }
    }
    catch (_a) {
        // userInfo() can throw when there is no backing passwd entry.
    }
    return 'default';
}
// Resolved lazily rather than frozen at import time so SWC_NODE_CACHE_DIR is
// honored whenever it is set (including by tests) and getTransformCacheDirectory
// always reflects the current value.
function getCacheDirectory() {
    var _a;
    return (_a = process.env.SWC_NODE_CACHE_DIR) !== null && _a !== void 0 ? _a : (0, node_path_2.join)((0, node_os_1.tmpdir)(), `swc-node-${cacheUserSegment()}`);
}
if (!Number.isFinite(MEMORY_CACHE_LIMIT) || MEMORY_CACHE_LIMIT < 0) {
    throw new Error(`Invalid value for SWC_NODE_CACHE_MEMORY_LIMIT: ${process.env.SWC_NODE_CACHE_MEMORY_LIMIT}`);
}
const REGISTER_VERSION = readPackageVersion('../package.json');
const SWC_VERSION = readPackageVersion('@swc/core/package.json');
const memoryCache = new Map();
let optionsSignatureCache = new WeakMap();
let ensuredCacheDirectory;
let diskWriteCounter = 0;
function getCachedTransform(cacheKey) {
    if (!CACHE_ENABLED) {
        return undefined;
    }
    const memoryValue = memoryCache.get(cacheKey);
    if (memoryValue) {
        return memoryValue;
    }
    const diskValue = readDiskCache(cacheKey);
    if (diskValue) {
        setMemoryCache(cacheKey, diskValue);
    }
    return diskValue;
}
function setCachedTransform(cacheKey, value) {
    if (!CACHE_ENABLED) {
        return;
    }
    setMemoryCache(cacheKey, value);
    writeDiskCache(cacheKey, value);
}
function createCacheKey(input) {
    // Keep cache reuse scoped to both source intent and toolchain version so
    // stale compiled output is not reused across upgrades/config changes. NUL
    // separators keep field boundaries unambiguous.
    const payload = [
        input.sourcecode,
        input.filename,
        input.fallbackToTs ? 'ts' : 'swc',
        getOptionsSignature(input.options),
        input.runSalt,
        `register:${REGISTER_VERSION};swc:${SWC_VERSION}`,
    ].join('\0');
    // xxh64 over a byte Buffer: faster than a crypto hash over strings on this
    // per-file hot path, and 64-bit collision odds are negligible for a transform
    // cache. Matches @swc-node/jest's hashing and standard build-cache practice.
    return (0, xxhash_1.xxh64)(Buffer.from(payload)).toString(16);
}
function getOptionsSignature(options) {
    const cached = optionsSignatureCache.get(options);
    if (cached) {
        return cached;
    }
    // Options are usually reused for most compiles in one process; cache the
    // normalized signature so hash generation stays near O(source length).
    const signature = (0, fast_json_stable_stringify_1.default)(options);
    optionsSignatureCache.set(options, signature);
    return signature;
}
function setMemoryCache(key, value) {
    memoryCache.set(key, value);
    // Bound in-process retention for long-lived services where many modules
    // may be touched once and never needed again.
    while (memoryCache.size > MEMORY_CACHE_LIMIT) {
        const oldestKey = memoryCache.keys().next().value;
        if (!oldestKey) {
            break;
        }
        memoryCache.delete(oldestKey);
    }
}
function readDiskCache(key) {
    try {
        const directory = ensureCacheDirectory();
        const file = node_fs_1.default.readFileSync((0, node_path_2.join)(directory, `${key}.json`), 'utf8');
        return JSON.parse(file);
    }
    catch (error) {
        debug('Failed to read cache file', error);
        return undefined;
    }
}
function writeDiskCache(key, value) {
    const directory = ensureCacheDirectory();
    const target = (0, node_path_2.join)(directory, `${key}.json`);
    // Write to a unique temp file then atomically rename into place. A crash or
    // concurrent writer can then only leave a stray .tmp file, never a
    // partial/zero-byte entry that a reader could observe at the final path.
    // Writes stay non-blocking (fire-and-forget).
    const tmp = `${target}.${process.pid}.${diskWriteCounter++}.tmp`;
    void node_fs_1.default.promises
        .writeFile(tmp, JSON.stringify(value), 'utf8')
        .then(() => node_fs_1.default.promises.rename(tmp, target))
        .catch((error) => {
        debug('Failed to write cache file', error);
        void node_fs_1.default.promises.rm(tmp, { force: true }).catch(() => { });
    });
}
function ensureCacheDirectory() {
    const directory = getCacheDirectory();
    if (ensuredCacheDirectory !== directory) {
        node_fs_1.default.mkdirSync(directory, { recursive: true });
        ensuredCacheDirectory = directory;
    }
    // Note that we do not attempt to clean up old cache files since we store it
    // on tmpdir and we assume the OS take care of that.
    return directory;
}
function readPackageVersion(path) {
    var _a;
    try {
        return (_a = require(path).version) !== null && _a !== void 0 ? _a : 'unknown';
    }
    catch (error) {
        debug(`Failed to read package ${path} version`, error);
        return 'unknown';
    }
}
function isEnabled(value, fallback) {
    if (!value) {
        return fallback;
    }
    const normalized = value.trim().toLowerCase();
    return normalized !== '0' && normalized !== 'false' && normalized !== 'off' && normalized !== 'no';
}
function clearTransformCache(options = {}) {
    const { memory = true, disk = true } = options;
    if (memory) {
        memoryCache.clear();
        optionsSignatureCache = new WeakMap();
    }
    if (disk) {
        try {
            node_fs_1.default.rmSync(getCacheDirectory(), { recursive: true, force: true });
        }
        catch (error) {
            debug('Failed to clear cache directory', error);
        }
        ensuredCacheDirectory = undefined;
    }
}
function getTransformCacheDirectory() {
    return getCacheDirectory();
}
function shouldSkipTransformForRuntimeJs(filename, sourcecode, moduleKind = ts.ModuleKind.ES2015, jsxEnabled = false, swcrcEnabled = Boolean(process.env.SWCRC)) {
    // Respect SWCRC workflows first. When users opt into external SWC config,
    // consistency with that config takes priority over local fast-path heuristics.
    if (swcrcEnabled) {
        return false;
    }
    const extension = node_path_1.default.extname(filename).toLowerCase();
    if (!JS_RUNTIME_EXTENSIONS.has(extension)) {
        return false;
    }
    // JSX in a .js file must be transformed; skipping would ship raw JSX to the
    // runtime and throw a SyntaxError. Never skip when JSX is configured or the
    // source looks like JSX. This guard runs before the module-kind branch so it
    // also protects ESM mode, which would otherwise skip every .js unconditionally.
    if (jsxEnabled || LOOKS_LIKE_JSX_REGEX.test(sourcecode)) {
        return false;
    }
    // In non-CommonJS output modes, runtime JS files are already executable for
    // Node, so compiling them again mostly adds overhead.
    if (moduleKind !== ts.ModuleKind.CommonJS) {
        return true;
    }
    // CommonJS mode is where accidental ESM-in-JS files usually break at runtime,
    // so we keep the transform path only when file content indicates that risk.
    return !LOOKS_LIKE_ESM_SYNTAX_REGEX.test(sourcecode);
}
//# sourceMappingURL=transform-cache.js.map