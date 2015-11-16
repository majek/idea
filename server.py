import tornado.ioloop
import tornado.web
import tornado.websocket
import os


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        pass

    def on_message(self, message):
        pass

    def on_close(self):
        pass

application = tornado.web.Application([
    (r"/ws",  EchoWebSocket),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": "out", "default_filename":"index.html"}),
])

if __name__ == "__main__":
    print ' [*] listening on 0.0.0.0:8887 pid=%r' % (os.getpid(),)
    application.listen(8887)
    tornado.ioloop.IOLoop.instance().start()
