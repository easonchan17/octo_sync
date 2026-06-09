(function () {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    script.onload = function () { this.remove(); };
    (document.head || document.documentElement).appendChild(script);

    window.addEventListener('message', function (event) {
        if (event.source !== window || !event.data || event.data.type !== 'OCTOPUS_CAPTURE') {
            return;
        }
        chrome.runtime.sendMessage({
            type: 'UPLOAD_CAPTURE',
            url: event.data.url,
            pageUrl: window.location.href,
            data: event.data.data
        });
    });
})();
