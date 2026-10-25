const form = document.querySelector("#review");
const status = document.querySelector("#status");
const out = document.querySelector("#out");

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function card(title, pass) {
  const node = document.createElement("article");
  node.className = "card";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const meta = document.createElement("p");
  meta.className = "meta";
  const usage = pass.usage || {};
  meta.textContent = [
    pass.model,
    pass.ms + " ms",
    (usage.prompt_tokens || 0) + " in",
    (usage.completion_tokens || 0) + " out",
  ].join(" · ");
  node.append(heading, meta);
  (pass.issues || []).forEach((issue) => {
    const line = document.createElement("p");
    line.textContent = issue.severity + ": " + issue.why;
    node.appendChild(line);
  });
  if (pass.error) {
    const err = document.createElement("p");
    err.textContent = pass.error;
    node.appendChild(err);
  }
  if (pass.revision) {
    const code = document.createElement("pre");
    code.textContent = pass.revision;
    node.appendChild(code);
  }
  return node;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "Calling Token Factory…";
  clear(out);
  out.hidden = true;
  const response = await fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: new FormData(form).get("source") }),
  });
  const payload = await response.json();
  if (!response.ok) {
    status.textContent = payload.error || "Request failed.";
    return;
  }
  status.textContent = payload.routed_to_super ? "Super ran." : "Nano was enough. Super did not run.";
  out.appendChild(card("Nano", payload.nano));
  if (payload.super) out.appendChild(card("Super", payload.super));
  out.hidden = false;
});

fetch("/api/health").then((r) => r.json()).then((health) => {
  if (!health.token_factory) status.textContent = "No NEBIUS_API_KEY on the server yet.";
}).catch(() => {});
