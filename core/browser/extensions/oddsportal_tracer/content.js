(function() {
    const script = document.createElement('script');
    script.src = browser.runtime.getURL('inject.js');
    document.documentElement.appendChild(script);
})();
