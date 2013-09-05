// You can edit this code!
// Click here and start typing.
package main

import (
	"bufio"
	"flag"
	"fmt"
	"net"
)

func main() {
	fmt.Println("a")
	var host_port *string = flag.String("host", "localhost:9999", "Target host:port")

	fmt.Printf("Host: %q %s\n", *host_port)

	conn, err := net.Dial("tcp", "google.com:80")
	if err != nil {
		// handle error
	}
	status, err := bufio.NewReader(conn).ReadString('\n')
	status = status

}
