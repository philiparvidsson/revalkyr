let mongoDbUri = "mongodb://localhost:27017"

let () = ignore(
  Mongoose.connect(mongoDbUri)->Js.Promise2.then(x => {
    Js.Console.log2("Well, something happened", x)
    Node.Process.exit(0)
    Js.Promise2.resolve()
  }),
)
