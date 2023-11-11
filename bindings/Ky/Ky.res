// revalkyr-generated 2023-11-11 11:06:19
// Ky.res

type response

@module("ky") @scope("default")
external get: string => Js.Promise.t<response> = "get"

@send
external text: response => Js.Promise.t<string> = "text"
