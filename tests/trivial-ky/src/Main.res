let url = "http://worldtimeapi.org/api/ip"
let foo = async () => {
  let a =await Ky.get(url)
  let b = await a->Ky.text
  Js.Console.log(b)
}

let () = ignore(foo())
