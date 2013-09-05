var net = require('net');

var server = net.createServer();
server.on('connection', function(c) {
    c.pipe(c);
    c.on('data', function(d) {
        console.log('received', d.length);
    });
    c.on('drain', function(d) {
        console.log('it\'s okay to receive');
    });
    var p = c.push;
    c.push = function(chunk) {
        var r = p.apply(c, [chunk]);
        if (r == false)
            console.log('stop receiving now!');
        return r;
    }
});
server.listen(10007);
