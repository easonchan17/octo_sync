chrome.runtime.onMessage.addListener(function (message) {
    if (message.type !== 'UPLOAD_CAPTURE') {
        return;
    }

    chrome.storage.local.get(['serverUrl', 'adminUsername', 'adminPassword', 'allowedPageUrls'], function (config) {
        if (!config.serverUrl || !config.adminUsername || !config.adminPassword) {
            console.warn('[Octopus] Server config not set — open extension popup to configure');
            return;
        }

        const allowedPageUrls = config.allowedPageUrls || [];
        if (allowedPageUrls.length > 0 && !allowedPageUrls.some(function (allowed) { return message.pageUrl === allowed; })) {
            return;
        }

        const credentials = btoa(config.adminUsername + ':' + config.adminPassword);

        fetch(config.serverUrl + '/admin/raw/match/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + credentials
            },
            body: JSON.stringify({ url: message.url, data: message.data })
        }).then(function (response) {
            if (!response.ok) {
                return response.text().then(function (text) {
                    console.error('[Octopus] Upload failed ' + response.status + ': ' + text);
                });
            }
            return response.json().then(function (result) {
                console.log('[Octopus] Uploaded match_id=' + result.match_id);
            });
        }).catch(function (error) {
            console.error('[Octopus] Upload error:', error);
        });
    });
});
