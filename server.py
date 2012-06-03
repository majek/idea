import tornado.ioloop
import tornado.web
import tornado.websocket
import os

print 'x ', os.getpid()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        print "WebSocket opened"

    def on_message(self, message):
        self.write_message(u"You said: " + message)

    def on_close(self):
        print "WebSocket closed"

application = tornado.web.Application([
    (r"/ws",  EchoWebSocket),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": "out", "default_filename":"index.html"}),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
