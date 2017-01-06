<%inherit file="basecomment.html"/>

<%block filter="filters.markdown">


neighbor 127.0.0.1 {
	router-id 127.0.0.2;
	local-address 127.0.0.2;
	local-as 65002;
	peer-as 65001;
	graceful-restart;
}

neighbor 127.0.0.2 {
	router-id 127.0.0.1;
	local-address 127.0.0.1;
	local-as 65001;
	peer-as 65002;
	graceful-restart;
}

env exabgp.tcp.bind="127.0.0.1" exabgp.tcp.port=1790 ./venv/bin/exabgp b.conf
env exabgp.tcp.bind="127.0.0.2" exabgp.tcp.port=1790 ./venv/bin/exabgp c.conf


        session classical-ebgp {
                router-id     10.0.0.1
                hold-time     180
                asn {
                        local  12345
                        peer   54321
                }
                capability {
                        family {
                                ipv4 [
                                        unicast
                                        multicast
                                        flow
                                ]
                        }
                        asn4 enable
                        route-refresh enable
                        graceful-restart 60
                }
        }



</%block>
