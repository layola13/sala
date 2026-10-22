package main

import (
	"fmt"
	"net/http"
	"os"
)

func main() {
	addr := "127.0.0.1:18094"
	if len(os.Args) > 1 {
		addr = os.Args[1]
	}
	body := []byte("ok")
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		w.Header().Set("Content-Length", "2")
		w.Write(body)
	})
	fmt.Println("listen", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		panic(err)
	}
}
