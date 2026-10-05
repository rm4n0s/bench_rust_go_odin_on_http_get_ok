package main

import (
	"log"

	"github.com/valyala/fasthttp"
)

func main() {
	handler := func(ctx *fasthttp.RequestCtx) {
		if !ctx.IsGet() {
			ctx.SetStatusCode(fasthttp.StatusMethodNotAllowed)
			return
		}
		ctx.SetContentType("text/plain; charset=utf-8")
		switch string(ctx.Path()) {
		case "/":
		case "/health":
			ctx.SetBodyString("ok")
		default:
			ctx.SetStatusCode(fasthttp.StatusNotFound)
		}
	}
	log.Fatal(fasthttp.ListenAndServe("0.0.0.0:8080", handler))
}
