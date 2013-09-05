package main

import (
	"net"
)

func main() {
	c := make(chan int)
	for i := 0; i < 1; i++ {
		go func() {
			conn, err := net.Dial("tcp", "localhost:10007")
			if err != nil {
				panic("net error")
			}
			a := make([]byte, 512*1024)
			for {
				conn.Write(a)
			}
		}()
	}
	<- c
}
