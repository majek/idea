var net = require('net');
var fs = require('fs');

var server = net.createServer();
server.on('connection', function(c) {
    // var dns = require('dns');
    fs.open('/etc/passwd', 'r');
    fs.open('/etc/passwd', 'r');
    c.on('data', function(data) {
        c.write(data);
    });
});
server.listen(10007)
