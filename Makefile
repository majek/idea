PYTHON=PYTHONPATH=$(PWD) $(PWD)/venv/bin/python

all: venv/.ok \
	out \
	out/index.html \
	$(subst site,out,$(wildcard site/20*))


venv:
	virtualenv venv

venv/.ok: venv requirements.txt
	./venv/bin/pip install -r requirements.txt
	touch venv/.ok

out:
	mkdir out

out/20%: site/20% $(wildcard site/20%/*) templates/* common/*py
	@-rm -rf "$@"
	@mkdir "$@"
	(cd "$<" && $(PYTHON) gen.py $(PWD)/$@)


# Assuming: files have dot in the name, directories don't
out/index.html: $(wildcard site/*/context.yml) $(wildcard site/*.*) templates/*
	(cd site && $(PYTHON) gen.py $(PWD)/out)



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
