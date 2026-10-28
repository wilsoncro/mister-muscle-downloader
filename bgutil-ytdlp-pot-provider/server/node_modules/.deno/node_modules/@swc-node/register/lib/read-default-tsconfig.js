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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSourceMapMode = getSourceMapMode;
exports.readDefaultTsConfig = readDefaultTsConfig;
exports.tsCompilerOptionsToSwcConfig = tsCompilerOptionsToSwcConfig;
const fs_1 = require("fs");
const path_1 = require("path");
const colorette_1 = require("colorette");
const debug_1 = __importDefault(require("debug"));
const ts = __importStar(require("typescript"));
const debug = (0, debug_1.default)('@swc-node');
const configCache = {};
// Keep compatibility with the legacy SWC_NODE_INLINE_SOURCE_MAP env by
// mapping it to SWC_NODE_SOURCE_MAP_MODE=inline.
if (typeof process.env.SWC_NODE_INLINE_SOURCE_MAP === 'string') {
    process.env.SWC_NODE_SOURCE_MAP_MODE = 'inline';
}
function getSourceMapMode() {
    var _a;
    switch ((_a = process.env.SWC_NODE_SOURCE_MAP_MODE) === null || _a === void 0 ? void 0 : _a.trim().toLowerCase()) {
        case 'both':
            return { inline: true, store: true };
        case 'inline':
            return { inline: true, store: false };
        case 'store':
            return { inline: false, store: true };
        case 'none':
            return { inline: false, store: false };
    }
    // In auto mode, always inline the map: the V8 inspector reads the inline
    // sourceMappingURL off the running code to bind breakpoints, and it does so
    // regardless of `process.sourceMapsEnabled` (which only governs how Node
    // rewrites Error.stack). Gating inline emission on that flag broke debuggers
    // in 1.12.0 (https://github.com/swc-project/swc-node/issues/1059).
    //
    // Additionally store the map when native source maps are off so
    // @swc-node/sourcemap-support keeps Error.stack line numbers correct; when
    // native maps are on, Node handles stack traces and storing would just retain
    // a duplicate map.
    return process.sourceMapsEnabled ? { inline: true, store: false } : { inline: true, store: true };
}
function readDefaultTsConfig(tsConfigPath) {
    var _a, _b;
    if (tsConfigPath === void 0) { tsConfigPath = (_b = (_a = process.env.SWC_NODE_PROJECT) !== null && _a !== void 0 ? _a : process.env.TS_NODE_PROJECT) !== null && _b !== void 0 ? _b : (0, path_1.join)(process.cwd(), 'tsconfig.json'); }
    let compilerOptions = {
        target: ts.ScriptTarget.ES2018,
        module: ts.ModuleKind.CommonJS,
        moduleResolution: ts.ModuleResolutionKind.NodeJs,
        sourceMap: true,
        esModuleInterop: true,
    };
    if (!tsConfigPath) {
        return compilerOptions;
    }
    const fullTsConfigPath = (0, path_1.resolve)(tsConfigPath);
    if (fullTsConfigPath in configCache) {
        return configCache[fullTsConfigPath];
    }
    if (!(0, fs_1.existsSync)(fullTsConfigPath)) {
        return compilerOptions;
    }
    try {
        debug(`Read config file from ${fullTsConfigPath}`);
        const { config } = ts.readConfigFile(fullTsConfigPath, ts.sys.readFile);
        const { options, errors, fileNames } = ts.parseJsonConfigFileContent(config, ts.sys, (0, path_1.dirname)(fullTsConfigPath));
        // if baseUrl not set, use dirname of tsconfig.json. align with ts https://www.typescriptlang.org/tsconfig#paths
        if (options.paths && !options.baseUrl) {
            options.baseUrl = (0, path_1.dirname)(fullTsConfigPath);
        }
        if (!errors.length) {
            compilerOptions = options;
            compilerOptions.files = fileNames;
        }
        else {
            console.info((0, colorette_1.yellow)(`Convert compiler options from json failed, ${errors.map((d) => d.messageText).join('\n')}`));
        }
    }
    catch (e) {
        console.info((0, colorette_1.yellow)(`Read ${tsConfigPath} failed: ${e.message}`));
    }
    configCache[fullTsConfigPath] = compilerOptions;
    return compilerOptions;
}
function toTsTarget(target) {
    switch (target) {
        case ts.ScriptTarget.ES3:
            return 'es3';
        case ts.ScriptTarget.ES5:
            return 'es5';
        case ts.ScriptTarget.ES2015:
            return 'es2015';
        case ts.ScriptTarget.ES2016:
            return 'es2016';
        case ts.ScriptTarget.ES2017:
            return 'es2017';
        case ts.ScriptTarget.ES2018:
            return 'es2018';
        case ts.ScriptTarget.ES2019:
            return 'es2019';
        case ts.ScriptTarget.ES2020:
            return 'es2020';
        case ts.ScriptTarget.ES2021:
            return 'es2021';
        case ts.ScriptTarget.ES2022:
            return 'es2022';
        case ts.ScriptTarget.ES2023:
            return 'es2023';
        case ts.ScriptTarget.ES2024:
        case ts.ScriptTarget.ESNext:
        case ts.ScriptTarget.Latest:
            return 'es2024';
        case ts.ScriptTarget.JSON:
            return 'es5';
    }
}
function toModule(moduleKind) {
    switch (moduleKind) {
        case ts.ModuleKind.CommonJS:
            return 'commonjs';
        case ts.ModuleKind.UMD:
            return 'umd';
        case ts.ModuleKind.AMD:
            return 'amd';
        case ts.ModuleKind.ES2015:
        case ts.ModuleKind.ES2020:
        case ts.ModuleKind.ES2022:
        case ts.ModuleKind.ESNext:
        case ts.ModuleKind.Node16:
        case ts.ModuleKind.NodeNext:
        case ts.ModuleKind.None:
            return 'es6';
        case ts.ModuleKind.System:
            throw new TypeError('Do not support system kind module');
    }
}
/**
 * The default value for useDefineForClassFields depends on the emit target
 * @see https://www.typescriptlang.org/tsconfig#useDefineForClassFields
 */
