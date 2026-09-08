// SYNTHETIC bootstrap fixture; existing tests still assert each business request.
export function withSession(fetchMock: typeof fetch): typeof fetch {
  return (input, init) => String(input) === "/api/bootstrap"
    ? Promise.resolve(new Response(JSON.stringify({ session_token: "SYNTHETIC-session" })))
    : fetchMock(input, init);
}
