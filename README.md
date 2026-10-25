# Two Speed

A code review that spends the small NVIDIA model first.

Paste one Python function. [Nemotron 3 Nano](https://tokenfactory.nebius.com/) (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`) on Nebius Token Factory returns a JSON review and a revision. [Nemotron 3 Super](https://tokenfactory.nebius.com/) (`nvidia/nemotron-3-super-120b-a12b`) runs only when Nano marks a high-severity behavior bug, or when Nano's reply is not JSON. The page shows the model id, latency, and token counts for each call that actually happened.

The snippet is not executed. The server sends it to `https://api.tokenfactory.nebius.com/v1/chat/completions` and keeps the key out of the browser.

Hackathon: Nebius x NVIDIA Global AI Hackathon. Track: Coding and Agentic Engineering. Deadline Oct 30, 2026, 1:00pm EDT.

## Run

Create a key at https://tokenfactory.nebius.com/ (Google or GitHub login). Put it in the environment, not in the repo.

```bash
export NEBIUS_API_KEY=your-key
python3 server.py
```

`server.py` also reads `NEBIUS_API_KEY` from a gitignored `.env` file in this directory.

Open http://127.0.0.1:8000.

```bash
python3 -m unittest discover -s tests -v
```

Override the ids if the console shows a newer routing key:

```bash
export NEMOTRON_NANO=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
export NEMOTRON_SUPER=nvidia/nemotron-3-super-120b-a12b
```

## What to tell the form

Token Factory: onboarding is a Google login and one API key. The OpenAI-compatible base URL worked with no SDK. Nano is the right default for a short review. Super is worth the wait only when the first pass finds a behavior bug. I would build on it again for that split. I would not send every call to Ultra.

NVIDIA models: Nano followed the JSON instruction often enough to parse, including when it wrapped the object in a fence. Super got a shorter prompt that already contained Nano's issues, which is the point of the second pass.

## Devpost description

Two Speed reviews one Python function with NVIDIA Nemotron on Nebius Token Factory. Nano always runs. Super runs only when Nano reports a high-severity behavior bug or returns something that is not JSON. The page shows which model ran, the latency, and the token counts, so the split is visible instead of hidden behind one chat box.
