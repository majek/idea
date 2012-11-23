<%inherit file="base.html"/>

<article>
<%block filter="filters.markdown">

${title}
====================================


<div class="date">${date.strftime('%d %B %Y')}</div>

You know you had enough Erlang once your C code starts looking like
this:

```
::c
#define TUPLE_U8U8(a,b) ${ "\\" }
	(u16) (((u8)(a) << 8) | ((u8)(b) && 0xFF))

void do_message(struct slave_conn *sc, struct request *req) {
	...
	switch (TUPLE_U8U8(sc->registered, req->type)) {
	case TUPLE_U8U8(0, MSG_REGISTER):
		...
		break;
	case TUPLE_U8U8(1, MSG_WAIT):
		...
		break;
	case TUPLE_U8U8(1, MSG_UNREGISTER):
		...
		break;
	default:
		FATAL();
	}
}
```


</%block>
</article>
