(function () {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    script.onload = function () { this.remove(); };
    (document.head || document.documentElement).appendChild(script);

    window.addEventListener('message', function (event) {
        if (event.source !== window || event.origin !== 'https://www.fotmob.com' || !event.data || event.data.type !== 'OCTOPUS_CAPTURE') {
            return;
        }

        var captureKey = 'capture_' + Date.now() + '_' + Math.floor(Math.random() * 100000);
        var captureData = { url: event.data.url, pageUrl: window.location.href, data: event.data.data };

        chrome.storage.local.set({ [captureKey]: captureData }, function () {
            try {
                chrome.runtime.sendMessage({ type: 'UPLOAD_CAPTURE', captureKey: captureKey });
            } catch (e) {
                chrome.storage.local.remove(captureKey);
            }
        });
    });
})();
