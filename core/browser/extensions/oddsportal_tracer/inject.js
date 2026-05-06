(function() {
    const _origParse = JSON.parse;
    JSON.parse = new Proxy(_origParse, {
        apply(target, thisArg, args) {
            const result = Reflect.apply(target, thisArg, args);
            try {
                if (result && typeof result === 'object' && result.d) {
                    const data = result.d
                    if (data.oddsdata) {
                        navigator.sendBeacon('/__app_trace__/odds/', JSON.stringify({
                            url: window.location.href,
                            data: result
                        }));
                    } else if (data.football_all) {
                        navigator.sendBeacon('/__app_trace__/leagues/', JSON.stringify({
                            url: window.location.href,
                            data: result
                        }));
                    } else if (data.pagination && data.pagination.url && data.pagination.url.startsWith('https://www.oddsportal.com/ajax-sport-country-tournament-archive_')) {
                        navigator.sendBeacon('/__app_trace__/fixtures/', JSON.stringify({
                            url: window.location.href,
                            data: result
                        }));
                    }
                }
            } catch (e) {}
            return result;
        }
    });
})();
