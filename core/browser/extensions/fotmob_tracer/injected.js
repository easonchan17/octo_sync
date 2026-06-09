(function () {
    const MATCH_DETAILS_PATTERN = /\/api\/data\/matchDetails/;
    const originalFetch = window.fetch;

    window.fetch = async function (...args) {
        const response = await originalFetch.apply(this, args);
        const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');

        if (MATCH_DETAILS_PATTERN.test(url)) {
            response.clone().json().then(function (data) {
                window.postMessage({ type: 'OCTOPUS_CAPTURE', url: url, data: data }, '*');
            }).catch(function () {});
        }

        return response;
    };
})();
