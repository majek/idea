// reconnect.js

var ws_url = function(){
    return ((document.location.protocol === 'http:') ? 'ws://' : 'wss://') +
        document.location.host + '/ws';
}

var try_reconnect = function(){
    console.log('[*] reconnecting...');
    setTimeout(function(){
        ws = new WebSocket(ws_url());
        ws.onclose = try_reconnect;
        ws.onopen = function(){
            ws.onclose = null;
            document.location.reload();
        };
    }, 150);
};

if ('WebSocket' in window && 'console' in window){
    var ws = new WebSocket(ws_url());
    ws.onopen = function(){
        console.log('[*] ws hooked! ' + Date());
        ws.onclose = try_reconnect;
    };
}
