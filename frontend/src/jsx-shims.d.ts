// Allow importing untyped .jsx component files from TS route files.
declare module "*.jsx" {
  const component: any;
  export default component;
  export const __esModule: true;
}

declare module "*.module.css" {
  const classes: Record<string, string>;
  export default classes;
}