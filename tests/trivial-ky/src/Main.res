let url = "http://worldtimeapi.org/api/ip"
let () = ignore(
  Ky.get(url)
  ->Ky.text
  ->Js.Promise2.then(async res => {
    Js.Console.log(res)
  }),
)
