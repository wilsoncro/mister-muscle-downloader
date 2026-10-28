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
var _a, _b;
Object.defineProperty(exports, "__esModule", { value: true });
exports.compile = compile;
exports.register = register;
const core_1 = require("@swc-node/core");
const sourcemap_support_1 = require("@swc-node/sourcemap-support");
const pirates_1 = require("pirates");
const ts = __importStar(require("typescript"));
const read_default_tsconfig_1 = require("./read-default-tsconfig");
const transform_cache_1 = require("./transform-cache");
const DEFAULT_EXTENSIONS = new Set([
    ts.Extension.Js,
    ts.Extension.Ts,
    ts.Extension.Jsx,
    ts.Extension.Tsx,
    ts.Extension.Mjs,
    ts.Extension.Mts,
    ts.Extension.Cjs,
    ts.Extension.Cts,
    '.es6',
    '.es',
]);
// Runtime knobs here are process-scoped and comparatively cheap to read, so
// they gate cache safety without paying per-module deep serialization costs.
// Every env var that changes transform output must appear here, otherwise a
// warm cache would serve output produced under a different configuration.
const CacheRuntimeSalt = [
    process.env.SWCRC ? 'swcrc=1' : 'swcrc=0',
    `swcConfig=${(_a = process.env.SWC_CONFIG_FILE) !== null && _a !== void 0 ? _a : ''}`,
    `sourceMapMode=${(_b = process.env.SWC_NODE_SOURCE_MAP_MODE) !== null && _b !== void 0 ? _b : 'auto'}`,
    // Toggles import()/import.meta rewriting, so it changes emitted code.
    `ignoreDynamic=${process.env.SWC_NODE_IGNORE_DYNAMIC ? '1' : '0'}`,
].join(';');
const injectInlineSourceMap = ({ filename, code, map, }) => {
    if (!map) {
        return code;
    }
    // Choose map storage strategy at emit time so one process can tune behavior
    // per runtime profile (debuggability vs memory) without rebuilds.
    const sourceMapMode = (0, read_default_tsconfig_1.getSourceMapMode)();
    if (sourceMapMode.store) {
        sourcemap_support_1.SourcemapMap.set(filename, map);
    }
    if (sourceMapMode.inline) {
        const base64Map = Buffer.from(map, 'utf8').toString('base64');
        const sourceMapContent = `//# sourceMappingURL=data:application/json;charset=utf-8;base64,${base64Map}`;
        return `${code}\n${sourceMapContent}`;
    }
    return code;
};
function compile(sourcecode, filename, options, async = false) {
    if (sourcecode == null) {
        return;
    }
    const fallbackToTs = Boolean(options && typeof options.fallbackToTs === 'function' && options.fallbackToTs(filename));
    delete options.fallbackToTs;
    // Preserve the overloaded return contract: an async caller may `.then()` the
    // result, so every synchronous return below must be wrapped when async.
    const finalize = (result) => (async ? Promise.resolve(result) : result);
    // Fast-path before cache work for files intentionally left as runtime JS.
    // This keeps cache logs meaningful and avoids unnecessary key generation.
    if (!fallbackToTs && (0, transform_cache_1.shouldSkipTransformForRuntimeJs)(filename, sourcecode, options.module, Boolean(options.jsx))) {
        return finalize(sourcecode);
    }
    const cacheInput = {
        sourcecode,
        filename,
        options,
        fallbackToTs,
        runSalt: CacheRuntimeSalt,
    };
    const cacheKey = (0, transform_cache_1.createCacheKey)(cacheInput);
    const cacheEntry = (0, transform_cache_1.getCachedTransform)(cacheKey);
    if (cacheEntry) {
        // Keep source-map behavior consistent for cache hits, otherwise stack trace
        // semantics would differ between warm and cold compiles.
        return finalize(injectInlineSourceMap({ filename, code: cacheEntry.code, map: cacheEntry.map }));
    }
    if (fallbackToTs) {
        const { outputText, sourceMapText } = ts.transpileModule(sourcecode, {
            fileName: filename,
            compilerOptions: options,
        });
        (0, transform_cache_1.setCachedTransform)(cacheKey, { code: outputText, map: sourceMapText });
        return finalize(injectInlineSourceMap({ filename, code: outputText, map: sourceMapText }));
    }
    let swcRegisterConfig;
    if (process.env.SWCRC) {
        // when SWCRC environment variable is set to true it will use swcrc file
        swcRegisterConfig = {
            swc: {
                swcrc: true,
                configFile: process.env.SWC_CONFIG_FILE,
            },
        };
    }
    else {
        swcRegisterConfig = (0, read_default_tsconfig_1.tsCompilerOptionsToSwcConfig)(options, filename);
    }
    if (async) {
        return (0, core_1.transform)(sourcecode, filename, swcRegisterConfig).then(({ code, map }) => {
            (0, transform_cache_1.setCachedTransform)(cacheKey, { code, map });
            return injectInlineSourceMap({ filename, code, map });
        });
    }
    else {
        const { code, map } = (0, core_1.transformSync)(sourcecode, filename, swcRegisterConfig);
        (0, transform_cache_1.setCachedTransform)(cacheKey, { code, map });
        return injectInlineSourceMap({ filename, code, map });
    }
}
function register(options = {}, hookOpts = {}) {
    if (!process.env.SWCRC) {
        options = Object.keys(options).length ? options : (0, read_default_tsconfig_1.readDefaultTsConfig)();
    }
    options.module = ts.ModuleKind.CommonJS;
    // Install source-map-support only when map-store mode is active; with inline
    // mode and native source maps, this avoids duplicate map retention.
    if ((0, read_default_tsconfig_1.getSourceMapMode)().store) {
        (0, sourcemap_support_1.installSourceMapSupport)();
    }
    return (0, pirates_1.addHook)((code, filename) => compile(code, filename, options), {
        exts: Array.from(DEFAULT_EXTENSIONS),
        ...hookOpts,
    });
}
//# sourceMappingURL=register.js.map