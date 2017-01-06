var http = require('http');

var server = http.createServer();
server.on('request', function(req, res) {
    res.writeHead(404);
    res.end();
});
server.listen(10007);
