import '@testing-library/jest-dom';

if (typeof globalThis.localStorage === 'undefined' || !globalThis.localStorage.getItem) {
  const store: Record<string, string> = {};
  globalThis.localStorage = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = String(value); },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    key: (i: number) => Object.keys(store)[i] || null,
    length: 0,
  } as Storage;
}
