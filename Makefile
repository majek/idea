PYTHON=PYTHONPATH=$(PWD) $(PWD)/venv/bin/python

all: venv/.ok \
	out/favicon.ico \
	out/zarowka.png \
	out/32px_grid_bg.gif \
	out/28px_grid_bg.gif \
	out/index.html \
	out/2012-05-27-hello-world/index.html


venv:
	virtualenv venv

venv/.ok: requirements.txt
	./venv/bin/pip install -r requirements.txt
	touch venv/.ok


out:
	mkdir out

out/2012-05-27-hello-world/index.html: $(wildcard site/2012-05-27-hello-world/*) out templates/*
	-rm -rf out/2012-05-27-hello-world
	mkdir out/2012-05-27-hello-world
	(cd site/2012-05-27-hello-world && $(PYTHON) gen.py $(PWD)/out/2012-05-27-hello-world)

out/index.html: $(wildcard site/*/context.yml) site/gen.py $(wildcard site/*) out templates/*
	(cd site && $(PYTHON) gen.py $(PWD)/out)


out/favicon.ico: site/favicon.ico
	cp site/favicon.ico out

out/zarowka.png: site/zarowka.png
	cp site/zarowka.png out

out/32px_grid_bg.gif: site/32px_grid_bg.gif
	cp site/32px_grid_bg.gif out

out/28px_grid_bg.gif: site/28px_grid_bg.gif
	cp site/28px_grid_bg.gif out

run_server:
	$(PYTHON) server.py

serve:
	@if [ -e .pidfile.pid ]; then		\
		kill `cat .pidfile.pid`;	\
		rm .pidfile.pid;		\
	fi

	@while [ 1 ]; do				\
		make all;				\
		echo " [*] Running http server";	\
		$(PYTHON) server.py & 			\
		SRVPID=$$!;				\
		echo $$SRVPID > .pidfile.pid;		\
		echo " [*] Server pid: $$SRVPID";	\
		inotifywait -r -q -e modify site templates common;	\
		kill `cat .pidfile.pid`;		\
		rm -f .pidfile.pid;			\
		sleep 0.1;				\
	done
