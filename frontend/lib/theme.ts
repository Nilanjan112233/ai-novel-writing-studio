export const THEME_STORAGE_KEY = 'novelforge:theme'

/** Inline script for <head>: applies the saved or system theme before first paint. */
export const themeBootScript = `(function(){try{var t=localStorage.getItem('${THEME_STORAGE_KEY}');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');}catch(e){}})();`
