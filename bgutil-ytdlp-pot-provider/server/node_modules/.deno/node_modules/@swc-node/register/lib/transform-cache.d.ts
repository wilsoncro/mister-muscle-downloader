import * as ts from 'typescript';
interface TransformCacheEntry {
    code: string;
    map?: string;
}
interface TransformCacheKeyInput {
    sourcecode: string;
    filename: string;
    options: Record<string, unknown>;
    fallbackToTs: boolean;
    runSalt: string;
}
export declare function getCachedTransform(cacheKey: string): TransformCacheEntry | undefined;
export declare function setCachedTransform(cacheKey: string, value: TransformCacheEntry): void;
export declare function createCacheKey(input: TransformCacheKeyInput): string;
export declare function clearTransformCache(options?: {
    memory?: boolean;
    disk?: boolean;
}): void;
export declare function getTransformCacheDirectory(): string;
export declare function shouldSkipTransformForRuntimeJs(filename: string, sourcecode: string, moduleKind?: ts.ModuleKind, jsxEnabled?: boolean, swcrcEnabled?: boolean): boolean;
export {};
