import { type Options as SwcOptions, type ReactConfig, type Config, type JscTarget, type TransformConfig as SwcTransformConfig } from '@swc/core';
export interface Options {
    target?: JscTarget;
    module?: 'commonjs' | 'umd' | 'amd' | 'es6';
    sourcemap?: Config['sourceMaps'];
    jsx?: boolean;
    experimentalDecorators?: boolean;
    decoratorVersion?: SwcTransformConfig['decoratorVersion'];
    emitDecoratorMetadata?: boolean;
    useDefineForClassFields?: boolean;
    dynamicImport?: boolean;
    esModuleInterop?: boolean;
    keepClassNames?: boolean;
    externalHelpers?: boolean;
    /**
     * Minify (compress) the transpiled output. Off by default: `@swc-node/core`
     * emits readable code, and consumers such as `@swc-node/register` cache and
     * execute that output directly. Opt in when smaller output matters more than
     * readability (e.g. shrinking an on-disk transform cache).
     */
    minify?: boolean;
    react?: Partial<ReactConfig>;
    baseUrl?: string;
    paths?: {
        [from: string]: [string];
    };
    swc?: SwcOptions;
    ignoreDynamic?: boolean;
}
export declare function transformSync(source: string, path: string, options?: Options): import("@swc/types").Output;
export declare function transformJest(source: string, path: string, options?: Options): import("@swc/types").Output;
export declare function transform(source: string, path: string, options?: Options): Promise<import("@swc/types").Output>;