function getUseDefineForClassFields(compilerOptions, target) {
    var _a;
    return (_a = compilerOptions.useDefineForClassFields) !== null && _a !== void 0 ? _a : target >= ts.ScriptTarget.ES2022;
}
function tsCompilerOptionsToSwcConfig(options, filename) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o;
    const isJsx = filename.endsWith('.tsx') || filename.endsWith('.jsx') || Boolean(options.jsx);
    const target = (_a = options.target) !== null && _a !== void 0 ? _a : ts.ScriptTarget.ES2018;
    const sourceMapModeName = (_b = process.env.SWC_NODE_SOURCE_MAP_MODE) === null || _b === void 0 ? void 0 : _b.trim().toLowerCase();
    const enableInlineSourceMap = (_c = options.inlineSourceMap) !== null && _c !== void 0 ? _c : (sourceMapModeName === 'inline' ? true : undefined);
    const shouldEmitSourceMap = Boolean(options.sourceMap || enableInlineSourceMap);
    return {
        module: toModule((_d = options.module) !== null && _d !== void 0 ? _d : ts.ModuleKind.ES2015),
        target: toTsTarget(target),
        jsx: isJsx,
        sourcemap: enableInlineSourceMap ? 'inline' : shouldEmitSourceMap,
        experimentalDecorators: (_e = options.experimentalDecorators) !== null && _e !== void 0 ? _e : false,
        emitDecoratorMetadata: (_f = options.emitDecoratorMetadata) !== null && _f !== void 0 ? _f : false,
        useDefineForClassFields: getUseDefineForClassFields(options, target),
        esModuleInterop: (_g = options.esModuleInterop) !== null && _g !== void 0 ? _g : false,
        dynamicImport: true,
        keepClassNames: true,
        externalHelpers: Boolean(options.importHelpers),
        react: ((_k = (_j = (_h = options.jsxFactory) !== null && _h !== void 0 ? _h : options.jsxFragmentFactory) !== null && _j !== void 0 ? _j : options.jsx) !== null && _k !== void 0 ? _k : options.jsxImportSource)
            ? {
                pragma: options.jsxFactory,
                pragmaFrag: options.jsxFragmentFactory,
                importSource: (_l = options.jsxImportSource) !== null && _l !== void 0 ? _l : 'react',
                runtime: ((_m = options.jsx) !== null && _m !== void 0 ? _m : 0) >= ts.JsxEmit.ReactJSX ? 'automatic' : 'classic',
                useBuiltins: true,
            }
            : undefined,
        baseUrl: options.baseUrl ? (0, path_1.resolve)(options.baseUrl) : undefined,
        paths: Object.fromEntries(Object.entries((_o = options.paths) !== null && _o !== void 0 ? _o : {}).map(([aliasKey, aliasPaths]) => {
            var _a;
            return [
                aliasKey,
                ((_a = aliasPaths) !== null && _a !== void 0 ? _a : []).map((path) => { var _a; return (0, path_1.resolve)((_a = options.baseUrl) !== null && _a !== void 0 ? _a : './', path); }),
            ];
        })),
        ignoreDynamic: Boolean(process.env.SWC_NODE_IGNORE_DYNAMIC),
        swc: {
            sourceRoot: options.sourceRoot,
            inputSourceMap: enableInlineSourceMap,
        },
    };
}
//# sourceMappingURL=read-default-tsconfig.js.map