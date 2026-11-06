import express from "express";
import { v4 as uuidv4 } from "uuid";

const app = express();

app.get("/api/health", (req, res) => {
  res.json({ status: "ok", id: uuidv4() });
});

app.listen(3000, () => {
  console.log("Server started");
});
