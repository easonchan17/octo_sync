document.addEventListener('DOMContentLoaded', function () {
    chrome.storage.local.get(['serverUrl', 'adminUsername', 'adminPassword', 'allowedPageUrls'], function (config) {
        if (config.serverUrl) document.getElementById('serverUrl').value = config.serverUrl;
        if (config.adminUsername) document.getElementById('adminUsername').value = config.adminUsername;
        if (config.adminPassword) document.getElementById('adminPassword').value = config.adminPassword;
        if (config.allowedPageUrls) document.getElementById('allowedPageUrls').value = config.allowedPageUrls.join('\n');
    });

    document.getElementById('save').addEventListener('click', function () {
        var allowedPageUrls = document.getElementById('allowedPageUrls').value
            .split('\n')
            .map(function (line) { return line.trim(); })
            .filter(function (line) { return line.length > 0; });

        var config = {
            serverUrl: document.getElementById('serverUrl').value.trim().replace(/\/$/, ''),
            adminUsername: document.getElementById('adminUsername').value.trim(),
            adminPassword: document.getElementById('adminPassword').value,
            allowedPageUrls: allowedPageUrls
        };

        chrome.storage.local.set(config, function () {
            var status = document.getElementById('status');
            status.textContent = 'Saved';
            setTimeout(function () { status.textContent = ''; }, 2000);
        });
    });
});
