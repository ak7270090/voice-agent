// The demo player, the use-case conversations, the platform tabs, links from config.js and the
// theme preview.

const DEMOS = [
  {
    id: "voice",
    tab: "Booking by voice",
    title: "A patient books by voice",
    text: "The agent understands the request, checks the doctor's free times, reads the details back and books, while the live step lights up in the flow.",
    video: "media/voice-call.mp4",
    poster: "media/voice-call.jpg",
  },
  {
    id: "phone",
    tab: "Phone call",
    title: "A real phone call",
    text: "The phone rings, the agent answers, and the appointment lands in the doctor's calendar.",
    video: "media/phone-call.mp4",
    poster: "media/phone-call.jpg",
    // Optional: [{"at": seconds, "role": "agent" | "caller", "text": "..."}], highlighted in time.
    transcript: "media/phone-call.json",
  },
  {
    id: "campaign",
    tab: "Reminder campaign",
    title: "Tomorrow's patients, called in minutes",
    text: "Upload a contact list and start. Each patient ends with an outcome: confirmed, moved, voicemail left, not reached and retried, or skipped without consent.",
    video: "media/campaign.mp4",
    poster: "media/campaign.jpg",
  },
  {
    id: "build",
    tab: "Build an agent",
    title: "From a template to a live agent",
    text: "Pick a template, adjust what it says, add a rule to the flow, publish, and test it on the spot.",
    video: "media/build-agent.mp4",
    poster: "media/build-agent.jpg",
  },
];

// Real conversations from the demo workspace, shortened only by leaving lines out.
const USE_CASES = [
  {
    tab: "Appointment booking",
    text: "Answers every call, finds a free slot with the right doctor and books it.",
    title: "City Hospital receptionist",
    outcome: "booked",
    lines: [
      ["agent", "Welcome to City Hospital. How can I help you today?"],
      ["caller", "I want to book an appointment with the skin doctor."],
      ["agent", "Dr. Priya Mehta has free times on Wednesday: eleven, eleven thirty, twelve, twelve thirty, one, and half past one. Which time would you like?"],
      ["caller", "1:30 pm works."],
      ["agent", "To confirm: Test Patient, aged 30, with Dr. Priya Mehta on Wednesday 4 November at 13:30. Is that right?"],
      ["caller", "Yes."],
      ["agent", "Your appointment with Dr. Priya Mehta is booked for Wednesday at 13:30. Your booking ID is 27996422. Thank you for calling."],
    ],
  },
  {
    tab: "Appointment reminders",
    text: "Calls tomorrow's patients, confirms they are coming, or passes a change to the front desk.",
    title: "Appointment reminders",
    outcome: "reschedule requested",
    lines: [
      ["caller", "Hello."],
      ["agent", "Hi Ravi, I'm calling to remind you about your appointment tomorrow at four pm. Will you be coming?"],
      ["caller", "I can't come tomorrow, so please move the appointment."],
      ["agent", "No problem. The front desk will call you to find a new time. Goodbye."],
    ],
  },
  {
    tab: "Voicemail",
    text: "Knows a voicemail greeting from a person and leaves a short message instead.",
    title: "Appointment reminders",
    outcome: "voicemail left",
    lines: [
      ["caller", "Hi. You've reached Rohan Gupta. I can't take your call right now. Please leave your name and number after the tone."],
      ["agent", "Hello Rohan, this is City Hospital reminding you of your appointment tomorrow at 4 pm. Please call us if you need to change it. Goodbye."],
    ],
  },
  {
    tab: "Hand-off to a person",
    text: "Puts the caller through to your team the moment they ask for a person.",
    title: "City Hospital receptionist",
    outcome: "transferred",
    lines: [
      ["agent", "Welcome to City Hospital. How can I help you today?"],
      ["caller", "Can I talk to a person, please?"],
      ["agent", "Let me connect you to our front desk."],
    ],
  },
];

const STEPS = [
  {
    tab: "Build",
    title: "Design the conversation",
    points: [
      "Start from a template: booking, reminders, lead qualification",
      "Each step collects what it needs before moving on",
      "Connect a calendar so each doctor's real availability is used",
      "Publish when it's ready; every version is kept",
    ],
    image: "media/step-build.png",
  },
  {
    tab: "Test",
    title: "Talk to it before your callers do",
    points: [
      "Type or speak to the agent right inside the builder",
      "Watch the live step light up as the call moves",
      "Fix a step and try again in seconds",
    ],
    image: "media/step-test.png",
  },
  {
    tab: "Deploy",
    title: "Put it on a number or a list",
    points: [
      "Answer on your own numbers, or call out from them",
      "Run campaigns from a contact list with calling hours and retries",
      "Voicemail handled, and a person one step away",
    ],
    image: "media/step-deploy.png",
  },
  {
    tab: "Monitor",
    title: "See what happened on every call",
    points: [
      "Transcript, collected details and every action the agent took",
      "Summary, success and quality score after each call",
      "Cost per call, and what was sent to your other tools",
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

function setUpCases() {
  const root = document.querySelector("[data-cases]");
  const list = root.querySelector(".case-list");
  const title = root.querySelector(".chat-title");
  const outcome = root.querySelector(".chat-outcome");
  const lines = root.querySelector(".chat-lines");

  function show(index) {
    const useCase = USE_CASES[index];
    [...list.children].forEach((button, n) => button.setAttribute("aria-selected", String(n === index)));
    title.textContent = useCase.title;
    outcome.textContent = useCase.outcome;
    lines.replaceChildren(
      ...useCase.lines.map(([role, said]) => {
        const item = document.createElement("li");
        item.className = role;
        item.textContent = said;
        return item;
      }),
    );
  }

  USE_CASES.forEach((useCase, index) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.innerHTML = "<strong></strong><span></span>";
    button.querySelector("strong").textContent = useCase.tab;
    button.querySelector("span").textContent = useCase.text;
    button.addEventListener("click", () => show(index));
    list.append(button);
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
setUpCases();
setUpSteps();
