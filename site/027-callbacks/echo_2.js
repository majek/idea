var net = require('net');

var server = net.createServer();
server.on('connection', function(c) {
    c.pipe(c);
});
server.listen(10007);
