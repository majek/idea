var show_alert = function(msg){
    document.getElementById('alertbox').style.display="block";
    document.getElementById('alert').innerHTML = msg;

};

if (document.location.href.indexOf('idea.popcount.org') === -1) {
    var counter = 0;

    var ws_url = function(){
        return ((document.location.protocol === 'http:') ? 'ws://' : 'wss://') +
            document.location.host + '/ws';
    }

    var try_reconnect = function(){
        counter += 1;
        show_alert('Reconnecting... (' + counter + ')');
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
}

// Escape frames for browsers without X-Frame-Options
if (top != window) {
    top.location.href = location.href;
}


var _debug = 0;
var flip_debug = function(){
    var leading = 28;
    var bg = ""
    if (!_debug) {
            bg = "url('/" + leading + "px_grid_bg.gif') 0 0";
    }
    _debug = !_debug;
    document.body.style.background = bg;
}

if ('captureEvents' in window) {
    window.captureEvents(Event.KEYPRESS);
    window.onkeypress = function(e) {
        if (e.which === 100) { // key "d"
            flip_debug();
        }
    };
};
