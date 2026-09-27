/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public URL of the API when the UI is hosted on its own (see web/.env.example). */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
