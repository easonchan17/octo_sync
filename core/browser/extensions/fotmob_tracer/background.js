async function handleUpload(captureKey) {
    const stored = await chrome.storage.local.get(captureKey);
    const capture = stored[captureKey];

    if (!capture) {
        return;
    }

    await chrome.storage.local.remove(captureKey);

    const config = await chrome.storage.local.get(['serverUrl', 'adminUsername', 'adminPassword', 'allowedPageUrls']);

    if (!config.serverUrl || !config.adminUsername || !config.adminPassword) {
        console.warn('[Octopus] Server config not set — open extension popup to configure');
        return;
    }

    const allowedPageUrls = new Set(config.allowedPageUrls || []);
    if (!allowedPageUrls.has(capture.pageUrl)) {
        return;
    }

    const credentials = btoa(config.adminUsername + ':' + config.adminPassword);

    const response = await fetch(config.serverUrl + '/admin/raw/match/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + credentials
        },
        body: JSON.stringify({ url: capture.url, data: capture.data })
    });

    if (!response.ok) {
        const text = await response.text();
        console.error('[Octopus] Upload failed ' + response.status + ': ' + text);
        return;
    }

    const result = await response.json();
    console.log('[Octopus] Uploaded match_id=' + result.match_id);
}

chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    if (message.type !== 'UPLOAD_CAPTURE') {
        return;
    }

    handleUpload(message.captureKey).catch(function (error) {
        console.error('[Octopus] Upload error:', error);
    });

    return true;
});
