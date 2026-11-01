// The recorded-call player, the how-it-works tabs, links from config.js and the theme preview.

const DEMOS = [
  {
    id: "voice",
    tab: "Voice call",
    title: "A booking by voice, in the browser",
    text: "The caller speaks; the agent hears, checks the doctor's free times, reads the details back and books. The live step lights up in the flow.",
    video: "media/voice-call.mp4",
    poster: "media/voice-call.jpg",
  },
  {
    id: "phone",
    tab: "Phone call",
    title: "A real phone call",
    text: "A phone rings through a SIP trunk; the same agent answers and books the appointment into Cal.com.",
    video: "media/phone-call.mp4",
    poster: "media/phone-call.jpg",
    // Optional: [{"at": seconds, "role": "agent" | "caller", "text": "..."}], highlighted in time.
    transcript: "media/phone-call.json",
  },
  {
    id: "campaign",
    tab: "Campaign",
    title: "A reminder campaign from a CSV",
    text: "Upload contacts, start, and watch each one move to its outcome: confirmed, reschedule, voicemail, not answered and retried, or no consent.",
    video: "media/campaign.mp4",
    poster: "media/campaign.jpg",
  },
  {
    id: "build",
    tab: "Build an agent",
    title: "From a template to a published flow",
    text: "Pick a template, edit it, drag a rule into the flow, publish, and test it right there.",
    video: "media/build-agent.mp4",
    poster: "media/build-agent.jpg",
  },
];

const STEPS = [
  {
    tab: "Build",
    title: "Draw the conversation",
    points: [
      "Start from a template: clinic booking, reminders, lead qualification",
      "Steps collect fields; tools check free times and book",
      "A Cal.com tool books into each doctor's own calendar",
      "Publishing checks the flow and keeps every version",
    ],
    image: "media/step-build.png",
  },
  {
    tab: "Test",
    title: "Talk to it before anyone else does",
    points: [
      "Type or speak to the agent from the flow builder",
      "The live step lights up as the call moves",
      "Scenario runs replay real conversations with the real LLM",
    ],
    image: "media/step-test.png",
  },
  {
    tab: "Deploy",
    title: "Give it a number or a list",
    points: [
      "Inbound and outbound numbers over SIP trunks",
      "Campaigns from a CSV with calling windows, retries and consent",
      "Voicemail detection and transfer to a person",
    ],
    image: "media/step-deploy.png",
  },
  {
    tab: "Monitor",
    title: "See every call",
    points: [
      "Transcript, collected fields, tool calls and reply delay per turn",
      "Summary, success and a QA score from post-call analysis",
      "Cost per call, and what was sent to Slack, HubSpot or a webhook",
    ],
    image: "media/step-monitor.png",
  },
];

function setUpLinks() {
  const links = window.SHOWCASE ?? {};
  const targets = { console: links.consoleUrl, repository: links.repositoryUrl };
  document.querySelectorAll("[data-link]").forEach((anchor) => {
    const url = targets[anchor.dataset.link];
    if (url) {
      anchor.href = url;
      if (!url.startsWith("#")) anchor.target = "_blank";
    } else {
      anchor.hidden = true;
    }
  });
}

function setUpPlayer() {
  const root = document.querySelector("[data-player]");
  const tabs = root.querySelector(".player-tabs");
  const video = root.querySelector(".player-video");
  const missing = root.querySelector(".player-missing");
  const title = root.querySelector(".player-title");
  const text = root.querySelector(".player-text");
  const transcript = root.querySelector(".player-transcript");
  let lines = [];

  async function show(demo) {
    tabs.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-selected", String(button.dataset.id === demo.id));
    });
    title.textContent = demo.title;
    text.textContent = demo.text;
    transcript.replaceChildren();
    lines = [];
    const exists = await fetch(demo.video, { method: "HEAD" }).then((r) => r.ok, () => false);
    video.hidden = !exists;
    missing.hidden = exists;
    if (!exists) {
      video.removeAttribute("src");
      missing.textContent = "This recording is coming soon.";
      return;
    }
    video.poster = demo.poster;
    video.src = demo.video;
    if (demo.transcript) {
      lines = await fetch(demo.transcript).then((r) => (r.ok ? r.json() : []), () => []);
      transcript.replaceChildren(
        ...lines.map((line) => {
          const item = document.createElement("li");
          item.dataset.role = line.role;
          item.innerHTML = `<span class="who"></span><span class="said"></span>`;
          item.querySelector(".who").textContent = line.role === "agent" ? "Agent" : "Caller";
          item.querySelector(".said").textContent = line.text;
          item.addEventListener("click", () => {
            video.currentTime = line.at;
            video.play();
          });
          return item;
        }),
      );
    }
  }

  video.addEventListener("timeupdate", () => {
    const items = transcript.children;
    let current = -1;
    lines.forEach((line, index) => {
      if (line.at <= video.currentTime) current = index;
    });
    [...items].forEach((item, index) => item.classList.toggle("now", index === current));
    items[current]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });

  DEMOS.forEach((demo) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.dataset.id = demo.id;
    button.textContent = demo.tab;
    button.addEventListener("click", () => show(demo));
    tabs.append(button);
  });
  show(DEMOS[0]);
}

function setUpSteps() {
  const root = document.querySelector("[data-steps]");
  const tabs = root.querySelector(".step-tabs");
  const heading = root.querySelector(".step-copy h3");
  const list = root.querySelector(".step-copy ul");
  const image = root.querySelector(".step-shot img");

  function show(index) {
    const step = STEPS[index];
    [...tabs.children].forEach((button, n) => button.setAttribute("aria-selected", String(n === index)));
    heading.textContent = step.title;
    list.replaceChildren(
      ...step.points.map((point) => Object.assign(document.createElement("li"), { textContent: point })),
    );
    image.src = step.image;
    image.alt = `${step.tab}: ${step.title}`;
  }

  STEPS.forEach((step, index) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.innerHTML = `<span class="step-number">${index + 1}</span>`;
    button.append(step.tab);
    button.addEventListener("click", () => show(index));
    tabs.append(button);
  });
  show(0);
}

function setUpThemes() {
  const saved = new URLSearchParams(location.search).get("theme");
  const apply = (theme) => {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.themeChoice === theme));
    });
  };
  apply(saved ?? "studio");
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      apply(button.dataset.themeChoice);
      history.replaceState(null, "", `?theme=${button.dataset.themeChoice}${location.hash}`);
    });
  });
}

setUpLinks();
setUpThemes();
setUpPlayer();
setUpSteps();
